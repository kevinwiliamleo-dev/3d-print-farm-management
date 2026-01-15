#!/usr/bin/env python3
"""Clear all queue items from the database"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / 'data' / 'farm.db'

print(f"Connecting to {db_path}...")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current queue count
    cursor.execute("SELECT COUNT(*) FROM queue")
    before_count = cursor.fetchone()[0]
    print(f"Queue items before: {before_count}")
    
    # Delete all queue items
    cursor.execute("DELETE FROM queue")
    conn.commit()
    
    # Verify deletion
    cursor.execute("SELECT COUNT(*) FROM queue")
    after_count = cursor.fetchone()[0]
    print(f"Queue items after: {after_count}")
    
    if after_count == 0:
        print("✓ Queue cleared successfully!")
    else:
        print("✗ Failed to clear queue")
    
    conn.close()

except Exception as e:
    print(f"ERROR: {e}")
