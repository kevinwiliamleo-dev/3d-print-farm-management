import requests
r = requests.get('http://localhost:5000/api/print-control/03900D5A2402051/mqtt-status')
data = r.json()
print(f"Remaining Time: {data.get('remaining_time', 'N/A')}")
print(f"Current File: {data.get('current_file', 'N/A')}")
print(f"Progress: {data.get('progress', 'N/A')}")
print(f"Status: {data.get('printer_status', 'N/A')}")
