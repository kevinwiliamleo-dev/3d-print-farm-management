"""
Test script for Template Mode gcode processing
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.gcode_templates import (
    GCodeTemplates, 
    GCodeLayerExtractor, 
    TemplateSettings, 
    PrinterConfig,
    process_gcode_with_templates
)

def find_gcode_file():
    """Find a gcode file in uploads or data folder"""
    search_dirs = ['data/uploads', 'data/gcode', 'data/queue_files', 'data']
    
    for dir_path in search_dirs:
        if not os.path.exists(dir_path):
            continue
        for file in os.listdir(dir_path):
            if file.endswith('.gcode'):
                return os.path.join(dir_path, file)
    
    return None


def test_with_sample():
    """Test with sample gcode"""
    sample = """
; sample gcode file
; nozzle_temperature = 220
; bed_temperature = 65
; filament_type = PLA

; start gcode
M104 S220
M140 S65
G28

; CHANGE_LAYER
; Z_HEIGHT: 0.2
G1 X100 Y100 Z0.2 F3000
G1 E5 F200
G1 X110 Y100 E5.1
G1 X110 Y110 E5.2

; CHANGE_LAYER
; Z_HEIGHT: 0.4
G1 X100 Y100 Z0.4 F3000
G1 E5.3 F200
G1 X110 Y100 E5.4

; EXECUTABLE_BLOCK_END
M104 S0
M140 S0
"""
    return sample


def main():
    print("=" * 60)
    print("TEMPLATE MODE GCODE PROCESSOR TEST")
    print("=" * 60)
    print()
    
    # Find or use sample gcode
    gcode_file = find_gcode_file()
    
    if gcode_file:
        print(f"📁 Found gcode file: {gcode_file}")
        with open(gcode_file, 'r', encoding='utf-8', errors='ignore') as f:
            gcode_content = f.read()
    else:
        print("📝 Using sample gcode (no file found)")
        gcode_content = test_with_sample()
    
    print(f"   Total lines: {len(gcode_content.split(chr(10)))}")
    print()
    
    # Test extraction
    print("=" * 60)
    print("1. EXTRACTING PRINT LAYERS")
    print("=" * 60)
    
    extractor = GCodeLayerExtractor()
    layers, metadata = extractor.extract_print_layers(gcode_content)
    
    print(f"   Original lines: {metadata['original_lines']}")
    print(f"   Extracted lines: {metadata['extracted_lines']}")
    print(f"   First layer at line: {metadata['first_layer_line']}")
    print(f"   Last layer at line: {metadata['last_layer_line']}")
    print()
    print("   Detected from file:")
    print(f"   - Nozzle temp: {metadata['nozzle_temp']}°C")
    print(f"   - Bed temp: {metadata['bed_temp']}°C")
    print(f"   - Filament: {metadata['filament_type']}")
    print()
    
    # Test template generation
    print("=" * 60)
    print("2. GENERATING START GCODE TEMPLATE")
    print("=" * 60)
    
    settings = TemplateSettings(
        nozzle_temp=metadata['nozzle_temp'],
        bed_temp=metadata['bed_temp'],
        use_ams=True,
        ams_slot=0,
        filament_already_loaded=True,  # Test skip AMS load
        auto_eject=True,
        cooldown_temp=32,
        pre_extrude=True,
        pre_extrude_length=2.2,
    )
    
    templates = GCodeTemplates(PrinterConfig())
    start_gcode = templates.generate_start_gcode(settings)
    
    print("   First 25 lines of start gcode:")
    print("-" * 40)
    for i, line in enumerate(start_gcode.split('\n')[:25]):
        print(f"   {line}")
    print("   ...")
    print()
    
    # Test end gcode
    print("=" * 60)
    print("3. GENERATING END GCODE TEMPLATE")
    print("=" * 60)
    
    end_gcode = templates.generate_end_gcode(settings)
    
    print("   Full end gcode:")
    print("-" * 40)
    for line in end_gcode.split('\n'):
        print(f"   {line}")
    print()
    
    # Test full processing
    print("=" * 60)
    print("4. FULL PROCESSING (START + LAYERS + END)")
    print("=" * 60)
    
    result = process_gcode_with_templates(gcode_content, settings)
    result_lines = result.split('\n')
    
    print(f"   Output lines: {len(result_lines)}")
    print()
    print("   First 15 lines:")
    print("-" * 40)
    for line in result_lines[:15]:
        print(f"   {line}")
    print("   ...")
    print()
    print("   Last 20 lines:")
    print("-" * 40)
    for line in result_lines[-20:]:
        print(f"   {line}")
    
    print()
    print("=" * 60)
    print("✅ TEMPLATE MODE TEST COMPLETE")
    print("=" * 60)
    
    # Check critical safety commands
    print()
    print("🔒 SAFETY CHECK:")
    has_hotend_off = 'M104 S0' in result
    has_bed_off = 'M140 S0' in result
    has_fan_off = 'M106 S0' in result
    
    print(f"   M104 S0 (hotend off): {'✅' if has_hotend_off else '❌ MISSING!'}")
    print(f"   M140 S0 (bed off): {'✅' if has_bed_off else '❌ MISSING!'}")
    print(f"   M106 S0 (fan off): {'✅' if has_fan_off else '❌ MISSING!'}")
    
    if not all([has_hotend_off, has_bed_off, has_fan_off]):
        print()
        print("⚠️  WARNING: Missing safety commands!")
        return False
    
    print()
    print("✅ All safety commands present")
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
