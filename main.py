from get_access_token import get_token, load_config

config = load_config()
cid = config.get("corp_id")
secret = config.get("corp_secret")

if __name__ == '__main__':
    # 获取 access_token
    access_token = get_token(cid, secret)


    # chat_id = 'your_chat_id'  # 替换为群聊的 chat_id
    #
    # messages, next_cursor = get_chat_history(access_token, chat_id)
    # print("消息记录:", messages)
    # print("下一页游标:", next_cursor)

