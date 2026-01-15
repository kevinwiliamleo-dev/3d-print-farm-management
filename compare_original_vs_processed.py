#!/usr/bin/env python3
"""Compare G-code between original upload and processed queue file"""

import zipfile
from pathlib import Path
import difflib

# File paths
original_file = Path("data/uploads/test2.gcode.3mf")
processed_file = Path("data/queue_files/queue_3_test2.gcode.3mf")

def extract_gcode(filepath):
    """Extract G-code content from 3MF file"""
    with zipfile.ZipFile(filepath, 'r') as z:
        for name in z.namelist():
            if name.endswith('.gcode'):
                with z.open(name) as gf:
                    return gf.read().decode('utf-8', errors='ignore')
    return None

print("=" * 70)
print("COMPARING ORIGINAL vs PROCESSED G-CODE")
print("=" * 70)

# Get G-code content
print(f"\n📁 Original: {original_file}")
print(f"📁 Processed: {processed_file}")

original_gcode = extract_gcode(original_file)
processed_gcode = extract_gcode(processed_file)

if not original_gcode:
    print(f"❌ Could not extract G-code from {original_file}")
    exit(1)
    
if not processed_gcode:
    print(f"❌ Could not extract G-code from {processed_file}")
    exit(1)

orig_lines = original_gcode.split('\n')
proc_lines = processed_gcode.split('\n')

print(f"\n📊 Statistics:")
print(f"   Original: {len(orig_lines)} lines, {len(original_gcode)} chars")
print(f"   Processed: {len(proc_lines)} lines, {len(processed_gcode)} chars")
print(f"   Difference: {len(proc_lines) - len(orig_lines)} lines")

# Find first difference
print("\n" + "=" * 70)
print("FINDING DIFFERENCES")
print("=" * 70)

first_diff = -1
for i in range(min(len(orig_lines), len(proc_lines))):
    if orig_lines[i] != proc_lines[i]:
        first_diff = i
        break

if first_diff >= 0:
    print(f"\n🔍 First difference at line {first_diff + 1}")
    
    # Show context
    start = max(0, first_diff - 3)
    end = min(len(orig_lines), first_diff + 15)
    
    print(f"\n📄 ORIGINAL (lines {start+1} to {end}):")
    print("-" * 70)
    for i in range(start, end):
        marker = ">>>" if i == first_diff else "   "
        line = orig_lines[i][:80] if len(orig_lines[i]) > 80 else orig_lines[i]
        print(f"{marker} {i+1:4}: {line}")
    
    end2 = min(len(proc_lines), first_diff + 15)
    print(f"\n📄 PROCESSED (lines {start+1} to {end2}):")
    print("-" * 70)
    for i in range(start, end2):
        marker = ">>>" if i == first_diff else "   "
        line = proc_lines[i][:80] if len(proc_lines[i]) > 80 else proc_lines[i]
        print(f"{marker} {i+1:4}: {line}")
else:
    print("\n✅ No differences found in common lines")

# Search for nozzle load line / purge line markers
print("\n" + "=" * 70)
print("SEARCHING FOR PURGE LINE / NOZZLE LOAD LINE")
print("=" * 70)

markers = [
    'nozzle load line',
    'nozzle_load_line', 
    'purge line',
    'draw wipe line',
    'wipe line',
    'prime line',
    'M83',  # Relative extruder mode
    'G1 E',  # Extrude commands
    'Y-3',   # Common purge line position
    'Y0',    # Common purge line position
]

for marker in markers:
    print(f"\n🔍 Searching for '{marker}':")
    
    orig_matches = [(i+1, line[:60]) for i, line in enumerate(orig_lines) if marker.lower() in line.lower()]
    proc_matches = [(i+1, line[:60]) for i, line in enumerate(proc_lines) if marker.lower() in line.lower()]
    
    if orig_matches or proc_matches:
        print(f"   Original ({len(orig_matches)} matches):")
        for ln, txt in orig_matches[:3]:
            print(f"     Line {ln}: {txt}")
        
        print(f"   Processed ({len(proc_matches)} matches):")
        for ln, txt in proc_matches[:3]:
            print(f"     Line {ln}: {txt}")

# Show unified diff for start gcode section (first 200 lines)
print("\n" + "=" * 70)
print("UNIFIED DIFF (first 200 lines)")
print("=" * 70)

differ = difflib.unified_diff(
    orig_lines[:200], 
    proc_lines[:200],
    fromfile='ORIGINAL',
    tofile='PROCESSED',
    lineterm='',
    n=2
)

diff_output = list(differ)
if diff_output:
    for line in diff_output[:80]:
        if len(line) > 90:
            line = line[:87] + '...'
        if line.startswith('+') and not line.startswith('+++'):
            print(f"🟢 {line}")
        elif line.startswith('-') and not line.startswith('---'):
            print(f"🔴 {line}")
        elif line.startswith('@@'):
            print(f"\n📍 {line}")
        else:
            print(f"   {line}")
else:
    print("✅ First 200 lines are identical")
