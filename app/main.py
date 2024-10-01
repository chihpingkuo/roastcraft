import json
import asyncio
from datetime import datetime
import typing

import logging
import socketio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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

from app.routers import settings

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=redefined-outer-name
    # Lifespan startup actions
    store.loop = asyncio.get_running_loop()

    yield
    # Lifespan cleanup actions


socketio_server = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

app = FastAPI(lifespan=lifespan)
app.include_router(settings.router)
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

socketio_app = socketio.ASGIApp(
    socketio_server=socketio_server, socketio_path="/socket.io"
)

# https://github.com/tiangolo/fastapi/discussions/10970
# path needs to match socketio_path in socketio.ASGIApp above
app.mount("/socket.io", socketio_app)

# store init
with open("app/settings.json", "rb") as f:
    store.settings = json.load(f)
    logger.info(settings)

if store.settings["device"] == "Kapok501":
    logger.info("device: Kapok501")

    device: Device = Kapok501(store.settings["serial"]["port"])
    store.device = device
else:
    logger.info("device: ArtisanLog")
    device: Device = ArtisanLog("util/24-08-04_0946_mozart.alog")
    store.device = device

# initialization
store.socketio_server = socketio_server

store.app_status = AppStatus.OFF

store.session = RoastSession()
for ch in store.settings["channels"]:
    c = Channel(id=ch["id"], color=ch["color"])
    store.session.channels.append(c)
    if ch["id"] == "BT":
        store.session.bt_channel = c


@socketio_server.on("gas_value")
def gas_value(sid, data):
    store.session.gas_channel.current_data = data
    store.session.gas_channel.data.append(
        Point(
            datetime.now(), store.session.timer, store.session.gas_channel.current_data
        )
    )

    logger.info("gas_channel : %s", store.session.gas_channel.data)


@socketio_server.on("charge")
async def on_charge(sid, data):
    session: RoastSession = store.session

    if data == "charge":
        index = len(session.bt_channel.data) - 1
    elif data == "to_left":
        index = session.roast_events[RoastEventId.C] - 1
    else:  # data == "to_right"
        index = session.roast_events[RoastEventId.C] + 1

    charge_point = session.bt_channel.data[index]
    logger.info("CHARGE at BT index : %s", index)
    logger.info("CHARGE at Point : %s", charge_point)

    # re calculate time
    session.start_time = charge_point.timestamp
    for channel in session.channels:
        for point in channel.data:
            point.time = (point.timestamp - session.start_time).total_seconds()
        for point in channel.ror:
            point.time = (point.timestamp - session.start_time).total_seconds()

    for point in session.gas_channel.data:
        point.time = (point.timestamp - session.start_time).total_seconds()

    session.roast_events[RoastEventId.C] = index

    await socketio_server.emit("roast_events", jsonable_encoder(session.roast_events))


@socketio_server.on("first_crack")
async def on_first_crack(sid, data):

    session: RoastSession = store.session

    index = len(session.bt_channel.data) - 1
    session.roast_events[RoastEventId.FC] = index

    logger.info("FIRST CRACK at BT index : %s", index)

    await socketio_server.emit("roast_events", jsonable_encoder(session.roast_events))


@socketio_server.on("drop")
async def on_drop(sid, data):
    session: RoastSession = store.session

    index = len(session.bt_channel.data) - 1
    session.roast_events[RoastEventId.D] = index

    logger.info("DROP at BT index : %s", index)

    await socketio_server.emit("roast_events", jsonable_encoder(session.roast_events))


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html.jinja2",
        context={"ctx_settings": store.settings, "ctx_appstatus": store.app_status},
    )


@socketio_server.on("on")
async def on_on(sid, data):
    # TODO: implicit reset data

    await store.device.connect()

    store.read_device_task = store.loop.create_task(
        ticker(interval=2.0, function_to_call=read_device)
    )

    store.app_status = AppStatus.ON
    await socketio_server.emit("app_status", jsonable_encoder(store.app_status.name))


@socketio_server.on("off")
async def on_off(sid, data):
    store.read_device_task.cancel()
    await store.device.close()

    store.app_status = AppStatus.OFF
    await socketio_server.emit("app_status", jsonable_encoder(store.app_status.name))


@socketio_server.on("start")
async def on_start(sid, data):
    store.session.start_time = datetime.now()

    store.update_timer_task = store.loop.create_task(
        ticker(interval=1.0, function_to_call=update_timer)
    )

    store.app_status = AppStatus.RECORDING

    store.session.gas_channel.data.append(
        Point(store.session.start_time, 0, store.session.gas_channel.current_data)
    )

    logger.info("gas_channel : %s", store.session.gas_channel.data)
    await socketio_server.emit("app_status", jsonable_encoder(store.app_status.name))


@socketio_server.on("stop")
async def on_stop(sid, data):
    store.read_device_task.cancel()
    await store.device.close()

    store.update_timer_task.cancel()

    store.app_status = AppStatus.OFF
    await socketio_server.emit("app_status", jsonable_encoder(store.app_status.name))


@socketio_server.on("reset")
async def on_reset(sid, data):
    session = RoastSession()
    store.session = session
    for c in store.settings["channels"]:
        store.session.channels.append(Channel(id=c["id"], color=c["color"]))

    await socketio_server.emit("update_timer", session.timer)
    await socketio_server.emit("read_device", jsonable_encoder(session))
    await socketio_server.emit("app_status", jsonable_encoder(store.app_status.name))


async def ticker(interval: float, function_to_call: typing.Callable):
    while True:
        await function_to_call()
        await asyncio.sleep(interval)


async def read_device():

    session: RoastSession = store.session

    result = await store.device.read()
    logger.info("result: %s", result)

    now = datetime.now()
    for c in session.channels:
        c.current_data = result[c.id]

        # calculate ror
        c.data_window.append(Point(now, session.timer, result[c.id]))
        if len(c.data_window) > 5:
            c.data_window.pop(0)

        delta = c.data_window[-1].value - c.data_window[0].value
        time_elapsed_sec = (
            c.data_window[-1].timestamp - c.data_window[0].timestamp
        ).total_seconds()

        if time_elapsed_sec > 0:
            c.current_ror = delta * 60 / time_elapsed_sec  # ror time frame : 60 sec

    if store.app_status == AppStatus.RECORDING:
        session.timer = (now - session.start_time).total_seconds()
        logger.info("roast_session timer : %s", session.timer)

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
            window_len = 11  # shouled be odd number
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
                    if p.time < 0:
                        pass
                    elif (
                        RoastEventId.D in session.roast_events
                        and idx > session.roast_events[RoastEventId.D] - 1
                    ):
                        pass
                    else:
                        c.ror_smoothed.append(Point(p.timestamp, p.time, res[idx]))

    await auto_detect_charge()
    await auto_detect_turning_point()
    await auto_detect_dry_end()
    await auto_detect_drop()
    session.phases = calculate_phases(
        session.timer, session.bt_channel.current_data, session.roast_events
    )
    logger.info(session.phases)

    await socketio_server.emit("read_device", jsonable_encoder(session))


async def update_timer():
    session: RoastSession = store.session
    session.timer = (datetime.now() - session.start_time).total_seconds()
    await socketio_server.emit("update_timer", session.timer)
