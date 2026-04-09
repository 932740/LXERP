import requests
import json
import sys


def load_config(file_path='config.json'):
    """读取并返回配置字典"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误: 找不到配置文件 {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误: {file_path} 格式不正确，请检查 JSON 语法")
        sys.exit(1)


def get_token(corp_id, corp_secret):
    """获取并返回 access_token"""
    url = "https://qyapi.weixin.qq.com/your_token"
    params = {
        "corpid": corp_id,
        "corpsecret": corp_secret
    }

    try:
        # 使用 params 参数更安全，requests 会自动处理 URL 编码
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('errcode') == 0:
            return data.get('access_token')
        else:
            print(f"企业微信返回错误: {data.get('errmsg')} (错误码: {data.get('errcode')})")
            return None

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}")
        return None


if __name__ == '__main__':
    # 1. 加载配置（只读一次文件）
    config = load_config()
    cid = config.get("corp_id")
    secret = config.get("corp_secret")

    # 2. 获取 Token
    token = get_token(cid, secret)

    # 3. 输出结果
    if token:
        print(f"成功获取 Token: \n{token}")
    else:
        print("获取 Token 失败，请检查配置或网络。")
