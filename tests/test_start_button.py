"""
Quick test: Upload file → Add to queue → Check status → Wait for user to click button
"""
import requests
import sys

BASE_URL = "http://localhost:5000"
PRINTER_ID = "03900D5A2402051"
TEST_FILE = "data/uploads/SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf"

print("="*60)
print("  QUICK START NEXT JOB TEST")
print("="*60)

# Step 1: Clear queue
print("\n📋 Step 1: Clearing queue...")
try:
    response = requests.get(f"{BASE_URL}/api/queue/{PRINTER_ID}")
    queue_data = response.json()
    for item in queue_data.get('queue_items', []):
        if item.get('status') == 'pending':
            queue_id = item.get('queue_id')
            print(f"   Removing queue_id={queue_id}")
            requests.delete(f"{BASE_URL}/api/queue/{queue_id}")
    print("✅ Queue cleared")
except Exception as e:
    print(f"❌ Error clearing queue: {e}")

# Step 2: Upload file
print("\n📤 Step 2: Uploading test file...")
try:
    with open(TEST_FILE, 'rb') as f:
        files = {'file': ('SpeedBoat.3mf', f, 'application/octet-stream')}
        data = {'loop_count': 1}
        response = requests.post(f'{BASE_URL}/api/jobs/upload', files=files, data=data)
        
    if response.status_code == 200:
        job = response.json()
        job_id = job['job_id']
        print(f"✅ Job created: job_id={job_id}, name={job['job_name']}")
    else:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Upload error: {e}")
    sys.exit(1)

# Step 3: Add to queue
print("\n📋 Step 3: Adding to queue...")
try:
    queue_data = {'job_id': job_id, 'printer_id': PRINTER_ID}
    response = requests.post(f'{BASE_URL}/api/queue/add', json=queue_data)
    
    if response.status_code == 200:
        queue_item = response.json()
        queue_id = queue_item['queue_id']
        print(f"✅ Added to queue: queue_id={queue_id}, position={queue_item['position_in_queue']}")
    else:
        print(f"❌ Failed to add to queue: {response.status_code} - {response.text}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Queue error: {e}")
    sys.exit(1)

# Step 4: Verify queue status
print("\n📊 Step 4: Queue status:")
try:
    response = requests.get(f'{BASE_URL}/api/queue/{PRINTER_ID}/status')
    status = response.json()
    print(f"   Pending: {status['pending_items']}")
    print(f"   Running: {status['running_items']}")
    print(f"   Completed: {status['completed_items']}")
    
    if status['pending_items'] > 0:
        print("\n✅ SUCCESS! Queue has pending job")
    else:
        print("\n❌ ERROR: No pending jobs in queue")
        sys.exit(1)
except Exception as e:
    print(f"❌ Status error: {e}")
    sys.exit(1)

# Step 5: Instructions
print("\n" + "="*60)
print("  ✅ READY TO TEST!")
print("="*60)
print("\n📍 Next steps:")
print("   1. Open dashboard: http://localhost:3000")
print("   2. Go to 'Queue & Upload' tab")
print("   3. You should see:")
print("      - Pending: 1")
print("      - 1 job in queue list")
print("   4. Click '▶ Start Next Job' button")
print("   5. File will upload to printer SD card via FTPS")
print("   6. Printer should start printing!")
print("\n" + "="*60)
