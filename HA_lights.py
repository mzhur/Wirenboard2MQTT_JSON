import asyncio, json
from base64 import encode
from unittest import result
from binascii import crc32
from dimmers import WB_Dimmer
import logging

class WB_Light():
    def __init__(self, dimmer, chanels, name, topic, frendly_name) -> None:
        if not isinstance(dimmer, WB_Dimmer):
            raise ValueError('The dimmer is not wirebboard dimmer object.')
        if isinstance(chanels, int):
            self.chanels = [chanels]
        elif isinstance(chanels, list):
            self.chanels = chanels
        else:
            raise ValueError('The chanels data must be int or list')
        self.dimmer = dimmer
        self.topic = topic + name
        self.state = False
        self.log = logging.getLogger()
        self.brightness_increment = 0
        if self.dimmer.type == 'WB_MRGBW_D':
            self.brightness = 255
            self.brightness_scale = 255
        else:
            self.brightness = 100
            self.brightness_scale = 100
        try:
            for ch in self.chanels:
                tmp = dimmer.chanels[ch]
                if (tmp is None):
                    raise ValueError('Диммер не успел получить данные по modbus. Возможно не запущена задача синхнонизации? Попробуйте снова создать класс через несколько секунд.')   
                elif int(tmp) > 0:
                    self.state = True
                    self.brightness = tmp
        except Exception as e:
                raise ValueError(f'Возможно испльзован недопустимый канал {self.chanels} для данного диммера? {self.dimmer.type}. : {e.with_traceback}')
        self.name = name
        self.frendly_name = frendly_name

    async def on(self):
        self.log.info(f'Включаем светильник {self.name} адрес {self.dimmer.address} : {self.chanels} яркость {self.brightness}')
        self.state = True
        await self.dimmer.push_data(self.brightness, self.chanels)
        return 0
            
    async def off(self):
        self.log.info(f'Выключаем светильник {self.name} адрес {self.dimmer.address} : {self.chanels} яркость {self.brightness}')
        self.state = False
        await self.dimmer.push_data(0, self.chanels)
        return 0

    async def set_brightness(self, brightness):
        self.log.info(f'Устанавливаем яркость {brightness} для светильник {self.name} адрес {self.dimmer.address} : {self.chanels}')
        self.brightness = brightness
        if self.state:
            await self.on()
        return 0

    async def sync_brightness(self):
        while True:
            if self.brightness_increment != 0:
                if (self.brightness + self.brightness_increment) < 1:
                   self.brightness = 1
                   self.log.info(f"Для светильника {self.unique_id()//10} Записываем в модбас 1")
                elif (self.brightness + self.brightness_increment) > self.brightness_scale:
                    self.brightness = self.brightness_scale
                    self.log.info(f"Для светильника {self.unique_id()//10} Записываем в модбас {self.brightness_scale}")
                else:
                    self.log.info(f"Для светильника {self.unique_id()//10} Записываем в модбас {self.brightness + self.brightness_increment}")
                    self.brightness = self.brightness + self.brightness_increment
                self.brightness_increment = 0
                if self.state:
                    await self.dimmer.push_data(self.brightness, self.chanels)
                else:
                    await asyncio.sleep(0)
            else:
                await asyncio.sleep(0)
        self.log.info(f"Для светильника {self.unique_id()//10} Завершили синхронизацию")

    def unique_id(self):
        return crc32(bytes(f'{self.name}_{self.dimmer.address}_{str(self.chanels)}', encoding='utf-8'))
    
    def to_json(self, type='state'):
        if type == 'init':
            return json.dumps({'~': self.topic, 'object_id': self.name, 'name': self.frendly_name, 'unique_id': self.unique_id(), 'brightness_scale': self.brightness_scale, 'cmd_t': '~/set', 'stat_t': '~/state', 'schema': 'json', 'brightness': True})
        else:
            if self.state:
                return json.dumps({'brightness': self.brightness, 'state': 'ON'})
            else:
                return json.dumps({'brightness': self.brightness, 'state': 'OFF'})
