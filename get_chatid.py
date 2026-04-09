import requests
from get_access_token import load_config, get_token


def fetch_external_chat_ids():
    # 1. 加载配置和获取 Token
    config = load_config()
    token = get_token(config["corp_id"], config["corp_secret"])

    if not token:
        print("获取 Token 失败")
        return

    # 2. 获取该应用可见范围内的所有外部群列表
    # 接口文档：https://developer.work.weixin.qq.com/document/path/92120
    list_url = f"https://qyapi.weixin.qq.com/cgi-bin/externalcontact/groupchat/list?access_token={token}"

    # 筛选条件：0表示全部
    payload = {
        "status_filter": 0,
        "limit": 100
    }

    try:
        res = requests.post(list_url, json=payload)
        data = res.json()

        if data.get("errcode") != 0:
            print(f"获取群列表失败: {data.get('errmsg')}")
            return

        chat_ids = data.get("group_chat_list", [])
        print(f"--- 成功发现 {len(chat_ids)} 个外部群 ---")

        # 3. 循环获取每个群的详细信息（为了拿到群名）
        for item in chat_ids:
            cid = item["chat_id"]
            detail_url = f"https://qyapi.weixin.qq.com/cgi-bin/externalcontact/groupchat/get?access_token={token}"
            detail_res = requests.post(detail_url, json={"chat_id": cid}).json()

            if detail_res.get("errcode") == 0:
                group_info = detail_res.get("group_chat", {})
                name = group_info.get("group_name", "未命名群聊")
                owner = group_info.get("owner", "未知群主")
                print(f"群名: {name} | 群主ID: {owner} | ChatID: {cid}")
            else:
                print(f"获取群 {cid} 详情失败")

    except Exception as e:
        print(f"运行出错: {e}")


if __name__ == "__main__":
    fetch_external_chat_ids()