#!/usr/bin/env python
import requests
import time

time.sleep(2)

try:
    r = requests.get('http://localhost:5000/api/printers', timeout=5)
    print(f'Status: {r.status_code}')
    data = r.json()
    print(f'Printers: {len(data)}')
    for p in data:
        print(f'  - {p["printer_name"]} (ID: {p["printer_id"]})')
except Exception as e:
    print(f'Error: {e}')
