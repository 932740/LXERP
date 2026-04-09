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
from get_token import *

# ================= 钉钉配置区 =================
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=2c4b9d154756b89b4440f60d00585ab5f42bfbbd18b8c6492e7ec62b668a0405"
DINGTALK_SECRET = "SEC4b2a55321b2ed0fa86ef70cfd4d6dfdd9cb2c05b8da37ab5437194088c87245d"


async def send_dingtalk_notification(content):
    """
    钉钉机器人推送模块
    """
    url = DINGTALK_WEBHOOK

    if DINGTALK_SECRET:
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


# ================= 原有逻辑区 =================

def get_lx_sign(all_params, app_id):
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
    key_bytes = app_id.encode('utf-8').ljust(16, b'\0')[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_data = pad(md5_val.encode('utf-8'), AES.block_size, style='pkcs7')
    aes_bytes = cipher.encrypt(padded_data)
    return base64.b64encode(aes_bytes).decode('utf-8')


async def get_sid_list(app_id, app_secret):
    url = "https://openapi.lingxing.com/erp/sc/data/seller/lists"
    access_token = get_access_token(app_id, app_secret)
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
    app_id = get_appid()
    app_secret = get_appsecret()
    access_token = get_access_token(app_id, app_secret)
    url = "https://openapi.lingxing.com/erp/sc/cs/feedback/listMws"

    # 获取当前时间
    now_time = datetime.now()
    today_str = now_time.strftime('%Y-%m-%d %H:%M:%S')
    end_date = now_time.strftime('%Y-%m-%d')

    # 计算90天前的日期
    days_ago = now_time - timedelta(days=90)
    start_date = days_ago.strftime('%Y-%m-%d')

    # 终端输出当前状态
    print("-" * 50)
    print(f"当前时间: {today_str}")
    print(f"查询区间: {start_date} 至 {end_date}")
    print(f"任务类型: 领星Feedback(店铺) 差评提取")
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
                    raw_star = item.get('star') or item.get('rating') or 0
                    star_val = int(raw_star)
                    status_val = item.get('status')
                    feedback_date = item.get('feedback_date')

                    # 过滤 1-3 星且状态为未处理(0)
                    if 1 <= star_val <= 3 and str(status_val) == "0" and feedback_date:
                        feedback_date_obj = datetime.strptime(feedback_date, '%Y-%m-%d')

                        if feedback_date_obj >= days_ago:
                            status_text = "待处理"
                            order_id = item.get('amazon_order_id')
                            seller_name = item.get('seller_name')
                            country = item.get('country')
                            content = item.get('feedback_content') or item.get('comment') or "(无评论内容)"

                            feedback_msg = (
                                f"- 订单号: {order_id}\n"
                                f"- 店铺名称: {seller_name}\n"
                                f"- 国家: {country}\n"
                                f"- 星级: {star_val}星\n"
                                f"- 处理状态: {status_text}\n"
                                f"- 评论内容: {content}\n"
                                f"- 评论时间: {feedback_date}\n"
                                f"-------------------------------------------------------------------\n"
                            )

                            print(f"[发现记录] 订单: {order_id} | 时间: {feedback_date}")
                            all_feedback_msg.append(feedback_msg)
            except:
                continue

    # 推送逻辑
    if all_feedback_msg:
        print(f"\n查询完成: 发现 {len(all_feedback_msg)} 条记录，正在推送...")
        ding_msg = (
            f"### 领星Feedback（店铺）1-3星待处理评价提醒\n\n"
            f"当前时间: {today_str}\n"
            f"数据查询区间: {start_date} ~ {end_date}\n\n"
            f"{''.join(all_feedback_msg)}"
        )
    else:
        print("\n查询完成: 暂无待处理1-3星评价。")
        ding_msg = (
            f"### 领星Feedback（店铺）1-3星待处理评价提醒\n\n"
            f"当前时间: {today_str}\n"
            f"数据查询区间: {start_date} ~ {end_date}\n\n"
            f"提示: 暂无待处理1-3星评价。"
        )

    result = await send_dingtalk_notification(ding_msg)
    print(f"推送结果: {result}")


if __name__ == "__main__":
    asyncio.run(fetch_feedback_final_v2())