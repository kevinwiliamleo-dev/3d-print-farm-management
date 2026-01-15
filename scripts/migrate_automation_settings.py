"""
Migration Script: Add Print Automation Settings to Queue Table

This adds the new automation columns for G-code preprocessing:
- filament_id: FK to filament_profiles for temperature overrides
- auto_bed_leveling: Enable G29 bed leveling
- flow_calibration: Enable flow test (M983/M984)
- vibration_test: Enable resonance test (M970)
- clean_nozzle: Enable nozzle cleaning sequence
- auto_eject: Auto push-off after print
- cooldown_temp: Target bed temp before eject (°C)
- startup_sound: Play startup melody
- end_sound: Play completion melody

Run this script once to update existing databases.
"""

import sqlite3
import os
from pathlib import Path

# Use the same DB_DIR as config.py
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "data"
DATABASE_PATH = str(DB_DIR / "farm.db")


def migrate():
    """Add automation settings columns to queue table"""
    print(f"📦 Migrating database: {DATABASE_PATH}")
    
    if not os.path.exists(DATABASE_PATH):
        print("❌ Database not found. It will be created when the server starts.")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Define new columns with their defaults
    new_columns = [
        ("filament_id", "INTEGER", "NULL"),
        ("auto_bed_leveling", "BOOLEAN", "1"),  # True by default
        ("flow_calibration", "BOOLEAN", "0"),   # False by default (for auto-eject)
        ("vibration_test", "BOOLEAN", "0"),
        ("clean_nozzle", "BOOLEAN", "1"),       # True by default
        ("auto_eject", "BOOLEAN", "1"),         # True by default for print farm
        ("cooldown_temp", "INTEGER", "32"),     # 32°C for room temp
        ("startup_sound", "BOOLEAN", "1"),
        ("end_sound", "BOOLEAN", "1"),
    ]
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(queue)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    print(f"📋 Existing columns: {existing_columns}")
    
    # Add missing columns
    for col_name, col_type, default in new_columns:
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE queue ADD COLUMN {col_name} {col_type} DEFAULT {default}"
                cursor.execute(sql)
                print(f"✅ Added column: {col_name} ({col_type}) DEFAULT {default}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"⏭️  Column already exists: {col_name}")
                else:
                    print(f"❌ Error adding {col_name}: {e}")
        else:
            print(f"⏭️  Column already exists: {col_name}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration complete!")
    print("   You can now restart the server.")


if __name__ == "__main__":
    migrate()
