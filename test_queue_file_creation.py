"""
Test script to verify _create_modified_queue_file works correctly
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
from src.services.queue_service import QueueService
from src.database import SessionLocal
import zipfile

# Source file
source = Path('data/uploads/Foldable phone stand bambu-fixed.gcode.3mf')
dest = Path('data/queue_files/test_manual_queue.3mf')

print('=== Testing _create_modified_queue_file directly ===')
print(f'Source exists: {source.exists()}')
print(f'Source is 3MF: {source.suffix.lower() == ".3mf"}')

# Create DB session
db = SessionLocal()

try:
    queue_service = QueueService(db)
    
    # Call the method with all settings DISABLED
    result = queue_service._create_modified_queue_file(
        source_file=source,
        dest_file=dest,
        auto_bed_leveling=False,   # Disable
        flow_calibration=False,    # Disable  
        vibration_test=False,      # Disable
        clean_nozzle=False,        # Disable
        startup_sound=False,       # Disable
        end_sound=False,           # Disable
        use_ams=True,
        ams_slot=0,
        filament_already_loaded=False,
        quick_start=True,
        preheat_offset=20,
        pre_extrude=True,
        pre_extrude_length=2.2
    )
    
    print(f'Result: {result}')
    print(f'Dest exists: {dest.exists()}')
    
    # Now check the content
    if dest.exists():
        with zipfile.ZipFile(dest, 'r') as zf:
            namelist = zf.namelist()
            gcode_file = [n for n in namelist if 'plate' in n.lower() and n.endswith('.gcode')]
            print(f'Gcode files: {gcode_file}')
            
            if gcode_file:
                content = zf.read(gcode_file[0]).decode('utf-8', errors='ignore')
                lines = content.split('\n')
                
                # Check for DISABLED markers
                disabled_count = sum(1 for line in lines if '[DISABLED]' in line)
                print(f'DISABLED markers: {disabled_count}')
                
                # Check for Quick Start
                preheat_found = any('PREHEAT-OFFSET' in line for line in lines)
                pre_extrude_found = any('PRE-EXTRUDE' in line for line in lines)
                print(f'PREHEAT-OFFSET found: {preheat_found}')
                print(f'PRE-EXTRUDE found: {pre_extrude_found}')
                
                # Show section markers
                print('\n=== Checking section markers ===')
                for i, line in enumerate(lines[:500]):
                    if 'mech mode' in line.lower() or 'auto extrude' in line.lower() or 'wipe nozzle' in line.lower() or 'bed leveling' in line.lower():
                        next_line = lines[i+1] if i+1 < len(lines) else ''
                        status = 'DISABLED' if '[DISABLED]' in next_line else 'ACTIVE'
                        print(f'Line {i}: {line[:60]:<60} -> {status}')
                        
except Exception as e:
    import traceback
    print(f'ERROR: {e}')
    traceback.print_exc()
finally:
    db.close()
