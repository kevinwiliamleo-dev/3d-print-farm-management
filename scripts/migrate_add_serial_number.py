"""
Migration: Add serial_number column to printers table
Run this ONCE on the server database to fix MQTT topics.

Usage:
    python scripts/migrate_add_serial_number.py

The serial_number column stores the actual Bambu printer serial
(e.g. '03900D5A2402051') needed for correct MQTT topic names.
"""
import sqlite3
import os
import sys

# Support both local and Docker paths
DB_PATHS = [
    "./data/farm.db",
    "/app/data/farm.db",
]

def get_db_path():
    for path in DB_PATHS:
        if os.path.exists(path):
            return path
    # Also check script's parent folder
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(script_dir, "data", "farm.db")
    if os.path.exists(path):
        return path
    return None

def migrate(db_path: str):
    print(f"[Migration] Connecting to: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(printers)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"[Migration] Existing columns: {columns}")

    if "serial_number" not in columns:
        print("[Migration] Adding 'serial_number' column to printers table...")
        cursor.execute("ALTER TABLE printers ADD COLUMN serial_number VARCHAR(100)")
        conn.commit()
        print("[Migration] ✅ Column added successfully!")
    else:
        print("[Migration] ✅ Column 'serial_number' already exists, skipping.")

    # Show current printers
    cursor.execute("SELECT printer_id, printer_name, printer_ip, serial_number FROM printers")
    printers = cursor.fetchall()
    print(f"\n[Migration] Current printers in database:")
    for p in printers:
        print(f"  printer_id={p[0]}, name={p[1]}, ip={p[2]}, serial_number={p[3]}")

    if printers:
        print("\n⚠️  PENTING: Update serial_number via API atau langsung di database:")
        print("   Contoh untuk printer BAMBU_192_168_4_101:")
        print("   > curl -X PATCH http://SERVER_IP:5051/api/printers/BAMBU_192_168_4_101/serial")
        print('     -H "Content-Type: application/json"')
        print('     -d \'{"serial_number": "03900D5A2402051"}\'')
        print()
        print("   Atau via SQLite langsung:")
        print("   UPDATE printers SET serial_number='03900D5A2402051' WHERE printer_id='BAMBU_192_168_4_101';")

    conn.close()
    print("\n[Migration] Done!")

if __name__ == "__main__":
    db_path = get_db_path()
    if not db_path:
        print(f"[Migration] ERROR: Database not found. Checked paths: {DB_PATHS}")
        sys.exit(1)
    migrate(db_path)
