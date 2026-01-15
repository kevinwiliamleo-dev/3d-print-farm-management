#!/usr/bin/env python3
"""Deep compare of G-code in two 3MF files - find exact differences"""

import zipfile
from pathlib import Path
import difflib

output_dir = Path('data/3mf_output')

files = ['test2.gcode.3mf', 'modified_test2.gcode.3mf']
gcode_contents = {}

# Extract G-code from both files
for fname in files:
    fpath = output_dir / fname
    with zipfile.ZipFile(fpath, 'r') as z:
        for name in z.namelist():
            if name.endswith('.gcode'):
                with z.open(name) as gf:
                    gcode_contents[fname] = gf.read().decode('utf-8', errors='ignore')

keys = list(gcode_contents.keys())
lines1 = gcode_contents[keys[0]].split('\n')
lines2 = gcode_contents[keys[1]].split('\n')

print("=" * 70)
print("DETAILED G-CODE COMPARISON")
print("=" * 70)
print(f"\n📁 Original:  {keys[0]} ({len(lines1)} lines)")
print(f"📁 Modified:  {keys[1]} ({len(lines2)} lines)")
print(f"📊 Difference: {len(lines2) - len(lines1)} lines")

# Find where the files start to differ
print("\n" + "=" * 70)
print("SEARCHING FOR DIFFERENCES")
print("=" * 70)

first_diff_line = -1
for i in range(min(len(lines1), len(lines2))):
    if lines1[i] != lines2[i]:
        first_diff_line = i
        break

if first_diff_line >= 0:
    print(f"\n🔍 First difference at line {first_diff_line + 1}")
    
    # Show context around first difference
    start = max(0, first_diff_line - 5)
    end = min(len(lines1), first_diff_line + 20)
    
    print(f"\n📄 Original (lines {start+1} to {end}):")
    print("-" * 70)
    for i in range(start, end):
        marker = ">>>" if i == first_diff_line else "   "
        line = lines1[i][:80] if len(lines1[i]) > 80 else lines1[i]
        print(f"{marker} {i+1:4}: {line}")
    
    end2 = min(len(lines2), first_diff_line + 20)
    print(f"\n📄 Modified (lines {start+1} to {end2}):")
    print("-" * 70)
    for i in range(start, end2):
        marker = ">>>" if i == first_diff_line else "   "
        line = lines2[i][:80] if len(lines2[i]) > 80 else lines2[i]
        print(f"{marker} {i+1:4}: {line}")

# Find key sections in both files
print("\n" + "=" * 70)
print("SECTION MARKERS COMPARISON")
print("=" * 70)

markers_to_find = [
    'HEADER_BLOCK_',
    'CONFIG_BLOCK_',
    'EXECUTABLE_BLOCK_',
    'CHANGE_LAYER',
    'machine_start_gcode',
    'machine_end_gcode',
    'nozzle load line',
    'draw wiping',
    'home after',
    'LAYER:',
    'G28',
    'M104',
    'M109',
    'M140',
    'M190',
]

for fname, content in gcode_contents.items():
    lines = content.split('\n')
    print(f"\n📄 {fname}:")
    print("-" * 50)
    
    for marker in markers_to_find:
        found = []
        for i, line in enumerate(lines):
            if marker.lower() in line.lower():
                found.append((i+1, line[:60]))
        
        if found:
            print(f"  {marker}:")
            for ln, txt in found[:3]:  # Show first 3 matches
                print(f"    Line {ln}: {txt}")

# Full unified diff (limited)
print("\n" + "=" * 70)
print("UNIFIED DIFF (showing all differences)")
print("=" * 70)

differ = difflib.unified_diff(
    lines1, lines2,
    fromfile='Original: ' + keys[0],
    tofile='Modified: ' + keys[1],
    lineterm='',
    n=3  # 3 lines of context
)

diff_lines = list(differ)
for line in diff_lines[:100]:  # First 100 lines of diff
    # Truncate long lines
    if len(line) > 100:
        line = line[:97] + '...'
    
    if line.startswith('+++') or line.startswith('---'):
        print(f"\n{line}")
    elif line.startswith('+'):
        print(f"🟢 {line}")
    elif line.startswith('-'):
        print(f"🔴 {line}")
    elif line.startswith('@@'):
        print(f"\n📍 {line}")
    else:
        print(f"   {line}")

if len(diff_lines) > 100:
    print(f"\n... ({len(diff_lines) - 100} more diff lines)")

print("\n" + "=" * 70)
print("COMPLETE")
print("=" * 70)
