import requests
from datetime import datetime, timedelta
# 假设 get_token 模块提供以下函数
# from get_token import get_access_token, get_appid, get_appsecret
import time
import hashlib

# 生成签名 sign（保持原逻辑：使用 access_token、app_key、timestamp 进行哈希处理）
def generate_sign(access_token, app_key, timestamp):
    sign_str = f"{access_token}{app_key}{timestamp}"
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

# 使用 token 查询 FBA 发货单
def get_fba_shipment_data(token, start_date, end_date, status=0):
    # 占位 URL，实际使用时请替换为真实的接口地址
    url = "https://openapi.example.com/api/fba/shipment"

    # 获取 app_key 和 app_id
    app_key = "YOUR_APP_KEY" # 实际应通过 get_appid() 获取

    # 当前时间戳
    timestamp = str(int(time.time()))

    # 生成签名 sign
    sign = generate_sign(token, app_key, timestamp)

    # 构建请求参数
    params = {
        "search_value": "待发货",
        "search_field": "shipment_sn",
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "length": 100,
        "access_token": token,
        "sign": sign,
        "timestamp": timestamp,
        "app_key": app_key
    }

    # 打印请求信息用于调试
    print(f"Request URL: {url}")
    print(f"Request Params: {params}")

    # 发送 GET 请求
    response = requests.get(url, params=params, timeout=15)

    print(f"Response Status Code: {response.status_code}")

    if response.status_code == 200:
        try:
            response_data = response.json()
            
            # 检查返回的数据格式
            if isinstance(response_data, dict) and 'data' in response_data and response_data['data'] is not None:
                return response_data['data']
            else:
                raise Exception(f"Unexpected response format: {response_data}")
        except ValueError:
            raise Exception("Response content is not valid JSON.")
    else:
        print(f"Error response from API: {response.text}")
        raise Exception(f"Request failed with error: {response.text}")

# 获取最近 30 天的时间范围
def get_last_30_days():
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    return start_date, end_date

if __name__ == '__main__':
    # 获取 token（需确保 get_token 逻辑正确）
    # token = get_access_token("YOUR_APP_ID", "YOUR_APP_SECRET")
    token = "YOUR_ACCESS_TOKEN"

    # 用户交互输入日期
    custom_start_date = input("Enter start date (YYYY-MM-DD) or press Enter to use last 30 days: ").strip()
    custom_end_date = input("Enter end date (YYYY-MM-DD) or press Enter to use today: ").strip()

    if not custom_start_date or not custom_end_date:
        start_date, end_date = get_last_30_days()
    else:
        start_date = custom_start_date
        end_date = custom_end_date

    # 状态筛选：0 为待发货
    status = 0

    try:
        # 调用接口获取 FBA 发货单数据
        fba_shipment_data = get_fba_shipment_data(token, start_date, end_date, status)

        # 遍历并打印单据信息
        if fba_shipment_data:
            for shipment in fba_shipment_data:
                print(f"发货单号: {shipment.get('shipment_no')}, SKU: {shipment.get('sku')}, "
                      f"物流中心编码: {shipment.get('logistics_center_code')}, 日期: {shipment.get('date')}, "
                      f"店铺: {shipment.get('shop_name')}, 货件单号: {shipment.get('shipment_id')}")
        else:
            print("未查询到相关发货单据信息。")

    except Exception as e:
        print(f"Error: {str(e)}")
