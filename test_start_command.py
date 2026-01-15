#!/usr/bin/env python3
import requests
import time

file_path = 'data/uploads/A1 Tilt Kit _PETG_7h55m.gcode.3mf'
with open(file_path, 'rb') as f:
    r = requests.post('http://localhost:5000/api/jobs/upload', files={'file': f})
    job_id = r.json()['job_id']
    print(f'Uploaded Job ID: {job_id}')

# Queue
r = requests.post('http://localhost:5000/api/queue/add', json={'job_id': job_id, 'printer_id': '03900D5A2402051'})
print(f'Queue add: {r.status_code}')

# Start
r = requests.post('http://localhost:5000/api/print-control/03900D5A2402051/start-print')
print(f'Start response: {r.status_code}')
print(f'Response: {r.json()}')

# Wait and check
time.sleep(3)
r = requests.get('http://localhost:5000/api/print-control/03900D5A2402051/mqtt-status')
status = r.json()
print(f'Printer status: {status["printer_status"]} - Progress: {status["print_progress"]}%')
