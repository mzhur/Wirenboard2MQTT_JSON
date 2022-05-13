import json
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

with open("settings.conf", "w", encoding="utf-8") as file:
    json.dump(CONFIG, file)