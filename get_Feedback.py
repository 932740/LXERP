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
# 注意：此模块需在本地环境中存在，或将 get_appid 等逻辑整合进代码
# from get_token import * # ================= 钉钉配置区 =================
# 请在此处填写你的钉钉机器人配置
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=your_token"
DINGTALK_SECRET = "your_secret"


async def send_dingtalk_notification(content):
    """
    钉钉机器人推送模块 (Markdown 格式)
    """
    url = DINGTALK_WEBHOOK

    if DINGTALK_SECRET and "your_secret" not in DINGTALK_SECRET:
        timestamp = str(round(time.time() * 1000))
        secret_enc = DINGTALK_SECRET.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, DINGTALK_SECRET)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign}"

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
            print(f"推送失败: {e}")
            return None


# ================= 通用逻辑区 =================

def get_lx_sign(all_params, app_id):
    """
    ERP 接口 MD5 + AES 签名逻辑
    """
    sorted_keys = sorted(all_params.keys())
    kv_pairs = []
    for k in sorted_keys:
        v = all_params[k]
        if v == "" or v is None:
            if v is None: kv_pairs.append(f"{k}=null")
            continue
        if isinstance(v, (list, dict)):
            v = json.dumps(v, separators=(',', ':'), ensure_ascii=False)
        kv_pairs.append(f"{k}={v}")
    
    sign_str = "&".join(kv_pairs)
    md5_val = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()
    
    # AES ECB 模式加密
    key_bytes = app_id.encode('utf-8').ljust(16, b'\0')[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_data = pad(md5_val.encode('utf-8'), AES.block_size, style='pkcs7')
    aes_bytes = cipher.encrypt(padded_data)
    return base64.b64encode(aes_bytes).decode('utf-8')


async def get_sid_list(app_id, app_secret):
    """
    获取名下所有的店铺 ID (SID)
    """
    url = "https://openapi.example.com/api/get_shops" # 已替换为占位路径
    # 假设 get_access_token 已在 get_token.py 中定义
    # access_token = get_access_token(app_id, app_secret)
    access_token = "YOUR_ACCESS_TOKEN" 
    
    params = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    params["sign"] = get_lx_sign(params, app_id)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15)
            res_data = response.json()
            if res_data.get('code') == 0:
                return [item['sid'] for item in res_data.get('data', [])]
        except:
            pass
    return []


async def fetch_feedback_final_v2():
    """
    差评提取核心任务
    """
    # 凭证获取逻辑需根据实际情况填入
    # app_id = get_appid()
    # app_secret = get_appsecret()
    # access_token = get_access_token(app_id, app_secret)
    app_id = "YOUR_APP_ID"
    app_secret = "YOUR_APP_SECRET"
    access_token = "YOUR_ACCESS_TOKEN"

    url = "https://openapi.example.com/api/feedback/query" # 已替换为占位路径

    # 时间区间计算
    now_time = datetime.now()
    today_str = now_time.strftime('%Y-%m-%d %H:%M:%S')
    end_date = now_time.strftime('%Y-%m-%d')
    days_ago = now_time - timedelta(days=90) # 90天回溯
    start_date = days_ago.strftime('%Y-%m-%d')

    print("-" * 50)
    print(f"任务启动: {today_str}")
    print(f"数据区间: {start_date} 至 {end_date}")
    print("-" * 50)

    sids = await get_sid_list(app_id, app_secret)
    all_feedback_msg = []

    async with httpx.AsyncClient() as client:
        for sid in sids:
            biz_params = {
                "sid": sid,
                "start_date": start_date,
                "end_date": end_date,
                "offset": 0,
                "length": 100
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
                data_list = res_json.get('data', [])

                if isinstance(data_list, dict):
                    data_list = data_list.get('list', [])

                if not data_list: continue

                for item in data_list:
                    # 兼容不同接口的字段命名
                    raw_star = item.get('star') or item.get('rating') or 0
                    star_val = int(raw_star)
                    status_val = item.get('status')
                    feedback_date = item.get('feedback_date')

                    # 业务规则：过滤 1-3 星且状态为未处理 (status 0)
                    if 1 <= star_val <= 3 and str(status_val) == "0" and feedback_date:
                        feedback_date_obj = datetime.strptime(feedback_date, '%Y-%m-%d')

                        if feedback_date_obj >= days_ago:
                            order_id = item.get('amazon_order_id')
                            seller_name = item.get('seller_name')
                            country = item.get('country')
                            content = item.get('feedback_content') or item.get('comment') or "(无评论内容)"

                            msg_block = (
                                f"- 订单号: {order_id}\n"
                                f"- 店铺名称: {seller_name}\n"
                                f"- 国家: {country}\n"
                                f"- 星级: {star_val}星\n"
                                f"- 处理状态: 待处理\n"
                                f"- 评论内容: {content}\n"
                                f"- 评论时间: {feedback_date}\n"
                                f"-------------------------------------------------------------------\n"
                            )

                            print(f"[发现记录] 店铺: {seller_name} | 订单: {order_id}")
                            all_feedback_msg.append(msg_block)
            except Exception as e:
                print(f"SID {sid} 查询异常: {e}")
                continue

    # 推送逻辑
    if all_feedback_msg:
        print(f"\n查询完成: 发现 {len(all_feedback_msg)} 条记录，正在推送报告...")
        ding_msg = (
            f"### 差评反馈（Feedback）待处理提醒\n\n"
            f"当前时间: {today_str}\n"
            f"数据查询区间: {start_date} ~ {end_date}\n\n"
            f"{''.join(all_feedback_msg)}"
        )
    else:
        print("\n查询完成: 暂无待处理评价。")
        ding_msg = (
            f"### 差评反馈（Feedback）待处理提醒\n\n"
            f"当前时间: {today_str}\n"
            f"提示: 暂无符合条件的待处理差评。"
        )

    result = await send_dingtalk_notification(ding_msg)
    print(f"推送完成，接口返回: {result}")


if __name__ == "__main__":
    asyncio.run(fetch_feedback_final_v2())
