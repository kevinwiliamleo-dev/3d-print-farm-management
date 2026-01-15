"""
Migration: Add filament_already_loaded column to queue and bucket_list tables

This column allows users to skip AMS load sequence when filament is already loaded in extruder.
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "data" / "farm.db"


def migrate():
    """Add filament_already_loaded column to queue and bucket_list tables"""
    
    if not DATABASE_PATH.exists():
        print(f"❌ Database not found: {DATABASE_PATH}")
        return False
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists in queue table
        cursor.execute("PRAGMA table_info(queue)")
        queue_columns = [col[1] for col in cursor.fetchall()]
        
        if 'filament_already_loaded' not in queue_columns:
            print("Adding filament_already_loaded column to queue table...")
            cursor.execute("""
                ALTER TABLE queue 
                ADD COLUMN filament_already_loaded BOOLEAN DEFAULT 0
            """)
            print("✅ Added column to queue table")
        else:
            print("ℹ️ Column already exists in queue table")
        
        # Check if column already exists in bucket_list table
        cursor.execute("PRAGMA table_info(bucket_list)")
        bucket_columns = [col[1] for col in cursor.fetchall()]
        
        if 'filament_already_loaded' not in bucket_columns:
            print("Adding filament_already_loaded column to bucket_list table...")
            cursor.execute("""
                ALTER TABLE bucket_list 
                ADD COLUMN filament_already_loaded BOOLEAN DEFAULT 0
            """)
            print("✅ Added column to bucket_list table")
        else:
            print("ℹ️ Column already exists in bucket_list table")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Migration: Add filament_already_loaded Column")
    print("=" * 50)
    migrate()
