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

from scipy.signal import savgol_filter
import numpy

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

# initialization
store.app_status = AppStatus.OFF

store.session = RoastSession()
for c in store.settings["channels"]:
    store.session.channels.append(Channel(id=c["id"]))


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

    store.app_status = AppStatus.ON

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

    store.app_status = AppStatus.OFF

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

    store.session.start_time = datetime.now()

    store.update_timer_task = store.loop.create_task(
        ticker(interval=1.0, function_to_call=update_timer)
    )

    store.app_status = AppStatus.RECORDING

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
    store.app_status = AppStatus.ON

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

    session: RoastSession = store.session

    result = await store.device.read()
    LOG_UVICORN.info("result: %s", result)

    now = datetime.now()
    for c in session.channels:
        c.current_data = result[c.id]

        # calculate ror
        c.data_window.append({"t": now, "v": result[c.id]})
        if len(c.data_window) > 5:
            c.data_window.pop(0)

        delta = c.data_window[-1]["v"] - c.data_window[0]["v"]
        time_elapsed_sec = (
            c.data_window[-1]["t"] - c.data_window[0]["t"]
        ).total_seconds()

        ror = 0
        if time_elapsed_sec != 0:
            ror: float = delta * 60 / time_elapsed_sec
        c.current_ror = ror

    if store.app_status == AppStatus.RECORDING:
        session.timer = (now - session.start_time).total_seconds()
        LOG_UVICORN.info("roast_session timer : %s", session.timer)

        for c in session.channels:
            c.data.append(Point(session.timer, result[c.id]))
            c.ror.append(Point(session.timer, c.current_ror))

            # ref artisanlib > canvas.py > smooth()
            window_len = 13
            if len(c.ror) >= window_len:
                y = []

                for p in c.ror:
                    y.append(p.v)

                s = numpy.r_[y[window_len - 1 : 0 : -1], y, y[-1:-window_len:-1]]
                w = numpy.hanning(window_len)
                ys = numpy.convolve(w / w.sum(), s, mode="valid")
                hwl = int(window_len / 2)
                res = ys[hwl:-hwl]

                c.ror_smoothed = []
                for idx, p in enumerate(c.ror):
                    c.ror_smoothed.append(Point(p.t, res[idx]))

    await socketio_server.emit("read_device", jsonable_encoder(session.channels))


async def update_timer():
    session: RoastSession = store.session
    session.timer = (datetime.now() - session.start_time).total_seconds()
    LOG_UVICORN.info(session.timer)
    await socketio_server.emit("update_timer", session.timer)
