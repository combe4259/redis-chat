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


load_dotenv()  # Load .env variables

if os.environ.get("ENV_STATE") == "prod":
    print("Production mode")
    redis_url = "redis://"+os.environ.get('REDIS_HOST')+":6379"
    broadcast = Broadcast(redis_url)
else:
    print("Development mode")
    redis_url = "redis://127.0.0.1:6379"
    broadcast = Broadcast(redis_url)
print(f"Connecting to Redis at: {redis_url}")
templates = Jinja2Templates("templates")


async def homepage(request):
    template = "index.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context)


async def chatroom_ws(websocket):
    await websocket.accept()
    channel_name = "demo"
    await run_until_first_complete(
        (chatroom_ws_receiver, {"websocket": websocket, "channel_name": channel_name}),
        (chatroom_ws_sender, {"websocket": websocket, "channel_name": channel_name}),
    )


async def chatroom_ws_receiver(websocket, channel_name):
    async for message in websocket.iter_text():
        print(f"WS Receiver: Received message: {message}")
        await broadcast.publish(channel=channel_name, message=message)
        print("WS Receiver: Published to Redis")


async def chatroom_ws_sender(websocket, channel_name):
    async with broadcast.subscribe(channel=channel_name) as subscriber:
        print("WS Sender: Subscribed to channel")
        async for event in subscriber:
            print(f"WS Sender: Got event from Redis: {event.message}")
            await websocket.send_text(event.message)

            # 봇 응답 처리
            await websocket.send_text('{"action":"message","user":"안내","message":"Claude가 입력 중입니다..."}')

            # API Gateway 호출 (Bedrock Claude)
            params = {"m": json.loads(event.message)['message']}
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

application= Starlette(
    routes=routes,
    on_startup=[broadcast.connect],
    on_shutdown=[broadcast.disconnect],
    middleware=middleware
)
