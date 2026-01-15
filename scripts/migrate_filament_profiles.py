"""
Migration script to add FilamentProfile table to the database
Run this script to add the filament profiles table.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.db import engine, Base, FilamentProfile, SessionLocal
from sqlalchemy import inspect

def migrate():
    """Add FilamentProfile table if it doesn't exist"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if 'filament_profiles' in existing_tables:
        print("✅ Table 'filament_profiles' already exists")
    else:
        print("Creating 'filament_profiles' table...")
        FilamentProfile.__table__.create(engine)
        print("✅ Table 'filament_profiles' created successfully")
    
    # Add some sample filament profiles
    db = SessionLocal()
    try:
        count = db.query(FilamentProfile).count()
        if count == 0:
            print("\n📦 Adding sample filament profiles...")
            
            sample_filaments = [
                # Bambu Lab PLA
                FilamentProfile(
                    name="Bambu PLA Basic - White",
                    brand="Bambu Lab",
                    material_type="PLA",
                    color_name="White",
                    color_hex="FFFFFFFF",
                    nozzle_temp_min=190, nozzle_temp_max=240, nozzle_temp_default=220,
                    bed_temp_min=45, bed_temp_max=65, bed_temp_default=55,
                    max_volumetric_speed=21.0,
                    k_value=0.02,
                    density=1.24,
                    drying_temp=50, drying_time=8,
                    requires_enclosure=False,
                    stock_count=1
                ),
                FilamentProfile(
                    name="Bambu PLA Basic - Black",
                    brand="Bambu Lab",
                    material_type="PLA",
                    color_name="Black",
                    color_hex="000000FF",
                    nozzle_temp_min=190, nozzle_temp_max=240, nozzle_temp_default=220,
                    bed_temp_min=45, bed_temp_max=65, bed_temp_default=55,
                    max_volumetric_speed=21.0,
                    k_value=0.02,
                    density=1.24,
                    drying_temp=50, drying_time=8,
                    requires_enclosure=False,
                    stock_count=1
                ),
                # Generic PLA
                FilamentProfile(
                    name="Generic PLA - Blue",
                    brand="Generic",
                    material_type="PLA",
                    color_name="Blue",
                    color_hex="41AAFFFF",
                    nozzle_temp_min=190, nozzle_temp_max=240, nozzle_temp_default=215,
                    bed_temp_min=45, bed_temp_max=60, bed_temp_default=55,
                    max_volumetric_speed=12.0,
                    k_value=0.02,
                    density=1.24,
                    drying_temp=50, drying_time=8,
                    requires_enclosure=False,
                    stock_count=1
                ),
                # PETG
                FilamentProfile(
                    name="Generic PETG - Clear",
                    brand="Generic",
                    material_type="PETG",
                    color_name="Clear",
                    color_hex="FFFFFF80",
                    nozzle_temp_min=220, nozzle_temp_max=260, nozzle_temp_default=240,
                    bed_temp_min=70, bed_temp_max=85, bed_temp_default=80,
                    max_volumetric_speed=10.0,
                    k_value=0.02,
                    density=1.27,
                    drying_temp=65, drying_time=8,
                    requires_enclosure=False,
                    stock_count=0
                ),
                # ABS
                FilamentProfile(
                    name="Generic ABS - Grey",
                    brand="Generic",
                    material_type="ABS",
                    color_name="Grey",
                    color_hex="808080FF",
                    nozzle_temp_min=230, nozzle_temp_max=270, nozzle_temp_default=250,
                    bed_temp_min=90, bed_temp_max=110, bed_temp_default=100,
                    max_volumetric_speed=10.0,
                    k_value=0.02,
                    density=1.04,
                    drying_temp=80, drying_time=8,
                    requires_enclosure=True,
                    stock_count=0
                ),
                # TPU
                FilamentProfile(
                    name="Generic TPU 95A - White",
                    brand="Generic",
                    material_type="TPU",
                    color_name="White",
                    color_hex="FFFFFFFF",
                    nozzle_temp_min=210, nozzle_temp_max=240, nozzle_temp_default=225,
                    bed_temp_min=25, bed_temp_max=60, bed_temp_default=50,
                    max_volumetric_speed=3.0,  # TPU prints slow
                    k_value=0.0,  # No pressure advance for TPU
                    density=1.21,
                    drying_temp=50, drying_time=8,
                    requires_enclosure=False,
                    notes="Print very slowly. Disable retraction or use minimal retraction.",
                    stock_count=0
                ),
            ]
            
            for filament in sample_filaments:
                db.add(filament)
            
            db.commit()
            print(f"✅ Added {len(sample_filaments)} sample filament profiles")
        else:
            print(f"ℹ️ Database already has {count} filament profiles")
            
    finally:
        db.close()
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate()
