#!/usr/bin/env python3
"""Direct test: Send print file to printer via MQTT"""

import sys
import time
import os
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from src.services.bambu_service import BambuLabMQTTClient

# Config
BAMBU_PRINTER_ID = os.getenv('BAMBU_PRINTER_ID', '03900D5A2402051')
BAMBU_PRINTER_IP = os.getenv('BAMBU_PRINTER_IP', '192.168.4.101')
BAMBU_ACCESS_CODE = os.getenv('BAMBU_ACCESS_CODE', '')

print("=" * 60)
print("DIRECT MQTT PRINT TEST")
print("=" * 60)

if not BAMBU_ACCESS_CODE:
    print("ERROR: BAMBU_ACCESS_CODE not set in .env")
    sys.exit(1)

# Step 1: Create MQTT client
print(f"\nSTEP 1: Create MQTT Client")
print(f"  Printer IP: {BAMBU_PRINTER_IP}")
print(f"  Printer ID: {BAMBU_PRINTER_ID}")

client = BambuLabMQTTClient(
    printer_id=BAMBU_PRINTER_ID,
    printer_ip=BAMBU_PRINTER_IP,
    access_code=BAMBU_ACCESS_CODE,
    use_lan_mode=True,
)

# Step 2: Connect
print(f"\nSTEP 2: Connect MQTT")
try:
    result = client.connect()
    print(f"  Connected: {result}")
    time.sleep(2)
except Exception as e:
    print(f"  ERROR: {e}")
    sys.exit(1)

# Step 3: Find file to print
print(f"\nSTEP 3: Find File to Print")

files_to_try = [
    "data/uploads/SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf",
    "data/uploads/test_model.3mf",
    "data/gcode/tmpjvehzam5.gcode",
]

file_path = None
for f in files_to_try:
    if os.path.exists(f):
        file_path = f
        print(f"  Found: {f}")
        break

if not file_path:
    print(f"  ERROR: No file found!")
    print(f"  Tried: {files_to_try}")
    sys.exit(1)

filename = os.path.basename(file_path)

# Step 4: Send print file
print(f"\nSTEP 4: Send Print File to Printer")
print(f"  File: {filename}")
print(f"  Path: {file_path}")

try:
    result = client.send_print_file(file_path)
    print(f"  Result: {result}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# Step 5: Check status
print(f"\nSTEP 5: Check Printer Status")
time.sleep(2)
try:
    status = client.get_printer_status()
    print(f"  Status: {status}")
except Exception as e:
    print(f"  ERROR: {e}")

# Cleanup
print(f"\nClosing MQTT connection...")
client.disconnect()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
