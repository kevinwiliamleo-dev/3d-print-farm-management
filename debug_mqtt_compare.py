#!/usr/bin/env python3
"""
Debug: Compare MQTT commands between manual and system send
"""

print("=" * 60)
print("COMPARING MQTT COMMANDS")
print("=" * 60)

# ==================== MANUAL SEND ====================
# From send_to_printer_simple.py line 114:
# mqtt_client.start_print_from_sd(remote_filename, use_ams=True)
# This uses ALL DEFAULT VALUES from bambu_service.py

print("\n📦 MANUAL SEND (send_to_printer_simple.py):")
print("-" * 50)
print("Calls: start_print_from_sd(filename, use_ams=True)")
print("Uses DEFAULTS from bambu_service.py function signature:")
print("  - flow_cali = True (DEFAULT)")
print("  - vibration_cali = True (DEFAULT)")  
print("  - bed_leveling = True (DEFAULT)")
print("  - timelapse = False (DEFAULT)")
print()

# ==================== SYSTEM SEND ====================
# From print_control_service.py line 372-380:
from src.database import SessionLocal
from src.database.db import Queue

db = SessionLocal()
queue_item = db.query(Queue).first()

print("📦 SYSTEM SEND (print_control_service.py):")
print("-" * 50)
if queue_item:
    print(f"Reads from queue_item (queue_id={queue_item.queue_id}):")
    print(f"  - flow_cali = {queue_item.flow_calibration}")
    print(f"  - vibration_cali = {queue_item.vibration_test}")
    print(f"  - bed_leveling = {queue_item.auto_bed_leveling}")
    print(f"  - timelapse = {queue_item.timelapse}")
else:
    print("No queue items found")

db.close()

print("\n" + "=" * 60)
print("ANALYSIS")
print("=" * 60)

print("""
🔴 MASALAH DITEMUKAN!

MANUAL SEND menggunakan DEFAULT VALUES dari function signature:
  - flow_cali = True
  - vibration_cali = True
  - bed_leveling = True

Padahal seharusnya juga mengikuti setting dari queue/preset!

SYSTEM SEND menggunakan nilai dari database:
  - flow_cali = False (dari preset)
  - vibration_cali = False (dari preset)  
  - bed_leveling = False (dari preset)

TAPI... Anda bilang MANUAL bekerja benar sedangkan SYSTEM tidak.
Ini berarti masalahnya BUKAN di MQTT command.

Mari cek apakah ada perbedaan di G-CODE FILE yang di-upload.
""")

print("=" * 60)
print("CHECKING PREPROCESSED FILES")
print("=" * 60)

import os
from pathlib import Path

# Check queue_files directory
queue_files_dir = Path("data/queue_files")
if queue_files_dir.exists():
    print(f"\n📁 Queue files in {queue_files_dir}:")
    for f in queue_files_dir.glob("*"):
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.2f} KB)")
else:
    print(f"\n❌ {queue_files_dir} not found")

# Check uploads directory  
uploads_dir = Path("data/uploads")
if uploads_dir.exists():
    print(f"\n📁 Uploads in {uploads_dir}:")
    for f in uploads_dir.glob("*"):
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.2f} KB)")

# Check output directory
output_dir = Path("data/3mf_output")
if output_dir.exists():
    print(f"\n📁 Output in {output_dir}:")
    for f in output_dir.glob("*"):
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.2f} KB)")
