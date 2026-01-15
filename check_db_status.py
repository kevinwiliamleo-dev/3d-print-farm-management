#!/usr/bin/env python
"""Check database tables status"""
import sqlite3

conn = sqlite3.connect('data/farm.db')
c = conn.cursor()

# Get all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [t[0] for t in c.fetchall()]

print('=== Database Tables Status ===')
print()
for table in sorted(tables):
    try:
        c.execute(f'SELECT COUNT(*) FROM {table}')
        count = c.fetchone()[0]
        status = '[EMPTY]' if count == 0 else f'{count} rows'
        print(f'{table}: {status}')
    except Exception as e:
        print(f'{table}: ERROR - {e}')

conn.close()
