import json
import asyncio
from datetime import datetime
import typing

import socketio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import asynccontextmanager
from fastapi.encoders import jsonable_encoder

from app import store

from app.device import ArtisanLog, Device, Kapok501
from app.classes import AppState, Point, Channel, AppStatus
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

store.app_state = AppState()
store.app_state.channels.append(Channel(id="BT"))
store.app_state.channels.append(Channel(id="ET"))
store.app_state.channels.append(Channel(id="INLET"))


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

    store.read_device_task = store.loop.create_task(
        ticker(interval=2.0, function_to_call=read_device)
    )

    store.app_state.status = AppStatus.ON

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
    store.read_device_task.cancel()

    await store.device.close()

    store.app_state.status = AppStatus.OFF

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

    store.app_state.start_time = datetime.now()

    store.update_timer_task = store.loop.create_task(
        ticker(interval=1.0, function_to_call=update_timer)
    )

    store.app_state.status = AppStatus.RECORDING

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
    # store.read_device_task.cancel()
    store.update_timer_task.cancel()
    store.app_state.status = AppStatus.ON

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

    state: AppState = store.app_state

    result = await store.device.read()
    LOG_UVICORN.info(result)

    state.channels[0].current_data = result["BT"]
    state.channels[1].current_data = result["ET"]
    state.channels[2].current_data = result["INLET"]

    if state.status == AppStatus.RECORDING:
        state.timer = (datetime.now() - state.start_time).total_seconds()
        LOG_UVICORN.info("roast_session timer : %s", state.timer)

        bt = Point(state.timer, result["BT"])
        state.channels[0].data.append(bt)

        et = Point(state.timer, result["ET"])
        state.channels[1].data.append(et)

        inlet = Point(state.timer, result["INLET"])
        state.channels[2].data.append(inlet)

    await socketio_server.emit("read_device", jsonable_encoder(state.channels))


async def update_timer():
    state: AppState = store.app_state
    state.timer = (datetime.now() - state.start_time).total_seconds()
    LOG_UVICORN.info(state.timer)
    await socketio_server.emit("update_timer", state.timer)
