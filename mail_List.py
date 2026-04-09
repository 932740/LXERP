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
DING_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=your_token"
DING_SECRET = "your_secret"

# 排除关键词
EXCLUDE_KEYWORDS = ["Sold, ship now", "Order shipment confirmation", "订单发货确认", "订单购买",
                    "Amazon.com has shipped", "Survey", "调查问卷"]

# 重点关注关键词
URGENT_KEYWORDS = ["Performance", "Warning", "Listing", "Account Health", "业绩", "政策", "安全", "货件丢失", "缺损",
                   "无在售"]

# A-to-Z 固定发件人
ATOZ_SENDER = "atoz-guarantee-no-reply@amazon.com"


def send_dingtalk_raw(content):
    """发送纯文本钉钉消息"""
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
    """领星签名逻辑"""
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
    """获取邮件详情，用于获取发件人等关键字段"""
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


# ================= 2. 核心巡查逻辑 =================
async def main():
    app_id, app_secret = get_appid(), get_appsecret()
    access_token = get_access_token(app_id, app_secret)
    email_to_check = "solaryusa@163.com"

    # 动态获取本周日期范围
    now = datetime.now()
    this_monday = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
    today_str = now.strftime('%Y-%m-%d')

    categories = {
        "atoz": {"name": "A-to-Z 紧急索赔告警", "list": []},
        "important_amazon": {"name": "亚马逊重要绩效/异常通知", "list": []}
    }

    # 获取邮件列表
    list_url = "https://openapi.lingxing.com/your_url"
    biz_list = {"flag": "receive", "email": email_to_check, "start_date": this_monday, "end_date": today_str,
                "offset": 0, "length": 200}
    query_list = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    query_list["sign"] = get_lx_sign({**biz_list, **query_list}, app_id)

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(list_url, params=query_list, json=biz_list, timeout=25)
            mail_items = res.json().get('data', [])
        except:
            return

    for item in mail_items:
        uuid = item.get('webmail_uuid')
        subject = item.get('subject', '')

        # 排除关键词过滤
        if any(kw.lower() in subject.lower() for kw in EXCLUDE_KEYWORDS):
            continue

        # 调用详情接口获取完整字段（包括 type, sender_email, reply_date 等）
        detail = await get_mail_detail(app_id, access_token, uuid)
        if not detail:
            continue

        m_id = detail.get('id')
        m_type = str(detail.get('type', ''))
        m_sender = detail.get('sender_email', detail.get('from', ''))
        m_receive_date = detail.get('receive_date', detail.get('date', ''))
        m_reply_date = detail.get('reply_date')  # 响应时间

        # 过滤类型，只处理 Type 2（亚马逊官方邮件）
        if m_type != "2":
            continue

        if not m_receive_date: continue
        receive_dt = datetime.strptime(m_receive_date, '%Y-%m-%d %H:%M:%S')

        # 逻辑 3：亚马逊邮件判断 (Type 2) - 本周内符合条件的
        # A：固定发件人地址判断 (A-to-Z)
        if m_sender and ATOZ_SENDER.lower() in m_sender.lower():
            categories["atoz"]["list"].append(f"[{m_receive_date}] 主题:{subject}")

        # B：邮件主题关键词判断
        elif any(kw.lower() in subject.lower() for kw in URGENT_KEYWORDS):
            categories["important_amazon"]["list"].append(f"[{m_receive_date}] 主题:{subject}")

        # 这里的等待是为了防止请求过快被接口限制
        await asyncio.sleep(0.05)

    # ================= 3. 发送报告 =================
    for key in ["atoz", "important_amazon"]:
        cat = categories[key]
        if not cat['list']: continue

        report_msg = f"亚马逊巡查报告 - {cat['name']}\n"
        report_msg += "----------------------------\n"
        for info in cat['list'][:15]:
            report_msg += f"{info}\n"
        report_msg += "----------------------------\n"
        report_msg += f"统计时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"

        send_dingtalk_raw(report_msg)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
