"""
Final verification script for queue file processing
"""
import zipfile
from pathlib import Path

dest = Path('data/queue_files/test_manual_queue.3mf')

with zipfile.ZipFile(dest, 'r') as zf:
    content = zf.read('Metadata/plate_1.gcode').decode('utf-8', errors='ignore')
    lines = content.split('\n')
    
    print('=== FINAL VERIFICATION ===')
    print(f'Total lines: {len(lines)}')
    
    # Check all important sections
    sections = [
        ('mech mode fast check start', 'vibration test'),
        ('auto extrude cali start', 'flow calibration'),
        ('bed leveling ==', 'bed leveling'),
        ('start printer sound', 'startup sound'),
        ('wipe nozzle ===', 'clean nozzle (main)'),
        ('brush material wipe nozzle', 'clean nozzle (brush)'),
        ('remove waste', 'clean nozzle (remove waste)'),
    ]
    
    print('\nAll settings FALSE - all should be DISABLED:')
    print()
    all_ok = True
    for pattern, name in sections:
        found = False
        for i, line in enumerate(lines):
            # Skip long header lines that contain escaped gcode (machine_start_gcode)
            if len(line) > 200 or '\\n' in line:
                continue
            if pattern in line.lower():
                is_disabled = '[DISABLED]' in line
                status = 'DISABLED' if is_disabled else 'ACTIVE'
                found = True
                match = 'OK' if status == 'DISABLED' else 'FAIL!'
                if status != 'DISABLED':
                    all_ok = False
                print(f'  {name:30} : {status:10} [{match}]')
                break
        if not found:
            print(f'  {name:30} : NOT FOUND')
    
    print()
    print('Quick Start features:')
    preheat = any('PREHEAT-OFFSET' in line for line in lines)
    pre_extrude = any('PRE-EXTRUDE' in line for line in lines)
    preheat_status = 'FOUND' if preheat else 'NOT FOUND'
    pre_extrude_status = 'FOUND' if pre_extrude else 'NOT FOUND'
    print(f'  PREHEAT-OFFSET: {preheat_status} [{"OK" if preheat else "FAIL"}]')
    print(f'  PRE-EXTRUDE:    {pre_extrude_status} [{"OK" if pre_extrude else "FAIL"}]')
    
    # Count disabled
    disabled_count = sum(1 for line in lines if '[DISABLED]' in line)
    print(f'\nTotal DISABLED lines: {disabled_count}')
    
    print()
    if all_ok and preheat and pre_extrude:
        print('=== ALL TESTS PASSED! ===')
    else:
        print('=== SOME TESTS FAILED ===')
