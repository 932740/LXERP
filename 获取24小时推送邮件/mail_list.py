import asyncio
import httpx
import json
import time
import hashlib
import base64
import hmac
import os
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from get_token import get_appid, get_appsecret, get_access_token

# ================= 1. 配置与管理类 =================

class MailStatistics:
    SEEN_IDS_FILE = "seen_mail_uuids.json"
    TARGET_SENDER = "atoz-guarantee-no-reply@amazon.com"
    
    # 钉钉机器人配置（已脱敏）
    DING_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN"
    DING_SECRET = "YOUR_SECRET_HERE"

    # 排除关键字清单
    EXCLUDE_KEYWORDS = [
        "订单配送", "亚马逊物流收货货件", "登记", "入库", 
        "亚马逊已配送您售出的商品", "调查问卷", "商品发货", 
        "Amazon has shipped your sold item(s)", 
        "Your Amazon ca Fulement by Amazon Merchant Invoice for",
        "配送订单", "您的订单已配送", "Amazon Transparency", "透明计划",
        "Your FBA request is complete", "Fulfillment by Amazon Merchant Credit Note",
        "Votre Avoir", "Votre Avoir Expédié Par Amazon", "您符合享受 MCF 首选定价优惠的条件", "已售出，即将发运"
    ]

    @staticmethod
    def load_history():
        if os.path.exists(MailStatistics.SEEN_IDS_FILE):
            try:
                with open(MailStatistics.SEEN_IDS_FILE, 'r') as f:
                    return set(json.load(f))
            except: return set()
        return set()

    @staticmethod
    def save_history(uuids):
        with open(MailStatistics.SEEN_IDS_FILE, 'w') as f:
            json.dump(list(uuids)[-1000:], f)

# ================= 2. 核心功能方法 =================

def send_dingtalk_notification(title, markdown_content):
    """加签模式钉钉推送 (Markdown类型)"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = MailStatistics.DING_SECRET.encode('utf-8')
    string_to_sign = f'{timestamp}\n{MailStatistics.DING_SECRET}'
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')

    url = f"{MailStatistics.DING_WEBHOOK}&timestamp={timestamp}&sign={sign}"
    
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": markdown_content
        }
    }
    try:
        with httpx.Client() as client:
            client.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    except Exception as e:
        print(f"钉钉推送失败: {str(e)}")

async def get_raw_mails_24h():
    """获取24H原始邮件列表"""
    try:
        app_id, app_secret = get_appid(), get_appsecret()
        access_token = get_access_token(app_id, app_secret)
    except Exception as e:
        print(f"授权失败: {e}")
        return [], "", ""

    now = datetime.now()
    time_24h_ago = now - timedelta(hours=24)
    start_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = now.strftime('%Y-%m-%d')

    all_raw = []
    offset = 0
    async with httpx.AsyncClient() as client:
        while True:
            biz_params = {
                "flag": "receive", 
                "email": "your_email@example.com", # 已替换
                "start_date": start_date, 
                "end_date": end_date, 
                "offset": offset, 
                "length": 100
            }
            query_params = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
            query_params["sign"] = get_lx_sign({**biz_params, **query_params}, app_id)
            
            res = await client.post("https://openapi.lingxing.com/erp/sc/data/mail/lists", params=query_params, json=biz_params)
            data = res.json().get('data', [])
            if not data: break
            
            for item in data:
                try:
                    m_date = datetime.strptime(item.get('date', ''), '%Y-%m-%d %H:%M:%S')
                    if m_date >= time_24h_ago: all_raw.append(item)
                except: continue
            
            if len(data) < 100: break
            offset += 100
    return all_raw, start_date, end_date

def filter_new_and_recent_mails(raw_mails):
    """筛选、分类、过滤、去重逻辑"""
    seen_uuids = MailStatistics.load_history()
    updated_uuids = seen_uuids.copy()
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)

    new_atoz_24h = []   
    new_other_24h = []  
    new_1h_count = 0    

    for mail in raw_mails:
        uuid = mail.get('webmail_uuid')
        subject = mail.get('subject', '')
        sender = (mail.get('from_address') or "").lower()
        m_date_str = mail.get('date', '')

        if any(kw.lower() in subject.lower() for kw in MailStatistics.EXCLUDE_KEYWORDS): 
            continue
            
        if uuid not in seen_uuids:
            if sender == MailStatistics.TARGET_SENDER.lower():
                new_atoz_24h.append(subject)
            else:
                new_other_24h.append(subject)
            
            updated_uuids.add(uuid)
            try:
                if datetime.strptime(m_date_str, '%Y-%m-%d %H:%M:%S') >= one_hour_ago:
                    new_1h_count += 1
            except: continue

    MailStatistics.save_history(updated_uuids)
    return new_atoz_24h, new_other_24h, new_1h_count

# ================= 3. 执行入口 =================

async def main():
    now_dt = datetime.now()
    now_str = now_dt.strftime('%Y-%m-%d %H:%M:%S')
    
    raw_mails, s_date, e_date = await get_raw_mails_24h()
    new_atoz, new_other, count_1h = filter_new_and_recent_mails(raw_mails)

    total_new = len(new_atoz) + len(new_other)
    atoz_total = len([m for m in raw_mails if (m.get('from_address') or "").lower() == MailStatistics.TARGET_SENDER.lower()])
    
    print("=" * 60)
    print(f"终端报告 - {now_str}")
    print(f"1. 24小时内系统总邮件数: {len(raw_mails)}")
    print(f"2. AtoZ邮件总数: {atoz_total}")
    print(f"3. 收到新邮件: {total_new}")
    print(f"4. 一小时内新收到邮件: {count_1h}")
    print("-" * 60)

    if new_atoz:
        detail = "\n".join([f"- {s}" for s in new_atoz])
        ding_content = f"**【紧急】收到 Amazon AtoZ 邮件**\n\n时间：{now_str}\n\n立即处理！\n\n【邮件明细】\n{detail}"
        send_dingtalk_notification("紧急提醒", ding_content)
    
    elif new_other:
        detail = "\n".join([f"- {s}" for s in new_other])
        ding_content = f"**【提醒】收到新邮件**\n\n时间：{now_str}\n\n请查收详情\n\n【邮件明细】\n{detail}"
        send_dingtalk_notification("新邮件提醒", ding_content)
    
    else:
        ding_content = f"**【报告】亚马逊邮件巡查报告**\n\n时间：{now_str}\n\n暂未收到新邮件。"
        send_dingtalk_notification("巡查报告", ding_content)

    print("执行完毕。")

def get_lx_sign(all_params, app_id):
    sorted_keys = sorted(all_params.keys())
    kv_pairs = [f"{k}={all_params[k]}" for k in sorted_keys if all_params[k] is not None]
    sign_str = "&".join(kv_pairs)
    md5_val = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()
    key_bytes = app_id.encode('utf-8').ljust(16, b'\0')[:16]
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_data = pad(md5_val.encode('utf-8'), AES.block_size, style='pkcs7')
    return base64.b64encode(cipher.encrypt(padded_data)).decode('utf-8')

if __name__ == "__main__":
    asyncio.run(main())
