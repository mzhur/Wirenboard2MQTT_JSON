import asyncio, json
from dimmers import WB_Dimmer

class WB_Light():
    def __init__(self, dimmer, chanels, name, topic) -> None:
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
        if self.dimmer.type == 'WB_MRGBW_D':
            self.brightness = 255
        else:
            self.brightness = 100
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
    def on(self, brightness=None):
        self.state = True
        if brightness is None:
            brightness = self.brightness
        asyncio.create_task(self.dimmer.push_data(brightness, self.chanels))
            
    def off(self):
        self.state = False
        asyncio.create_task(self.dimmer.push_data(0, self.chanels))

    def set_brightness(self, brightness):
        self.brightness = brightness
        if self.state:
            asyncio.create_task(self.dimmer.push_data(brightness, self.chanels))
    
    def to_json(self, type='state'):
        if type == 'init':
            return json.dumps({'~': self.topic, 'name': self.name, 'unique_id': f'{self.name}_{self.dimmer.address}_{str(self.chanels)}', 'cmd_t': '~/set', 'stat_t': '~/state', 'schema': 'json', 'brightness': True})
        else:
            if self.state:
                return json.dumps({'brightness': self.brightness, 'state': 'ON'})
            else:
                return json.dumps({'brightness': self.brightness, 'state': 'OFF'})
