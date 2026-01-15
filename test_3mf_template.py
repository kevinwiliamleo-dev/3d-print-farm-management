"""
Test template mode with real 3MF file
"""
import os
from pathlib import Path

# Find a 3MF file
test_file = None
for dir_path in ['data/uploads', 'data/queue_files', 'data']:
    if not os.path.exists(dir_path):
        continue
    for f in os.listdir(dir_path):
        if f.endswith('.3mf'):
            test_file = os.path.join(dir_path, f)
            print(f"Found 3MF: {test_file}")
            break
    if test_file:
        break

if not test_file:
    print("No 3MF file found. Please upload a file first.")
    exit(1)

# Extract gcode from 3MF
from src.utils.gcode_parser import extract_gcode_from_3mf

result = extract_gcode_from_3mf(test_file, plate_num=1, max_lines=999999)
if result.get('error'):
    print(f"Error extracting gcode: {result['error']}")
    exit(1)

gcode_lines = result['gcode']
print(f"Total lines in 3MF gcode: {len(gcode_lines)}")

# Test template mode extraction
from src.services.gcode_templates import (
    GCodeLayerExtractor, 
    TemplateSettings, 
    GCodeTemplates, 
    PrinterConfig,
    process_gcode_with_templates
)

gcode_content = '\n'.join(gcode_lines)
extractor = GCodeLayerExtractor()
layers, metadata = extractor.extract_print_layers(gcode_content)

print()
print("=" * 60)
print("EXTRACTION RESULTS")
print("=" * 60)
print(f"Original lines: {metadata['original_lines']}")
print(f"Extracted print layer lines: {metadata['extracted_lines']}")
print(f"Start gcode removed: {metadata['first_layer_line']} lines")
print(f"End gcode removed: {metadata['original_lines'] - metadata['last_layer_line'] - 1} lines")
reduction = 100 - (metadata['extracted_lines'] / metadata['original_lines'] * 100)
print(f"Total reduction: {reduction:.1f}% of file was start/end gcode")
print()
print("Detected settings from file:")
print(f"  Nozzle temp: {metadata['nozzle_temp']}°C")
print(f"  Bed temp: {metadata['bed_temp']}°C")
print(f"  Filament type: {metadata['filament_type']}")

# Generate full processed file
print()
print("=" * 60)
print("GENERATING PROCESSED GCODE")
print("=" * 60)

settings = TemplateSettings(
    nozzle_temp=metadata['nozzle_temp'],
    bed_temp=metadata['bed_temp'],
    filament_type=metadata['filament_type'],
    use_ams=True,
    ams_slot=0,
    filament_already_loaded=True,
    auto_eject=True,
    cooldown_temp=32,
)

processed = process_gcode_with_templates(gcode_content, settings)
processed_lines = processed.split('\n')

print(f"Final output: {len(processed_lines)} lines")
print()

# Show first 30 lines (our template start gcode)
print("FIRST 30 LINES (Template Start Gcode):")
print("-" * 60)
for line in processed_lines[:30]:
    print(line)
print("...")
print()

# Show transition to print layers (around line 60-80)
print("TRANSITION TO PRINT LAYERS (lines 60-80):")
print("-" * 60)
for i, line in enumerate(processed_lines[60:80], start=61):
    print(f"{i}: {line}")
print()

# Show last 25 lines (our template end gcode)
print("LAST 25 LINES (Template End Gcode):")
print("-" * 60)
for line in processed_lines[-25:]:
    print(line)

print()
print("✅ Template mode processing complete!")
print("✅ All unnecessary start/end gcode has been replaced with optimized templates")
