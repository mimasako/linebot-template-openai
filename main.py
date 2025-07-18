from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage
from linebot.exceptions import InvalidSignatureError
from dotenv import load_dotenv
from PIL import Image
import openai
import os
import requests
import io

load_dotenv()

app = FastAPI()

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        return {"status": "invalid signature"}

    return {"status": "ok"}

# 画像メッセージを受信したとき
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="画像を受け取りました。処理中です…")
    )

    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)

    image_data = b""
    for chunk in message_content.iter_content():
        image_data += chunk

    try:
        image = Image.open(io.BytesIO(image_data))
        import pytesseract
        text = pytesseract.image_to_string(image, lang='eng+jpn')
    except Exception as e:
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=f"OCR処理でエラーが発生しました：{str(e)}")
        )
        return

    try:
        prompt = f"以下の競艇出走表のデータをもとに、AIが本命の1〜3着を予想してください。\n\n{text}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        prediction = response.choices[0].message.content.strip()

        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=f"✅ AI予想結果：\n{prediction}")
        )
    except Exception as e:
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=f"OpenAI処理でエラーが発生しました：{str(e)}")
        )

# テキストメッセージを受信したとき
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    reply_text = f"あなたが送ったメッセージ：「{event.message.text}」"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)