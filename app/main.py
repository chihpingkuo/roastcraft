import tomllib
from datetime import datetime
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import asynccontextmanager

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

import pymodbus.client as ModbusClient
from pymodbus import (
    Framer,
    ModbusException,
)
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lifespan startup actions
    scheduler = AsyncScheduler()

    async with scheduler:
        await scheduler.start_in_background()
        app.state.scheduler = scheduler

        yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

with open("config.toml", "rb") as f:
    app.state.config = tomllib.load(f)


@app.get("/hello")
async def hello():
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
        framer=Framer.RTU,
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

    print(decoder.decode_16bit_int()*0.1)


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
