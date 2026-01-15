# 3MF Parser Documentation

## Overview

Parser for extracting metadata from 3MF files (Bambu Lab format) based on learnings from:
- [OctoPrint-BambuPrinter](https://github.com/jneilliii/OctoPrint-BambuPrinter)
- [FDM-Monster](https://github.com/fdm-monster/fdm-monster)
- [SlicerCompanion](https://github.com/graelo/SlicerCompanion) - Pure Swift 3MF/GCode thumbnail extractor

## 3MF File Structure (Bambu Studio)

A 3MF file is a ZIP archive containing:

```
├── [Content_Types].xml          # MIME type definitions
├── Metadata/
│   ├── plate_1.gcode            # Sliced G-code (main file for printing)
│   ├── plate_1.json             # Plate configuration
│   ├── plate_1.png              # Plate thumbnail
│   ├── plate_1_small.png        # Small thumbnail
│   ├── plate_no_light_1.png     # Thumbnail without lighting
│   ├── project_settings.config  # Project configuration
│   ├── model_settings.config    # Model settings
│   ├── filament_settings_*.config # Filament settings
│   └── slice_info.config        # Slice information
├── 3D/
│   └── 3dmodel.model            # 3D model in XML format
└── Auxiliaries/
    └── .thumbnails/             # Additional thumbnails
```

## Standard Thumbnail Paths (SlicerCompanion Reference)

The parser searches for thumbnails in this order:
1. `Metadata/plate_1.png` (Bambu Studio)
2. `Metadata/plate_1.jpeg`
3. `Metadata/thumbnail.png` (Standard 3MF)
4. `Metadata/thumbnail.jpeg`
5. `Thumbnails/thumbnail.png` (Alternative)
6. `Thumbnails/thumbnail.jpeg`

## GCode Embedded Thumbnails

GCode files (PrusaSlicer, BambuStudio) can contain embedded thumbnails as base64-encoded PNG:

```gcode
; thumbnail begin 300x300 12345
; iVBORw0KGgoAAAANSUhEUgAA...
; ... (base64 PNG data) ...
; thumbnail end
```

Enable thumbnails in PrusaSlicer: **Printer Settings > General > G-code thumbnails**

## Extracted Metadata

The parser extracts the following metadata from 3MF files:

| Field | Description | Example |
|-------|-------------|---------|
| `model_name` | Model name from filename | `BoxGrip.gcode` |
| `file_type` | File type | `3mf` |
| `file_size_mb` | File size in MB | `1.59` |
| `estimated_time` | Total print time | `21m 51s` |
| `estimated_time_seconds` | Print time in seconds | `1311` |
| `model_printing_time` | Model-only print time | `14m 41s` |
| `filament_used_g` | Filament weight in grams | `4.15` |
| `filament_used_mm` | Filament length in mm | `1426.75` |
| `filament_type` | Filament material | `PLA`, `PETG` |
| `filament_color` | Filament color hex | `#FFFFFF` |
| `layer_count` | Total layers | `70` |
| `layer_height` | Layer height in mm | `0.2` |
| `max_z_height` | Max print height | `14.0` |
| `nozzle_temp` | Nozzle temperature | `220` |
| `bed_temp` | Bed temperature | `60` |
| `nozzle_diameter` | Nozzle size | `0.4` |
| `printer_model` | Printer model | `Bambu Lab A1` |
| `slicer_name` | Slicer software | `BambuStudio` |
| `slicer_version` | Slicer version | `02.04.00.70` |
| `gcode_path` | G-code path inside 3MF | `Metadata/plate_1.gcode` |
| `thumbnail` | Thumbnail path inside 3MF | `Metadata/plate_1.png` |
| `plates` | List of plate info | Array of plate objects |

## G-code Header Format (Bambu Studio)

```gcode
; HEADER_BLOCK_START
; BambuStudio 02.04.00.70
; model printing time: 14m 41s; total estimated time: 21m 51s
; total layer number: 70
; total filament length [mm] : 1426.75
; total filament volume [cm^3] : 3431.74
; total filament weight [g] : 4.15
; filament_density: 1.21
; filament_diameter: 1.75
; max_z_height: 14.00
; HEADER_BLOCK_END
```

## API Endpoints

### GET /api/jobs/{job_id}/metadata
Get metadata from uploaded 3MF file.

```json
{
  "job_id": 1,
  "job_name": "BoxGrip.gcode.3mf",
  "estimated_time": "21m 51s",
  "estimated_time_seconds": 1311,
  "filament_used_g": 4.15,
  "filament_type": "PLA",
  "layer_count": 70,
  "printer_model": "Bambu Lab A1"
}
```

### GET /api/jobs/{job_id}/thumbnail
Get thumbnail image from 3MF or GCode file.

**Supports:**
- **3MF**: Extracts embedded PNG/JPEG from Metadata/plate_1.png or Metadata/thumbnail.png
- **GCode**: Extracts base64-encoded PNG from `; thumbnail begin/end` blocks

Returns: `image/png` or `image/jpeg` with model preview

### GET /api/jobs/{job_id}/structure
Get internal file structure of 3MF (for debugging).

```json
{
  "job_id": 1,
  "job_name": "BoxGrip.gcode.3mf",
  "gcode_files": [{"name": "Metadata/plate_1.gcode", "size": 1913632}],
  "config_files": [{"name": "[Content_Types].xml", "size": 512}],
  "image_files": [{"name": "Metadata/plate_1.png", "size": 2935}],
  "total_size": 1666048
}
```

## Usage in Code

```python
from src.utils.gcode_parser import (
    parse_file_metadata,
    extract_3mf_thumbnail,
    extract_gcode_thumbnail_from_file,
    get_3mf_structure,
    THUMBNAIL_PATHS_3MF
)

# Parse metadata
metadata = parse_file_metadata(Path("model.3mf"))
print(f"Print time: {metadata['estimated_time']}")
print(f"Filament: {metadata['filament_used_g']}g")

# Extract thumbnail from 3MF
thumbnail_bytes = extract_3mf_thumbnail(Path("model.3mf"))
with open("preview.png", "wb") as f:
    f.write(thumbnail_bytes)

# Extract thumbnail from GCode
gcode_thumb = extract_gcode_thumbnail_from_file(Path("model.gcode"))
if gcode_thumb:
    with open("preview_gcode.png", "wb") as f:
        f.write(gcode_thumb)

# Debug structure
structure = get_3mf_structure(Path("model.3mf"))
print(f"G-code files: {structure['gcode_files']}")
```

## Print Command for Bambu Printers

When starting a print with Bambu printer:

```python
# The gcode_path from metadata is used for print command
print_command = {
    "print": {
        "command": "project_file",
        "param": "Metadata/plate_1.gcode",  # From gcode_path
        "url": "file:///sdcard/model.3mf",
        "subtask_name": "model.3mf"
    }
}
```

## Important Notes

1. **Sliced vs Unsliced 3MF**: Only sliced 3MF files contain G-code and print metadata. Unsliced files only have 3D model data.

2. **Plate Support**: Multi-plate prints have multiple G-code files (`plate_1.gcode`, `plate_2.gcode`, etc.)

3. **Thumbnail Priority (from SlicerCompanion)**: 
   - `Metadata/plate_1.png` (Bambu Studio)
   - `Metadata/thumbnail.png` (Standard 3MF)
   - `Thumbnails/thumbnail.png` (Alternative)
   - Any other PNG/JPEG

4. **File Validation**: Parser handles invalid/corrupted ZIP files gracefully

## Reference Implementations

This parser is based on learnings from:
- [OctoPrint-BambuPrinter](https://github.com/jneilliii/OctoPrint-BambuPrinter) - Python/pybambu
- [FDM-Monster](https://github.com/fdm-monster/fdm-monster) - TypeScript
- [SlicerCompanion](https://github.com/graelo/SlicerCompanion) - Pure Swift thumbnail extractor
