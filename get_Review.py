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
from get_token import * # 确保同级目录下有 get_token.py

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
    key_bytes = app_id.encode('utf-8').ljust(16, b'\0')[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_data = pad(md5_val.encode('utf-8'), AES.block_size, style='pkcs7')
    aes_bytes = cipher.encrypt(padded_data)
    return base64.b64encode(aes_bytes).decode('utf-8')


async def send_dingtalk_notification(content, webhook_url, secret=None):
    """发送钉钉通知"""
    url = webhook_url

    if secret:
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


# ================= 2. 获取店铺SID =================

async def get_sid_list(app_id, app_secret, access_token):
    """获取所有店铺sid"""
    url = "https://openapi.lingxing.com/erp/sc/data/seller/lists"
    params = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    params["sign"] = get_lx_sign(params, app_id)
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, params=params, timeout=15)
            data = res.json().get('data', [])
            return [item['sid'] for item in data] if data else []
        except Exception as e:
            print(f"获取SID列表失败: {e}")
            return []


# ================= 3. 核心提取逻辑 =================

async def fetch_low_star_reviews():
    # 配置信息
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=2c4b9d154756b89b4440f60d00585ab5f42bfbbd18b8c6492e7ec62b668a0405"
    secret = "SEC4b2a55321b2ed0fa86ef70cfd4d6dfdd9cb2c05b8da37ab5437194088c87245d"

    app_id = get_appid()
    app_secret = get_appsecret()
    access_token = get_access_token(app_id, app_secret)

    url = "https://openapi.lingxing.com/erp/sc/v2/data/mws/reviews"

    # 时间记录
    now_time = datetime.now()
    today_str = now_time.strftime('%Y-%m-%d %H:%M:%S')
    start_date_obj = now_time - timedelta(days=90)
    api_end_date = now_time.strftime('%Y-%m-%d')
    api_start_date = start_date_obj.strftime('%Y-%m-%d')

    # 终端输出当前状态
    print("-" * 50)
    print(f"当前时间: {today_str}")
    print(f"查询区间: {api_start_date} 至 {api_end_date}")
    print(f"任务类型: 领星Review(评论) 差评提取")
    print("-" * 50)

    sids = await get_sid_list(app_id, app_secret, access_token)
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
                        print(f"SID {sid} 接口返回错误: {res_json.get('message')}")
                        break

                    data_list = res_json.get('data', [])
                    if not data_list:
                        break

                    for item in data_list:
                        star = item.get('last_star')
                        status = str(item.get('status'))
                        # 状态 0 代表待处理，过滤 1-3 星
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
                            print(f"[匹配差评] ASIN: {review_data['asin']} | 星级: {review_data['star']}星 | 时间: {review_data['date']}")

                    offset += 100
                except Exception as e:
                    print(f"请求SID {sid} 失败: {e}")
                    break

    total_count = len(all_pending_items)
    print("-" * 50)
    print(f"统计完成: 共发现 {total_count} 条记录")
    print("-" * 50)

    # ================= 4. 推送逻辑 =================

    if total_count > 0:
        batch_size = 20
        for i in range(0, total_count, batch_size):
            batch = all_pending_items[i: i + batch_size]

            ding_msg = f"### 领星Review待处理评价提醒 ({i + 1}-{min(i + batch_size, total_count)}/{total_count})\n"
            ding_msg += f"当前时间: {today_str}\n"
            ding_msg += f"数据查询区间: {api_start_date} ~ {api_end_date}\n\n"

            for info in batch:
                ding_msg += (
                    f"---\n"
                    f"- ASIN: {info['asin']}\n"
                    f"- 星级: {info['star']}星\n"
                    f"- 评价时间: {info['date']}\n"
                    f"- 评价内容: {info['content'][:150]}...\n"
                    f"- 评论链接: {info['url']}\n"
                )

            print(f"正在推送第 {i // batch_size + 1} 段数据至钉钉...")
            result = await send_dingtalk_notification(ding_msg, webhook_url, secret)
            print(f"推送结果: {result}")
            await asyncio.sleep(1.2)
    else:
        print("\n查询完成: 系统中没有符合条件的待处理差评。")
        ding_msg = (
            f"### 领星Review差评查询提醒\n\n"
            f"当前时间: {today_str}\n"
            f"数据查询区间: {api_start_date} ~ {api_end_date}\n\n"
            f"提示: 系统中没有符合条件的待处理差评。"
        )
        result = await send_dingtalk_notification(ding_msg, webhook_url, secret)
        print(f"推送结果: {result}")


if __name__ == "__main__":
    asyncio.run(fetch_low_star_reviews())