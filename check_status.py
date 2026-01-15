import requests
r = requests.get('http://localhost:5000/api/print-control/03900D5A2402051/mqtt-status')
status = r.json()
print(f"Printer: {status['printer_status']} | Progress: {status['print_progress']}%")
if 'nozzle_temp' in status:
    print(f"Nozzle: {status['nozzle_temp']}°C")
