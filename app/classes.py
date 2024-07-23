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


class RoastEvent(Enum):
    C = "C"  # charge
    TP = "TP"  # turning point
    DE = "DE"  # dry end
    FC = "FC"  # first crack
    FCE = "FCE"  # first crack end
    SC = "SC"  # second crack
    SCE = "SCE"  # second crack end
    D = "D"  # drop


class RoastSession:
    def __init__(self):
        self.start_time: datetime = datetime.now()
        self.timer: float = 0.0
        self.channels: list[Channel] = []
        self.roast_events_index = {
            RoastEvent.C: 0,
            RoastEvent.TP: 0,
            RoastEvent.DE: 0,
            RoastEvent.FC: 0,
            RoastEvent.FCE: 0,
            RoastEvent.SC: 0,
            RoastEvent.SCE: 0,
            RoastEvent.D: 0,
        }


class AppStatus(Enum):
    OFF = 1
    ON = 2
    RECORDING = 3
