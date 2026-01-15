import sqlite3

conn = sqlite3.connect('data/farm.db')
c = conn.cursor()
c.execute("SELECT gcode FROM gcode_templates WHERE template_key = 'startup_sound'")
row = c.fetchone()
if row:
    print("Gcode content:")
    print(row[0])
else:
    print("Template not found")
conn.close()
