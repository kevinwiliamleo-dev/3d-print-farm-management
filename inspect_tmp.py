import zipfile
import sys
from pathlib import Path

p = Path('data/3mf_output/modified_foldable_phone-tablet_stand_-_12_mm_-_part_a_v2_PLA-CF_20m55s.gcode.3mf')
print(p)
if not p.exists():
    print('missing')
    sys.exit(1)

with zipfile.ZipFile(p, 'r') as z:
    names = z.namelist()
    print('entries', len(names))
    g = [n for n in names if n.endswith('.gcode')]
    if not g:
        print('no gcode')
        sys.exit(1)
    gname = g[0]
    print('gcode', gname)
    data = z.read(gname).decode('utf-8', 'replace')
    lines = data.splitlines()
    print('lines', len(lines))
    print('---HEADER first 80---')
    for i, line in enumerate(lines[:80], 1):
        print(f"{i:04d}: {line}")
    keys = ['{', 'filament_already_loaded', 'START_', 'END_']
    print('---PLACEHOLDERS search---')
    for k in keys:
        idx = [i for i, l in enumerate(lines, 1) if k in l]
        if idx:
            print(k, idx[:10], 'count', len(idx))
    print('---FOOTER last 40---')
    for i, line in enumerate(lines[-40:], len(lines) - 39):
        print(f"{i:04d}: {line}")
