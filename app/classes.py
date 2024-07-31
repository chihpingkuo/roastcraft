from datetime import datetime
from enum import Enum


class Point:
    def __init__(self, timestamp: datetime, time: float, value: float):
        self.timestamp: datetime = timestamp
        self.time: float = time
        self.value: float = value

    def __str__(self):
        return f"({self.timestamp}, {self.time}, {self.value})"

    def __repr__(self):
        return f"({self.timestamp}, {self.time}, {self.value})"


class Channel:
    def __init__(self, id: str, color: str):
        self.id: str = id
        self.color: str = color

        self.current_data: float = 0
        self.current_ror: float = 0
        self.data_window: list = []  # for calculate current ror

        self.data: list[Point] = []
        self.ror: list[Point] = []
        self.ror_filtered: list[Point] = []
        self.ror_smoothed: list[Point] = []


class RoastEventId(Enum):
    C = "C"  # charge
    TP = "TP"  # turning point
    DE = "DE"  # dry end
    FC = "FC"  # first crack
    FCE = "FCE"  # first crack end
    SC = "SC"  # second crack
    SCE = "SCE"  # second crack end
    D = "D"  # drop


class Phase:
    def __init__(self, time: float, percent: float, temp_rise: float):
        self.time: float = time
        self.percent: float = percent
        self.temp_rise: float = temp_rise


class RoastSession:
    def __init__(self):
        self.start_time: datetime = datetime.now()
        self.timer: float = 0.0
        self.channels: list[Channel] = []
        self.roast_events: dict = {}


class AppStatus(Enum):
    OFF = 1
    ON = 2
    RECORDING = 3
