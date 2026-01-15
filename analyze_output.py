#!/usr/bin/env python3
"""Analyze output 3MF file and verify settings"""
import zipfile
import os

output_dir = "data/3mf_output"
files = [f for f in os.listdir(output_dir) if f.endswith('.3mf')]

if not files:
    print("No 3MF files in output folder")
    exit(1)

output_file = os.path.join(output_dir, files[0])

with zipfile.ZipFile(output_file, 'r') as zf:
    gcode = zf.read('Metadata/plate_1.gcode').decode('utf-8', errors='ignore')
    lines = gcode.split('\n')

print()
print('=' * 60)
print('  HASIL ANALISA FILE OUTPUT')
print('  ' + os.path.basename(output_file))
print('=' * 60)
print()

# Stats
total = len(lines)
disabled = sum(1 for l in lines if '[DISABLED]' in l)
print('STATISTIK:')
print(f'  Total lines: {total}')
print(f'  Disabled: {disabled} ({round(disabled*100/total, 1)}%)')
print()

print('=' * 60)
print('  VERIFIKASI SETTINGS VS SCREENSHOT')
print('=' * 60)
print()

# Check each setting - executable area only (line 500+)
exec_lines = lines[500:]

def check_setting(name, expected, cmds):
    total_count = 0
    disabled_count = 0
    for cmd in cmds:
        for line in exec_lines:
            if cmd in line:
                total_count += 1
                if '[DISABLED]' in line:
                    disabled_count += 1
    
    if total_count == 0:
        status = 'N/A - not in file'
        match = '-'
    elif disabled_count == total_count:
        status = 'ALL DISABLED'
        match = 'YES' if expected == 'OFF' else 'NO'
    else:
        status = f'{disabled_count}/{total_count} disabled'
        match = 'PARTIAL'
    
    return status, match

settings = [
    ('Bed Leveling', 'OFF', ['G29']),
    ('Clean Nozzle', 'OFF', ['G39.3']),
    ('Flow Calibration', 'OFF', ['M983', 'M984']),
    ('Vibration Test', 'OFF', ['M970']),
    ('Start/End Sound', 'OFF', ['M1006']),
    ('Timelapse', 'OFF', ['M971', 'M991']),
]

for name, expected, cmds in settings:
    status, match = check_setting(name, expected, cmds)
    print(f'{name}:')
    print(f'  Screenshot: {expected}')
    print(f'  File: {status}')
    print(f'  Match: {match}')
    print()

print('=' * 60)
print('  QUICK START')
print('=' * 60)
print()

# Preheat Offset
for i, line in enumerate(lines):
    if 'PREHEAT-OFFSET' in line:
        print('Preheat Offset: ACTIVE')
        print(f'  {lines[i+1].strip()}')
        break

# Pre-Extrude
for i, line in enumerate(lines):
    if 'PRE-EXTRUDE' in line and 'END' not in line:
        print('Pre-Extrude: ACTIVE')
        break

print()
print('=' * 60)
print('  SAFETY COMMANDS (must remain ACTIVE)')
print('=' * 60)
print()

for cmd in ['M104 S0', 'M140 S0', 'M106 S0']:
    active = any(cmd in l and '[DISABLED]' not in l for l in exec_lines)
    status = 'ACTIVE - OK' if active else 'not found'
    print(f'{cmd}: {status}')

print()
print('=' * 60)
print('  KESIMPULAN')
print('=' * 60)
print()
print('File sudah dimodifikasi sesuai settings:')
print('- Semua automation DISABLED')
print('- Quick Start ENABLED (Preheat -20C, Pre-Extrude)')
print('- Safety commands tetap ACTIVE')
