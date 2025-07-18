from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent
from linebot.models import TextSendMessage
import os
import openai
import requests
import pytesseract
from PIL import Image
from io import BytesIO

app = FastAPI()

channel_secret = os.getenv("LINE_CHANNEL_SECRET")
channel_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

configuration = Configuration(access_token=channel_token)
handler = WebhookHandler(channel_secret)

@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")
    handler.handle(body.decode("utf-8"), signature)
    return PlainTextResponse("OK")

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    message_id = event.message.id
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        message_content = line_bot_api.get_message_content(message_id)
        image_data = BytesIO()
        for chunk in message_content.iter_content():
            image_data.write(chunk)
        image_data.seek(0)
        img = Image.open(image_data)
        text = pytesseract.image_to_string(img, lang="jpn")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"以下の競艇出走表から予想してください:\n{text}"}],
        )
        reply_text = response.choices[0].message.content.strip()
        line_bot_api.reply_message(
            event.reply_token,
            [TextSendMessage(text=reply_text)]
        )