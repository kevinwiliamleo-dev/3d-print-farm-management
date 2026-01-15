"""
Test complete queue flow: Upload → Add to Queue → Start Next Job
"""
import requests
import time
from pathlib import Path

BASE_URL = "http://localhost:5000"
PRINTER_ID = "03900D5A2402051"
TEST_FILE = "data/uploads/SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_queue_flow():
    """Test complete upload → queue → print flow"""
    
    print_section("🧪 TESTING QUEUE FLOW")
    
    # Step 1: Check initial queue status
    print_section("📋 Step 1: Check Initial Queue Status")
    response = requests.get(f"{BASE_URL}/api/queue/{PRINTER_ID}/status")
    status = response.json()
    print(f"✅ Pending: {status['pending_items']}")
    print(f"✅ Running: {status['running_items']}")
    print(f"✅ Completed: {status['completed_items']}")
    
    # Step 2: Upload file and create job
    print_section("📤 Step 2: Upload File")
    
    if not Path(TEST_FILE).exists():
        print(f"❌ Test file not found: {TEST_FILE}")
        return
    
    with open(TEST_FILE, 'rb') as f:
        files = {'file': (Path(TEST_FILE).name, f, 'application/octet-stream')}
        data = {'loop_count': 1}
        
        print(f"Uploading: {Path(TEST_FILE).name}")
        response = requests.post(f"{BASE_URL}/api/jobs/upload", files=files, data=data)
        
        if response.status_code == 200:
            job = response.json()
            job_id = job['job_id']
            print(f"✅ Job created: job_id={job_id}, name={job['job_name']}")
        else:
            print(f"❌ Upload failed: {response.text}")
            return
    
    # Step 3: Add job to queue
    print_section("🔢 Step 3: Add Job to Queue")
    
    queue_data = {
        "job_id": job_id,
        "printer_id": PRINTER_ID
    }
    
    response = requests.post(f"{BASE_URL}/api/queue/add", json=queue_data)
    
    if response.status_code == 200:
        queue_item = response.json()
        queue_id = queue_item['queue_id']
        print(f"✅ Added to queue: queue_id={queue_id}, position={queue_item['position_in_queue']}")
    else:
        print(f"❌ Failed to add to queue: {response.text}")
        return
    
    # Step 4: Check queue status again
    print_section("📊 Step 4: Verify Queue Status")
    
    response = requests.get(f"{BASE_URL}/api/queue/{PRINTER_ID}/status")
    status = response.json()
    print(f"✅ Pending: {status['pending_items']}")
    print(f"✅ Running: {status['running_items']}")
    print(f"✅ Completed: {status['completed_items']}")
    
    # Step 5: Get queue items
    print_section("📋 Step 5: View Queue")
    
    response = requests.get(f"{BASE_URL}/api/queue/{PRINTER_ID}")
    queue = response.json()
    print(f"✅ Total items in queue: {queue['total']}")
    
    for item in queue['queue_items']:
        print(f"\n  Queue ID: {item['queue_id']}")
        print(f"  Job ID: {item['job_id']}")
        print(f"  Status: {item['status']}")
        print(f"  Position: {item['position_in_queue']}")
    
    # Step 6: Start next job (THIS WILL UPLOAD TO SD CARD AND START PRINT!)
    print_section("▶️ Step 6: Start Next Job (Upload to SD Card)")
    
    print("⚠️  This will:")
    print("   1. Upload file to printer SD card via FTPS")
    print("   2. Send MQTT command to start printing")
    print("")
    
    user_input = input("Continue? (yes/no): ").strip().lower()
    
    if user_input != 'yes':
        print("\n❌ Cancelled by user")
        return
    
    print("\n📤 Starting upload and print...")
    response = requests.post(f"{BASE_URL}/api/print-control/{PRINTER_ID}/start-print")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ SUCCESS!")
        print(f"   Message: {result['message']}")
        print(f"   Status: {result.get('status', {})}")
    else:
        print(f"\n❌ FAILED!")
        print(f"   Status: {response.status_code}")
        print(f"   Error: {response.text}")
    
    # Step 7: Final queue status
    print_section("📊 Step 7: Final Queue Status")
    
    time.sleep(2)  # Wait for status update
    
    response = requests.get(f"{BASE_URL}/api/queue/{PRINTER_ID}/status")
    status = response.json()
    print(f"✅ Pending: {status['pending_items']}")
    print(f"✅ Running: {status['running_items']}")
    print(f"✅ Completed: {status['completed_items']}")
    
    print_section("✅ TEST COMPLETE")
    print("Check your printer - it should start printing from SD card!")
    print("")

if __name__ == "__main__":
    try:
        test_queue_flow()
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
