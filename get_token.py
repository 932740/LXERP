import requests
import json

def get_appid():
    """从配置文件读取 appId"""
    try:
        with open('config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
        return config.get('app_id', 'YOUR_APP_ID')
    except Exception as e:
        print(f"读取 appId 失败: {str(e)}")
        return None

def get_appsecret():
    """从配置文件读取 appSecret"""
    try:
        with open('config.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
        return config.get('app_secret', 'YOUR_APP_SECRET')
    except Exception as e:
        print(f"读取 appSecret 失败: {str(e)}")
        return None

def get_access_token(app_id, app_secret):
    """通过 API 获取 access_token"""
    # 占位 URL，实际使用时请替换为真实的接口地址
    url = "https://openapi.example.com/api/token"

    # 准备请求负载
    data = {
        "appId": app_id,
        "appSecret": app_secret
    }

    # 设置请求头
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        # 发起 POST 请求
        response = requests.post(url, data=data, headers=headers, timeout=10)

        # 检查 HTTP 状态码
        if response.status_code == 200:
            try:
                response_data = response.json()

                # 解析 access_token
                if 'data' in response_data and 'access_token' in response_data['data']:
                    return response_data['data']['access_token']
                else:
                    error_msg = response_data.get('msg', 'Unknown error')
                    raise Exception(f"API Error: {error_msg}")
            except ValueError:
                raise Exception("Error parsing JSON response.")
        else:
            raise Exception(f"Request failed with status code {response.status_code}")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Request error: {str(e)}")

if __name__ == '__main__':
    # 示例运行逻辑
    try:
        current_app_id = get_appid()
        current_app_secret = get_appsecret()
        
        if current_app_id and current_app_secret:
            token = get_access_token(current_app_id, current_app_secret)
            print(f"Access Token: {token}")
    except Exception as e:
        print(f"Error: {str(e)}")
