import urllib.request, json

base = 'http://192.168.4.67:5051'

# Get printers list
resp = urllib.request.urlopen(base + '/api/printers', timeout=5)
printers = json.loads(resp.read())
print('=== Printers ===')
for p in printers:
    pid = p.get('printer_id') or p.get('id', '?')
    name = p.get('name', '?')
    bed_temp = p.get('bed_temp', 'N/A')
    bed_target = p.get('bed_target_temp', 'N/A')
    status = p.get('status', '?')
    print(f'  printer_id={pid} | name={name} | bed_temp={bed_temp} | bed_target={bed_target} | status={status}')

    # Bed cooling status
    try:
        r = urllib.request.urlopen(f'{base}/api/printers/{pid}/bed-cooling/status', timeout=5)
        cooling = json.loads(r.read())
        print(f'    cooling: is_cooling={cooling.get("is_cooling")} | kit_enabled={cooling.get("kit_enabled")} | kit_ip={cooling.get("kit_ip")} | start_temp={cooling.get("start_temp")} | target_temp={cooling.get("target_temp")} | elapsed={cooling.get("elapsed_seconds")}s')
    except Exception as e:
        print(f'    cooling status error: {e}')

# Check fan state from Orange Pi directly
print('\n=== Fan (Orange Pi 192.168.4.197) ===')
try:
    r2 = urllib.request.urlopen('http://192.168.4.197:5000/kit/fan?state=status', timeout=5)
    fan = json.loads(r2.read())
    print(f'  status={fan.get("status")} | state={fan.get("state")}')
except Exception as e:
    print(f'  error: {e}')
