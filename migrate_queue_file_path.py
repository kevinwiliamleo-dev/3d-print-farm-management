#!/usr/bin/env python3
"""
Migration script to add queue_file_path column to queue table
Run this once to update existing database schema
"""
import sqlite3
from pathlib import Path

# Database path
DB_DIR = Path(__file__).parent / "data"
DATABASE_PATH = str(DB_DIR / "farm.db")

# Queue files directory
QUEUE_FILES_DIR = DB_DIR / "queue_files"

def migrate():
    """Add queue_file_path column to queue table"""
    print(f"🔧 Migrating database: {DATABASE_PATH}")
    
    # Create queue_files directory
    QUEUE_FILES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created queue_files directory: {QUEUE_FILES_DIR}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(queue)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'queue_file_path' in columns:
            print("✅ Column 'queue_file_path' already exists")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE queue 
                ADD COLUMN queue_file_path VARCHAR(500)
            """)
            conn.commit()
            print("✅ Added 'queue_file_path' column to queue table")
        
        # Show updated schema
        cursor.execute("PRAGMA table_info(queue)")
        columns = cursor.fetchall()
        print("\n📊 Queue table columns:")
        for col in columns:
            print(f"   - {col[1]}: {col[2]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate()
