"""
Migration script to add Quick Start options to Queue and BucketList tables.

New columns:
- quick_start: Skip vibration + flow for faster startup
- preheat_offset: Heat to nozzle_temp - offset (0 = disabled, 20 = recommended)
- pre_extrude: Add pre-extrude command before print
- pre_extrude_length: Length to extrude in mm (default 2.2)

Based on FactorianDesigns optimization techniques.
"""
import sqlite3
from pathlib import Path

DATABASE_PATH = Path("data/farm.db")

def run_migration():
    """Add Quick Start columns to Queue and BucketList tables"""
    
    if not DATABASE_PATH.exists():
        print(f"Database not found: {DATABASE_PATH}")
        return False
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Columns to add
    new_columns = [
        ("quick_start", "BOOLEAN DEFAULT 0"),
        ("preheat_offset", "INTEGER DEFAULT 0"),
        ("pre_extrude", "BOOLEAN DEFAULT 0"),
        ("pre_extrude_length", "REAL DEFAULT 2.2"),
    ]
    
    tables = ["queue", "bucket_list"]
    
    for table in tables:
        print(f"\nMigrating table: {table}")
        
        # Get existing columns
        cursor.execute(f"PRAGMA table_info({table})")
        existing_columns = [col[1] for col in cursor.fetchall()]
        print(f"Existing columns: {len(existing_columns)}")
        
        for col_name, col_def in new_columns:
            if col_name in existing_columns:
                print(f"  - Column '{col_name}' already exists, skipping")
            else:
                try:
                    sql = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"
                    cursor.execute(sql)
                    print(f"  ✓ Added column '{col_name}'")
                except Exception as e:
                    print(f"  ✗ Failed to add '{col_name}': {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✓ Migration completed successfully!")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Quick Start Options Migration")
    print("Adding FactorianDesigns optimization columns")
    print("=" * 60)
    run_migration()
