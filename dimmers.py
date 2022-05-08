import asyncio
from datetime import datetime
import logging
import random

class WB_Dimmer():
    dimmer_types = ['WB_MRGBW_D', 'WB-MDM3']
    lock = False
    def __init__(self, d_type, address, client) -> None:
        if d_type in self.dimmer_types:
            self.client = client.protocol
            self.address = address
            self.log = logging.getLogger()
            if d_type == 'WB_MRGBW_D':
                self.chanels =[None,None,None,None]
                self.type = d_type
            elif d_type == 'WB-MDM3':
                self.chanels =[None,None,None]
                self.type = d_type
        else:
            raise ValueError('Unsupported dimmer type.')
        asyncio.create_task(self.sync_registers())

    def __str__(self) -> str:
        return self.type

    async def get_lock(self):
        while self.lock:
            await asyncio.sleep(0)
        self.lock = True

    async def sync_registers(self):
        while True:
            await self.get_lock()
            unsuccess = True   # проверить, возможно эту переменную можно убрать, оставив только self.lock в условии
            while unsuccess: 
                try:
                    registers = await self.client.read_holding_registers(0, len(self.chanels) , unit=self.address)
                    unsuccess = False
                    self.lock = False
                except Exception as e:
                    self.log.warning(f'Ошибка считывания данных modbus для {self.type} адрес {self.address} : {e.with_traceback}')
                    await asyncio.sleep(random.random()/2)
            for n, r in enumerate(registers.registers):
                self.chanels[n] = r
            await asyncio.sleep(random.random()*10)
    async def push_data(self, data, chanals):
            await self.get_lock()
            tmp_ch = self.chanels
            for ch in chanals:
                tmp_ch[ch] = data
            await self.get_lock()
            unsuccess = True   # проверить, возможно эту переменную можно убрать, оставив только self.lock в условии
            while unsuccess: 
                try:
                    registers = await self.client.write_registers(0, tmp_ch , unit=self.address)
                    self.log.warning(f'Успешно записали в {self.type} адрес {self.address} значения: {tmp_ch} ({list(registers.registers)})')
                    unsuccess = False
                    self.lock = False
                except Exception as e:
                    self.log.warning(f'Ошибка считывания данных modbus для {self.type} адрес {self.address} : {e.with_traceback}')
                    await asyncio.sleep(random.random()/2)