import sqlite3

conn = sqlite3.connect('data/farm.db')
c = conn.cursor()

# List tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [r[0] for r in c.fetchall()])

# Check queue
try:
    c.execute("PRAGMA table_info(queue)")
    print("\nqueue columns:")
    for r in c.fetchall():
        print(f"  {r}")
    
    c.execute("SELECT * FROM queue ORDER BY queue_id DESC LIMIT 2")
    print("\nLatest queue items:")
    cols = [d[0] for d in c.description]
    print("Columns:", cols)
    for row in c.fetchall():
        print(dict(zip(cols, row)))
except Exception as e:
    print(f"Error: {e}")

conn.close()
