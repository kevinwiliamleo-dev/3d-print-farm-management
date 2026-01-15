"""
Migration: Add skip_preprocessing column to queue table
Date: January 15, 2026
Purpose: Allow bypassing all G-code preprocessing for simple print workflow
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/farm.db")

def migrate():
    """Add skip_preprocessing column to queue table"""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(queue)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'skip_preprocessing' in columns:
            print("✅ Column 'skip_preprocessing' already exists")
            return True
        
        # Add column
        print("📝 Adding skip_preprocessing column...")
        cursor.execute("""
            ALTER TABLE queue 
            ADD COLUMN skip_preprocessing BOOLEAN DEFAULT 0
        """)
        
        conn.commit()
        print("✅ Migration complete: skip_preprocessing column added")
        print("   Default value: False (preprocessing enabled)")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration: Add skip_preprocessing")
    print("=" * 50)
    success = migrate()
    if success:
        print("\n✅ Migration successful!")
    else:
        print("\n❌ Migration failed!")
