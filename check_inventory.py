"""Check existing inventory data before migration"""
import sqlite3

conn = sqlite3.connect('data/farm.db')
c = conn.cursor()

# List semua tabel
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('=== TABLES IN DATABASE ===')
for t in tables:
    print(f'  - {t[0]}')

# Cek data di setiap tabel penting
important_tables = ['filament_profiles', 'ams_slots', 'printers', 'automation_settings']
for table in important_tables:
    try:
        c.execute(f'SELECT COUNT(*) FROM {table}')
        count = c.fetchone()[0]
        print(f'\n{table}: {count} records')
        if count > 0 and count <= 20:
            c.execute(f'SELECT * FROM {table}')
            rows = c.fetchall()
            # Get column names
            c.execute(f'PRAGMA table_info({table})')
            cols = [col[1] for col in c.fetchall()]
            print(f'  Columns: {cols}')
            for row in rows:
                print(f'  {row}')
    except Exception as e:
        print(f'{table}: TABLE NOT EXISTS or ERROR - {e}')

conn.close()
print('\n=== DATA AKAN DIPERTAHANKAN ===')
