#!/usr/bin/env python3
"""Compare two 3MF files in output folder"""

import zipfile
from pathlib import Path
import difflib

output_dir = Path('data/3mf_output')
temp_dir = Path('data/temp_compare')
temp_dir.mkdir(exist_ok=True)

files = ['test2.gcode.3mf', 'modified_test2.gcode.3mf']

print("=" * 60)
print("COMPARING 3MF FILES")
print("=" * 60)

# Get file sizes
for fname in files:
    fpath = output_dir / fname
    size_kb = fpath.stat().st_size / 1024
    print(f"\n📦 {fname}")
    print(f"   Size: {size_kb:.2f} KB")

# Extract both files
gcode_contents = {}

for fname in files:
    fpath = output_dir / fname
    
    with zipfile.ZipFile(fpath, 'r') as z:
        # List contents
        print(f"\n📂 Contents of {fname}:")
        for name in z.namelist():
            info = z.getinfo(name)
            print(f"   - {name} ({info.file_size:,} bytes)")
        
        # Find and read gcode file
        for name in z.namelist():
            if name.endswith('.gcode'):
                with z.open(name) as gf:
                    content = gf.read().decode('utf-8', errors='ignore')
                    gcode_contents[fname] = content
                    lines = content.split('\n')
                    print(f"\n   📄 G-code: {name}")
                    print(f"   Lines: {len(lines):,}")
                    print(f"   Size: {len(content):,} chars")

print("\n" + "=" * 60)
print("G-CODE ANALYSIS")
print("=" * 60)

# Analyze start gcode differences
for fname, content in gcode_contents.items():
    lines = content.split('\n')
    
    print(f"\n📄 {fname}")
    print("-" * 40)
    
    # Find key sections
    start_machine_idx = -1
    generated_start_idx = -1
    first_layer_idx = -1
    
    for i, line in enumerate(lines[:500]):  # Check first 500 lines
        if ';===== Start Machine' in line or ';===== start machine' in line:
            start_machine_idx = i
        if 'GENERATED START GCODE' in line:
            generated_start_idx = i
        if ';LAYER:0' in line or '; layer_z' in line:
            first_layer_idx = i
            break
    
    print(f"   Start Machine marker at line: {start_machine_idx}")
    print(f"   Generated Start marker at line: {generated_start_idx}")
    print(f"   First Layer starts at line: {first_layer_idx}")
    
    # Show first 50 lines (start gcode)
    print(f"\n   First 50 lines of G-code:")
    print("   " + "-" * 36)
    for i, line in enumerate(lines[:50]):
        # Truncate long lines
        display = line[:70] + '...' if len(line) > 70 else line
        print(f"   {i+1:3}: {display}")

# Compare the two
print("\n" + "=" * 60)
print("KEY DIFFERENCES")
print("=" * 60)

if len(gcode_contents) == 2:
    keys = list(gcode_contents.keys())
    lines1 = gcode_contents[keys[0]].split('\n')[:100]
    lines2 = gcode_contents[keys[1]].split('\n')[:100]
    
    differ = difflib.unified_diff(
        lines1, lines2,
        fromfile=keys[0],
        tofile=keys[1],
        lineterm=''
    )
    
    diff_output = list(differ)
    if diff_output:
        print("\n📊 Differences in first 100 lines:")
        for line in diff_output[:50]:  # Show first 50 diff lines
            if line.startswith('+') and not line.startswith('+++'):
                print(f"   🟢 {line}")
            elif line.startswith('-') and not line.startswith('---'):
                print(f"   🔴 {line}")
    else:
        print("\n✅ First 100 lines are identical")
    
    # Count total differences
    all_lines1 = gcode_contents[keys[0]].split('\n')
    all_lines2 = gcode_contents[keys[1]].split('\n')
    
    diff_count = 0
    for l1, l2 in zip(all_lines1, all_lines2):
        if l1 != l2:
            diff_count += 1
    
    print(f"\n📈 Statistics:")
    print(f"   {keys[0]}: {len(all_lines1):,} lines")
    print(f"   {keys[1]}: {len(all_lines2):,} lines")
    print(f"   Line count difference: {len(all_lines1) - len(all_lines2):,}")
    print(f"   Lines that differ: {diff_count:,}")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
