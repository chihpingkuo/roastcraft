import codecs
import ast
from typing import Any, Dict


class Device:

    def connect(self) -> bool:
        return False

    def read(self) -> dict:
        return {}


class ArtisanLog(Device):
    def __init__(self, filename: str):

        self.filename: str = filename
        self.bt: list[float] = []
        self.et: list[float] = []
        self.inlet: list[float] = []

    def connect(self) -> bool:
        with codecs.open(self.filename, "rb", encoding='utf-8') as file:

            result: Dict[str, Any] = ast.literal_eval(file.read())

            self.bt: list[float] = result['temp2']
            self.et: list[float] = result['temp1']
            self.inlet: list[float] = result['extratemp1'][0]
            return True

    def read(self) -> dict:
        if len(self.bt) > 0:
            return {
                "BT": self.bt.pop(0),
                "ET": self.et.pop(0),
                "INLET": self.inlet.pop(0)
            }
        return {}
