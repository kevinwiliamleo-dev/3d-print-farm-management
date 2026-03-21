"""
G-code and 3MF file parser for extracting print metadata

Reference implementations:
- OctoPrint-BambuPrinter: https://github.com/jneilliii/OctoPrint-BambuPrinter
- FDM-Monster: https://github.com/fdm-monster/fdm-monster
- SlicerCompanion: https://github.com/graelo/SlicerCompanion

3MF file structure (Bambu Studio format):
- Metadata/plate_X.gcode - Sliced G-code for each plate
- Metadata/slice_info.config - Slice configuration
- Metadata/model_settings.config - Model settings
- Metadata/plate_X.png - Plate thumbnails  
- 3D/3dmodel.model - 3D model XML
- Auxiliaries/ - Additional resources

Standard 3MF thumbnail paths (from SlicerCompanion):
- Metadata/thumbnail.png
- Metadata/thumbnail.jpeg
- Thumbnails/thumbnail.png
- Thumbnails/thumbnail.jpeg
- Metadata/plate_*.png (Bambu Studio)

GCode thumbnail format (PrusaSlicer/BambuStudio):
- Embedded as base64 PNG between:
  ; thumbnail begin WxH SIZE
  ; <base64 data>
  ; thumbnail end
"""
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging
import json
import base64

logger = logging.getLogger(__name__)

# Standard 3MF thumbnail paths (in priority order, from SlicerCompanion)
THUMBNAIL_PATHS_3MF = [
    "Metadata/plate_1.png",
    "Metadata/plate_1.jpeg",
    "Metadata/plate_1.jpg",
    "Metadata/thumbnail.png",
    "Metadata/thumbnail.jpeg",
    "Metadata/thumbnail.jpg",
    "Thumbnails/thumbnail.png",
    "Thumbnails/thumbnail.jpeg",
    "Thumbnails/thumbnail.jpg",
]


def parse_gcode_metadata(gcode_content: str) -> Dict[str, Any]:
    """
    Parse G-code file content to extract print metadata.
    
    Supports multiple slicer formats:
    - Bambu Studio / BambuSlicer
    - PrusaSlicer / SuperSlicer
    - Cura
    - OrcaSlicer
    
    Common comment patterns:
    ; estimated printing time (normal mode) = 1h 23m 45s
    ; filament used [mm] = 12345.67
    ; filament used [g] = 45.6
    ; filament_type = PLA
    ; filament_colour = #FFFFFF
    ; nozzle_temperature = 220
    ; bed_temperature = 60
    ; total layer number: 123
    ; PRINT.SIZE: X=100 Y=100 Z=50
    ; TIME: 3600
    """
    metadata = {
        'estimated_time': None,
        'estimated_time_seconds': None,
        'filament_used_mm': None,
        'filament_used_g': None,
        'filament_type': None,
        'filament_color': None,
        'nozzle_temp': None,
        'bed_temp': None,
        'layer_count': None,
        'layer_height': None,
        'first_layer_height': None,
        'model_name': None,
        'printer_model': None,
        'nozzle_diameter': None,
        'print_width': None,
        'print_depth': None,
        'print_height': None,
        'slicer_name': None,
        'slicer_version': None,
        # Automation settings detection from section markers
        # Section markers format: ;===== section_name =====
        # Found in actual G-code files from OrcaSlicer/BambuStudio
        'has_vibration_test': False,  # ;===== mech mode fast check =====
        'has_flow_calibration': False,  # ;===== auto extrude cali =====
        'has_auto_eject': False,
        'has_bed_leveling': False,  # ;===== bed leveling =====
        'has_clean_nozzle': False,  # ;===== wipe nozzle =====
        'has_startup_sound': False,  # ;=====start printer sound =====
        'has_end_sound': False,  # ;=====printer finish sound =====
        'has_timelapse': False,
        # OrcaSlicer Reserved Tags detection
        'has_wipe_tower': False,
        'has_color_change': False,
        'has_pause_print': False,
        'has_layer_change_markers': False,
    }
    
    # Read first 50000 characters for metadata (usually at the beginning)
    header = gcode_content[:50000] if len(gcode_content) > 50000 else gcode_content
    
    # Also check last 10000 chars for PrusaSlicer format (metadata at end)
    footer = gcode_content[-10000:] if len(gcode_content) > 10000 else ""
    combined = header + "\n" + footer
    
    patterns = {
        # Bambu Studio format
        'estimated_time': r';\s*(?:total estimated time|estimated printing time).*?[:=]\s*(.+?)(?:;|$)',
        'model_printing_time': r';\s*model printing time:\s*(.+?)(?:;|$)',
        'filament_used_mm': r';\s*(?:total filament length \[mm\]|filament used \[mm\])\s*[:=]\s*([\d.]+)',
        'filament_used_g': r';\s*(?:total filament weight \[g\]|filament used \[g\]|total filament used \[g\])\s*[:=]\s*([\d.]+)',
        'filament_type': r';\s*filament_type\s*[:=]\s*(\w+)',
        'filament_color': r';\s*filament_colour\s*[:=]\s*(#[A-Fa-f0-9]+)',
        'nozzle_temp': r';\s*(?:nozzle_temperature|first_layer_temperature)\s*[:=]\s*(\d+)',
        'bed_temp': r';\s*(?:bed_temperature|first_layer_bed_temperature)\s*[:=]\s*(\d+)',
        'layer_count': r';\s*(?:total layer number|LAYER_COUNT)[:=]?\s*(\d+)',
        'layer_height': r';\s*layer_height\s*[:=]\s*([\d.]+)',
        'first_layer_height': r';\s*(?:first_layer_height|initial_layer_print_height)\s*[:=]\s*([\d.]+)',
        'printer_model': r';\s*(?:printer_model|machine_name|printer_type)\s*[:=]\s*(.+)',
        'nozzle_diameter': r';\s*nozzle_diameter\s*[:=]\s*([\d.]+)',
        'slicer_name': r';\s*(?:generated by\s+)?(BambuStudio|PrusaSlicer|Cura|OrcaSlicer|SuperSlicer)',
        'slicer_version': r';\s*(?:generated by\s+)?(?:BambuStudio|PrusaSlicer|Cura|OrcaSlicer|SuperSlicer)\s+([\d.]+)',
        'max_z_height': r';\s*max_z_height:\s*([\d.]+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, combined, re.IGNORECASE | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            if key in ['filament_used_mm', 'filament_used_g', 'layer_height', 'first_layer_height', 'nozzle_diameter', 'max_z_height']:
                try:
                    metadata[key] = float(value)
                except ValueError:
                    pass
            elif key in ['nozzle_temp', 'bed_temp', 'layer_count']:
                try:
                    metadata[key] = int(value)
                except ValueError:
                    pass
            else:
                metadata[key] = value
    
    # Parse print dimensions (Bambu format: ; PRINT.SIZE: X=100 Y=100 Z=50)
    size_match = re.search(r';\s*PRINT\.SIZE.*?X=([\d.]+).*?Y=([\d.]+).*?Z=([\d.]+)', combined, re.IGNORECASE)
    if size_match:
        try:
            metadata['print_width'] = float(size_match.group(1))
            metadata['print_depth'] = float(size_match.group(2))
            metadata['print_height'] = float(size_match.group(3))
        except ValueError:
            pass
    
    # Parse estimated time to seconds
    if metadata['estimated_time']:
        time_str = metadata['estimated_time']
        total_seconds = 0
        
        # Handle format: 1h 23m 45s
        hours_match = re.search(r'(\d+)\s*h', time_str)
        mins_match = re.search(r'(\d+)\s*m', time_str)
        secs_match = re.search(r'(\d+)\s*s', time_str)
        
        if hours_match:
            total_seconds += int(hours_match.group(1)) * 3600
        if mins_match:
            total_seconds += int(mins_match.group(1)) * 60
        if secs_match:
            total_seconds += int(secs_match.group(1))
        
        if total_seconds > 0:
            metadata['estimated_time_seconds'] = total_seconds
    
    # Try alternative time format: ; TIME: 3600 (seconds)
    if not metadata['estimated_time_seconds']:
        time_match = re.search(r';\s*TIME:\s*(\d+)', combined)
        if time_match:
            metadata['estimated_time_seconds'] = int(time_match.group(1))
            metadata['estimated_time'] = format_time_seconds(int(time_match.group(1)))
    
    # Detect automation features using OrcaSlicer section markers and Reserved Tags
    # Reference: OrcaSlicer GCodeProcessor.hpp ETags, ha-bambulab commands.py
    # NOTE: bed_leveling, flow_cali, vibration_cali are RUNTIME options sent via JSON
    #       when print starts - they are NOT embedded in the G-code file!
    #
    # Optimization: Section markers and tags are found in header (startup code)
    # and footer (end code). The middle of G-code is just coordinates.
    # Use header (first 100KB) + footer (last 100KB) instead of full content.
    _SCAN_SIZE = 100_000  # 100KB each for header and footer
    if len(gcode_content) > _SCAN_SIZE * 2:
        scan_content = gcode_content[:_SCAN_SIZE] + "\n" + gcode_content[-_SCAN_SIZE:]
    else:
        scan_content = gcode_content
    
    # ==== SECTION MARKERS & G-CODE COMMANDS ====
    # Reference: Actual G-code files from Bambu A1/X1 printers with OrcaSlicer/BambuStudio
    # Section markers format: ;===== section_name ===== (variable = count)
    # Some sections have "start" and "end" variants
    
    # ---- BED LEVELING ----
    # Section: ;===== bed leveling ==================================
    # Command: G29 (Auto Bed Leveling)
    if re.search(r';=+\s*bed\s*leveling\s*=+', scan_content, re.IGNORECASE):
        metadata['has_bed_leveling'] = True
        logger.debug("Detected bed leveling section marker")
    elif re.search(r'\bG29\s+A', scan_content):  # G29 A1 X... is ABL command
        metadata['has_bed_leveling'] = True
        logger.debug("Detected G29 bed leveling command")
    
    # ---- FLOW CALIBRATION (Auto Extrude Cali) ----
    # Section: ;===== auto extrude cali start =========================
    # Section: ;===== extrude cali test ===============================
    # Commands: M983 (dynamic extrusion compensation), M984 (extrusion test)
    if re.search(r';=+\s*(?:auto\s+)?extrude\s*cali', scan_content, re.IGNORECASE):
        metadata['has_flow_calibration'] = True
        logger.debug("Detected flow calibration section marker")
    elif re.search(r'\bM983\b', scan_content):
        metadata['has_flow_calibration'] = True
        logger.debug("Detected M983 flow calibration command")
    elif re.search(r'\bM984\b', scan_content):
        metadata['has_flow_calibration'] = True
        logger.debug("Detected M984 flow calibration command")
    
    # ---- VIBRATION TEST (Mech Mode Fast Check) ----
    # Section: ;===== mech mode fast check start =====================
    # Commands: M970.2, M970.3 (vibration compensation), M974 (resonance test)
    if re.search(r';=+\s*mech\s*mode\s*(?:fast\s*)?check', scan_content, re.IGNORECASE):
        metadata['has_vibration_test'] = True
        logger.debug("Detected vibration test section marker")
    elif re.search(r'\bM970\.[23]\b', scan_content):
        metadata['has_vibration_test'] = True
        logger.debug("Detected M970.x vibration test command")
    elif re.search(r'\bM974\b', scan_content):
        metadata['has_vibration_test'] = True
        logger.debug("Detected M974 resonance test command")
    
    # ---- TIMELAPSE ----
    # Section: ;===== timelapse wipe start ===== 
    # Command: M971 (timelapse photo)
    if re.search(r';=+\s*timelapse', scan_content, re.IGNORECASE):
        metadata['has_timelapse'] = True
        logger.debug("Detected timelapse section marker")
    elif re.search(r'\bM971\b', scan_content):
        metadata['has_timelapse'] = True
        logger.debug("Detected M971 timelapse command")
    
    # ---- STARTUP SOUND ----
    # Section: ;=====start printer sound ===================
    if re.search(r';=+\s*start\s*(?:printer\s*)?sound\s*=+', scan_content, re.IGNORECASE):
        metadata['has_startup_sound'] = True
        logger.debug("Detected start sound section")
    
    # ---- END/FINISH SOUND ----
    # Section: ;=====printer finish  sound=========
    if re.search(r';=+\s*(?:printer\s+)?finish\s+sound\s*=+', scan_content, re.IGNORECASE):
        metadata['has_end_sound'] = True
        logger.debug("Detected finish sound section")
    elif re.search(r';=+\s*end\s*(?:printer\s*)?sound\s*=+', scan_content, re.IGNORECASE):
        metadata['has_end_sound'] = True
        logger.debug("Detected end sound section")
    
    # ---- NOZZLE WIPE/CLEAN ----
    # Section: ;===== wipe nozzle ===============================
    # Section: ;===== brush material wipe nozzle =====
    # Section: ;===== remove waste by touching start =====
    if re.search(r';=+\s*(?:wipe\s*nozzle|brush\s*material|remove\s*waste|clean\s*nozzle)', scan_content, re.IGNORECASE):
        metadata['has_clean_nozzle'] = True
        logger.debug("Detected nozzle wipe/clean section")
    
    # ==== ORCASLICER RESERVED TAGS (;TAG_NAME) ====
    # These are inline tags used by OrcaSlicer's GCodeProcessor
    
    # Wipe Tower detection - ;WIPE_TOWER_START / ;WIPE_TOWER_END
    if re.search(r';\s*WIPE_TOWER_START', scan_content):
        metadata['has_wipe_tower'] = True
        logger.debug("Detected WIPE_TOWER_START tag in gcode")
    
    # Color Change detection - ;COLOR_CHANGE
    if re.search(r';\s*COLOR_CHANGE', scan_content):
        metadata['has_color_change'] = True
        logger.debug("Detected COLOR_CHANGE tag in gcode")
    
    # Pause Print detection - ;PAUSE_PRINT
    if re.search(r';\s*PAUSE_PRINT', scan_content):
        metadata['has_pause_print'] = True
        logger.debug("Detected PAUSE_PRINT tag in gcode")
    
    # Layer Change detection - ;LAYER_CHANGE
    if re.search(r';\s*LAYER_CHANGE', scan_content):
        metadata['has_layer_change_markers'] = True
        logger.debug("Detected LAYER_CHANGE tag in gcode")
    
    # Auto-eject detection - Push print off bed when cooled
    # NOTE: M991 S0 P-1 is for END TIMELAPSE, not auto-eject!
    # Auto-eject requires specific section marker or G-code sequence
    # Section: ;===== auto eject ===== or ;===== push off =====
    if re.search(r';=+\s*(?:auto\s*eject|push\s*off|eject\s*print)\s*=+', scan_content, re.IGNORECASE):
        metadata['has_auto_eject'] = True
        logger.debug("Detected auto-eject section in gcode")
    
    return metadata


def parse_3mf_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Parse 3MF file to extract print metadata.
    
    3MF is a ZIP archive containing (Bambu Studio format):
    - Metadata/plate_*.gcode - Sliced G-code for each build plate
    - Metadata/slice_info.config - Slice configuration JSON
    - Metadata/model_settings.config - Model settings JSON  
    - Metadata/plate_*.png - Plate preview thumbnails
    - 3D/3dmodel.model - 3D model in XML format
    - Auxiliaries/plate_*.png - Additional plate images
    - [Content_Types].xml - MIME type definitions
    
    The gcode files contain full print metadata in comments.
    Bambu print command uses: param="Metadata/plate_1.gcode"
    """
    metadata = {
        'estimated_time': None,
        'estimated_time_seconds': None,
        'filament_used_mm': None,
        'filament_used_g': None,
        'filament_type': None,
        'filament_color': None,
        'nozzle_temp': None,
        'bed_temp': None,
        'layer_count': None,
        'layer_height': None,
        'model_name': file_path.stem,
        'printer_model': None,
        'file_type': '3mf',
        'plates': [],
        'thumbnail': None,
        'gcode_path': None,  # Path to gcode inside 3MF for print command
        'slicer_name': None,
        'slicer_version': None,
        'print_width': None,
        'print_depth': None, 
        'print_height': None,
        # Automation settings detection from section markers in G-Code
        # Section markers format: ;===== section_name ===== 
        'has_vibration_test': False,  # ;===== mech mode fast check ===== or M970.x
        'has_flow_calibration': False,  # ;===== auto extrude cali ===== or M983/M984
        'has_auto_eject': False,  # M991 S0 P-1
        'has_bed_leveling': False,  # ;===== bed leveling ===== or G29 A
        'has_clean_nozzle': False,  # ;===== wipe nozzle =====
        'has_startup_sound': False,  # ;=====start printer sound =====
        'has_end_sound': False,  # ;=====printer finish sound =====
        'has_timelapse': False,  # M971
        # OrcaSlicer Reserved Tags detection
        'has_wipe_tower': False,
        'has_color_change': False,
        'has_pause_print': False,
        'has_layer_change_markers': False,
    }
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            file_list = zf.namelist()
            
            logger.debug(f"3MF contents: {file_list}")
            
            # Find gcode files inside 3MF (Bambu Studio format: Metadata/plate_*.gcode)
            gcode_files = sorted([f for f in file_list if f.lower().endswith('.gcode')])
            file_list_lower = {f.lower(): f for f in file_list}
            
            # Find thumbnail using standard paths first (from SlicerCompanion reference)
            for standard_path in THUMBNAIL_PATHS_3MF:
                standard_lower = standard_path.lower()
                if standard_lower in file_list_lower:
                    metadata['thumbnail'] = file_list_lower[standard_lower]
                    break
            
            # Fallback: search for any thumbnail-like images
            if not metadata['thumbnail']:
                thumbnail_files = [f for f in file_list 
                                 if ('.png' in f.lower() or '.jpg' in f.lower()) 
                                 and ('thumbnail' in f.lower() or 'plate' in f.lower())]
                
                if thumbnail_files:
                    # Prefer plate_1 thumbnail
                    for tf in thumbnail_files:
                        if 'plate_1' in tf.lower() or 'plate1' in tf.lower():
                            metadata['thumbnail'] = tf
                            break
                    if not metadata['thumbnail']:
                        metadata['thumbnail'] = thumbnail_files[0]
            
            # Parse each gcode file for metadata
            for gcode_file in gcode_files:
                try:
                    with zf.open(gcode_file) as gf:
                        # Optimization: Read only header + footer for metadata/automation detection.
                        # Section markers are in startup/end code, not in the coordinate body.
                        raw_bytes = gf.read()
                        _PARTIAL_SIZE = 100_000  # 100KB
                        if len(raw_bytes) > _PARTIAL_SIZE * 2:
                            partial = raw_bytes[:_PARTIAL_SIZE] + b"\n" + raw_bytes[-_PARTIAL_SIZE:]
                            gcode_content = partial.decode('utf-8', errors='ignore')
                        else:
                            gcode_content = raw_bytes.decode('utf-8', errors='ignore')
                        gcode_metadata = parse_gcode_metadata(gcode_content)
                        
                        # Store the first (main) gcode path for print command
                        if not metadata['gcode_path']:
                            metadata['gcode_path'] = gcode_file
                        
                        # Merge metadata (prefer non-None values, OR for booleans)
                        for key, value in gcode_metadata.items():
                            if key.startswith('has_'):
                                # For boolean flags, use OR logic (True if any plate has it)
                                if value:
                                    metadata[key] = True
                            elif value is not None and metadata.get(key) is None:
                                metadata[key] = value
                        
                        # Add to plates list
                        plate_name = Path(gcode_file).stem
                        plate_info = {
                            'name': plate_name,
                            'file': gcode_file,
                            'estimated_time': gcode_metadata.get('estimated_time'),
                            'estimated_time_seconds': gcode_metadata.get('estimated_time_seconds'),
                            'filament_used_g': gcode_metadata.get('filament_used_g'),
                            'layer_count': gcode_metadata.get('layer_count'),
                        }
                        metadata['plates'].append(plate_info)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse gcode in 3MF: {gcode_file}, error: {e}")
            
            # Try to read slice_info.config (Bambu Studio format - JSON)
            slice_info_files = [f for f in file_list if 'slice_info' in f.lower()]
            for slice_file in slice_info_files:
                try:
                    with zf.open(slice_file) as sf:
                        content = sf.read().decode('utf-8', errors='ignore')
                        # May be JSON or config format
                        if content.strip().startswith('{'):
                            config = json.loads(content)
                            # Extract useful info
                            if 'layer_height' in config and metadata['layer_height'] is None:
                                metadata['layer_height'] = float(config['layer_height'])
                            if 'printer_model' in config and metadata['printer_model'] is None:
                                metadata['printer_model'] = config['printer_model']
                except Exception as e:
                    logger.debug(f"Could not parse {slice_file}: {e}")
            
            # Try to read model_settings.config
            model_settings_files = [f for f in file_list if 'model_settings' in f.lower()]
            for settings_file in model_settings_files:
                try:
                    with zf.open(settings_file) as sf:
                        content = sf.read().decode('utf-8', errors='ignore')
                        if content.strip().startswith('{'):
                            config = json.loads(content)
                            # Extract model info if available
                            logger.debug(f"Model settings: {list(config.keys())[:10]}")
                except Exception as e:
                    logger.debug(f"Could not parse {settings_file}: {e}")
            
            # Try project_settings.config for printer model
            project_files = [f for f in file_list if 'project_settings' in f.lower()]
            for pf in project_files:
                try:
                    with zf.open(pf) as psf:
                        content = psf.read().decode('utf-8', errors='ignore')
                        if content.strip().startswith('{'):
                            config = json.loads(content)
                            if 'printer_model' in config and metadata['printer_model'] is None:
                                metadata['printer_model'] = config['printer_model']
                except:
                    pass
            
            # If no gcode found, try to read 3D model info
            if not gcode_files:
                logger.warning(f"No gcode files found in 3MF: {file_path.name}")
                # Try to get model dimensions from 3dmodel.model
                model_files = [f for f in file_list if '3dmodel.model' in f.lower()]
                for mf in model_files:
                    try:
                        with zf.open(mf) as model_file:
                            content = model_file.read().decode('utf-8', errors='ignore')
                            # Parse XML if needed
                            logger.debug(f"Found 3D model file: {mf}")
                    except:
                        pass
                        
    except zipfile.BadZipFile:
        logger.error(f"Invalid 3MF file (not a valid ZIP): {file_path}")
        return {
            'error': 'Invalid 3MF file - not a valid ZIP archive',
            'file_type': '3mf',
            'model_name': file_path.stem,
        }
    except Exception as e:
        logger.error(f"Error parsing 3MF file: {e}")
        return {
            'error': f'Error parsing 3MF: {str(e)}',
            'file_type': '3mf',
            'model_name': file_path.stem,
        }
    
    return metadata


def parse_file_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Parse any supported file type and return metadata.
    
    Supports: .3mf, .gcode
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return {'error': 'File not found', 'filename': file_path.name}
    
    suffix = file_path.suffix.lower()
    
    try:
        if suffix == '.3mf':
            metadata = parse_3mf_metadata(file_path)
        elif suffix in ['.gcode', '.g']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            metadata = parse_gcode_metadata(content)
            metadata['file_type'] = 'gcode'
        else:
            metadata = {
                'file_type': suffix,
                'model_name': file_path.stem,
            }
        
        # Add file info
        metadata['filename'] = file_path.name
        metadata['file_size_mb'] = round(file_path.stat().st_size / (1024 * 1024), 2)
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error parsing file {file_path}: {e}")
        return {
            'error': f'Parse error: {str(e)}',
            'filename': file_path.name,
            'file_type': suffix,
        }


def extract_3mf_thumbnail(file_path: Path, output_path: Optional[Path] = None) -> Optional[bytes]:
    """
    Extract thumbnail image from a 3MF file.
    
    Uses standard 3MF thumbnail paths (from SlicerCompanion reference):
    - Metadata/plate_1.png (Bambu Studio)
    - Metadata/thumbnail.png (standard 3MF)
    - Thumbnails/thumbnail.png (alternative)
    
    Args:
        file_path: Path to the 3MF file
        output_path: Optional path to save the thumbnail
        
    Returns:
        Thumbnail image bytes or None if not found
    """
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            file_list = zf.namelist()
            file_list_lower = {f.lower(): f for f in file_list}
            
            # First try standard paths in order
            for standard_path in THUMBNAIL_PATHS_3MF:
                standard_lower = standard_path.lower()
                if standard_lower in file_list_lower:
                    actual_path = file_list_lower[standard_lower]
                    with zf.open(actual_path) as tf:
                        thumbnail_data = tf.read()
                    
                    logger.debug(f"Found thumbnail at standard path: {actual_path}")
                    
                    if output_path:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, 'wb') as out:
                            out.write(thumbnail_data)
                    
                    return thumbnail_data
            
            # Fallback: Look for any image files with priority scoring
            thumbnail_candidates = []
            
            for f in file_list:
                f_lower = f.lower()
                if f_lower.endswith(('.png', '.jpg', '.jpeg')):
                    # Score by location and name (lower is better)
                    score = 10
                    if 'metadata' in f_lower:
                        score = 1
                    elif 'thumbnails' in f_lower:
                        score = 2
                    elif 'auxiliaries' in f_lower:
                        score = 3
                    
                    # Prefer plate_1 or thumbnail
                    if 'plate_1' in f_lower or 'plate1' in f_lower:
                        score -= 0.5
                    elif 'thumbnail' in f_lower:
                        score -= 0.3
                        
                    thumbnail_candidates.append((score, f))
            
            if not thumbnail_candidates:
                logger.debug(f"No thumbnail found in 3MF: {file_path.name}")
                return None
            
            # Sort by priority and pick the best
            thumbnail_candidates.sort(key=lambda x: x[0])
            thumbnail_file = thumbnail_candidates[0][1]
            
            # Read the thumbnail
            with zf.open(thumbnail_file) as tf:
                thumbnail_data = tf.read()
            
            # Save if output path provided
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as out:
                    out.write(thumbnail_data)
                logger.debug(f"Thumbnail saved to: {output_path}")
            
            return thumbnail_data
            
    except zipfile.BadZipFile:
        logger.error(f"Invalid 3MF file: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error extracting thumbnail: {e}")
        return None


def get_3mf_structure(file_path: Path) -> Dict[str, Any]:
    """
    Get the full structure of a 3MF file for debugging.
    
    Returns:
        Dictionary with file lists and sizes
    """
    structure = {
        'gcode_files': [],
        'config_files': [],
        'model_files': [],
        'image_files': [],
        'other_files': [],
        'total_size': 0,
    }
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            for info in zf.infolist():
                name = info.filename
                size = info.file_size
                structure['total_size'] += size
                
                file_info = {'name': name, 'size': size}
                
                if name.lower().endswith('.gcode'):
                    structure['gcode_files'].append(file_info)
                elif name.lower().endswith(('.json', '.config', '.xml')):
                    structure['config_files'].append(file_info)
                elif name.lower().endswith('.model'):
                    structure['model_files'].append(file_info)
                elif name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    structure['image_files'].append(file_info)
                else:
                    structure['other_files'].append(file_info)
                    
    except Exception as e:
        structure['error'] = str(e)
    
    return structure


def extract_gcode_thumbnail(gcode_content: str) -> Optional[Tuple[bytes, int, int]]:
    """
    Extract embedded thumbnail from GCode file content.
    
    GCode files (PrusaSlicer, BambuStudio, etc.) can have embedded thumbnails
    as base64-encoded PNG images in comment blocks:
    
    ; thumbnail begin 300x300 12345
    ; iVBORw0KGgoAAAANSU...
    ; thumbnail end
    
    Args:
        gcode_content: The full GCode file content
        
    Returns:
        Tuple of (image_bytes, width, height) or None if no thumbnail found
    """
    # Pattern to match thumbnail begin block
    # Format: ; thumbnail begin WIDTHxHEIGHT SIZE
    begin_pattern = r';\s*thumbnail\s+begin\s+(\d+)x(\d+)\s+(\d+)'
    end_pattern = r';\s*thumbnail\s+end'
    
    thumbnails = []
    
    lines = gcode_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for thumbnail begin
        match = re.search(begin_pattern, line, re.IGNORECASE)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            # declared_size = int(match.group(3))
            
            # Collect base64 lines until thumbnail end
            base64_lines = []
            i += 1
            
            while i < len(lines):
                curr_line = lines[i]
                
                # Check for thumbnail end
                if re.search(end_pattern, curr_line, re.IGNORECASE):
                    break
                
                # Extract base64 data (remove leading "; " or ";")
                if curr_line.startswith('; '):
                    base64_lines.append(curr_line[2:])
                elif curr_line.startswith(';'):
                    base64_lines.append(curr_line[1:])
                
                i += 1
            
            # Decode base64
            if base64_lines:
                try:
                    base64_string = ''.join(base64_lines)
                    image_data = base64.b64decode(base64_string)
                    thumbnails.append((image_data, width, height))
                except Exception as e:
                    logger.debug(f"Failed to decode thumbnail base64: {e}")
        
        i += 1
    
    if not thumbnails:
        return None
    
    # Return the largest thumbnail
    largest = max(thumbnails, key=lambda t: t[1] * t[2])
    return largest


def extract_gcode_thumbnail_from_file(file_path: Path) -> Optional[bytes]:
    """
    Extract embedded thumbnail from a GCode file.
    
    Args:
        file_path: Path to the GCode file
        
    Returns:
        Thumbnail image bytes or None if not found
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        result = extract_gcode_thumbnail(content)
        if result:
            return result[0]  # Return just the image bytes
        return None
    except Exception as e:
        logger.error(f"Error extracting GCode thumbnail: {e}")
        return None


def format_time_seconds(seconds: int) -> str:
    """Format seconds to human readable time string."""
    if seconds is None:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def extract_gcode_from_3mf(file_path: Path, plate_num: int = 1, max_lines: int = 5000) -> Dict[str, Any]:
    """
    Extract G-code content from a 3MF file.
    
    Args:
        file_path: Path to the 3MF file
        plate_num: Build plate number to extract (default: 1)
        max_lines: Maximum number of lines to return (default: 5000)
        
    Returns:
        Dict with:
        - gcode: List of gcode lines (trimmed to max_lines)
        - total_lines: Total number of lines in the file
        - plates: List of available plate gcode files
        - selected_plate: The plate file that was extracted
    """
    result = {
        'gcode': [],
        'total_lines': 0,
        'plates': [],
        'selected_plate': None,
        'error': None
    }
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            file_list = zf.namelist()
            
            # Find all gcode files (plate_1.gcode, plate_2.gcode, etc.)
            gcode_files = sorted([
                f for f in file_list 
                if f.lower().endswith('.gcode') and 'plate' in f.lower()
            ])
            
            result['plates'] = gcode_files
            
            if not gcode_files:
                result['error'] = 'No G-code files found in 3MF'
                return result
            
            # Try to find requested plate
            target_file = None
            for gf in gcode_files:
                if f'plate_{plate_num}' in gf.lower():
                    target_file = gf
                    break
            
            # Fallback to first plate
            if not target_file:
                target_file = gcode_files[0]
            
            result['selected_plate'] = target_file
            
            # Extract gcode content
            with zf.open(target_file) as gcode_file:
                content = gcode_file.read().decode('utf-8', errors='ignore')
                lines = content.splitlines()
                result['total_lines'] = len(lines)
                
                # Return trimmed content
                result['gcode'] = lines[:max_lines]
                
    except zipfile.BadZipFile:
        result['error'] = 'Invalid 3MF file - not a valid ZIP archive'
    except Exception as e:
        result['error'] = f'Error extracting G-code: {str(e)}'
        logger.error(f"Error extracting gcode from 3MF: {e}")
    
    return result


def parse_gcode_sections(lines: List[str]) -> Dict[str, Any]:
    """
    Parse G-code lines into structured sections with enable/disable support.
    
    Bambu Studio G-code format:
    - BLOCK markers: ; HEADER_BLOCK_START/END, ; CONFIG_BLOCK_START/END, ; EXECUTABLE_BLOCK_START
    - Section markers: ;===== section_name =====  or  ;===== section_name end =====
    - Feature markers: ; FEATURE: Inner wall, Outer wall, etc.
    - Layer markers: ; LAYER_HEIGHT, ; layer num/total_layer_count
    
    Returns:
        Dict with:
        - sections: List of main sections (Start G-Code, Print Body, End G-Code)
        - Each section has subSections with id, name, enabled, canDisable, lines
    """
    
    # Define which sections can be disabled (non-critical for print)
    DISABLEABLE_SECTIONS = {
        # Calibration related
        'bed leveling', 'auto bed leveling', 'bed_leveling',
        'vibration calibration', 'vibration_cali', 'input shaping',
        'flow calibration', 'flow_cali', 'auto extrude cali', 'extrude cali',
        'mech mode fast check', 'mech mode', 'mechanical scan',
        # Sound related
        'sound', 'printer sound', 'start printer sound', 'printer finish sound',
        # Inspection/scan related
        'first layer inspection', 'layer_inspect', 'lidar scan', 'lidar',
        # Timelapse
        'timelapse', 'mc_timelapse',
        # Noise reduction
        'cog noise reduction',
    }
    
    def get_section_icon(name: str) -> str:
        """Get icon based on section name."""
        lower = name.lower()
        if 'header' in lower: return '📄'
        if 'config' in lower: return '⚙️'
        if 'executable' in lower: return '▶️'
        if 'heat' in lower or 'temperature' in lower: return '🔥'
        if 'sound' in lower: return '🔊'
        if 'home' in lower: return '🏠'
        if 'level' in lower: return '📐'
        if 'wipe' in lower or 'clean' in lower or 'brush' in lower or 'waste' in lower: return '🧹'
        if 'calibr' in lower or 'cali' in lower or 'extrude cali' in lower: return '💧'
        if 'ams' in lower or 'material' in lower or 'filament' in lower: return '🗃️'
        if 'vibr' in lower or 'mech' in lower: return '📳'
        if 'nozzle' in lower: return '🔩'
        if 'plate' in lower or 'bed' in lower: return '🛏️'
        if 'machine' in lower or 'reset' in lower: return '🔧'
        if 'end stop' in lower or 'avoid' in lower: return '🚧'
        if 'cog' in lower or 'noise' in lower: return '🔇'
        if 'light' in lower: return '💡'
        if 'end' in lower or 'cool' in lower or 'off' in lower or 'finish' in lower: return '🏁'
        if 'prime' in lower or 'purge' in lower or 'load' in lower: return '📏'
        if 'sequence' in lower or 'start' in lower: return '▶️'
        if 'lidar' in lower or 'scan' in lower: return '📡'
        if 'timelapse' in lower: return '📹'
        if 'date' in lower: return '📅'
        return '📋'
    
    def can_disable_section(name: str) -> bool:
        """Check if a section can be safely disabled."""
        lower = name.lower().replace('_', ' ')
        # Skip "end" sections - they are just markers, not standalone
        if lower.endswith(' end'):
            return False
        for pattern in DISABLEABLE_SECTIONS:
            if pattern in lower:
                return True
        return False
    
    def is_section_end_marker(name: str) -> bool:
        """Check if this is an end marker for a section."""
        lower = name.lower().strip()
        return lower.endswith(' end') or lower.endswith('_end')
    
    def is_valid_section_marker(raw_name: str) -> bool:
        """Check if a marker is a valid section (not a long comment or description)."""
        # Skip date-only markers
        if re.match(r'^date:\s*\d+$', raw_name, re.IGNORECASE):
            return False
        # Skip machine markers
        if re.match(r'^machine:\s*\w+', raw_name, re.IGNORECASE):
            return False
        # Skip long descriptions (more than 40 chars or contains comma)
        if len(raw_name) > 40 or ',' in raw_name:
            return False
        # Skip markers that are clearly just comments/notes
        if raw_name.lower().startswith('for ') or raw_name.lower().startswith('note:'):
            return False
        return True
    
    def normalize_section_name(name: str) -> str:
        """Normalize section name for comparison (to detect duplicates)."""
        return re.sub(r'[^a-z0-9]', '', name.lower())
    
    def extract_sub_sections(start_idx: int, end_idx: int) -> List[Dict[str, Any]]:
        """Extract sub-sections from a range of lines using Bambu markers."""
        subs = []
        current_sub = None
        section_id = 0
        pending_lines_before_first = []
        seen_section_names = {}  # Track normalized names to merge duplicates
        
        for i in range(start_idx, min(end_idx + 1, len(lines))):
            line = lines[i]
            trimmed = line.strip()
            
            # Check for BLOCK markers (HEADER_BLOCK_START, CONFIG_BLOCK_START, etc.)
            block_match = re.match(r'^;\s*(HEADER_BLOCK_START|HEADER_BLOCK_END|CONFIG_BLOCK_START|CONFIG_BLOCK_END|EXECUTABLE_BLOCK_START)$', trimmed, re.IGNORECASE)
            
            # Check for Bambu section markers: ;===== section name =====
            bambu_match = re.match(r'^;=+ ?(.+?)=*\s*$', trimmed)
            
            section_name = None
            is_new_section = False
            
            if block_match:
                section_name = block_match.group(1).replace('_', ' ').title()
                is_new_section = True
            elif bambu_match:
                raw_name = bambu_match.group(1).strip()
                # Validate this is a real section marker
                if not is_valid_section_marker(raw_name):
                    if current_sub:
                        current_sub['lines'].append(line)
                    continue
                section_name = raw_name.replace('=', '').replace('_', ' ').strip()
                section_name = ' '.join(w.capitalize() for w in section_name.split())
                is_new_section = True
            
            if is_new_section and section_name:
                # Check if this is an "end" marker - merge with previous section
                if is_section_end_marker(section_name):
                    if current_sub:
                        current_sub['lines'].append(line)
                        current_sub['endLine'] = i
                        # Add to list and reset
                        subs.append(current_sub)
                        current_sub = None
                    continue
                
                # Check for duplicate section name (e.g., two "Start Printer Sound" in a row)
                normalized_name = normalize_section_name(section_name)
                
                # If same section appears again right after, merge into current
                if current_sub and normalize_section_name(current_sub['name']) == normalized_name:
                    current_sub['lines'].append(line)
                    continue
                
                # Save previous sub-section
                if current_sub and current_sub['lines']:
                    current_sub['endLine'] = i - 1
                    subs.append(current_sub)
                
                # If we have pending lines before first section, create intro section
                if pending_lines_before_first and not subs:
                    section_id += 1
                    subs.append({
                        'id': f"sub_{start_idx}_{section_id}",
                        'name': 'G-Code Info',
                        'icon': '📄',
                        'startLine': start_idx,
                        'endLine': i - 1,
                        'enabled': True,
                        'canDisable': False,
                        'lines': pending_lines_before_first,
                    })
                    pending_lines_before_first = []
                
                section_id += 1
                current_sub = {
                    'id': f"sub_{start_idx}_{section_id}",
                    'name': section_name,
                    'icon': get_section_icon(section_name),
                    'startLine': i,
                    'endLine': i,
                    'enabled': True,
                    'canDisable': can_disable_section(section_name),
                    'lines': [line],
                }
                seen_section_names[normalized_name] = len(subs)
            elif current_sub:
                current_sub['lines'].append(line)
            else:
                # Lines before first marker
                pending_lines_before_first.append(line)
        
        # Handle remaining pending lines if no sections found
        if pending_lines_before_first and not subs and not current_sub:
            section_id += 1
            subs.append({
                'id': f"sub_{start_idx}_{section_id}",
                'name': 'G-Code Commands',
                'icon': '📋',
                'startLine': start_idx,
                'endLine': end_idx,
                'enabled': True,
                'canDisable': False,
                'lines': pending_lines_before_first,
            })
        
        # Save last sub-section
        if current_sub and current_sub['lines']:
            current_sub['endLine'] = end_idx
            subs.append(current_sub)
        
        return subs
    
    # Find key markers
    print_body_start = -1
    end_gcode_start = -1
    
    for idx, line in enumerate(lines):
        trimmed = line.strip()
        # First layer marker indicates start of print body
        if print_body_start == -1:
            if trimmed == ';LAYER_CHANGE' or re.match(r'^; LAYER_HEIGHT:', trimmed):
                print_body_start = idx
        # End gcode marker
        if (re.match(r'^;=+ ?(end_?gcode|machine_?end|end g-?code)', trimmed, re.IGNORECASE) or
            re.match(r'^; end_?gcode', trimmed, re.IGNORECASE)) and end_gcode_start == -1:
            end_gcode_start = idx
    
    # Fallback: find end by heater off
    if end_gcode_start == -1 and print_body_start != -1:
        last_layer_line = print_body_start
        for idx, line in enumerate(lines):
            if re.match(r'^;LAYER:|^;LAYER_CHANGE', line.strip()):
                last_layer_line = idx
        for i in range(last_layer_line, len(lines)):
            if re.match(r'^M140\s+S0|^;=+ ?turn off|^; end', lines[i].strip(), re.IGNORECASE):
                end_gcode_start = i
                break
    
    # Default fallback
    if print_body_start == -1:
        print_body_start = int(len(lines) * 0.1)
    if end_gcode_start == -1:
        end_gcode_start = len(lines) - 50
    
    # Build sections
    main_sections = []
    
    # 1. START G-CODE
    start_subs = extract_sub_sections(0, print_body_start - 1)
    main_sections.append({
        'id': 1,
        'title': 'Start G-Code',
        'icon': '▶️',
        'phase': 'preparation',
        'startLine': 0,
        'endLine': print_body_start - 1,
        'subSections': start_subs,
        'enabled': True,
        'canDisable': False,
    })
    
    # 2. PRINT BODY
    print_lines = lines[print_body_start:end_gcode_start]
    # Count layers using various layer marker formats
    layer_count = sum(1 for line in print_lines if re.match(r'^;\s*(LAYER_CHANGE|CHANGE_LAYER|LAYER_HEIGHT)', line.strip()))
    main_sections.append({
        'id': 2,
        'title': 'Print Body',
        'icon': '🖨️',
        'phase': 'printing',
        'startLine': print_body_start,
        'endLine': end_gcode_start - 1,
        'subSections': [],  # Print body has no sub-sections, just layers
        'layerCount': layer_count,
        'lineCount': len(print_lines),
        'enabled': True,
        'canDisable': False,
    })
    
    # 3. END G-CODE
    end_subs = extract_sub_sections(end_gcode_start, len(lines) - 1)
    main_sections.append({
        'id': 3,
        'title': 'End G-Code',
        'icon': '🏁',
        'phase': 'completion',
        'startLine': end_gcode_start,
        'endLine': len(lines) - 1,
        'subSections': end_subs,
        'enabled': True,
        'canDisable': False,
    })
    
    return {
        'sections': main_sections,
        'totalLines': len(lines),
        'printBodyStart': print_body_start,
        'endGcodeStart': end_gcode_start,
    }


def apply_section_modifications(lines: List[str], modifications: List[Dict]) -> List[str]:
    """
    Apply enable/disable modifications to G-code lines.
    Disabled sections are commented out with ;[DISABLED] prefix.
    
    Args:
        lines: Original G-code lines
        modifications: List of {sectionId, enabled, startLine, endLine}
    
    Returns:
        Modified lines with disabled sections commented out
    """
    modified_lines = lines.copy()
    
    for mod in modifications:
        if not mod.get('enabled', True):
            start = mod.get('startLine', 0)
            end = mod.get('endLine', start)
            
            for i in range(start, min(end + 1, len(modified_lines))):
                line = modified_lines[i]
                # Skip if already a comment or empty
                if line.strip().startswith(';') or not line.strip():
                    continue
                # Add disabled prefix
                modified_lines[i] = f';[DISABLED] {line}'
    
    return modified_lines


def restore_disabled_section(lines: List[str], start_line: int, end_line: int) -> List[str]:
    """
    Restore a disabled section by removing ;[DISABLED] prefix.
    
    Args:
        lines: G-code lines
        start_line: Start line of section
        end_line: End line of section
    
    Returns:
        Lines with section restored
    """
    modified_lines = lines.copy()
    
    for i in range(start_line, min(end_line + 1, len(modified_lines))):
        line = modified_lines[i]
        if line.startswith(';[DISABLED] '):
            modified_lines[i] = line[12:]  # Remove prefix
    
    return modified_lines
