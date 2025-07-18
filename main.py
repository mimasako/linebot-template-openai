import os
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import openai
import requests
from io import BytesIO

# .env 読み込み
load_dotenv()

# LINE APIキー
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# OpenAI APIキー
openai.api_key = os.getenv("OPENAI_API_KEY")

# tesseract パス設定（Render用）
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# FastAPI 初期化
app = FastAPI()

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return PlainTextResponse("Invalid signature", status_code=400)
    return PlainTextResponse("OK", status_code=200)

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="画像を受け取りました。処理中です…")
    )

    # 画像の取得
    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = BytesIO(message_content.content)

    try:
        image = Image.open(image_data)

        # OCRでテキスト抽出
        ocr_text = pytesseract.image_to_string(image, lang='jpn')

        # OpenAIで予想生成
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは競艇の予想AIです。出走表の情報から、勝ちそうな選手を予想してください。"},
                {"role": "user", "content": ocr_text}
            ]
        )

        prediction = response["choices"][0]["message"]["content"].strip()

        # 結果を返信
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=f"予想結果：\n{prediction}")
        )

    except Exception as e:
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=f"OCR処理でエラーが発生しました：{str(e)}")
        )