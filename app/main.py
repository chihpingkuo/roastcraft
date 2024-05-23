from datetime import datetime
from typing import cast

import socketio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import asynccontextmanager
from fastapi.encoders import jsonable_encoder

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

import pymodbus.client as ModbusClient
from pymodbus import Framer, ModbusException
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from .classes import Batch, Point, Channel
from .settings import load_settings


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=redefined-outer-name
    # Lifespan startup actions
    scheduler = AsyncScheduler()

    async with scheduler:
        await scheduler.start_in_background()
        app.state.scheduler = scheduler

        yield

socketio_server = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins="*"
)

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

socketio_app = socketio.ASGIApp(
    socketio_server=socketio_server,
    socketio_path='/socket.io'
)

# https://github.com/tiangolo/fastapi/discussions/10970
# path needs to match socketio_path in socketio.ASGIApp above
app.mount("/socket.io", socketio_app)

app.state.settings = load_settings()


@app.get("/hello")
async def hello():
    await socketio_server.emit("hello", "hello everyone")
    return {"message": "Hello World"}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"ctx_settings": app.state.settings}
    )


@app.post("/connect")
async def connect(request: Request) -> Response:

    settings: dict = request.app.state.settings
    port: str = settings['serial']['port']
    client = ModbusClient.AsyncModbusSerialClient(
        port,
        framer=Framer.ASCII,
        # timeout=10,
        # retries=3,
        # retry_on_empty=False,
        # strict=True,
        baudrate=9600,
        bytesize=8,
        parity="N",
        stopbits=1,
        # handle_local_echo=False,
    )

    app.state.client = client

    await client.connect()

    return PlainTextResponse("connected")


async def tick(client: ModbusClient.AsyncModbusSerialClient):

    async def read(slave: int) -> float:

        try:
            # See all calls in client_calls.py
            rr = await client.read_holding_registers(18176, 1, slave)
        except ModbusException as e:
            print(f"Received ModbusException({e}) from library")
            return

        value: float = BinaryPayloadDecoder.fromRegisters(
            rr.registers,
            byteorder=Endian.BIG,
            wordorder=Endian.BIG
        ).decode_16bit_int()*0.1
        print(value)
        return value

    batch: Batch = app.state.batch
    batch.timer = (
        datetime.now() - batch.start_time).total_seconds()
    print("timer is", batch.timer)

    # for kapok 501 inlet
    bt = Point(batch.timer, await read(slave=2))
    batch.channels[0].data.append(bt)

    et = Point(batch.timer, await read(slave=1))
    batch.channels[1].data.append(et)

    inlet = Point(batch.timer, await read(slave=3))
    batch.channels[2].data.append(inlet)

    await socketio_server.emit("tick", jsonable_encoder(batch.channels))


@app.post("/start")
async def start(request: Request) -> Response:

    batch = Batch()
    batch.channels.append(Channel(id="BT"))
    batch.channels.append(Channel(id="ET"))
    batch.channels.append(Channel(id="INLET"))
    batch.start_time = datetime.now()

    app.state.batch = batch

    await cast(AsyncScheduler, request.app.state.scheduler).add_schedule(
        tick, args=[request.app.state.client], trigger=IntervalTrigger(seconds=2), id="tick"
    )
    return PlainTextResponse("start ticking")


@app.post("/stop")
async def stop(request: Request) -> Response:
    await cast(AsyncScheduler, request.app.state.scheduler).remove_schedule(
        id="tick"
    )
    return PlainTextResponse("stop ticking")
