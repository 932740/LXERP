import requests
from datetime import datetime, timedelta
from get_token import get_access_token, get_appid, get_appsecret
import time
import hashlib

# 生成签名 sign（假设签名需要用 access_token、app_key、timestamp 进行哈希处理）
def generate_sign(access_token, app_key, timestamp):
    sign_str = f"{access_token}{app_key}{timestamp}"
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

# 使用 token 查询 FBA 发货单
def get_fba_shipment_data(token, start_date, end_date, status=0):
    url = "https://openapi.lingxing.com/your_url"

    # 获取 app_key 和 app_id
    app_key = get_appid()  # 假设这个函数返回 app_key

    # 当前时间戳
    timestamp = str(int(time.time()))  # 获取当前时间戳

    # 生成签名 sign
    sign = generate_sign(token, app_key, timestamp)

    # 构建请求参数
    params = {
        "search_value": "待发货",  # 查询发货状态为待发货的单据
        "search_field": "shipment_sn",  # 可根据需求更改为 sku 或 shipment_id
        "status": status,  # 0: 待发货
        "start_date": start_date,
        "end_date": end_date,
        "length": 100,  # 可以根据需要调整查询的长度
        "access_token": token,  # 添加 access_token
        "sign": sign,  # 添加 sign
        "timestamp": timestamp,  # 添加 timestamp
        "app_key": app_key  # 添加 app_key
    }

    # 打印请求的 URL 和参数，帮助调试
    print(f"Request URL: {url}")
    print(f"Request Params: {params}")

    # 发送 GET 请求（因为查询参数是通过 URL 传递的）
    response = requests.get(url, params=params)

    print(f"Response Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")

    if response.status_code == 200:
        try:
            # 尝试将响应转换为 JSON 格式
            response_data = response.json()
            print("Response Data (JSON):", response_data)  # 打印返回的数据格式

            # 检查返回的数据是否是字典
            if isinstance(response_data, dict) and 'data' in response_data and response_data['data'] is not None:
                return response_data['data']
            else:
                raise Exception(f"Unexpected response format: {response_data}")
        except ValueError:
            raise Exception("Response content is not valid JSON.")
    else:
        # 如果 API 返回错误，直接打印响应内容
        print(f"Error response from API: {response.text}")
        raise Exception(f"Request failed with error: {response.text}")

# 获取最近30天的数据
def get_last_30_days():
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    return start_date, end_date

if __name__ == '__main__':
    # 获取 token
    token = get_access_token(get_appid(), get_appsecret())  # 获取 token

    # 自定义日期，如果没有输入，使用最近30天
    custom_start_date = input("Enter start date (YYYY-MM-DD) or press Enter to use last 30 days: ").strip()
    custom_end_date = input("Enter end date (YYYY-MM-DD) or press Enter to use today: ").strip()

    if not custom_start_date or not custom_end_date:
        # 如果用户没有输入日期，使用最近30天
        start_date, end_date = get_last_30_days()
    else:
        # 如果用户输入了日期，使用自定义日期
        start_date = custom_start_date
        end_date = custom_end_date

    # 自定义状态，0 为待发货，1 为待配货
    status = 0  # 修改为 1 可以查询待配货的单据

    try:
        # 获取发货状态为待发货的 FBA 发货单
        fba_shipment_data = get_fba_shipment_data(token, start_date, end_date, status)

        # 打印待发货单据信息
        for shipment in fba_shipment_data:
            print(f"发货单号: {shipment.get('shipment_no')}, SKU: {shipment.get('sku')}, "
                  f"物流中心编码: {shipment.get('logistics_center_code')}, 日期: {shipment.get('date')}, "
                  f"店铺: {shipment.get('shop_name')}, 货件单号: {shipment.get('shipment_id')}")

    except Exception as e:
        print(f"Error: {str(e)}")
