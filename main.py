from fastapi import FastAPI, Request
from linebot.v3.messaging import LineBotApi, WebhookHandler
from linebot.v3.webhook import WebhookParser, WebhookEvent
from linebot.v3.exceptions import InvalidSignatureError
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

line_bot_api = LineBotApi(channel_access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(channel_secret=os.getenv("LINE_CHANNEL_SECRET"))

@app.post("/webhook")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        return {"status": "invalid signature"}
    return {"status": "ok"}