"""
Quick script to remove all printers from database
Run to test discovery from scratch
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import SessionLocal
from src.database.db import Printer

def clear_printers():
    db = SessionLocal()
    try:
        printers = db.query(Printer).all()
        print(f'📋 Found {len(printers)} printer(s) in database:')
        
        for p in printers:
            print(f'  - {p.printer_id}: {p.printer_name} ({p.status})')
        
        if printers:
            print(f'\n🗑️  Removing all printers...')
            for p in printers:
                db.delete(p)
            db.commit()
            print('✅ All printers removed from database')
            print('\n💡 Now test discovery: Click "📡 Scan Now" in frontend')
        else:
            print('✅ Database already empty')
        
    finally:
        db.close()

if __name__ == '__main__':
    clear_printers()
