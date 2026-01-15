#!/usr/bin/env python3
"""Test print flow: upload job -> add to queue -> start printing"""

import requests
import json
import time

BASE_URL = 'http://localhost:5000/api'

# Get printers
print("=" * 60)
print("STEP 1: Get available printers")
print("=" * 60)
printers_resp = requests.get(f'{BASE_URL}/printers')
if printers_resp.status_code != 200:
    print(f"ERROR: Failed to get printers: {printers_resp.status_code}")
    exit(1)

printers = printers_resp.json()['printers']
printer_id = printers[0]['printer_id']
print(f"✓ Using printer: {printers[0]['printer_name']} (ID: {printer_id})")

# Get existing jobs
print("\n" + "=" * 60)
print("STEP 2: Get available jobs")
print("=" * 60)
jobs_resp = requests.get(f'{BASE_URL}/jobs')
jobs = jobs_resp.json().get('jobs', [])

if not jobs:
    print("ERROR: No jobs found - please upload a job first via web UI")
    exit(1)

job_id = jobs[0]['job_id']
print(f"✓ Using job: {jobs[0]['job_name']} (ID: {job_id})")

# Add to queue
print("\n" + "=" * 60)
print("STEP 3: Add job to queue")
print("=" * 60)
queue_resp = requests.post(f'{BASE_URL}/queue/add', json={
    'job_id': job_id,
    'printer_id': printer_id
})

if queue_resp.status_code != 200:
    print(f"ERROR: Failed to add to queue: {queue_resp.status_code}")
    print(f"Response: {queue_resp.text}")
    exit(1)

queue_data = queue_resp.json()
queue_id = queue_data.get('queue_id')
position = queue_data.get('position_in_queue', 'N/A')
print(f"✓ Added to queue!")
print(f"  Queue ID: {queue_id}")
print(f"  Position: {position}")

# Get queue status before start
print("\n" + "=" * 60)
print("STEP 4: Get queue status (before start)")
print("=" * 60)
queue_status = requests.get(f'{BASE_URL}/queue/{printer_id}')
if queue_status.status_code == 200:
    items = queue_status.json().get('queue_items', [])
    print(f"Queue has {len(items)} items:")
    for item in items:
        print(f"  - {item.get('job_name')} (status: {item.get('status')})")

# Start the job
print("\n" + "=" * 60)
print("STEP 5: Start queue job")
print("=" * 60)
start_resp = requests.post(f'{BASE_URL}/queue/{queue_id}/start')

if start_resp.status_code != 200:
    print(f"ERROR: Failed to start: {start_resp.status_code}")
    print(f"Response: {start_resp.text}")
    exit(1)

print(f"✓ Started queue job!")
print(f"Response: {start_resp.json()}")

# Get queue status after start
print("\n" + "=" * 60)
print("STEP 6: Get queue status (after start)")
print("=" * 60)
time.sleep(1)
queue_status = requests.get(f'{BASE_URL}/queue/{printer_id}')
if queue_status.status_code == 200:
    items = queue_status.json().get('queue_items', [])
    print(f"Queue has {len(items)} items:")
    for item in items:
        print(f"  - {item.get('job_name')}")
        print(f"    Status: {item.get('status')}")
        print(f"    Position: {item.get('position_in_queue')}")

print("\n" + "=" * 60)
print("✓ PRINT FLOW TEST COMPLETE!")
print("=" * 60)
