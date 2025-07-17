from fastapi import FastAPI, Request
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# 各種キーの読み込み
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
openai_api_key = os.getenv("OPENAI_API_KEY")

configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    # ここに好きな返答を入れてください
    reply_text = f"あなたは「{text}」と言いましたね。"
    MessagingApi(configuration).reply_message(
        event.reply_token,
        [
            {
                "type": "text",
                "text": reply_text
            }
        ]
    )