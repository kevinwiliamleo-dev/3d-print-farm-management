"""
Migration script to create AMS slot assignments table.
This stores the mapping between AMS slots and filament inventory.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "farm.db")

def migrate():
    """Create ams_slot_assignments table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create ams_slot_assignments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ams_slot_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            printer_id TEXT NOT NULL,
            slot_number INTEGER NOT NULL,
            filament_id INTEGER,
            remaining_grams REAL DEFAULT 0,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(printer_id, slot_number),
            FOREIGN KEY (filament_id) REFERENCES filament_profiles(filament_id)
        )
    """)
    
    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ams_slots_printer 
        ON ams_slot_assignments(printer_id)
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ Migration complete: ams_slot_assignments table created")

if __name__ == "__main__":
    migrate()
