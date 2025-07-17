from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import AsyncLineBotApi
from linebot.v3.exceptions import InvalidSignatureError
from dotenv import load_dotenv
import os

# 環境変数の読み込み
load_dotenv()

# 環境変数の取得
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# 必須チェック
if channel_secret is None or channel_access_token is None:
    raise ValueError("環境変数が設定されていません")

# LINE SDK の初期化
parser = WebhookParser(channel_secret)
line_bot_api = AsyncLineBotApi(channel_access_token)

# FastAPIの初期化
app = FastAPI()

# Webhookのエンドポイント
@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("x-line-signature", "")
    body = await request.body()

    try:
        events = parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return JSONResponse(status_code=400, content={"message": "Invalid signature"})

    for event in events:
        print("受信イベント:", event)

    return JSONResponse(content={"message": "OK"})

# ↓Renderではこの部分は不要なのでコメントアウト
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=10000)