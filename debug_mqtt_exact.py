#!/usr/bin/env python3
"""
Debug: Compare EXACT MQTT commands sent by manual vs system
"""

import json
import time

print("=" * 70)
print("EXACT MQTT COMMAND COMPARISON")
print("=" * 70)

# ==================== MANUAL SEND ====================
# Simulating what send_to_printer_simple.py sends
# It calls: mqtt_client.start_print_from_sd(remote_filename, use_ams=True)
# Which uses DEFAULT values from function signature:

filename = "test2.gcode.3mf"
subtask_name = filename

# DEFAULT values from bambu_service.py start_print_from_sd signature:
# def start_print_from_sd(self, filename: str, use_ams: bool = True, plate_number: int = 1, 
#                         ams_mapping = None, ams_slot: int = 0, flow_cali: bool = True, vibration_cali: bool = True,
#                         bed_leveling: bool = True, layer_inspect: bool = False, timelapse: bool = False)

manual_command = {
    "print": {
        "sequence_id": str(int(time.time() * 1000)),
        "command": "project_file",
        "param": "Metadata/plate_1.gcode",
        "md5": "",
        "profile_id": "0",
        "project_id": "0",
        "subtask_id": "0",
        "task_id": "0",
        "subtask_name": subtask_name,
        "url": f"file:///sdcard/{filename}",
        "bed_type": "auto",
        "timelapse": False,           # DEFAULT
        "bed_leveling": True,         # DEFAULT ← TRUE
        "flow_cali": True,            # DEFAULT ← TRUE
        "vibration_cali": True,       # DEFAULT ← TRUE  
        "layer_inspect": False,       # DEFAULT
        "use_ams": True,              # from parameter
        "ams_mapping": [0]            # DEFAULT (ams_slot=0)
    }
}

print("\n📦 MANUAL SEND (send_to_printer_simple.py):")
print("-" * 70)
print(json.dumps(manual_command, indent=2))

# ==================== SYSTEM SEND ====================
# Simulating what print_control_service.py sends
# Based on queue_item values from database

# From database query earlier:
# flow_calibration = False
# vibration_test = False
# auto_bed_leveling = False
# timelapse = False
# use_ams = True
# ams_slot = 3

system_command = {
    "print": {
        "sequence_id": str(int(time.time() * 1000)),
        "command": "project_file",
        "param": "Metadata/plate_1.gcode",
        "md5": "",
        "profile_id": "0",
        "project_id": "0",
        "subtask_id": "0",
        "task_id": "0",
        "subtask_name": subtask_name,
        "url": f"file:///sdcard/{filename}",
        "bed_type": "auto",
        "timelapse": False,           # from queue_item
        "bed_leveling": False,        # from queue_item ← FALSE
        "flow_cali": False,           # from queue_item ← FALSE
        "vibration_cali": False,      # from queue_item ← FALSE
        "layer_inspect": False,       # hardcoded
        "use_ams": True,              # from queue_item
        "ams_mapping": [3]            # from queue_item.ams_slot
    }
}

print("\n📦 SYSTEM SEND (print_control_service.py):")
print("-" * 70)
print(json.dumps(system_command, indent=2))

# ==================== DIFFERENCES ====================
print("\n" + "=" * 70)
print("PARAMETER DIFFERENCES")
print("=" * 70)

differences = []
for key in manual_command["print"]:
    manual_val = manual_command["print"][key]
    system_val = system_command["print"].get(key)
    
    if manual_val != system_val and key not in ["sequence_id"]:
        differences.append((key, manual_val, system_val))

print("\n🔴 Parameters that DIFFER:")
for key, manual, system in differences:
    print(f"   {key}:")
    print(f"     Manual: {manual}")
    print(f"     System: {system}")

print("\n" + "=" * 70)
print("ANALYSIS")
print("=" * 70)
print("""
🤔 PARADOX:
- Manual sends: bed_leveling=True, flow_cali=True, vibration_cali=True
- System sends: bed_leveling=False, flow_cali=False, vibration_cali=False

But you say:
- Manual: NO purge line (correct behavior)
- System: HAS purge line (wrong behavior)

This is BACKWARDS from what the parameters suggest!

POSSIBLE EXPLANATIONS:
1. Bambu firmware interprets flow_cali differently on A1 vs X1
2. The ams_mapping difference (0 vs 3) affects behavior
3. There's firmware-level flow calibration that runs regardless
4. The G-code file content is being processed differently
5. There's a separate calibration triggered by the printer

🔍 NEXT STEP: Check if ams_mapping affects flow calibration behavior
""")
