import os
import pytesseract
from PIL import Image
from io import BytesIO
from fastapi import FastAPI, Request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhook import WebhookEvent
from linebot.v3.messaging import (
    MessagingApi,
    MessagingApiBlob,
    Configuration,
    ApiClient,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhook.models import (
    MessageEvent,
    ImageMessageContent
)
import openai
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# LINE & OpenAI 環境変数
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# LINE Webhookハンドラ設定
handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
line_bot_api = MessagingApi(ApiClient(configuration))
blob_api = MessagingApiBlob(ApiClient(configuration))


@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return "Invalid signature", 400
    return "OK", 200


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event: MessageEvent):
    reply_token = event.reply_token
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text="画像を受け取りました。処理中です…")]
        )
    )

    try:
        # 画像データの取得
        message_id = event.message.id
        image_data = blob_api.get_message_content(message_id)
        image_bytes = BytesIO()
        for chunk in image_data:
            image_bytes.write(chunk)
        image_bytes.seek(0)

        # OCR処理
        image = Image.open(image_bytes)
        text = pytesseract.image_to_string(image, lang="jpn")

        # ChatGPTで予想生成
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "以下は競艇の出走表です。展開予想とおすすめの買い目を教えてください。"},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        result = response["choices"][0]["message"]["content"]

        # 返信
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=result)]
            )
        )

    except Exception as e:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"OCR処理でエラーが発生しました：{str(e)}")]
            )
        )