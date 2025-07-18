import os
import io
import openai
import pytesseract
from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
from dotenv import load_dotenv
from PIL import Image

# ✅ Tesseract のパスを指定（Render の Ubuntu 環境ではこれ）
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

load_dotenv()

# LINE APIキーなど環境変数読み込み
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

app = FastAPI()

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers["x-line-signature"]
    body = await request.body()
    body = body.decode("utf-8")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK", 200

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="画像を受け取りました。処理中です…")
    )

    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = io.BytesIO(message_content.content)
    image = Image.open(image_data)

    try:
        text = pytesseract.image_to_string(image, lang="jpn")
    except Exception as e:
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=f"OCR処理でエラーが発生しました：{str(e)}")
        )
        return

    # OpenAI APIで予想を生成
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "これはボートレースの出走表です。予想を簡潔に伝えてください。"},
                {"role": "user", "content": text}
            ]
        )
        result = response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        result = f"AIの応答でエラーが発生しました：{str(e)}"

    line_bot_api.push_message(
        event.source.user_id,
        TextSendMessage(text=result)
    )