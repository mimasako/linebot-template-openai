import os
import io
import openai
import pytesseract
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from PIL import Image
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, ImageMessage
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage
import base64
import httpx

# .envの読み込み
load_dotenv()

# 環境変数
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI設定
openai.api_key = OPENAI_API_KEY

# FastAPI初期化
app = FastAPI()

# LINE SDK初期化
handler = WebhookHandler(LINE_CHANNEL_SECRET)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
line_bot_api = MessagingApi(ApiClient(configuration))

@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature")

    try:
        handler.handle(body.decode("utf-8"), signature)
    except Exception as e:
        return PlainTextResponse(str(e), status_code=400)

    return PlainTextResponse("OK", status_code=200)

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event: MessageEvent):
    message_id = event.message.id

    try:
        # 画像受信を通知
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="画像を受け取りました。処理中です…")]
            )
        )

        # 画像取得
        content = line_bot_api.get_message_content(message_id)
        image_data = io.BytesIO()
        for chunk in content.iter_content():
            image_data.write(chunk)
        image_data.seek(0)

        # OCR処理
        image = Image.open(image_data)
        text = pytesseract.image_to_string(image, lang='jpn')

        # OpenAIで予測
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "以下は競艇の出走表です。選手や展示タイムをもとにレースの予想をしてください。"},
                {"role": "user", "content": text}
            ]
        )

        reply_text = response.choices[0].message["content"].strip()

        # 返信
        line_bot_api.push_message(
            ReplyMessageRequest(
                to=event.source.user_id,
                messages=[TextMessage(text=reply_text)]
            )
        )

    except Exception as e:
        error_message = f"OCR処理でエラーが発生しました：{str(e)}"
        line_bot_api.push_message(
            ReplyMessageRequest(
                to=event.source.user_id,
                messages=[TextMessage(text=error_message)]
            )
        )