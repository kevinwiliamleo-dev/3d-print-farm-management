"""
Process 3MF files from input folder and save modified versions to output folder

Settings:
- All automation disabled (vibration, flow, bed leveling, clean nozzle, sounds)
- Quick Start enabled (preheat offset -20°C, pre-extrude 2.2mm)
"""
import sys
sys.path.insert(0, '.')

from pathlib import Path
import zipfile
from src.services.gcode_preprocessor import GCodePreprocessor, PrintSettings, FilamentSettings
from src.utils.gcode_parser import extract_gcode_from_3mf

INPUT_DIR = Path('data/3mf_input')
OUTPUT_DIR = Path('data/3mf_output')

def process_3mf_files():
    # Get all 3MF files in input
    files = list(INPUT_DIR.glob('*.3mf'))
    print(f'Found {len(files)} file(s) to process')
    
    if not files:
        print('No 3MF files found in data/3mf_input/')
        return
    
    for source_file in files:
        print(f'\nProcessing: {source_file.name}')
        
        # Extract G-code
        result = extract_gcode_from_3mf(source_file, plate_num=1, max_lines=999999)
        if result.get('error'):
            print(f'  ERROR: {result["error"]}')
            continue
        
        lines = result['gcode']
        selected_plate = result['selected_plate']
        original_content = '\n'.join(lines)
        
        print(f'  Original: {len(lines)} lines')
        
        # Process with preprocessor - ALL settings DISABLED, Quick Start ENABLED
        preprocessor = GCodePreprocessor()
        settings = PrintSettings(
            auto_bed_leveling=False,
            flow_calibration=False,
            vibration_test=False,
            clean_nozzle=False,  # DISABLED
            startup_sound=False,
            end_sound=False,
            quick_start=True,
            preheat_offset=20,
            pre_extrude=True,
            pre_extrude_length=2.2
        )
        settings = settings.validate()
        filament = FilamentSettings()
        
        modified_content = preprocessor.process_gcode(original_content, settings, filament)
        modified_lines = modified_content.split('\n')
        
        print(f'  Modified: {len(modified_lines)} lines')
        
        # Count disabled
        disabled_count = sum(1 for line in modified_lines if '[DISABLED]' in line)
        print(f'  Disabled lines: {disabled_count}')
        
        # Check Quick Start
        preheat = any('PREHEAT-OFFSET' in line for line in modified_lines)
        pre_extrude = any('PRE-EXTRUDE' in line for line in modified_lines)
        print(f'  PREHEAT-OFFSET: {"OK" if preheat else "MISSING"}')
        print(f'  PRE-EXTRUDE: {"OK" if pre_extrude else "MISSING"}')
        
        # Create output 3MF
        dest_file = OUTPUT_DIR / f'modified_{source_file.name}'
        
        with zipfile.ZipFile(source_file, 'r') as zf_in:
            with zipfile.ZipFile(dest_file, 'w', zipfile.ZIP_DEFLATED) as zf_out:
                for item in zf_in.namelist():
                    if item == selected_plate:
                        # Write modified gcode
                        zf_out.writestr(item, modified_content.encode('utf-8'))
                    else:
                        # Copy other files as-is
                        zf_out.writestr(item, zf_in.read(item))
        
        print(f'  Output: {dest_file.name}')
        print(f'  Size: {dest_file.stat().st_size:,} bytes')
    
    print('\n=== DONE ===')

if __name__ == '__main__':
    process_3mf_files()
