import asyncio
import httpx
import json
import time
import hashlib
import hmac
import base64
import urllib.parse
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# 注意：确保本地有 get_token 模块提供授权信息
# from get_token import get_appid, get_appsecret, get_access_token

# ================= 1. 工具函数 =================

def get_lx_sign(all_params, app_id):
    """领星API签名加密逻辑"""
    sorted_keys = sorted(all_params.keys())
    kv_pairs = []
    for k in sorted_keys:
        v = all_params[k]
        if v == "" or v is None: continue
        if isinstance(v, (list, dict)):
            v = json.dumps(v, separators=(',', ':'), ensure_ascii=False)
        kv_pairs.append(f"{k}={v}")

    sign_str = "&".join(kv_pairs)
    md5_val = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()
    
    # AES 加密
    key_bytes = app_id.encode('utf-8').ljust(16, b'\0')[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_data = pad(md5_val.encode('utf-8'), AES.block_size, style='pkcs7')
    aes_bytes = cipher.encrypt(padded_data)
    return base64.b64encode(aes_bytes).decode('utf-8')


async def send_dingtalk_notification(content, webhook_url, secret=None):
    """发送钉钉通知（支持签名校验）"""
    url = webhook_url

    if secret and "your_secret" not in secret:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    headers = {"Content-Type": "application/json"}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "评价处理通知",
            "text": content
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, timeout=10)
            return response.json()
        except Exception as e:
            print(f"钉钉推送网络异常: {e}")
            return None


# ================= 2. 接口交互逻辑 =================

async def get_sid_list(app_id, access_token):
    """获取所有店铺 SID"""
    url = "https://openapi.example.com/api/get_shops" # 已脱敏
    params = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    params["sign"] = get_lx_sign(params, app_id)
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, params=params, timeout=15)
            data = res.json().get('data', [])
            return [item['sid'] for item in data] if data else []
        except Exception as e:
            print(f"获取 SID 列表失败: {e}")
            return []


# ================= 3. 核心提取逻辑 =================

async def fetch_low_star_reviews():
    # 配置信息（请填入真实信息）
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=your_token"
    secret = "your_secret"

    # 获取凭证（此处逻辑假设你已有 get_token 模块）
    # app_id = get_appid()
    # access_token = get_access_token(app_id, get_appsecret())
    app_id = "YOUR_APP_ID"
    access_token = "YOUR_ACCESS_TOKEN"

    url = "https://openapi.example.com/api/review/list" # 已脱敏

    # 时间区间计算
    now_time = datetime.now()
    today_str = now_time.strftime('%Y-%m-%d %H:%M:%S')
    start_date_obj = now_time - timedelta(days=90)
    api_end_date = now_time.strftime('%Y-%m-%d')
    api_start_date = start_date_obj.strftime('%Y-%m-%d')

    print("-" * 50)
    print(f"当前时间: {today_str}")
    print(f"查询区间: {api_start_date} 至 {api_end_date}")
    print("-" * 50)

    sids = await get_sid_list(app_id, access_token)
    if not sids:
        print("未获取到店铺SID，程序终止")
        return

    all_pending_items = []

    async with httpx.AsyncClient() as client:
        for sid in sids:
            offset = 0
            while True:
                biz_params = {
                    "sid": int(sid),
                    "start_date": api_start_date,
                    "end_date": api_end_date,
                    "offset": offset,
                    "length": 100,
                    "date_field": "review_date"
                }

                query_params = {
                    "access_token": access_token,
                    "app_key": app_id,
                    "timestamp": str(int(time.time()))
                }
                query_params["sign"] = get_lx_sign({**biz_params, **query_params}, app_id)

                try:
                    response = await client.post(url, params=query_params, json=biz_params, timeout=15)
                    res_json = response.json()

                    if res_json.get('code') != 0:
                        break

                    data_list = res_json.get('data', [])
                    if not data_list: break

                    for item in data_list:
                        star = item.get('last_star')
                        status = str(item.get('status'))
                        
                        # 核心过滤逻辑：状态 0 为待处理，过滤 1-3 星
                        if status == "0" and star is not None and 1 <= int(star) <= 3:
                            review_data = {
                                "asin": item.get('asin', 'N/A'),
                                "review_id": item.get('review_id', 'N/A'),
                                "star": star,
                                "date": item.get('review_date', 'N/A'),
                                "url": item.get('review_url', '无链接'),
                                "content": item.get('last_content', '无内容').replace('\n', ' ')
                            }
                            all_pending_items.append(review_data)
                            print(f"[发现差评] SID: {sid} | ASIN: {review_data['asin']} | {star}星")

                    offset += 100
                    if len(data_list) < 100: break # 数据取完，跳出分页
                except Exception as e:
                    print(f"请求 SID {sid} 异常: {e}")
                    break

    # ================= 4. 推送逻辑 =================

    total_count = len(all_pending_items)
    if total_count > 0:
        # 分批推送，防止钉钉单条消息过长
        batch_size = 20
        for i in range(0, total_count, batch_size):
            batch = all_pending_items[i: i + batch_size]

            ding_msg = f"### 领星 Review 待处理评价提醒 ({i + 1}-{min(i + batch_size, total_count)}/{total_count})\n"
            ding_msg += f"当前时间: {today_str}\n"
            ding_msg += f"查询区间: {api_start_date} ~ {api_end_date}\n\n"

            for info in batch:
                ding_msg += (
                    f"---\n"
                    f"- ASIN: {info['asin']}\n"
                    f"- 星级: {info['star']}星\n"
                    f"- 评价时间: {info['date']}\n"
                    f"- 内容摘要: {info['content'][:150]}...\n"
                    f"- [点击查看评价]({info['url']})\n"
                )

            await send_dingtalk_notification(ding_msg, webhook_url, secret)
            await asyncio.sleep(1.2) # 避免触发钉钉流控
    else:
        print("查询完成: 系统中没有符合条件的待处理差评。")


if __name__ == "__main__":
    asyncio.run(fetch_low_star_reviews())
