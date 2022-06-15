import asyncio
from datetime import datetime
import logging
import random
from turtle import right

class WB_Dimmer():
    dimmer_types = ['WB_MRGBW_D', 'WB-MDM3']
    lock = False
    def __init__(self, d_type, address, client) -> None:
        if d_type in self.dimmer_types:
            self.client = client
            self.address = int(address)
            self.log = logging.getLogger()
            if d_type == 'WB_MRGBW_D':
                self.chanels =[None,None,None,None]
                self.type = d_type
            elif d_type == 'WB-MDM3':
                self.chanels =[None,None,None]
                self.type = d_type
        else:
            raise ValueError('Unsupported dimmer type.')

    def __str__(self) -> str:
        return self.type

    async def get_update(self, wd=0):
        await self.get_lock()
        count = 0
        while self.lock:
            try:
                response = await self.client.read_holding_registers(0, len(self.chanels) , unit=int(self.address))
                for n, reg in enumerate(response.registers):
                    self.chanels[n] = int(reg)
                self.lock = False
            except Exception as e:
                self.log.info(f'Ошибка считывания данных modbus для {self.type} адрес {self.address} : {e.with_traceback}')
                if wd > 0:
                   count = count + 1
                if (wd - count) < 0:
                    self.lock = False
                    return 1
                await asyncio.sleep(0)
        return 0

    async def get_lock(self):
        self.log.debug(f'Получена блокировка')
        while self.lock:
            await asyncio.sleep(0)
        self.lock = True

    async def push_data(self, data, chanals, wd=0):
            count = 0
            self.log.info(f'Новые данные для {self.address} канал {chanals} : {data}')
            await self.get_lock()
            tmp_ch = self.chanels
            self.log.debug(f'Старые значения каналов {tmp_ch}')
            for ch in chanals:
                if (self.type == 'WB-MDM3') and (data > 100):
                    tmp_ch[ch] = 100    
                else:
                    tmp_ch[ch] = data
            self.log.debug(f'Новые значения каналов {tmp_ch}')
            while self.lock:
                try:
                    registers = await self.client.write_registers(0, tmp_ch , unit=int(self.address))
                    self.log.debug(f'Успешно записали в {self.type} адрес {self.address} значения: {tmp_ch}')
                    self.chanels = tmp_ch
                    self.lock = False
                    self.log.debug(f'Снята блокировка')
                except Exception as e:
                    self.log.info(f'Ошибка записи данных modbus для {self.type} адрес {self.address} : {e.with_traceback}')
                    if wd > 0:
                        count = count + 1
                    if (wd - count) < 0:
                        self.lock = False
                        return 1
                    await asyncio.sleep(random.random()/2)
            return 0