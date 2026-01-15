"""
Test script to verify 3MF parser is working correctly

Based on learnings from:
- OctoPrint-BambuPrinter: https://github.com/jneilliii/OctoPrint-BambuPrinter
- FDM-Monster: https://github.com/fdm-monster/fdm-monster
"""
import sys
import os
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.gcode_parser import (
    parse_file_metadata,
    parse_3mf_metadata,
    extract_3mf_thumbnail,
    get_3mf_structure,
    format_time_seconds
)

def test_3mf_files():
    """Test parsing of 3MF files in uploads directory"""
    
    uploads_dir = Path(__file__).parent / "data" / "uploads"
    
    print("=" * 60)
    print("3MF Parser Test")
    print("=" * 60)
    print()
    
    if not uploads_dir.exists():
        print(f"❌ Uploads directory not found: {uploads_dir}")
        return
    
    # Find all 3MF files
    threemf_files = list(uploads_dir.glob("*.3mf"))
    
    if not threemf_files:
        print("❌ No .3mf files found in uploads directory")
        print(f"   Looking in: {uploads_dir}")
        return
    
    print(f"Found {len(threemf_files)} .3mf file(s)")
    print()
    
    for file_path in threemf_files:
        print("-" * 60)
        print(f"📁 File: {file_path.name}")
        print(f"   Size: {file_path.stat().st_size / 1024:.1f} KB")
        print()
        
        # Get structure
        print("📋 3MF Structure:")
        structure = get_3mf_structure(file_path)
        
        if 'error' in structure:
            print(f"   ❌ Error: {structure['error']}")
            continue
            
        print(f"   G-code files: {len(structure['gcode_files'])}")
        for gf in structure['gcode_files']:
            print(f"      - {gf['name']} ({gf['size']:,} bytes)")
        
        print(f"   Config files: {len(structure['config_files'])}")
        for cf in structure['config_files'][:5]:  # Show first 5
            print(f"      - {cf['name']}")
        
        print(f"   Image files: {len(structure['image_files'])}")
        for img in structure['image_files'][:3]:  # Show first 3
            print(f"      - {img['name']}")
        
        print()
        
        # Parse metadata
        print("📊 Parsed Metadata:")
        metadata = parse_file_metadata(file_path)
        
        if 'error' in metadata:
            print(f"   ❌ Error: {metadata['error']}")
        else:
            # Show key metadata
            key_fields = [
                'model_name', 'file_type', 'file_size_mb',
                'estimated_time', 'estimated_time_seconds',
                'filament_used_g', 'filament_type', 'filament_color',
                'layer_count', 'layer_height',
                'nozzle_temp', 'bed_temp',
                'printer_model', 'gcode_path',
                'slicer_name', 'slicer_version',
            ]
            
            for field in key_fields:
                value = metadata.get(field)
                if value is not None:
                    print(f"   {field}: {value}")
            
            # Show plates info
            if metadata.get('plates'):
                print()
                print(f"   📋 Plates ({len(metadata['plates'])} found):")
                for plate in metadata['plates']:
                    print(f"      - {plate['name']}: {plate.get('estimated_time', 'N/A')}")
        
        print()
        
        # Try to extract thumbnail
        print("🖼️  Thumbnail:")
        thumbnail_data = extract_3mf_thumbnail(file_path)
        if thumbnail_data:
            print(f"   ✅ Found! Size: {len(thumbnail_data):,} bytes")
            
            # Save thumbnail for verification
            thumbnail_path = file_path.parent / f"{file_path.stem}_thumbnail.png"
            with open(thumbnail_path, 'wb') as f:
                f.write(thumbnail_data)
            print(f"   💾 Saved to: {thumbnail_path.name}")
        else:
            print("   ❌ No thumbnail found")
        
        print()

def test_gcode_files():
    """Test parsing of G-code files"""
    
    gcode_dir = Path(__file__).parent / "data" / "gcode"
    
    print("=" * 60)
    print("G-code Parser Test")
    print("=" * 60)
    print()
    
    if not gcode_dir.exists():
        print(f"No gcode directory: {gcode_dir}")
        return
    
    gcode_files = list(gcode_dir.glob("*.gcode")) + list(gcode_dir.glob("*.g"))
    
    if not gcode_files:
        print("No .gcode files found")
        return
    
    print(f"Found {len(gcode_files)} G-code file(s)")
    
    for file_path in gcode_files[:3]:  # Test first 3
        print()
        print("-" * 60)
        print(f"📁 File: {file_path.name}")
        
        metadata = parse_file_metadata(file_path)
        
        for key, value in metadata.items():
            if value is not None:
                print(f"   {key}: {value}")


if __name__ == "__main__":
    print()
    test_3mf_files()
    print()
    test_gcode_files()
    print()
    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)
