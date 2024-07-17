import json
import asyncio
from datetime import datetime
import typing

import socketio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import asynccontextmanager
from fastapi.encoders import jsonable_encoder

from app import store

from app.device import ArtisanLog, Device, Kapok501
from app.classes import RoastSession, Point, Channel, AppStatus
from app.loggers import LOG_FASTAPI_CLI, LOG_UVICORN

from app.routers import settings


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=redefined-outer-name
    # Lifespan startup actions
    store.loop = asyncio.get_running_loop()

    yield
    # Lifespan cleanup actions


socketio_server = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

app = FastAPI(lifespan=lifespan)
app.include_router(settings.router)
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

socketio_app = socketio.ASGIApp(
    socketio_server=socketio_server, socketio_path="/socket.io"
)

# https://github.com/tiangolo/fastapi/discussions/10970
# path needs to match socketio_path in socketio.ASGIApp above
app.mount("/socket.io", socketio_app)

# store init
with open("settings.json", "rb") as f:
    store.settings = json.load(f)
    LOG_FASTAPI_CLI.info(settings)

if store.settings["device"] == "Kapok501":
    LOG_FASTAPI_CLI.info("device: Kapok501")

    device: Device = Kapok501(store.settings["serial"]["port"])
    store.device = device
else:
    LOG_FASTAPI_CLI.info("device: ArtisanLog")
    device: Device = ArtisanLog("../util/23-11-05_1013.alog")
    store.device = device

store.app_status = AppStatus.OFF


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html.jinja2",
        context={"ctx_settings": store.settings},
    )


@app.post("/on", response_class=HTMLResponse)
async def connect() -> Response:
    await store.device.connect()

    return """
    <div class="flex gap-1 mt-1">
        <button
            class="btn"
            hx-post="/off"
            hx-trigger="click"
            hx-target="closest div"
            hx-swap="outerHTML"
        >
            off
        </button>
        <button 
            class="btn" 
            hx-post="/start" 
            hx-trigger="click"
            hx-target="this"
            hx-swap="outerHTML"
        >
            start
        </button>
    </div>
    """


@app.post("/off", response_class=HTMLResponse)
async def close() -> Response:
    await store.device.close()

    return """
    <div class="flex gap-1 mt-1">
        <button
            class="btn"
            hx-post="/on"
            hx-trigger="click"
            hx-target="closest div"
            hx-swap="outerHTML"
        >
            on
        </button>
    </div>
    """


@app.post("/start", response_class=HTMLResponse)
async def start() -> Response:

    rs = RoastSession()
    rs.channels.append(Channel(id="BT"))
    rs.channels.append(Channel(id="ET"))
    rs.channels.append(Channel(id="INLET"))
    rs.start_time = datetime.now()

    store.roast_session = rs

    store.read_device_task = store.loop.create_task(
        ticker(interval=2.0, function_to_call=read_device)
    )
    store.update_timer_task = store.loop.create_task(
        ticker(interval=1.0, function_to_call=update_timer)
    )

    return """
    <button 
        class="btn" 
        hx-post="/stop" 
        hx-trigger="click"
        hx-target="this"
        hx-swap="outerHTML"
    >
        stop
    </button>
    """


@app.post("/stop", response_class=HTMLResponse)
async def stop() -> Response:
    store.read_device_task.cancel()
    store.update_timer_task.cancel()

    return """
    <button 
        class="btn" 
        hx-post="/reset" 
        hx-trigger="click"
        hx-target="this"
        hx-swap="outerHTML"
    >
        reset
    </button>
    """


@app.post("/reset", response_class=HTMLResponse)
async def reset() -> Response:

    return """
    <button 
        class="btn" 
        hx-post="/start" 
        hx-trigger="click"
        hx-target="this"
        hx-swap="outerHTML"
    >
        start
    </button>
    """


async def ticker(interval: float, function_to_call: typing.Callable):
    while True:
        await function_to_call()
        await asyncio.sleep(interval)


async def read_device():

    roast_session: RoastSession = store.roast_session
    roast_session.timer = (datetime.now() - roast_session.start_time).total_seconds()
    LOG_UVICORN.info("roast_session timer : %s", roast_session.timer)

    result = await store.device.read()
    LOG_UVICORN.info(result)

    bt = Point(roast_session.timer, result["BT"])
    roast_session.channels[0].data.append(bt)

    et = Point(roast_session.timer, result["ET"])
    roast_session.channels[1].data.append(et)

    inlet = Point(roast_session.timer, result["INLET"])
    roast_session.channels[2].data.append(inlet)

    await socketio_server.emit("read_device", jsonable_encoder(roast_session.channels))


async def update_timer():
    roast_session: RoastSession = store.roast_session
    roast_session.timer = (datetime.now() - roast_session.start_time).total_seconds()
    LOG_UVICORN.info(roast_session.timer)
    await socketio_server.emit("update_timer", roast_session.timer)
