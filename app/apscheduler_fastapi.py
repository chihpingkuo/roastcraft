from datetime import datetime
from typing import cast

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.concurrency import asynccontextmanager


from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger


def tick():
    print("Hello, the time is", datetime.now())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lifespan startup actions
    scheduler = AsyncScheduler()

    async with scheduler:
        await scheduler.start_in_background()
        app.state.scheduler = scheduler

        yield

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root(request: Request) -> Response:
    return PlainTextResponse("Hello, world!")


@app.get("/start")
async def start(request: Request) -> Response:
    await cast(AsyncScheduler, request.app.state.scheduler).add_schedule(
        tick, IntervalTrigger(seconds=1), id="tick"
    )
    return PlainTextResponse("start ticking")


@app.get("/stop")
async def stop(request: Request) -> Response:
    await cast(AsyncScheduler, request.app.state.scheduler).remove_schedule(
        id="tick"
    )
    return PlainTextResponse("stop ticking")
