"""
Database migration to add AMS columns to queue table
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'farm.db')
print(f"Migrating database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(queue)")
columns = [col[1] for col in cursor.fetchall()]
print(f"Existing columns: {columns}")

migrations = [
    ("ams_slot", "ALTER TABLE queue ADD COLUMN ams_slot INTEGER DEFAULT 0"),
    ("ams_mapping", "ALTER TABLE queue ADD COLUMN ams_mapping TEXT DEFAULT ''"),
    ("use_ams", "ALTER TABLE queue ADD COLUMN use_ams INTEGER DEFAULT 1"),
]

for col_name, sql in migrations:
    if col_name in columns:
        print(f"  Column '{col_name}' already exists, skipping")
    else:
        try:
            cursor.execute(sql)
            print(f"  Added column '{col_name}'")
        except Exception as e:
            print(f"  Error adding '{col_name}': {e}")

conn.commit()
conn.close()
print("Migration complete!")
