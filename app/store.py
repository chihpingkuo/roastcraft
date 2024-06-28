# https://docs.python.org/3/faq/programming.html#how-do-i-share-global-variables-across-modules
import asyncio
import pymodbus.client as ModbusClient
from app.classes import RoastSession
from app.device import Device

settings: dict

client: ModbusClient.AsyncModbusSerialClient

device: Device

roast_session: RoastSession

loop: asyncio.AbstractEventLoop

read_device_task: asyncio.Task
update_timer_task: asyncio.Task
