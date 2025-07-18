import os
import io
import pytesseract
import openai
from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, ImageMessage, TextMessage, TextSendMessage

from dotenv import load_dotenv
from PIL import Image

load_dotenv()

app = FastAPI()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers["X-Line-Signature"]
    body = await request.body()
    body = body.decode("utf-8")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK", 200

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_text = event.message.text

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": user_text}
        ]
    )

    ai_reply = response.choices[0].message["content"]
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_reply)
    )

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="画像を受け取りました。処理中です…"))

    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = io.BytesIO(message_content.content)

    try:
        image = Image.open(image_data)
        text = pytesseract.image_to_string(image, lang='jpn')

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"以下のテキストを分析して、競艇の予想をしてください:\n{text}"}
            ]
        )
        ai_reply = response.choices[0].message["content"]
    except Exception as e:
        ai_reply = f"OCR処理でエラーが発生しました：{str(e)}"

    line_bot_api.push_message(
        event.source.user_id,
        TextSendMessage(text=ai_reply)
    )