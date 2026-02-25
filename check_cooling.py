import urllib.request, json
base = 'http://192.168.4.67:5051'
pid = 'BAMBU_192_168_4_101'

# Bed cooling status
resp = urllib.request.urlopen(base + '/api/printers/' + pid + '/bed-cooling/status', timeout=5)
cooling = json.loads(resp.read())
print('=== Bed Cooling Status ===')
for k, v in cooling.items():
    print('  ' + str(k) + ' : ' + str(v))

# Fan state from Orange Pi
print()
print('=== Fan (Orange Pi 192.168.4.197) ===')
resp2 = urllib.request.urlopen('http://192.168.4.197:5000/kit/fan?state=status', timeout=5)
fan = json.loads(resp2.read())
print('  status : ' + str(fan.get('status')))
print('  state  : ' + str(fan.get('state')))
