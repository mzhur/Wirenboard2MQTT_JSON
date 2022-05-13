import asyncio, logging, signal, json, uvloop
from pymodbus.client.asynchronous.serial import (AsyncModbusSerialClient as ModbusClient)
from pymodbus.client.asynchronous import schedulers
from asyncudp import open_local_endpoint
from dimmers import WB_Dimmer
from HA_lights import WB_Light
from gmqtt import Client as MQTTClient
from datetime import datetime

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)
STOP = asyncio.Event()
WB_DIMMERS = {}
WB_LIGHTS = {}

#read settings from configuration file (json)
with open('settings.conf') as f:
        CONFIG = json.load(f)



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
        WB_DIMMERS[int(addr)] = WB_Dimmer(CONFIG['devices'][addr], addr, client) # раскомментировать client для работы с modbus
        WB_DIMMERS[int(addr)].run_sync()
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
                WB_LIGHTS[name] = WB_Light(WB_DIMMERS[CONFIG['lights'][name]['address']], CONFIG['lights'][name]['chanels'], name, 'englishmile/light/')
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
        mqtt.subscribe(f'{WB_LIGHTS[name].topic}', qos=2)
        mqtt.subscribe(f'{WB_LIGHTS[name].topic}/set', qos=2)
        mqtt.publish(f'homeassistant/light/{name}/config', WB_LIGHTS[name].to_json('init'), retain=True)
        log.info(f'Опубликовали: {WB_LIGHTS[name].to_json("init")}')
        mqtt.publish(f'{WB_LIGHTS[name].topic}/state', WB_LIGHTS[name].to_json(), retain=True)
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