#!/usr/bin/env python3
"""
Debug: Check what file is ACTUALLY being sent vs what you send manually
"""

import zipfile
from pathlib import Path

print("=" * 70)
print("CHECKING ACTUAL FILES BEING USED")
print("=" * 70)

# Files to check
files_to_check = [
    ("MANUAL (your test)", Path("data/3mf_output/test2.gcode.3mf")),
    ("QUEUE FILE", Path("data/queue_files/queue_3_test2.gcode.3mf")),
    ("ORIGINAL UPLOAD", Path("data/uploads/test2.gcode.3mf")),
]

def check_gcode_content(filepath, label):
    """Extract and analyze G-code from 3MF"""
    print(f"\n📦 {label}")
    print(f"   Path: {filepath}")
    
    if not filepath.exists():
        print(f"   ❌ FILE NOT FOUND!")
        return
    
    size_kb = filepath.stat().st_size / 1024
    print(f"   Size: {size_kb:.2f} KB")
    
    with zipfile.ZipFile(filepath, 'r') as z:
        for name in z.namelist():
            if name.endswith('.gcode'):
                with z.open(name) as gf:
                    content = gf.read().decode('utf-8', errors='ignore')
                    lines = content.split('\n')
                    
                    print(f"   G-code: {name}")
                    print(f"   Lines: {len(lines)}")
                    
                    # Check for key markers
                    markers_found = []
                    for i, line in enumerate(lines):
                        lower = line.lower()
                        if 'skip: nozzle load line' in lower:
                            markers_found.append(f"Line {i+1}: SKIP Nozzle Load Line")
                        if 'nozzle_load_line=false' in lower:
                            markers_found.append(f"Line {i+1}: nozzle_load_line=False")
                        if 'flow_calibration=false' in lower:
                            markers_found.append(f"Line {i+1}: flow_calibration=False")
                        if 'generated start gcode' in lower:
                            markers_found.append(f"Line {i+1}: GENERATED START GCODE")
                        if 'template mode' in lower:
                            markers_found.append(f"Line {i+1}: Template mode marker")
                    
                    if markers_found:
                        print(f"   Key markers:")
                        for m in markers_found[:10]:
                            print(f"     ✓ {m}")
                    else:
                        print(f"   ⚠️ No automation markers found!")
                    
                    # Check first 20 lines after EXECUTABLE_BLOCK_START
                    exec_start = -1
                    for i, line in enumerate(lines):
                        if 'EXECUTABLE_BLOCK_START' in line:
                            exec_start = i
                            break
                    
                    if exec_start >= 0:
                        print(f"\n   First 15 lines after EXECUTABLE_BLOCK_START:")
                        for i in range(exec_start + 1, min(exec_start + 16, len(lines))):
                            line = lines[i][:70] if len(lines[i]) > 70 else lines[i]
                            print(f"     {i+1}: {line}")

for label, filepath in files_to_check:
    check_gcode_content(filepath, label)

print("\n" + "=" * 70)
print("COMPARISON SUMMARY")
print("=" * 70)

# Compare file sizes
sizes = {}
for label, filepath in files_to_check:
    if filepath.exists():
        sizes[label] = filepath.stat().st_size

print("\nFile sizes:")
for label, size in sizes.items():
    print(f"  {label}: {size:,} bytes")
