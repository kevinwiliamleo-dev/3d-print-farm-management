import sqlite3
conn = sqlite3.connect('data/farm.db')
c = conn.cursor()
c.execute('SELECT template_key, name, category, setting_key, controllable FROM gcode_templates ORDER BY category, [order]')
rows = c.fetchall()
start = [r for r in rows if r[2]=='start']
end = [r for r in rows if r[2]=='end']
print(f'=== START GCODE ({len(start)}) ===')
for i, r in enumerate(start):
    sk = r[3] if r[3] else '-'
    print(f'{i+1}. {r[1]} [{sk}]')
print()
print(f'=== END GCODE ({len(end)}) ===')
for i, r in enumerate(end):
    sk = r[3] if r[3] else '-'
    print(f'{i+1}. {r[1]} [{sk}]')
