import json
with open('settings.conf') as f:
    templates = json.load(f)
print(type(templates))
for item in templates:
    print(type(item), ' : ', item, ' : ', type(templates[item]), ' : ', templates[item])
