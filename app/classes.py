from datetime import datetime
from enum import Enum


class Point:
    # t : time
    # v : value
    def __init__(self, t: float, v: float):
        self.t: float = t
        self.v: float = v

    def __str__(self):
        return f"({self.t}, {self.v})"

    def __repr__(self):
        return f"({self.t}, {self.v})"


class Channel:
    def __init__(self, id: str):
        self.id: str = id
        self.data: list[Point] = []


class RoastSession:
    def __init__(self):

        self.start_time: datetime = datetime.now()
        self.timer: float = 0.0
        self.channels: list[Channel] = []


class AppStatus(Enum):
    OFF = 1
    ON = 2
    RECORDING = 3
