"""Test start print workflow step by step"""
import os
import sys
import logging

# Configure logging to see everything
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from src.database.db import SessionLocal, Queue, Job
from src.services.bambu_service import BambuLabMQTTClient
from src.services.print_control_service import PrintControlService
from src.config import BAMBU_PRINTER_ID, BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE

print("=== Starting Test ===")
print(f"Printer IP: {BAMBU_PRINTER_IP}")
print(f"Printer ID: {BAMBU_PRINTER_ID}")
print(f"Access Code: {BAMBU_ACCESS_CODE}")

# Step 1: Get database session
db = SessionLocal()
printer_id = "03900D5A2402051"

# Step 2: Check queue
print("\n=== Step 2: Check Queue ===")
queue_item = db.query(Queue).filter(
    Queue.printer_id == printer_id,
    Queue.status == "pending"
).order_by(Queue.position_in_queue).first()

if not queue_item:
    print("ERROR: No pending jobs in queue!")
    db.close()
    sys.exit(1)
    
print(f"Found queue: queue_id={queue_item.queue_id}, job_id={queue_item.job_id}")

# Step 3: Get job
print("\n=== Step 3: Get Job ===")
job = db.query(Job).filter(Job.job_id == queue_item.job_id).first()
if not job:
    print("ERROR: Job not found!")
    db.close()
    sys.exit(1)
    
print(f"Found job: job_name={job.job_name}, filename={job.filename}")

# Step 4: Check file paths
print("\n=== Step 4: Check File Paths ===")
gcode_path = f"data/gcode/{job.job_name}.gcode"
threemf_path = f"data/uploads/{job.filename}"

print(f"Checking gcode: {gcode_path} - exists: {os.path.exists(gcode_path)}")
print(f"Checking 3mf: {threemf_path} - exists: {os.path.exists(threemf_path)}")

if os.path.exists(gcode_path):
    file_path = gcode_path
elif os.path.exists(threemf_path):
    file_path = threemf_path
else:
    print("ERROR: No print file found!")
    db.close()
    sys.exit(1)
    
print(f"Will use: {file_path}")

# Step 5: Create MQTT client
print("\n=== Step 5: Create MQTT Client ===")
try:
    bambu_client = BambuLabMQTTClient(
        printer_id=BAMBU_PRINTER_ID,
        printer_ip=BAMBU_PRINTER_IP,
        access_code=BAMBU_ACCESS_CODE,
        use_lan_mode=True,
    )
    print("MQTT client created")
except Exception as e:
    print(f"ERROR creating MQTT client: {e}")
    db.close()
    sys.exit(1)

# Step 6: Connect MQTT
print("\n=== Step 6: Connect MQTT ===")
try:
    bambu_client.connect()
    print("MQTT connected")
except Exception as e:
    print(f"ERROR connecting MQTT: {e}")
    db.close()
    sys.exit(1)

# Step 7: Send file to printer
print("\n=== Step 7: Send Print File ===")
try:
    result = bambu_client.send_print_file(file_path)
    print(f"Send print file result: {result}")
except Exception as e:
    print(f"ERROR sending print file: {e}")
    import traceback
    traceback.print_exc()

db.close()
print("\n=== Test Complete ===")
