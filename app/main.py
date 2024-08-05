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

import numpy

from app import store

from app.calculate import (
    auto_detect_charge,
    auto_detect_drop,
    auto_detect_dry_end,
    auto_detect_turning_point,
    calculate_phases,
    hampel_filter_forloop_point,
)
from app.device import ArtisanLog, Device, Kapok501
from app.classes import RoastSession, RoastEventId, Point, Channel, AppStatus
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
    device: Device = ArtisanLog("../util/24-08-04_0946_mozart.alog")
    store.device = device

# initialization
store.socketio_server = socketio_server

store.app_status = AppStatus.OFF

store.session = RoastSession()
for c in store.settings["channels"]:
    store.session.channels.append(Channel(id=c["id"], color=c["color"]))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html.jinja2",
        context={"ctx_settings": store.settings, "ctx_appstatus": store.app_status},
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
            hx-target="closest div"
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
            hx-post="/reset"
            hx-trigger="click"
        >
            reset
        </button>
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
    <div class="flex gap-1 mt-1">
        <button 
            class="btn" 
            hx-post="/stop" 
            hx-trigger="click"
            hx-target="closest div"
            hx-swap="outerHTML"
        >
            stop
        </button>
    </div>
    """


@app.post("/stop", response_class=HTMLResponse)
async def stop() -> Response:

    store.read_device_task.cancel()
    await store.device.close()

    store.update_timer_task.cancel()

    store.app_status = AppStatus.OFF

    return """
    <div class="flex gap-1 mt-1">
        <button
            class="btn"
            hx-post="/reset"
            hx-trigger="click"
        >
            reset
        </button>
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


@app.post("/reset", response_class=HTMLResponse)
async def reset() -> Response:

    return """
    
    """


@app.post("/charge", response_class=HTMLResponse)
async def charge() -> Response:

    session: RoastSession = store.session

    index = len(session.channels[0].data) - 1

    charge_point = session.channels[0].data[index]
    LOG_UVICORN.info("CHARGE at BT index : %s", index)
    LOG_UVICORN.info("CHARGE at Point : %s", charge_point)

    # re calculate time
    session.start_time = charge_point.timestamp
    for channel in session.channels:
        for point in channel.data:
            point.time = (point.timestamp - session.start_time).total_seconds()
        for point in channel.ror:
            point.time = (point.timestamp - session.start_time).total_seconds()

    session.roast_events[RoastEventId.C] = index

    await socketio_server.emit(
        "roast_events",
        jsonable_encoder(
            [{"id": key, "index": value} for key, value in session.roast_events.items()]
        ),
    )

    return """
    <button 
        class="btn btn-disabled" 
    >
        charge
    </button>
    """


@app.post("/charge/toLeft")
async def charge_to_left() -> Response:

    session: RoastSession = store.session

    new_index = session.roast_events[RoastEventId.C] - 1

    # re calculate time
    session.start_time = session.channels[0].data[new_index].timestamp
    for channel in session.channels:
        for point in channel.data:
            point.time = (point.timestamp - session.start_time).total_seconds()
        for point in channel.ror:
            point.time = (point.timestamp - session.start_time).total_seconds()

    session.roast_events[RoastEventId.C] = new_index

    await socketio_server.emit(
        "roast_events",
        jsonable_encoder(
            [{"id": key, "index": value} for key, value in session.roast_events.items()]
        ),
    )

    return {"message": "Ok"}


@app.post("/charge/toRight")
async def charge_to_right() -> Response:

    session: RoastSession = store.session

    new_index = session.roast_events[RoastEventId.C] + 1

    # re calculate time
    session.start_time = session.channels[0].data[new_index].timestamp
    for channel in session.channels:
        for point in channel.data:
            point.time = (point.timestamp - session.start_time).total_seconds()
        for point in channel.ror:
            point.time = (point.timestamp - session.start_time).total_seconds()

    session.roast_events[RoastEventId.C] = new_index

    await socketio_server.emit(
        "roast_events",
        jsonable_encoder(
            [{"id": key, "index": value} for key, value in session.roast_events.items()]
        ),
    )

    return {"message": "Ok"}


@app.post("/fc", response_class=HTMLResponse)
async def fc() -> Response:

    session: RoastSession = store.session

    index = len(session.channels[0].data) - 1
    session.roast_events[RoastEventId.FC] = index

    LOG_UVICORN.info("FIRST CRACK at BT index : %s", index)

    await socketio_server.emit(
        "roast_events",
        jsonable_encoder(
            [{"id": key, "index": value} for key, value in session.roast_events.items()]
        ),
    )

    return """
    <button 
        class="btn btn-disabled" 
    >
        FC
    </button>
    """


@app.post("/drop", response_class=HTMLResponse)
async def drop() -> Response:

    session: RoastSession = store.session

    index = len(session.channels[0].data) - 1
    session.roast_events[RoastEventId.D] = index

    LOG_UVICORN.info("DROP at BT index : %s", index)

    await socketio_server.emit(
        "roast_events",
        jsonable_encoder(
            [{"id": key, "index": value} for key, value in session.roast_events.items()]
        ),
    )

    return """
    <button 
        class="btn btn-disabled" 
    >
        drop
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
            c.data.append(Point(now, session.timer, result[c.id]))
            c.ror.append(Point(now, session.timer, c.current_ror))

            # filter outliers
            filter_window_size = 7  # shouled be odd number
            n_sigmas = 2
            if len(c.ror) >= filter_window_size:

                c.ror_filtered, outliers = hampel_filter_forloop_point(
                    c.ror, int(filter_window_size / 2), n_sigmas
                )

            # smooth curve
            # https://scipy-cookbook.readthedocs.io/items/SignalSmooth.html
            window_len = 15  # shouled be odd number
            if len(c.ror_filtered) >= window_len:
                x = []

                for p in c.ror_filtered:
                    x.append(p.value)

                s = numpy.r_[
                    x[window_len - 1 : 0 : -1], x, x[-2 : -window_len - 1 : -1]
                ]
                w = numpy.hanning(window_len)
                y = numpy.convolve(w / w.sum(), s, mode="valid")
                res = y[int(window_len / 2) - 1 : -int(window_len / 2)]

                c.ror_smoothed = []
                for idx, p in enumerate(c.ror_filtered):
                    c.ror_smoothed.append(Point(p.timestamp, p.time, res[idx]))

    await auto_detect_charge()
    await auto_detect_turning_point()
    await auto_detect_dry_end()
    await auto_detect_drop()
    phases = calculate_phases(
        session.timer, session.channels[0].current_data, session.roast_events
    )
    LOG_UVICORN.info(phases)

    await socketio_server.emit("read_device", jsonable_encoder(session.channels))
    await socketio_server.emit("phases", jsonable_encoder(phases))


async def update_timer():
    session: RoastSession = store.session
    session.timer = (datetime.now() - session.start_time).total_seconds()
    LOG_UVICORN.info(session.timer)
    await socketio_server.emit("update_timer", session.timer)
