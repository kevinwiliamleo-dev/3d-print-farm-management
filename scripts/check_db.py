import sqlite3

conn = sqlite3.connect('data/farm.db')
cursor = conn.cursor()

# Get table info
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", [t[0] for t in tables])

# Check printers table
try:
    cursor.execute("PRAGMA table_info(printers)")
    columns = cursor.fetchall()
    print("\nPrinter columns:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
    
    cursor.execute("SELECT * FROM printers")
    rows = cursor.fetchall()
    print(f"\nTotal printers: {len(rows)}")
    for row in rows:
        print(f"  {row}")
except Exception as e:
    print(f"Error: {e}")

conn.close()
