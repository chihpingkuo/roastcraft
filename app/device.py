import codecs
import ast
from typing import Any, Dict
import pymodbus.client as ModbusClient
from pymodbus import FramerType, ModbusException
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder


class Device:

    async def connect(self) -> bool:
        return False

    async def close(self) -> bool:
        return False

    async def read(self) -> dict:
        return {}


class ArtisanLog(Device):
    def __init__(self, filename: str) -> None:

        self.filename: str = filename
        self.bt: list[float] = []
        self.et: list[float] = []
        self.inlet: list[float] = []

    async def connect(self) -> bool:
        with codecs.open(self.filename, "rb", encoding="utf-8") as file:

            result: Dict[str, Any] = ast.literal_eval(file.read())

            self.bt: list[float] = result["temp2"]
            self.et: list[float] = result["temp1"]
            self.inlet: list[float] = result["extratemp1"][0]
            return True

    async def close(self) -> bool:
        return True

    async def read(self) -> dict:
        if len(self.bt) > 0:
            return {
                "BT": self.bt.pop(0),
                "ET": self.et.pop(0),
                "INLET": self.inlet.pop(0),
            }
        return {}


class Kapok501(Device):
    def __init__(self, port: str) -> None:
        self.port = port
        self.client = None

    async def connect(self) -> bool:
        if self.client is None:
            self.client = ModbusClient.AsyncModbusSerialClient(
                self.port,
                framer=FramerType.ASCII,
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
        await self.client.connect()
        return True

    async def close(self) -> bool:
        self.client.close()
        return True

    async def read(self) -> Dict:
        async def read(slave: int) -> float:

            try:
                # See all calls in client_calls.py
                rr = await self.client.read_holding_registers(18176, 1, slave)
            except ModbusException as e:
                print(f"Received ModbusException({e}) from library")
                return

            value: float = (
                BinaryPayloadDecoder.fromRegisters(
                    rr.registers, byteorder=Endian.BIG, wordorder=Endian.BIG
                ).decode_16bit_int()
                * 0.1
            )
            return value

        bt = await read(slave=2)
        et = await read(slave=1)
        inlet = await read(slave=3)
        return {"BT": bt, "ET": et, "INLET": inlet}
