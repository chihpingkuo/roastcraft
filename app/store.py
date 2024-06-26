# https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules
import asyncio
import pymodbus.client as ModbusClient
from .classes import Batch

config: dict

client: ModbusClient.AsyncModbusSerialClient

batch: Batch

loop: asyncio.AbstractEventLoop

task: asyncio.Task