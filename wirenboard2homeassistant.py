import asyncio, logging, signal #, uvloop
from pymodbus.client.asynchronous.serial import (AsyncModbusSerialClient as ModbusClient)
from pymodbus.client.asynchronous import schedulers
from asyncudp import open_local_endpoint
from dimmers import WB_Dimmer
from gmqtt import Client as MQTTClient
from datetime import datetime

#asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)
STOP = asyncio.Event()
WB_DIMMERS = {}
WB_LIGHTS = {}
CONFIG = {'mqtt_host': '192.168.55.1',
          'serial_port': '/dev/ttyS0',
          'devices': {
               100 : 'WB_MRGBW_D',
               103 : 'WB_MRGBW_D',
               108 : 'WB_MRGBW_D',
               60  : 'WB-MDM3'
                     },
          'lights': {
              'test_stolovaya' : {
                  'address': 60,
                  'chanels': [0]
                },
                'test_vanyna_komnata' : {
                  'address': 60,
                  'chanels': [1]
                },
                'test_spalnia' : {
                  'address': 60,
                  'chanels': [2]
                },
                'test_prohojia' : {
                  'address': 108,
                  'chanels': [0]
                },
                'test_kladovaia' : {
                  'address': 108,
                  'chanels': [3]
                },
                'test_zona_tv' : {
                  'address': 100,
                  'chanels': [0,3]
                },
                'test_wc' : {
                  'address': 100,
                  'chanels': [1,2]
                },
                'test_stoleshnitsa' : {
                  'address': 103,
                  'chanels': [3]
                },
                'test_kholl' : {
                  'address': 108,
                  'chanels': [1]
                }

                     } 
          }


class WB_Light():
    def __init__(self, dimmer, chanels, name) -> None:
        if not isinstance(dimmer, WB_Dimmer):
            raise ValueError('The dimmer is not wirebboard dimmer object.')
        if isinstance(chanels, int):
            self.chanels = [chanels]
        elif isinstance(chanels, list):
            self.chanels = chanels
        else:
            raise ValueError('The chanels data must be int or list')
        self.dimmer = dimmer
        self.topic = f'englishmile/light/{name}'
        self.state = False
        if self.dimmer.type == 'WB_MRGBW_D':
            self.brightness = 255
        else:
            self.brightness = 100
        try:
            for ch in self.chanels:
                tmp = dimmer.chanels[ch]
                if (tmp is None):
                    raise ValueError('Dimmer dont initializing data. please wait several seconds')   
                elif int(tmp) > 0:
                    self.state = True
                    self.brightness = tmp
        except Exception as e:
                raise ValueError('Unaxepteble chanel for dimmer instance.')
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
            return '{' + f'"~": "englishmile/light/{self.name}", "name": "{self.name}", "unique_id": "{self.name}_{self.dimmer.address}_{str(self.chanels)}", "cmd_t": "~/set", "stat_t": "~/state", "schema": "json", "brightness": true, ' + '"availability_topic": "etrv/state", "payload_available": "online", "payload_not_available": "offline"}' 
        else:
            if self.state:
                return '{"brightness": %s, "state": "ON",}' % str(self.brightness)
            else:
                return '{"brightness": %s, "state": "OFF",}' % str(self.brightness)

#Определяем основные функции для MQTT клиента
def on_connect(client, flags, rc, properties):
    log.debug(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Connecfileted\n")
    
def on_message(client, topic, payload, qos, properties):
    log.warning(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Message in topic: {topic} with content: {str(payload, 'utf-8')}\n")
            
def on_disconnect(client, packet, exc=None):
    log.debug(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Disconected\n")
    


def on_subscribe(client, mid, qos, properties):
    log.debug(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Subscribed to topic\n")
    

def ask_exit(*args):
    log.debug(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Start exitin by user request\n")
    STOP.set()



async def init_loop(loop, client):
      
    # Создаем сущности физических димеров согласно конфигурационному файлу
    for addr in CONFIG['devices']:
        WB_DIMMERS[addr] = WB_Dimmer(CONFIG['devices'][addr], addr, client) # раскомментировать client для работы с modbus
        log.info(f"Создали объект диммера адрес: {addr}, тип: {CONFIG['devices'][addr]}")
    # Создаем логические светильники с нужным количеством каналов диммера
    log.info(f"Диммеры: {WB_DIMMERS}")
    for name in CONFIG['lights']:
        log.info(f"Имя {name}")
        log.info(f"Адрес {CONFIG['lights'][name]['address']}")
        log.info(f"Каналы {CONFIG['lights'][name]['chanels']}")
        log.info(f"Диммер {WB_DIMMERS[CONFIG['lights'][name]['address']]}")
        unsuccess = True
        while unsuccess:
            try:
                WB_LIGHTS[name] = WB_Light(WB_DIMMERS[CONFIG['lights'][name]['address']], CONFIG['lights'][name]['chanels'], name)
                unsuccess = False
            except Exception as e:
                log.info(e)
                await asyncio.sleep(1)
        log.info(f"Создали объект светильника имя: {name}, адрес: {CONFIG['lights'][name]['address']}, каналы {CONFIG['lights'][name]['chanels']}")
    # Публикуем их для Home Assistant
    mqtt = MQTTClient("Lights")
    mqtt.on_connect = on_connect
    mqtt.on_message = on_message
    mqtt.on_disconnect = on_disconnect
    mqtt.on_subscribe = on_subscribe
    log.info(f'Подключаемся: {CONFIG["mqtt_host"]}')
    await mqtt.connect(str(CONFIG["mqtt_host"]))
    for name in WB_LIGHTS:
        mqtt.subscribe(f'{WB_LIGHTS[name].topic}', qos=0)
        mqtt.subscribe(f'{WB_LIGHTS[name].topic}/set', qos=2)
        mqtt.publish(f'homeassistant/light/{name}/config', WB_LIGHTS[name].to_json('init'), qos=2, retain=True)
        log.info(f'Опубликовали: {WB_LIGHTS[name].to_json("init")}')
        mqtt.publish(f'homeassistant/light/{name}/state', WB_LIGHTS[name].to_json(), qos=2, retain=True)
        log.info(f'Опубликовали состояние: {WB_LIGHTS[name].to_json()}')


    await STOP.wait()
    await mqtt.disconnect()
    while True:
        for ent in WB_LIGHTS:
            log.info(f'Светильник {ent} mqtt {WB_LIGHTS[ent].state} : {WB_LIGHTS[ent].brightness}')
        await asyncio.sleep(30)
    

if __name__ == '__main__':
    print('Начали')
    loop, client = ModbusClient(schedulers.ASYNC_IO, port='/dev/ttyS0', baudrate=9600, method="rtu", bytesize=8, stopbits=2, parity = 'N', timeout=0.5)
    loop.add_signal_handler(signal.SIGINT, ask_exit())
    loop.add_signal_handler(signal.SIGTERM, ask_exit())
    loop.run_until_complete(init_loop(loop, client))