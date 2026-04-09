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
# 请确保您的本地环境中存在 get_token.py 文件及其对应的函数
from get_token import get_appid, get_appsecret, get_access_token


# ================= 1. 领星签名算法 =================
def get_lx_sign(all_params, app_id):
    """根据领星 API 文档实现的签名算法"""
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


# ================= 2. 核心逻辑 =================
async def get_mail_detail(app_id, access_token, uuid):
    """获取邮件详情数据"""
    url = "https://openapi.lingxing.com/erp/sc/data/mail/detail"
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
    # 获取授权信息
    app_id, app_secret = get_appid(), get_appsecret()
    access_token = get_access_token(app_id, app_secret)
    email_to_check = "solaryusa@163.com"

    now = datetime.now()
    # 扩大搜索范围至最近 3 天，确保覆盖 24 小时未回复的邮件
    start_date = (now - timedelta(days=3)).strftime('%Y-%m-%d')
    end_date = now.strftime('%Y-%m-%d')

    # --- 关键词配置 (根据文档截图优化) ---
    # 1. 无需关注：多为系统自动生成的订单或物流通知
    exclude_keywords = [
        "配送", "已配送", "承运人", "Shipment", "Delivered", "Carrier",
        "Sold", "shipped", "Advertising Invoice", "已从卖家账户扣除",
        "Payment initiated", "秒杀建议", "优惠券"
    ]

    # 2. 重点关注：账号风险、审核、绩效及索赔
    priority_keywords = [
        "A-to-Z", "Chargeback", "Claim", "Performance", "Safety", "Action Required",
        "Removal", "Restricted", "Lost", "KYC", "停用", "Deactivated", "CASE",
        "身份验证", "Identity Verification", "Violation", "Warning", "绩效", "侵权",
        "Policy Warning", "Reactivate", "合规性", "Compliance"
    ]

    # 初始化报告分类
    report_order = ["inbox", "atoz", "official", "external"]
    categories = {
        "inbox": {"name": "站内信(超24h未回复)", "list": []},
        "atoz": {"name": "A-to-Z & Chargeback (索赔)", "list": []},
        "official": {"name": "亚马逊重要通知/绩效", "list": []},
        "external": {"name": "其他业务邮件", "list": []}
    }

    # 获取邮件列表
    list_url = "https://openapi.lingxing.com/erp/sc/data/mail/lists"
    biz_list = {
        "flag": "receive",
        "email": email_to_check,
        "start_date": start_date,
        "end_date": end_date,
        "offset": 0,
        "length": 500
    }
    query_list = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    query_list["sign"] = get_lx_sign({**biz_list, **query_list}, app_id)

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(list_url, params=query_list, json=biz_list, timeout=25)
            mail_items = res.json().get('data', [])
        except Exception as e:
            print(f"获取邮件列表失败: {e}")
            return

    processed_keys = set()
    for item in mail_items:
        subject = item.get('subject', '')
        uuid = item.get('webmail_uuid')
        unique_key = f"{subject}_{email_to_check}"

        # 过滤已处理或属于“无需查看”类别的邮件
        if unique_key in processed_keys or any(kw in subject for kw in exclude_keywords):
            continue

        # 获取邮件详细分类信息
        detail = await get_mail_detail(app_id, access_token, uuid)
        if not detail:
            continue

        processed_keys.add(unique_key)
        # 领星 type 字段：1 站内信，2 亚马逊邮件
        mail_type = str(detail.get('type', '3'))
        mail_date_str = detail.get('date', '')
        mail_date = datetime.strptime(mail_date_str, '%Y-%m-%d %H:%M:%S') if mail_date_str else now
        mail_info = {"date": mail_date_str, "subject": subject}

        # 执行分类逻辑
        # 1. 站内信：仅提醒收到超过 24 小时且未回复的邮件
        if mail_type == "1":
            if (now - mail_date).total_seconds() > 86400:
                categories["inbox"]["list"].append(mail_info)

        # 2. A-to-Z / 索赔类
        elif any(kw.lower() in subject.lower() for kw in ["a-to-z", "chargeback", "claim"]):
            categories["atoz"]["list"].append(mail_info)

        # 3. 亚马逊重要通知 (类型 2 或 包含重点关键词)
        elif mail_type == "2" or any(kw.lower() in subject.lower() for kw in [k.lower() for k in priority_keywords]):
            categories["official"]["list"].append(mail_info)

        # 4. 其他
        else:
            categories["external"]["list"].append(mail_info)

        await asyncio.sleep(0.1)  # 避免请求过快导致接口限流

    # ================= 3. 控制台输出报告 =================
    print(f"\n{'=' * 20} 亚马逊巡查报告 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) {'=' * 20}")
    for key in report_order:
        cat = categories[key]
        count = len(cat['list'])
        print(f"\n【{cat['name']}】")
        print(f"查询邮箱：{email_to_check}")
        print(f"待处理条数：{count}")
        print("-" * 50)

        if count == 0:
            print("(当前分类下暂无需要关注的邮件)")
        else:
            # 按时间从新到旧排序
            sorted_mails = sorted(cat['list'], key=lambda x: x['date'], reverse=True)
            for m in sorted_mails[:20]:  # 每个分类最多显示 20 封
                print(f"[{m['date']}] {m['subject']}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())