import requests
import json
import sys

# ================= 1. 配置加载 =================
def load_config(file_path='config.json'):
    """
    从本地 JSON 文件读取配置
    建议 config.json 包含 {"corp_id": "...", "corp_secret": "..."}
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误: 找不到配置文件 {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"错误: {file_path} 格式不正确，请检查 JSON 语法")
        sys.exit(1)

# ================= 2. 接口交互 =================
def get_token(corp_id, corp_secret):
    """
    向企业微信服务器请求 access_token
    """
    # 已替换为占位 URL，实际使用时请查阅官方文档
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken" 
    params = {
        "corpid": corp_id,
        "corpsecret": corp_secret
    }

    try:
        # 使用 timeout 防止脚本无限期挂起
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('errcode') == 0:
            return data.get('access_token')
        else:
            print(f"API 返回错误: {data.get('errmsg')} (错误码: {data.get('errcode')})")
            return None

    except requests.exceptions.RequestException as e:
        print(f"网络请求失败: {e}")
        return None

# ================= 3. 主程序 =================
if __name__ == '__main__':
    # 1. 加载配置（建议将敏感信息放在外部 config.json 并加入 .gitignore）
    config = load_config()
    cid = config.get("corp_id")
    secret = config.get("corp_secret")

    if not cid or not secret:
        print("错误: 配置文件中缺少 corp_id 或 corp_secret")
        sys.exit(1)

    # 2. 获取 Token
    print("正在连接企业微信 API...")
    token = get_token(cid, secret)

    # 3. 输出结果
    if token:
        print("-" * 30)
        print(f"成功获取 Token: \n{token}")
        print("-" * 30)
    else:
        print("获取 Token 失败，请检查企业 ID、凭证或网络连通性。")
