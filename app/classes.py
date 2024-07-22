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

        self.current_data: float = 0
        self.current_ror: float = 0
        self.data_window: list = []  # for calculate current ror

        self.data: list[Point] = []
        self.ror: list[Point] = []
        self.ror_filtered: list[Point] = []
        self.ror_smoothed: list[Point] = []


class RoastSession:
    def __init__(self):
        self.start_time: datetime = datetime.now()
        self.timer: float = 0.0
        self.channels: list[Channel] = []


class RoastEventId(Enum):
    CHARGE = 1
    TP = 2
    DRY_END = 3
    FC_START = 4
    FC_END = 5
    SC_START = 6
    SC_END = 6
    DROP = 6


class RoastEvent:
    def __init__(self, id: RoastEventId, index: int):
        self.id: RoastEventId = id
        self.index: int = index


class AppStatus(Enum):
    OFF = 1
    ON = 2
    RECORDING = 3
