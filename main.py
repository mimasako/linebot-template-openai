# -*- coding: utf-8 -*-

import openai
import os
import sys
import json
import aiohttp

from fastapi import Request, FastAPI, HTTPException
from linebot import AsyncLineBotApi, WebhookParser
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# dotenv の読み込み
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())  # .envファイルを読み込み

# OpenAI API 初期化
def call_openai_chat_api(user_message):
    openai.api_key = os.getenv('OPENAI_API_KEY', None)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message},
        ]
    )

    return response.choices[0].message['content']

# LINE チャネルシークレットとアクセストークンの取得
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)

if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

# LINE Bot API 初期化
app = FastAPI()
session = aiohttp.ClientSession()
async_http_client = AiohttpAsyncHttpClient(session)
line_bot_api = AsyncLineBotApi(channel_access_token, async_http_client)
parser = WebhookParser(channel_secret)

@app.post("/callback")
async def handle_callback(request: Request):
    signature = request.headers['X-Line-Signature']
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        result = call_openai_chat_api(event.message.text)

        await line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=result)
        )

    return 'OK'