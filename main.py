import os
import openai
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    MessagingApi,
    Configuration,
    ApiClient,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

# .env を読み込む
load_dotenv()

# 環境変数からキーを取得
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
openai_api_key = os.getenv("OPENAI_API_KEY")

# LINE Messaging API の設定
configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)
line_bot_api = MessagingApi(ApiClient(configuration))

# OpenAI API キー設定
openai.api_key = openai_api_key

# FastAPI アプリ作成
app = FastAPI()

@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get("x-line-signature")

    try:
        handler.handle(body.decode("utf-8"), signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return "OK"

# メッセージ受信時の処理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    user_message = event.message.text

    # OpenAI へ問い合わせ
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": user_message}
        ]
    )
    ai_reply = response.choices[0].message.content.strip()

    # LINEへ返信
    reply = ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[TextMessage(text=ai_reply)]
    )
    line_bot_api.reply_message(reply)