import asyncio
import httpx
import json
import time
import hashlib
import base64
import hmac
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from get_token import get_appid, get_appsecret, get_access_token

# ================= 1. 配置信息 =================
DING_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=your_accesstoken"
DING_SECRET = "your_secret"
EMAIL_TO_CHECK = "your_email"


def send_dingtalk_raw(content):
    timestamp = str(round(time.time() * 1000))
    secret_enc = DING_SECRET.encode('utf-8')
    string_to_sign = f'{timestamp}\n{DING_SECRET}'
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    url = f"{DING_WEBHOOK}&timestamp={timestamp}&sign={sign}"
    payload = {"msgtype": "text", "text": {"content": content}}
    try:
        with httpx.Client() as client:
            client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    except Exception as e:
        print(f"钉钉发送失败: {str(e)}")


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
    return base64.b64encode(cipher.encrypt(padded_data)).decode('utf-8')


async def get_mail_detail(app_id, access_token, uuid):
    url = "https://openapi.lingxing.com/your_url"
    biz_params = {"webmail_uuid": uuid}
    query_params = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    query_params["sign"] = get_lx_sign({**biz_params, **query_params}, app_id)
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, params=query_params, json=biz_params, timeout=10)
            return res.json().get('data', {})
        except:
            return None


async def main():
    app_id, app_secret = get_appid(), get_appsecret()
    access_token = get_access_token(app_id, app_secret)

    # 获取当前时间，计算出24小时前的时间
    now = datetime.now()
    start_time = now - timedelta(hours=24)
    start_date = start_time.strftime('%Y-%m-%d')  # 查询的开始时间
    end_date = now.strftime('%Y-%m-%d')  # 查询的结束时间

    unreplied_list = []

    list_url = "https://openapi.lingxing.com/your_url"
    biz_list = {"flag": "receive", "email": EMAIL_TO_CHECK, "start_date": start_date, "end_date": end_date, "offset": 0,
                "length": 200}  # 可以根据需求调整每次查询的长度
    query_list = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    query_list["sign"] = get_lx_sign({**biz_list, **query_list}, app_id)

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(list_url, params=query_list, json=biz_list, timeout=25)
            mail_items = res.json().get('data', [])
        except Exception as e:
            print(f"邮件列表获取失败: {e}")
            return

    for item in mail_items:
        uuid = item.get('webmail_uuid')
        detail = await get_mail_detail(app_id, access_token, uuid)
        if not detail:
            continue

        m_type = str(detail.get('type', ''))
        m_receive_date = detail.get('receive_date', detail.get('date', ''))
        m_reply_date = detail.get('reply_date')
        subject = detail.get('subject', '')

        if m_type == "1":  # 仅站内信
            if not m_receive_date: continue
            receive_dt = datetime.strptime(m_receive_date, '%Y-%m-%d %H:%M:%S')

            # 24小时内 且 reply_date 为空
            if (now - receive_dt) <= timedelta(hours=24):
                if not m_reply_date or str(m_reply_date).strip() == "":
                    unreplied_list.append(f"主题: {subject}, 收到时间: {m_receive_date}")

        await asyncio.sleep(0.1)

    if unreplied_list:
        # 生成报告内容
        report_msg = "亚马逊巡查报告 - 站内信超时未回复(24H)\n"
        report_msg += "----------------------------\n"
        for info in unreplied_list:
            report_msg += f"{info}\n"
        report_msg += "----------------------------\n"
        report_msg += f"统计时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"

        # 打印报告到终端
        print("亚马逊巡查报告 - 站内信超时未回复(24H)")
        print("----------------------------")
        for info in unreplied_list:
            print(info)
        print("----------------------------")
        print(f"统计时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")

        # 发送报告到钉钉
        send_dingtalk_raw(report_msg)


if __name__ == "__main__":
    asyncio.run(main())
