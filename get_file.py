import logging
from fastapi import FastAPI, Request, Response
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.enterprise import parse_message, create_reply
from wechatpy.enterprise.client import WeChatClient
from get_access_token import load_config

config = load_config()
cid = config.get("corp_id")

# --- 配置区 ---
CONFIG = {
    "corp_id": cid,
    "secret": "eU2Xx75I6chJDYOPsh7GEK7skKavuM5cF1cKCZM5Dnk",
    "token": "E4e9Hr8KnUlZ",
    "aes_key": "F4Qmvverguv5VMGiFoM9eCwoHY7aVFxUZSi0J5177Lw",
    "agent_id": "1000002"
}

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# 初始化 SDK 客户端（用于主动发送消息/下载文件）
client = WeChatClient(CONFIG["corp_id"], CONFIG["secret"])
# 初始化加密器（用于被动接收消息）
crypto = WeChatCrypto(CONFIG["token"], CONFIG["aes_key"], CONFIG["corp_id"])


@app.get("/wework")
async def verify(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    """
    企业微信后台配置 URL 时的首次验证逻辑
    """
    try:
        echo_str = crypto.check_signature(msg_signature, timestamp, nonce, echostr)
        return Response(content=echo_str)
    except InvalidSignatureException:
        return Response(content="Invalid Signature", status_code=403)


@app.post("/wework")
async def handle_msg(request: Request, msg_signature: str, timestamp: str, nonce: str):
    """
    接收外部群消息及文件的核心逻辑
    """
    body = await request.body()
    try:
        # 1. 解密 XML 消息
        decrypted_xml = crypto.decrypt_message(body, msg_signature, timestamp, nonce)
        msg = parse_message(decrypted_xml)

        # 2. 处理不同类型的消息
        if msg.type == 'text':
            logging.info(f"收到文本消息: {msg.content} 来自群: {msg.source}")
            # 可以在这里写逻辑，比如回复一个“收到”

        elif msg.type == 'file':
            logging.info(f"收到文件消息，FileID: {msg.media_id}")
            # 3. 下载文件逻辑
            file_response = client.media.get(msg.media_id)
            file_path = f"./downloads/{msg.media_id}.bin"  # 实际建议根据文件名后缀保存
            with open(file_path, "wb") as f:
                f.write(file_response.content)
            logging.info(f"文件已保存至: {file_path}")

            # 4. 如果需要发回群里（示例：上传后再发送）
            # r = client.media.upload('file', open(file_path, 'rb'))
            # client.message.send_file(msg.agent_id, msg.source, r['media_id'])

        return Response(content="success")  # 必须返回 success 告知企业微信已收到
    except Exception as e:
        logging.error(f"处理失败: {e}")
        return Response(content="error", status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)