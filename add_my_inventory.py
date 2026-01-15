#!/usr/bin/env python
"""Add filament inventory to database"""
import requests

BASE_URL = "http://localhost:5000/api/filaments"

# Filament inventory with correct API fields
filaments = [
    # Active filaments (in use)
    {"name": "Sunlu PLA+ 2.0 White", "brand": "Sunlu", "material_type": "PLA+", "color_name": "White", "color_hex": "FFFFFFFF", 
     "nozzle_temp_default": 220, "bed_temp_default": 60, "spool_weight": 700},
    
    {"name": "Elegoo PLA Light Blue", "brand": "Elegoo", "material_type": "PLA", "color_name": "Light Blue", "color_hex": "87CEEBFF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 850},
    
    {"name": "Elegoo PLA Purple", "brand": "Elegoo", "material_type": "PLA", "color_name": "Purple", "color_hex": "800080FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 950},
    
    {"name": "Sunlu HS Matt PETG Sky Blue", "brand": "Sunlu", "material_type": "PETG", "color_name": "Sky Blue", "color_hex": "87CEEBFF", 
     "nozzle_temp_default": 240, "nozzle_temp_min": 230, "nozzle_temp_max": 250, "bed_temp_default": 75, "bed_temp_min": 70, "bed_temp_max": 85, 
     "max_volumetric_speed": 15.0, "spool_weight": 1000},
    
    {"name": "Sunlu PETG White", "brand": "Sunlu", "material_type": "PETG", "color_name": "White", "color_hex": "FFFFFFFF", 
     "nozzle_temp_default": 235, "nozzle_temp_min": 220, "nozzle_temp_max": 250, "bed_temp_default": 75, "bed_temp_min": 70, "bed_temp_max": 85, 
     "spool_weight": 1000},
    
    {"name": "Sunlu PLA+ Transparent Blue", "brand": "Sunlu", "material_type": "PLA+", "color_name": "Transparent Blue", "color_hex": "1E90FF80", 
     "nozzle_temp_default": 220, "bed_temp_default": 60, "spool_weight": 1000},
    
    {"name": "Sunlu TPU Silk Cream White", "brand": "Sunlu", "material_type": "TPU", "color_name": "Cream White", "color_hex": "FFFDD0FF", 
     "nozzle_temp_default": 225, "nozzle_temp_min": 210, "nozzle_temp_max": 240, "bed_temp_default": 50, "bed_temp_min": 30, "bed_temp_max": 60, 
     "max_volumetric_speed": 5.0, "spool_weight": 1000},
    
    {"name": "Elegoo PLA Sea Green", "brand": "Elegoo", "material_type": "PLA", "color_name": "Sea Green", "color_hex": "2E8B57FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    {"name": "Elegoo PLA Brown", "brand": "Elegoo", "material_type": "PLA", "color_name": "Brown", "color_hex": "8B4513FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    {"name": "Anycubic PLA Magenta", "brand": "Anycubic", "material_type": "PLA", "color_name": "Magenta", "color_hex": "FF00FFFF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    # Stock filaments - eSun
    {"name": "eSun PLA Basic Green", "brand": "eSun", "material_type": "PLA", "color_name": "Green", "color_hex": "008000FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    {"name": "eSun PLA Basic Holly Green", "brand": "eSun", "material_type": "PLA", "color_name": "Holly Green", "color_hex": "006400FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    {"name": "eSun PLA Basic Beige", "brand": "eSun", "material_type": "PLA", "color_name": "Beige", "color_hex": "F5F5DCFF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    {"name": "eSun PLA Basic Grey", "brand": "eSun", "material_type": "PLA", "color_name": "Grey", "color_hex": "808080FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    {"name": "eSun PLA Basic Light Grey", "brand": "eSun", "material_type": "PLA", "color_name": "Light Grey", "color_hex": "D3D3D3FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    {"name": "eSun PLA Matte", "brand": "eSun", "material_type": "PLA", "color_name": "Matte", "color_hex": "A0A0A0FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    # Stock filaments - Sunlu
    {"name": "Sunlu PLA Matte", "brand": "Sunlu", "material_type": "PLA", "color_name": "Matte", "color_hex": "A0A0A0FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
    
    {"name": "Sunlu TPU Grey", "brand": "Sunlu", "material_type": "TPU", "color_name": "Grey", "color_hex": "808080FF", 
     "nozzle_temp_default": 225, "nozzle_temp_min": 210, "nozzle_temp_max": 240, "bed_temp_default": 50, "bed_temp_min": 30, "bed_temp_max": 60, 
     "max_volumetric_speed": 5.0, "spool_weight": 1000},
    
    # Stock filaments - Elegoo
    {"name": "Elegoo PLA Wood", "brand": "Elegoo", "material_type": "PLA", "color_name": "Wood", "color_hex": "DEB887FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "notes": "Wood-infused PLA, may require larger nozzle", "spool_weight": 1000},
    
    {"name": "Elegoo PLA Red", "brand": "Elegoo", "material_type": "PLA", "color_name": "Red", "color_hex": "FF0000FF", 
     "nozzle_temp_default": 210, "bed_temp_default": 55, "spool_weight": 1000},
]

print("Adding filament inventory...")
print("=" * 50)

success = 0
failed = 0

for f in filaments:
    try:
        response = requests.post(BASE_URL, json=f, timeout=10)
        if response.status_code in [200, 201]:
            print(f"[OK] {f['name']}")
            success += 1
        else:
            print(f"[FAIL] {f['name']}: {response.status_code}")
            failed += 1
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] {f['name']}")
        failed += 1
    except Exception as e:
        print(f"[ERROR] {f['name']}: {e}")
        failed += 1

print("=" * 50)
print(f"Added: {success}, Failed: {failed}")
