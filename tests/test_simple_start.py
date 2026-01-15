#!/usr/bin/env python3
"""Test start print with pre-sliced file"""

import sys
import time
import os
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from src.services.bambu_service import BambuLabMQTTClient

BAMBU_PRINTER_ID = os.getenv('BAMBU_PRINTER_ID', '03900D5A2402051')
BAMBU_PRINTER_IP = os.getenv('BAMBU_PRINTER_IP', '192.168.4.101')
BAMBU_ACCESS_CODE = os.getenv('BAMBU_ACCESS_CODE', '')

print("=" * 60)
print("TEST START PRINT (PRE-SLICED FILE)")
print("=" * 60)

if not BAMBU_ACCESS_CODE:
    print("ERROR: BAMBU_ACCESS_CODE not set")
    sys.exit(1)

client = BambuLabMQTTClient(
    printer_id=BAMBU_PRINTER_ID,
    printer_ip=BAMBU_PRINTER_IP,
    access_code=BAMBU_ACCESS_CODE,
    use_lan_mode=True,
)

print("\n1. Connecting to printer...")
try:
    client.connect()
    time.sleep(2)
    print(f"   Connected: {client.mqtt_connected}")
except Exception as e:
    print(f"   ERROR: {e}")
    sys.exit(1)

if client.mqtt_connected:
    print("\n2. Sending print command with HTTP download URL...")
    
    # Use actual file from data/uploads/
    test_file = "data/uploads/test_model.3mf"
    
    if not os.path.exists(test_file):
        print(f"   ERROR: Test file not found: {test_file}")
        sys.exit(1)
    
    print(f"   File: {test_file}")
    print(f"   URL: http://localhost:5000/uploads/test_model.3mf")
    
    try:
        # Send print file with HTTP URL (printer will download from localhost:5000/uploads/)
        result = client.send_print_file(test_file, local_server_url="http://localhost:5000")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    time.sleep(2)
    
    print("\n3. Checking printer status...")
    try:
        status = client.get_printer_status()
        print(f"   Status: {status}")
    except Exception as e:
        print(f"   ERROR: {e}")

print("\n4. Closing connection...")
client.disconnect()

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)

