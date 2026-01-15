from broadcaster import Broadcast
from starlette.applications import Starlette
from starlette.concurrency import run_until_first_complete
from starlette.routing import Route, WebSocketRoute
from starlette.templating import Jinja2Templates
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
import aiohttp
import urllib.parse


load_dotenv()  # Load .env variables

# 메모리 broadcast 사용 (Redis 없이)
broadcast = Broadcast("memory://")
print("Using in-memory broadcast")
templates = Jinja2Templates("templates")

# 대화 기록 저장 (웹소켓 ID별로)
chat_histories = {}


async def homepage(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context)


async def chatroom_ws(websocket):
    await websocket.accept()
    channel_name = "demo"

    # 웹소켓별 대화 기록 초기화
    ws_id = id(websocket)
    chat_histories[ws_id] = []

    try:
        await run_until_first_complete(
            (chatroom_ws_receiver, {"websocket": websocket, "channel_name": channel_name}),
            (chatroom_ws_sender, {"websocket": websocket, "channel_name": channel_name, "ws_id": ws_id}),
        )
    finally:
        # 연결 종료 시 대화 기록 삭제
        if ws_id in chat_histories:
            del chat_histories[ws_id]


async def chatroom_ws_receiver(websocket, channel_name):
    async for message in websocket.iter_text():
        print(f"WS Receiver: Received message: {message}")
        await broadcast.publish(channel=channel_name, message=message)
        print("WS Receiver: Published")


async def chatroom_ws_sender(websocket, channel_name, ws_id):
    async with broadcast.subscribe(channel=channel_name) as subscriber:
        print("WS Sender: Subscribed to channel")
        async for event in subscriber:
            print(f"WS Sender: Got event: {event.message}")
            await websocket.send_text(event.message)

            # 봇 응답 처리
            await websocket.send_text('{"action":"message","user":"안내","message":"Claude가 입력 중입니다..."}')

            # 현재 메시지 추출
            user_message = json.loads(event.message)['message']

            # 대화 기록을 JSON 문자열로 인코딩
            history = chat_histories.get(ws_id, [])
            history_json = urllib.parse.quote(json.dumps(history, ensure_ascii=False))

            # API Gateway 호출 (Bedrock Claude) - 대화 기록 포함
            params = {
                "m": user_message,
                "history": history_json
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://wjd36tvv38.execute-api.ap-northeast-2.amazonaws.com/default/test-lambda",
                    params=params
                ) as resp:
                    r = await resp.json()
                    # Bedrock Claude 응답은 body에 직접 텍스트가 있음
                    bot_message = r.get('body', str(r))
                    bot_message_json = json.dumps(bot_message, ensure_ascii=False)
                    await websocket.send_text(f'{{"action":"message","user":"Bedrock Claude","message":{bot_message_json}}}')

                    # 대화 기록에 추가 (user + assistant)
                    chat_histories[ws_id].append({"role": "user", "content": user_message})
                    chat_histories[ws_id].append({"role": "assistant", "content": bot_message})

                    # 대화 기록이 너무 길면 오래된 것 삭제 (최근 10개 대화만 유지)
                    if len(chat_histories[ws_id]) > 20:
                        chat_histories[ws_id] = chat_histories[ws_id][-20:]


routes = [
    Route("/", homepage),
    WebSocketRoute("/", chatroom_ws, name='chatroom_ws'),
]

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://www.fromisus.store",
    "https://www.fromisus.store"
]

middleware = [
    Middleware(CORSMiddleware,
               allow_origins=origins,
               allow_methods=['*'],
               allow_headers=['*'])
]

application = Starlette(
    routes=routes,
    on_startup=[broadcast.connect],
    on_shutdown=[broadcast.disconnect],
    middleware=middleware
)
