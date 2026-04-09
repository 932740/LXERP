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
from get_token import *

# ================= 钉钉配置 =================
# 替换为你自己的 Webhook 地址
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=your_token"
# 如果你在机器人安全设置里开启了“加签”，填入密钥；没开则留空
DINGTALK_SECRET = "your_secret"

# ================= 1. 签名算法 =================
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


# ================= 2. 钉钉消息推送函数 =================
async def send_dingtalk_msg(content):
    url = DINGTALK_WEBHOOK
    if DINGTALK_SECRET:
        timestamp = str(round(time.time() * 1000))
        secret_enc = DINGTALK_SECRET.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, DINGTALK_SECRET)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "店铺风控巡查",
            "text": content
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.json().get("errcode") == 0:
                print("钉钉消息推送成功")
            else:
                print(f"钉钉推送失败: {resp.text}")
        except Exception as e:
            print(f"钉钉请求异常: {e}")


# ================= 3. 获取店铺名称映射 =================
async def get_shop_name_map(app_id, app_secret):
    url = "https://openapi.lingxing.com/your_url"
    access_token = get_access_token(app_id, app_secret)
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


# ================= 4. 风控筛选逻辑 =================
def filter_problematic_stores(store_list, name_map):
    problem_stores = []
    for store in store_list:
        reasons = []
        sid_str = str(store.get('sid'))
        store['shop_name'] = name_map.get(sid_str, f"未知店铺(SID:{sid_str})")

        def to_float(val):
            if val == "-" or val is None: return 0.0
            try:
                return float(str(val).replace('%', ''))
            except:
                return 0.0

        # --- 提取 ahr 参数 ---
        ahr_status = str(store.get('ahr_status', '')).upper()
        ahr_score = str(store.get('ahr_score', '0'))

        # 风险判定逻辑
        if ahr_status and ahr_status not in ['GREAT', 'HEALTHY', 'GOOD']:
            reasons.append(f"账户状况评级异常({ahr_status})")

        # 其他指标判定
        if int(store.get('commodity_policy_compliance', 0)) > 0:
            reasons.append(f"政策合规性异常({store['commodity_policy_compliance']})")
        if to_float(store.get('late_shipment', '0')) >= 4.0:
            reasons.append(f"迟发率过高({store['late_shipment']}%)")
        if to_float(store.get('invoice_defect', '0')) >= 5.0:
            reasons.append(f"发票缺陷率过高({store['invoice_defect']}%)")

        tracking_rate = to_float(store.get('valid_tracking', '100'))
        if tracking_rate < 95.0 and store.get('valid_tracking') != "-":
            reasons.append(f"有效追踪率过低({store['valid_tracking']}%)")

        if reasons:
            # 整合异常原因，支持分数展示
            store['problem_reasons_str'] = ", ".join(reasons)
            store['ahr_status'] = ahr_status
            store['ahr_score'] = ahr_score
            problem_stores.append(store)
    return problem_stores


# ================= 5. 主程序 =================
async def main():
    app_id = get_appid()
    app_secret = get_appsecret()
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"正在巡查日期: {target_date}")

    name_map = await get_shop_name_map(app_id, app_secret)

    url = "https://openapi.lingxing.com/your_url"
    access_token = get_access_token(app_id, app_secret)
    biz_params = {"offset": 0, "length": 100, "search_field_time": "pull_date", "search_time": target_date}
    query_params = {"access_token": access_token, "app_key": app_id, "timestamp": str(int(time.time()))}
    query_params["sign"] = get_lx_sign({**biz_params, **query_params}, app_id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, params=query_params, json=biz_params, timeout=15)
            result = response.json()

            if result.get('code') == 0:
                bad_stores = filter_problematic_stores(result.get('data', []), name_map)

                if bad_stores:
                    msg_md = ""
                    for s in bad_stores:
                        # 按照图片要求的列表格式构造
                        msg_md += f"* **店铺**: {s['shop_name']}\n"
                        msg_md += f"* **账户状况**: 分数 {s['ahr_score']} / 评级 {s['ahr_status']}\n"
                        msg_md += f"* **异常**: {s['problem_reasons_str']}\n"
                        msg_md += f"* **更新时间**: {s['update_date']}\n\n"
                        msg_md += "---\n\n"

                    await send_dingtalk_msg(msg_md)
                    print(f"已推送 {len(bad_stores)} 个异常店铺")
                else:
                    print("未发现异常")
            else:
                print(f"查询失败: {result.get('message')}")
        except Exception as e:
            print(f"执行异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())
