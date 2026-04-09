import logging
from fastapi import FastAPI, Request, Response
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.enterprise import parse_message, create_reply
from wechatpy.enterprise.client import WeChatClient
# 假设 get_access_token 模块提供 load_config 功能
# from get_access_token import load_config

# --- 配置加载 ---
# 建议将敏感信息存储在 config.json 或环境变量中
# config = load_config()
# cid = config.get("corp_id")

CONFIG = {
    "corp_id": "YOUR_CORP_ID",
    "secret": "YOUR_SECRET",
    "token": "YOUR_TOKEN",
    "aes_key": "YOUR_AES_KEY",
    "agent_id": "YOUR_AGENT_ID"
}

app = FastAPI()
logging.basicConfig(level=logging.INFO)

# 初始化 SDK 客户端（用于主动发送消息、下载媒体文件等）
client = WeChatClient(CONFIG["corp_id"], CONFIG["secret"])
# 初始化加密器（用于被动接收并解密回调消息）
crypto = WeChatCrypto(CONFIG["token"], CONFIG["aes_key"], CONFIG["corp_id"])

@app.get("/wework")
async def verify(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    """
    企业微信后台配置 URL 时的首次验证逻辑（GET 请求）
    """
    try:
        # 校验签名并解密 echostr
        echo_str = crypto.check_signature(msg_signature, timestamp, nonce, echostr)
        return Response(content=echo_str)
    except InvalidSignatureException:
        logging.error("Signature verification failed")
        return Response(content="Invalid Signature", status_code=403)

@app.post("/wework")
async def handle_msg(request: Request, msg_signature: str, timestamp: str, nonce: str):
    """
    处理企业微信推送的消息及事件（POST 请求）
    """
    body = await request.body()
    try:
        # 1. 解密 XML 消息内容
        decrypted_xml = crypto.decrypt_message(body, msg_signature, timestamp, nonce)
        msg = parse_message(decrypted_xml)

        # 2. 根据消息类型执行对应逻辑
        if msg.type == 'text':
            logging.info(f"Received text message: {msg.content} from source: {msg.source}")
            # 业务逻辑：处理文本内容

        elif msg.type == 'file':
            logging.info(f"Received file message, MediaID: {msg.media_id}")
            
            # 3. 下载文件逻辑
            # 注意：媒体文件在企业微信服务器仅保存 3 天
            file_response = client.media.get(msg.media_id)
            
            # 建议根据实际业务需求处理文件名和后缀
            file_path = f"./downloads/{msg.media_id}.bin"
            with open(file_path, "wb") as f:
                f.write(file_response.content)
            
            logging.info(f"File saved to: {file_path}")

            # 4. 如需回复消息，可使用 create_reply
            # reply = create_reply("File received", msg)
            # return Response(content=crypto.encrypt_message(reply.render(), nonce, timestamp))

        # 必须返回字符串 "success" 告知企业微信服务器已正常接收
        return Response(content="success")
    
    except Exception as e:
        logging.error(f"Processing failed: {e}")
        return Response(content="error", status_code=500)

if __name__ == "__main__":
    import uvicorn
    # 生产环境建议通过配置文件管理端口和地址
    uvicorn.run(app, host="0.0.0.0", port=8000)
