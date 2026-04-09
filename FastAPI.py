import logging
import uvicorn
from fastapi import FastAPI, Request, Query, Response
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise import parse_message
from wechatpy.exceptions import InvalidSignatureException

# 确保 get_access_token.py 与此文件在同一目录下
from get_access_token import load_config

# 1. 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# 2. 加载配置（建议将 Token 和 AES_KEY 也写入 config.json）
config = load_config()
CORP_ID = config.get("corp_id")
TOKEN = config.get("token") or "E4e9Hr8KnUlZ"
ENCODING_AES_KEY = config.get("aes_key") or "eU2Xx75I6chJDYOPsh7GEK7skKavuM5cF1cKCZM5Dnk"

# 初始化加密器
crypto = WeChatCrypto(TOKEN, ENCODING_AES_KEY, CORP_ID)


@app.get("/wework")
async def verify(
        msg_signature: str = Query(...),
        timestamp: str = Query(...),
        nonce: str = Query(...),
        echostr: str = Query(...)
):
    """
    企业微信验证接口 (GET)
    """
    try:
        # 解密微信发来的验证字符串
        echo_str = crypto.check_signature(msg_signature, timestamp, nonce, echostr)
        # 注意：echo_str 是 bytes，Response 会自动处理
        return Response(content=echo_str)
    except InvalidSignatureException:
        logger.error("签名验证失败，请检查 Token 和 AESKey")
        return Response(content="Invalid Signature", status_code=403)
    except Exception as e:
        logger.error(f"验证过程出错: {e}")
        return Response(content="Error", status_code=500)


@app.post("/wework")
async def handle_message(
        request: Request,
        msg_signature: str = Query(...),
        timestamp: str = Query(...),
        nonce: str = Query(...)
):
    """
    接收实际消息接口 (POST)
    """
    body = await request.body()
    try:
        # 1. 解密 XML 数据
        decrypted_xml = crypto.decrypt_message(body, msg_signature, timestamp, nonce)
        # 2. 解析为消息对象
        msg = parse_message(decrypted_xml)

        # 3. 提取关键信息
        # 外部群消息的关键字段是 chat_id
        chat_id = getattr(msg, 'chat_id', '非群聊消息')
        from_user = msg.source
        msg_type = msg.type

        logger.info("=" * 30)
        logger.info(f"收到类型: {msg_type}")
        logger.info(f"发送人ID: {from_user}")
        logger.info(f"群聊ID (ChatID): {chat_id}")

        if msg_type == 'text':
            logger.info(f"消息内容: {msg.content}")
        elif msg_type == 'file':
            logger.info(f"文件名: {getattr(msg, 'file_name', '未知')}")
            logger.info(f"MediaID: {msg.media_id}")

        logger.info("=" * 30)

        # 4. 必须给微信服务器返回 "success"
        return Response(content="success")
    except Exception as e:
        logger.error(f"解析消息失败: {e}")
        return Response(content="error", status_code=500)


if __name__ == "__main__":
    # 5. 启动服务
    # host="0.0.0.0" 表示监听所有网卡，以便公网访问
    # port=8000 是你打算在后台填写的端口
    logger.info(f"服务启动中，监听端口 80...")
    uvicorn.run(app, host="0.0.0.0", port=80)