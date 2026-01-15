import sqlite3
conn = sqlite3.connect('data/farm.db')
c = conn.cursor()

# Verify Quick Print settings
c.execute('''
    SELECT name, quick_start, cog_noise_reduction, brush_material_wipe, 
           flow_calibration, vibration_test, final_wipe_nozzle, extrude_calibration_test,
           home_after_wipe, wipe_nozzle
    FROM print_presets WHERE name = 'Quick Print'
''')
row = c.fetchone()
if row:
    print('Quick Print preset settings:')
    print(f'  quick_start={row[1]}')
    print(f'  cog_noise_reduction={row[2]}')
    print(f'  brush_material_wipe={row[3]}')
    print(f'  flow_calibration={row[4]}')
    print(f'  vibration_test={row[5]}')
    print(f'  final_wipe_nozzle={row[6]}')
    print(f'  extrude_calibration_test={row[7]}')
    print(f'  home_after_wipe={row[8]}')
    print(f'  wipe_nozzle={row[9]}')
else:
    print('Quick Print preset not found!')

conn.close()
c.execute("SELECT name, cog_noise_reduction, brush_material_wipe, final_wipe_nozzle, wipe_nozzle, extrude_calibration_test, home_after_wipe FROM print_presets WHERE name = 'Quick Print'")
row = c.fetchone()
print(row)
conn.close()
