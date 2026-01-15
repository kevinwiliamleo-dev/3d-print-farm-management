#!/usr/bin/env python3
"""Script untuk menambahkan inventory filament ke database."""

import requests
import json

API_BASE = "http://localhost:5000/api"

# Daftar inventory filament
my_inventory = [
    {
        "name": "Sunlu PLA+ 2.0 - Putih",
        "brand": "Sunlu",
        "material_type": "PLA+ 2.0",
        "color_hex": "FFFFFFFF",
        "color_name": "White",
        "nozzle_temp_min": 205,
        "nozzle_temp_max": 235,
        "nozzle_temp_default": 215,
        "bed_temp_min": 55,
        "bed_temp_max": 65,
        "bed_temp_default": 60,
        "max_volumetric_speed": 20,
        "k_value": 0.025,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 700,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Elegoo PLA - Light Blue",
        "brand": "Elegoo",
        "material_type": "PLA",
        "color_hex": "87CEEBFF",
        "color_name": "Light Blue",
        "nozzle_temp_min": 190,
        "nozzle_temp_max": 230,
        "nozzle_temp_default": 205,
        "bed_temp_min": 50,
        "bed_temp_max": 60,
        "bed_temp_default": 60,
        "max_volumetric_speed": 15,
        "k_value": 0.030,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 850,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Elegoo PLA - Purple",
        "brand": "Elegoo",
        "material_type": "PLA",
        "color_hex": "9900FFFF",
        "color_name": "Purple",
        "nozzle_temp_min": 190,
        "nozzle_temp_max": 230,
        "nozzle_temp_default": 205,
        "bed_temp_min": 50,
        "bed_temp_max": 60,
        "bed_temp_default": 60,
        "max_volumetric_speed": 15,
        "k_value": 0.030,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 950,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Sunlu High Speed Matt PETG - Sky Blue",
        "brand": "Sunlu",
        "material_type": "High Speed Matt PETG",
        "color_hex": "00BFFFFF",
        "color_name": "Sky Blue",
        "nozzle_temp_min": 230,
        "nozzle_temp_max": 250,
        "nozzle_temp_default": 240,
        "bed_temp_min": 70,
        "bed_temp_max": 85,
        "bed_temp_default": 80,
        "max_volumetric_speed": 18,
        "k_value": 0.038,
        "density": 1.27,
        "drying_temp": 65,
        "drying_time": 6,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 1000,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Sunlu PETG - White",
        "brand": "Sunlu",
        "material_type": "PETG",
        "color_hex": "FFFFFFFF",
        "color_name": "White",
        "nozzle_temp_min": 220,
        "nozzle_temp_max": 250,
        "nozzle_temp_default": 235,
        "bed_temp_min": 70,
        "bed_temp_max": 80,
        "bed_temp_default": 75,
        "max_volumetric_speed": 14,
        "k_value": 0.040,
        "density": 1.27,
        "drying_temp": 65,
        "drying_time": 6,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 1000,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Sunlu PLA+ - Transparent Blue",
        "brand": "Sunlu",
        "material_type": "PLA+",
        "color_hex": "4A90D9AA",
        "color_name": "Transparent Blue",
        "nozzle_temp_min": 200,
        "nozzle_temp_max": 235,
        "nozzle_temp_default": 215,
        "bed_temp_min": 55,
        "bed_temp_max": 65,
        "bed_temp_default": 60,
        "max_volumetric_speed": 18,
        "k_value": 0.028,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 1000,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Sunlu TPU Silk - Cream White",
        "brand": "Sunlu",
        "material_type": "TPU Silk",
        "color_hex": "FFFDD0FF",
        "color_name": "Cream White",
        "nozzle_temp_min": 200,
        "nozzle_temp_max": 230,
        "nozzle_temp_default": 215,
        "bed_temp_min": 50,
        "bed_temp_max": 60,
        "bed_temp_default": 55,
        "max_volumetric_speed": 4,
        "k_value": 0.200,
        "density": 1.21,
        "drying_temp": 55,
        "drying_time": 6,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 1000,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Elegoo PLA - Sea Green",
        "brand": "Elegoo",
        "material_type": "PLA",
        "color_hex": "2E8B57FF",
        "color_name": "Sea Green",
        "nozzle_temp_min": 190,
        "nozzle_temp_max": 230,
        "nozzle_temp_default": 205,
        "bed_temp_min": 50,
        "bed_temp_max": 60,
        "bed_temp_default": 60,
        "max_volumetric_speed": 15,
        "k_value": 0.030,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 1000,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Elegoo PLA - Brown",
        "brand": "Elegoo",
        "material_type": "PLA",
        "color_hex": "8B4513FF",
        "color_name": "Brown",
        "nozzle_temp_min": 190,
        "nozzle_temp_max": 230,
        "nozzle_temp_default": 205,
        "bed_temp_min": 50,
        "bed_temp_max": 60,
        "bed_temp_default": 60,
        "max_volumetric_speed": 15,
        "k_value": 0.030,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 1000,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Anycubic PLA - Magenta",
        "brand": "Anycubic",
        "material_type": "PLA Standard",
        "color_hex": "FF00FFFF",
        "color_name": "Magenta",
        "nozzle_temp_min": 190,
        "nozzle_temp_max": 230,
        "nozzle_temp_default": 200,
        "bed_temp_min": 50,
        "bed_temp_max": 60,
        "bed_temp_default": 60,
        "max_volumetric_speed": 15,
        "k_value": 0.030,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 1000,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "Anycubic PLA - Clear",
        "brand": "Anycubic",
        "material_type": "PLA Standard",
        "color_hex": "F5F5F5AA",
        "color_name": "Clear",
        "nozzle_temp_min": 190,
        "nozzle_temp_max": 230,
        "nozzle_temp_default": 200,
        "bed_temp_min": 50,
        "bed_temp_max": 60,
        "bed_temp_default": 60,
        "max_volumetric_speed": 15,
        "k_value": 0.030,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 1000,
        "stock_count": 1,
        "notes": ""
    },
    {
        "name": "eSUN PLA+ - Red",
        "brand": "eSUN",
        "material_type": "PLA+",
        "color_hex": "FF0000FF",
        "color_name": "Red",
        "nozzle_temp_min": 205,
        "nozzle_temp_max": 235,
        "nozzle_temp_default": 215,
        "bed_temp_min": 50,
        "bed_temp_max": 65,
        "bed_temp_default": 60,
        "max_volumetric_speed": 18,
        "k_value": 0.025,
        "density": 1.24,
        "drying_temp": 45,
        "drying_time": 4,
        "requires_enclosure": False,
        "requires_hardened_nozzle": False,
        "spool_weight": 600,
        "stock_count": 1,
        "notes": ""
    },
]

def add_filaments():
    """Tambahkan semua filament ke database."""
    print("="*60)
    print("Menambahkan Filament ke Inventory")
    print("="*60)
    
    success_count = 0
    fail_count = 0
    
    for i, filament in enumerate(my_inventory, 1):
        print(f"\n[{i}/{len(my_inventory)}] {filament['name']}")
        
        try:
            response = requests.post(
                f"{API_BASE}/filaments",
                json=filament,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200 or response.status_code == 201:
                result = response.json()
                print(f"   ✓ Berhasil ditambahkan (ID: {result.get('id', 'N/A')})")
                success_count += 1
            else:
                print(f"   ✗ Gagal: {response.status_code} - {response.text}")
                fail_count += 1
                
        except Exception as e:
            print(f"   ✗ Error: {e}")
            fail_count += 1
    
    print("\n" + "="*60)
    print(f"Hasil: {success_count} berhasil, {fail_count} gagal")
    print("="*60)

if __name__ == "__main__":
    add_filaments()
