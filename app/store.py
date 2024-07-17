# https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules
import asyncio
import pymodbus.client as ModbusClient
from app.classes import AppState
from app.device import Device

settings: dict

client: ModbusClient.AsyncModbusSerialClient

device: Device

app_state: AppState

loop: asyncio.AbstractEventLoop

read_device_task: asyncio.Task
update_timer_task: asyncio.Task
