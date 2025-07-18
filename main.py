from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage
from linebot.exceptions import InvalidSignatureError
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        return {"status": "invalid signature"}
    return {"status": "ok"}

# テキストメッセージの処理
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    reply_text = f"あなたが送ったメッセージ:「{event.message.text}」"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# 画像メッセージの処理
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    reply_text = "画像を受け取りました。処理中です..."
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)