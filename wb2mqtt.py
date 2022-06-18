import asyncio, logging, signal, json, argparse, sys
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusClient
from pymodbus.client.asynchronous import schedulers
from dimmers import WB_Dimmer
from HA_lights import WB_Light
from datetime import datetime
from gmqtt import Client as MQTTClient
import uvloop
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
#read settings from configuration file (json)

LOG_LEVEL = logging.INFO
exit_status = 0

def createParser ():
    parser = argparse.ArgumentParser()
    parser.add_argument ('-c', '--config', default='settings.conf')
    return parser
parser = createParser()

with open(parser.parse_args().config) as f:
        CONFIG = json.load(f)
if CONFIG.get('serial_port', False):
    from pymodbus.client.asynchronous.serial import (AsyncModbusSerialClient as ModbusClient)
elif CONFIG.get('modbus_tcp_server', False):
    from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusClient
elif CONFIG.get('mqtt_host') is None:
    sys.exit("В конфигурационном файле не обнаружен адрес MQTT сервера")
elif CONFIG.get('udp_server') is None:
    sys.exit("В конфигурационном файле не обнаружен адрес UDP сервера")
elif CONFIG.get('udp_port') is None:
    sys.exit("В конфигурационном файле не обнаружен адрес UDP порта")
else:
    sys.exit("В конфигурационном файле не обнаружен протокол по которому будем общаться с устройствами")




asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

f_name = f"wb{CONFIG['udp_port']}.log"
try:
    logging.basicConfig(filename=f_name,filemode='a',level = LOG_LEVEL)
except:
    with open(f_name,'w') as f:
        f.write(f_name)
        logging.basicConfig(filename=f_name,filemode='a',level = LOG_LEVEL)

log = logging.getLogger()

STOP = asyncio.Event()

WB_DIMMERS = {}
WB_LIGHTS = {}
SENSORS = {}

mqtt = MQTTClient("wirenboardlight-"+str(CONFIG['udp_port']))

async def on_message(client, topic, payload, qos, properties):
    log.debug('[RECV MSG {}] TOPIC: {} PAYLOAD: {} QOS: {} PROPERTIES: {}'
                 .format(client._client_id, topic, payload, qos, properties))
    result = 0
    for light in WB_LIGHTS:
        if topic == f'{WB_LIGHTS[light].topic}/set':
            try:
                message = json.loads(str(payload, 'utf-8'))
                if ('brightness' in message):
                    result = await WB_LIGHTS[light].set_brightness(message['brightness'])
                if ('state' in message):
                    if message['state'] == 'ON':
                        result = await WB_LIGHTS[light].on()
                    else:
                        result = await WB_LIGHTS[light].off()
                if result > 0:
                    exit_status = 1
                    log.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Многократная ошибка записи в modbus, выходим для перезапуска\n")
                    STOP.set()                
                mqtt.publish(f'{WB_LIGHTS[light].topic}/state', WB_LIGHTS[light].to_json(),qos=1)
            except:
                log.warning('ERROR JSON DECODE WITH [RECV MSG {}] TOPIC: {} PAYLOAD: {} QOS: {} PROPERTIES: {}'
                 .format(client._client_id, topic, payload, qos, properties))
    return 0                    

mqtt.on_message = on_message


def ask_exit(*args):
    log.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Start exitin by user request\n")
    STOP.set()

class UDPWorker:
    def connection_made(self, transport):
        self.transport = transport
        log.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Создали udp server")

    def datagram_received(self, data, addr):
        log.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - UDP packet from {addr} sensor {data[0]} light {(data[4] << 24) | (data[3] << 16) | (data[2] << 8) | data[1]} increment {int.from_bytes([data[6],data[5]], byteorder='big', signed=True)}")
        id_light = (data[4] << 24) | (data[3] << 16) | (data[2] << 8) | data[1]
        for light in WB_LIGHTS:
            if (WB_LIGHTS[light].unique_id()//10 == id_light):
                WB_LIGHTS[light].brightness_increment = WB_LIGHTS[light].brightness_increment + int.from_bytes([data[6],data[5]], byteorder='big', signed=True)
                log.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Для светильника {WB_LIGHTS[light].unique_id()//10} увеличить яркость на {WB_LIGHTS[light].brightness_increment}") 
           


async def init_loop(loop, client):
    server_socket = socket(AF_INET, SOCK_DGRAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(('', CONFIG['udp_port']))
    transport, _ = await loop.create_datagram_endpoint(lambda: UDPWorker(), sock=server_socket)
    await mqtt.connect(CONFIG['mqtt_host'])

    # Создаем сущности физических димеров согласно конфигурационному файлу
    for addr in CONFIG['devices']:
        WB_DIMMERS[int(addr)] = WB_Dimmer(CONFIG['devices'][addr], addr, client)
        if await WB_DIMMERS[int(addr)].get_update(wd=5):
            raise ValueError('Не смогли получить от диммера текущие состояния регистров')
        log.info(f"Создали объект диммера адрес: {addr}, тип: {CONFIG['devices'][addr]}")
        
    # Создаем логические светильники с нужным количеством каналов диммера
    log.info(f"Диммеры: {WB_DIMMERS}")
    for name in CONFIG['lights']:
        log.info(f"Имя {name}")
        log.info(f"Адрес {CONFIG['lights'][name]['address']}")
        log.info(f"Каналы {CONFIG['lights'][name]['chanels']}")
        log.info(f"Диммер {WB_DIMMERS[CONFIG['lights'][name]['address']]}")
        WB_LIGHTS[name] = WB_Light(WB_DIMMERS[CONFIG['lights'][name]['address']], CONFIG['lights'][name]['chanels'], name, 'englishmile/light/', CONFIG['lights'][name]['name'])
        if WB_LIGHTS[name].state:
            await WB_LIGHTS[name].on()
        asyncio.create_task(WB_LIGHTS[name].sync_brightness())
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
    transport.close()
    await mqtt.disconnect()
    server_socket.close()
    if exit_status > 0:
        sys.exit(1)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)
    if CONFIG.get('serial_port', False):
       log.warning(f'Запускаем соединение по протоколу Modbus RTU')
       loop, client = ModbusClient(schedulers.ASYNC_IO, port=CONFIG['serial_port'], baudrate=9600, method="rtu", bytesize=8, stopbits=2, parity = 'N')
    elif CONFIG.get('modbus_tcp_server', False):
        log.warning(f'Запускаем соединение по протоколу Modbus TCP')
        loop, client = ModbusClient(schedulers.ASYNC_IO, host=CONFIG['modbus_tcp_server'], port=23, loop=loop)
    else:
        sys.exit("В конфигурационном файле не обнаружен протокол по которому будем общаться с устройствами")
    loop.run_until_complete(init_loop(loop, client,))