import json

CONFIG1 = {'mqtt_host': '192.168.55.1',
          'serial_port': '/dev/ttyS0',
          'udp_server':'192.168.55.1',
          'udp_port': 7077, 
          'devices': {
               60  : 'WB-MDM3'
                     },
          'lights': {
              'stolovaia' : {
                  'address': 60,
                  'chanels': [0],
                  'name': 'Столовая'
                },
                'vanina_komnata' : {
                  'address': 60,
                  'chanels': [1],
                  'name': 'Ванина комната'
                },
                'spalnia' : {
                  'address': 60,
                  'chanels': [2],
                  'name': 'Спальня'
                }
                }

                     } 



CONFIG = {'mqtt_host': '192.168.55.1',
          'serial_port': '/dev/ttyS0',
          'udp_server':'192.168.55.1',
          'udp_port': 7077,
          'devices': {
               100 : 'WB_MRGBW_D',
               103 : 'WB_MRGBW_D',
               108 : 'WB_MRGBW_D'
                     },
          'lights': {
                'prikhozhaia' : {
                  'address': 108,
                  'chanels': [0],
                  'name': 'Прихожая'
                },
                'kladovaia' : {
                  'address': 108,
                  'chanels': [3],
                  'name': 'Кладовая'
                },
                'zona_tv' : {
                  'address': 100,
                  'chanels': [0,3],
                  'name': 'Зона ТВ'
                },
                'tualet_dush' : {
                  'address': 100,
                  'chanels': [1,2],
                  'name': 'Туалет/Душ'
                },
                'stoleshnitsa' : {
                  'address': 103,
                  'chanels': [3],
                  'name': 'Столешница'
                },
                'kholl' : {
                  'address': 108,
                  'chanels': [1],
                  'name': 'Холл'
                }

                     } 
          }

with open("rtu.conf", "w", encoding="utf-8") as file:
    json.dump(CONFIG, file)