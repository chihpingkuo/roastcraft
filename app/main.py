import tomllib
from datetime import datetime
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import asynccontextmanager
from fastapi.encoders import jsonable_encoder

import socketio


from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

import pymodbus.client as ModbusClient
from pymodbus import (
    Framer,
    ModbusException,
)
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder


class Point:
    # t : time
    # v : value
    def __init__(self, t: int, v: float):
        self.t = t
        self.v = v

    def __str__(self):
        return f"({self.t}, {self.v})"

    def __repr__(self):
        return f"({self.t}, {self.v})"


@asynccontextmanager
async def lifespan(app: FastAPI):
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


with open("config.toml", "rb") as f:
    app.state.config = tomllib.load(f)

app.state.timer = 0
app.state.bt = []


@app.get("/hello")
async def hello():
    await socketio_server.emit("hello", "hello everyone")
    return {"message": "Hello World"}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html"
    )


@app.post("/connect")
async def connect(request: Request) -> Response:

    config: dict = request.app.state.config
    port: str = config['serial']['port']
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
    print("Hello, the time is", datetime.now())

    try:
        # See all calls in client_calls.py
        rr = await client.read_holding_registers(18176, 1, slave=1)
    except ModbusException as e:
        print(f"Received ModbusException({e}) from library")
        return

    decoder = BinaryPayloadDecoder.fromRegisters(
        rr.registers, byteorder=Endian.BIG, wordorder=Endian.BIG
    )

    value: float = decoder.decode_16bit_int()*0.1
    print(value)

    app.state.timer += 2
    p = Point(app.state.timer, value)
    app.state.bt.append(p)


@app.post("/start")
async def start(request: Request) -> Response:
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


@app.get("/bt")
async def bt(request: Request) -> Response:
    return JSONResponse(jsonable_encoder(app.state.bt))
