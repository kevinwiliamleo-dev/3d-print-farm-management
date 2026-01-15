#!/usr/bin/env python3
"""Test queue item attribute reading"""

from src.database import SessionLocal
from src.database.db import Queue

db = SessionLocal()
queue_item = db.query(Queue).first()

if queue_item:
    print("Testing hasattr and actual values:")
    print(f"  hasattr flow_calibration: {hasattr(queue_item, 'flow_calibration')}")
    print(f"  flow_calibration value: {queue_item.flow_calibration}")
    print(f"  flow_calibration type: {type(queue_item.flow_calibration)}")
    print()
    print(f"  hasattr vibration_test: {hasattr(queue_item, 'vibration_test')}")
    print(f"  vibration_test value: {queue_item.vibration_test}")
    print()
    print(f"  hasattr auto_bed_leveling: {hasattr(queue_item, 'auto_bed_leveling')}")
    print(f"  auto_bed_leveling value: {queue_item.auto_bed_leveling}")
    print()
    
    # Simulate what queue_service does
    flow_cali = queue_item.flow_calibration if hasattr(queue_item, 'flow_calibration') else True
    print(f"Simulated flow_cali (current code): {flow_cali}")
    
    # Boolean False is 0 in SQLite, check if it reads correctly
    print(f"Boolean check: flow_cali == False: {flow_cali == False}")
    print(f"Boolean check: flow_cali == 0: {flow_cali == 0}")
    print(f"Boolean check: not flow_cali: {not flow_cali}")
    print(f"Boolean check: bool(flow_cali): {bool(flow_cali)}")
else:
    print("No queue items found")

db.close()
