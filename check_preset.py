import sqlite3
conn = sqlite3.connect('data/farm.db')
c = conn.cursor()

# Check quick_print preset
c.execute("SELECT * FROM print_presets WHERE name = 'Quick Print'")
row = c.fetchone()
if row:
    cols = [d[0] for d in c.description]
    preset = dict(zip(cols, row))
    print("Quick Print Preset:")
    for k, v in preset.items():
        print(f"  {k}: {v}")
else:
    print("Quick print preset not found")

# Check which templates are enabled
print("\n\nEnabled Templates:")
c.execute("SELECT template_key, name, enabled, controllable FROM gcode_templates WHERE enabled = 1 ORDER BY category, \"order\"")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} (controllable={row[3]})")

print("\n\nDisabled Templates:")
c.execute("SELECT template_key, name, enabled, controllable FROM gcode_templates WHERE enabled = 0 ORDER BY category, \"order\"")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]} (controllable={row[3]})")

conn.close()
