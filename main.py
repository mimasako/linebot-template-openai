import os
import requests
import openai
import tempfile
import pytesseract
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import (
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.models import MessageEvent, ImageMessage

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

handler = WebhookHandler(CHANNEL_SECRET)
messaging_api = MessagingApi()
messaging_api.configuration.access_token = CHANNEL_ACCESS_TOKEN
openai.api_key = OPENAI_API_KEY


@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return PlainTextResponse("Invalid signature", status_code=400)
    return PlainTextResponse("OK", status_code=200)


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_id = event.message.id
    image_content = MessagingApiBlob().get_message_content(message_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
        for chunk in image_content.iter_content():
            tf.write(chunk)
        temp_image_path = tf.name

    try:
        extracted_text = pytesseract.image_to_string(temp_image_path, lang="jpn")
    except Exception as e:
        error_text = f"OCR処理でエラーが発生しました：{str(e)}"
        reply_message = TextMessage(text=error_text)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[reply_message]
            )
        )
        return

    prompt = f"次の情報をもとに競艇のレース予想をして：\n{extracted_text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        result_text = response["choices"][0]["message"]["content"]
    except Exception as e:
        result_text = f"OpenAI APIエラー: {str(e)}"

    reply_message = TextMessage(text=result_text)
    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[reply_message]
        )
    )