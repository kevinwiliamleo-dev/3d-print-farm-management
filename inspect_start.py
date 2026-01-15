import zipfile
from pathlib import Path
p=Path('data/3mf_output/modified_foldable_phone-tablet_stand_-_12_mm_-_part_a_v2_PLA-CF_20m55s.gcode.3mf')
with zipfile.ZipFile(p,'r') as z:
    g=[n for n in z.namelist() if n.endswith('.gcode')][0]
    lines=z.read(g).decode('utf-8','replace').splitlines()
start=None
for i,l in enumerate(lines):
    if 'GENERATED START GCODE' in l:
        start=i
        break
if start is None:
    print('not found'); raise SystemExit
s=max(0,start-3); e=min(len(lines), start+240)
for idx in range(s,e):
    print(f"{idx+1:05d}: {lines[idx]}")
