# https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules
import asyncio
import pymodbus.client as ModbusClient
from app.classes import Batch
from app.device import Device

settings: dict

client: ModbusClient.AsyncModbusSerialClient

device: Device

batch: Batch

loop: asyncio.AbstractEventLoop

task: asyncio.Task

