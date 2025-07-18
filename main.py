import os
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import (
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    ImageMessage,
)
from linebot.v3.models import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent
)
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import openai
import requests
from io import BytesIO

# .env 読み込み
load_dotenv()

# APIキー設定
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
messaging_api = MessagingApi()
blob_api = MessagingApiBlob()
openai.api_key = os.getenv("OPENAI_API_KEY")

# tesseractパス（Render用）
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# FastAPI 初期化
app = FastAPI()


@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except Exception as e:
        return PlainTextResponse(f"Invalid signature or error: {str(e)}", status_code=400)
    return PlainTextResponse("OK", status_code=200)


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    # 「画像受信」応答
    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text="画像を受け取りました。処理中です…")]
        )
    )

    try:
        # 画像取得
        message_id = event.message.id
        content = blob_api.get_message_content(message_id)
        image_data = BytesIO(content.content)
        image = Image.open(image_data)

        # OCR処理
        ocr_text = pytesseract.image_to_string(image, lang='jpn')

        # OpenAIに送信
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは競艇の予想AIです。出走表の情報から、勝ちそうな選手を予想してください。"},
                {"role": "user", "content": ocr_text}
            ]
        )

        prediction = response["choices"][0]["message"]["content"].strip()

        # 結果を返信
        messaging_api.push_message(
            PushMessageRequest(
                to=event.source.user_id,
                messages=[TextMessage(text=f"予想結果：\n{prediction}")]
            )
        )

    except Exception as e:
        messaging_api.push_message(
            PushMessageRequest(
                to=event.source.user_id,
                messages=[TextMessage(text=f"OCR処理またはAI応答でエラーが発生しました：{str(e)}")]
            )
        )