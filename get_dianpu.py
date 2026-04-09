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
# 确保 get_token.py 存在并包含 get_appid, get_appsecret, get_access_token
# from get_token import *

# ================= 钉钉配置 =================
# 钉钉 Webhook 地址中的 access_token
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=your_token"
# 钉钉机器人安全设置中的加签密钥
DINGTALK_SECRET = "your_secret"

# ================= 1. 领星 API 签名算法 =================
def get_lx_sign(all_params, app_id):
    """
    领星 ERP 开放平台签名逻辑：参数排序 -> MD5 -> AES加密 -> Base64
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


# ================= 2. 钉钉推送逻辑 =================
async def send_dingtalk_msg(content):
    """
    发送钉钉 Markdown 消息
    """
    url = DINGTALK_WEBHOOK
    if DINGTALK_SECRET and "your_secret" not in DINGTALK_SECRET:
        timestamp = str(round(time.time() * 1000))
        secret_enc = DINGTALK_SECRET.encode('utf-8')
        string_to_sign = f'{timestamp}\n{DINGTALK_SECRET}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "店铺风控巡查报告",
            "text": content
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, timeout=10)
            if resp.json().get("errcode") == 0:
                print("DingTalk notification sent successfully.")
            else:
                print(f"DingTalk error: {resp.text}")
        except Exception as e:
            print(f"DingTalk network error: {e}")


# ================= 3. 获取店铺名称映射 =================
async def get_shop_name_map(app_id, app_secret):
    """
    获取 SID 到店铺名称的映射关系
    """
    url = "https://openapi.example.com/api/shops" # 占位路径
    # access_token = get_access_token(app_id, app_secret)
    access_token = "YOUR_ACCESS_TOKEN" 
    
    params = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    params["sign"] = get_lx_sign(params, app_id)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=15)
            res_data = response.json()
            if res_data.get('code') == 0:
                return {str(item['sid']): item['name'] for item in res_data.get('data', [])}
        except:
            pass
    return {}


# ================= 4. 风控判别核心逻辑 =================
def filter_problematic_stores(store_list, name_map):
    """
    根据业务规则筛选异常店铺
    """
    problem_stores = []
    for store in store_list:
        reasons = []
        sid_str = str(store.get('sid'))
        store['shop_name'] = name_map.get(sid_str, f"Unknown(SID:{sid_str})")

        def to_float(val):
            if val == "-" or val is None: return 0.0
            try:
                return float(str(val).replace('%', ''))
            except:
                return 0.0

        # AHR 账户状况参数
        ahr_status = str(store.get('ahr_status', '')).upper()
        ahr_score = str(store.get('ahr_score', '0'))

        # 1. 账户评级非健康状态
        if ahr_status and ahr_status not in ['GREAT', 'HEALTHY', 'GOOD']:
            reasons.append(f"账户评级异常({ahr_status})")

        # 2. 政策合规性投诉 > 0
        if int(store.get('commodity_policy_compliance', 0)) > 0:
            reasons.append(f"合规性异常({store['commodity_policy_compliance']})")
        
        # 3. 迟发率判定 (阈值 4.0%)
        if to_float(store.get('late_shipment', '0')) >= 4.0:
            reasons.append(f"迟发率过高({store['late_shipment']}%)")
        
        # 4. 发票缺陷率判定 (阈值 5.0%)
        if to_float(store.get('invoice_defect', '0')) >= 5.0:
            reasons.append(f"发票缺陷率过高({store['invoice_defect']}%)")

        # 5. 有效追踪率判定 (阈值 95.0%)
        tracking_rate = to_float(store.get('valid_tracking', '100'))
        if tracking_rate < 95.0 and store.get('valid_tracking') != "-":
            reasons.append(f"追踪率过低({store['valid_tracking']}%)")

        if reasons:
            store['problem_reasons_str'] = ", ".join(reasons)
            store['ahr_status'] = ahr_status
            store['ahr_score'] = ahr_score
            problem_stores.append(store)
    return problem_stores


# ================= 5. 任务主循环 =================
async def main():
    # app_id = get_appid()
    # app_secret = get_appsecret()
    app_id = "YOUR_APP_ID"
    app_secret = "YOUR_APP_SECRET"
    
    # 默认巡查昨天的数据
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Task Started: Inspecting data for {target_date}")

    name_map = await get_shop_name_map(app_id, app_secret)

    # 风控数据接口地址
    url = "https://openapi.example.com/api/risk_data" # 占位路径
    # access_token = get_access_token(app_id, app_secret)
    access_token = "YOUR_ACCESS_TOKEN"

    biz_params = {
        "offset": 0, 
        "length": 100, 
        "search_field_time": "pull_date", 
        "search_time": target_date
    }
    query_params = {
        "access_token": access_token, 
        "app_key": app_id, 
        "timestamp": str(int(time.time()))
    }
    query_params["sign"] = get_lx_sign({**biz_params, **query_params}, app_id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, params=query_params, json=biz_params, timeout=15)
            result = response.json()

            if result.get('code') == 0:
                bad_stores = filter_problematic_stores(result.get('data', []), name_map)

                if bad_stores:
                    msg_md = "### 亚马逊风控巡查异常提醒\n\n"
                    msg_md += f"巡查日期: {target_date}\n\n---\n\n"
                    
                    for s in bad_stores:
                        msg_md += f"* **店铺**: {s['shop_name']}\n"
                        msg_md += f"* **账户状况**: 分数 {s['ahr_score']} / 评级 {s['ahr_status']}\n"
                        msg_md += f"* **异常原因**: {s['problem_reasons_str']}\n"
                        msg_md += f"* **数据更新**: {s.get('update_date', 'N/A')}\n\n"
                        msg_md += "---\n\n"

                    await send_dingtalk_msg(msg_md)
                    print(f"Report sent. Found {len(bad_stores)} problematic stores.")
                else:
                    print("No risk detected.")
            else:
                print(f"API Error: {result.get('message')}")
        except Exception as e:
            print(f"Task Execution Failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
