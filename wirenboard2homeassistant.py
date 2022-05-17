import asyncio, logging, signal, json
from pymodbus.client.asynchronous.serial import (AsyncModbusSerialClient as ModbusClient)
from pymodbus.client.asynchronous import schedulers
from asyncudp import open_local_endpoint
from dimmers import WB_Dimmer
from HA_lights import WB_Light
from datetime import datetime
import uvloop
from gmqtt import Client as MQTTClient

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

STOP = asyncio.Event()

WB_DIMMERS = {}
WB_LIGHTS = {}

mqtt = MQTTClient("wirenboardlight")

async def on_message(client, topic, payload, qos, properties):
    logging.debug('[RECV MSG {}] TOPIC: {} PAYLOAD: {} QOS: {} PROPERTIES: {}'
                 .format(client._client_id, topic, payload, qos, properties))
    for light in WB_LIGHTS:
        if topic == f'{WB_LIGHTS[light].topic}/set':
            message = json.loads(str(payload, 'utf-8'))
            if ('brightness' in message):
                await WB_LIGHTS[light].set_brightness(message['brightness'])
            if ('state' in message):
                if message['state'] == 'ON':
                    await WB_LIGHTS[light].on()
                else:
                    await WB_LIGHTS[light].off()
            

            mqtt.publish(f'{WB_LIGHTS[light].topic}/state', WB_LIGHTS[light].to_json())
    return 0                    

mqtt.on_message = on_message

#read settings from configuration file (json)
with open('settings.conf') as f:
        CONFIG = json.load(f)


def ask_exit(*args):
    log.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Start exitin by user request\n")
    STOP.set()



async def init_loop(loop, client):
    

    await mqtt.connect(CONFIG['mqtt_host'])

    # Создаем сущности физических димеров согласно конфигурационному файлу
    for addr in CONFIG['devices']:
        WB_DIMMERS[int(addr)] = WB_Dimmer(CONFIG['devices'][addr], addr, client) # раскомментировать client для работы с modbus
        asyncio.create_task(WB_DIMMERS[int(addr)].sync_registers())
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

    log.info(f'Подключаемся: {CONFIG["mqtt_host"]}')
    
    for name in WB_LIGHTS:
        log.info(f'Подписываемся: {WB_LIGHTS[name].topic}/set')
        mqtt.subscribe(WB_LIGHTS[name].topic + '/set', qos=2)
        mqtt.publish(f'homeassistant/light/{name}/config', WB_LIGHTS[name].to_json('init'), retain=True)
        log.info(f'Опубликовали: {WB_LIGHTS[name].to_json("init")}')
        mqtt.publish(f'{WB_LIGHTS[name].topic}/state', WB_LIGHTS[name].to_json(), retain=True)
        log.info(f'Опубликовали состояние: {WB_LIGHTS[name].to_json()}')

    await STOP.wait()
    #while True:
    #    log.info('tic')
    #    asyncio.sleep(30)
    await mqtt.disconnect()


if __name__ == '__main__':
    print('Начали')
    loop, client = ModbusClient(schedulers.ASYNC_IO, port='/dev/ttyS0', baudrate=9600, method="rtu", bytesize=8, stopbits=2, parity = 'N', timeout=0.5)
    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)
    loop.run_until_complete(init_loop(loop, client,))

