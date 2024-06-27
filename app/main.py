import asyncio
from datetime import datetime
from typing import cast

import socketio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import asynccontextmanager
from fastapi.encoders import jsonable_encoder

import pymodbus.client as ModbusClient
from pymodbus import Framer, ModbusException
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from app import store

from app.device import ArtisanLog, Device, Kapok501
from app.classes import Batch, Point, Channel
from app.settings import load_settings
from app.loggers import LOG_FASTAPI_CLI, LOG_UVICORN


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=redefined-outer-name
    # Lifespan startup actions
    store.loop = asyncio.get_running_loop()

    yield
    # Lifespan cleanup actions

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

store.settings = load_settings()

# device initialization
if store.settings['device'] == "Kapok501":
    LOG_FASTAPI_CLI.info("device: Kapok501")

    device: Device = Kapok501(store.settings['serial']['port'])
    store.device = device
else:
    LOG_FASTAPI_CLI.info("device: ArtisanLog")
    device: Device = ArtisanLog("../util/23-11-05_1013.alog")
    store.device = device


@app.get("/hello")
async def hello():
    await socketio_server.emit("hello", "hello everyone")
    LOG_UVICORN.warning("Hello World")
    return {"message": "Hello World"}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html.jinja2", context={"ctx_settings": store.settings}
    )


@app.post("/connect")
async def connect(request: Request) -> Response:
    
    await store.device.connect()

    return PlainTextResponse("connected")

async def timer(interval: float):
    while True:
        await tick()
        await asyncio.sleep(interval)

async def tick():   

    batch: Batch = store.batch
    batch.timer = (datetime.now() - batch.start_time).total_seconds()
    LOG_UVICORN.info("batch timer : %s", batch.timer)

    result = await store.device.read()
    LOG_UVICORN.info(result)

    bt = Point(batch.timer, result["BT"])
    batch.channels[0].data.append(bt)

    et = Point(batch.timer, result["ET"])
    batch.channels[1].data.append(et)

    inlet = Point(batch.timer, result["INLET"])
    batch.channels[2].data.append(inlet)

    await socketio_server.emit("tick", jsonable_encoder(batch.channels))


@app.post("/start")
async def start(request: Request) -> Response:

    batch = Batch()
    batch.channels.append(Channel(id="BT"))
    batch.channels.append(Channel(id="ET"))
    batch.channels.append(Channel(id="INLET"))
    batch.start_time = datetime.now()

    store.batch = batch
    
    store.task = store.loop.create_task(timer(interval=2.0), name="timer")

    return PlainTextResponse("start ticking")


@app.post("/stop")
async def stop(request: Request) -> Response:
    store.task.cancel()
    return PlainTextResponse("stop ticking")
