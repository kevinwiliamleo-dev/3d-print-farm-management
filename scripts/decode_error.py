"""
Decode Bambu Lab print error codes and check file validity
"""
import zipfile
import os

# Error code from printer
ERROR_CODE = 83935248

print("=" * 60)
print("Bambu Lab Error Code Analysis")
print("=" * 60)

# Convert to hex
hex_code = hex(ERROR_CODE)
print(f"Error code: {ERROR_CODE}")
print(f"Hex: {hex_code}")

# Bambu error codes are usually structured
# High byte = category, Low bytes = specific error
high_byte = (ERROR_CODE >> 24) & 0xFF
mid_byte = (ERROR_CODE >> 16) & 0xFF
low_word = ERROR_CODE & 0xFFFF

print(f"High byte: {high_byte} (0x{high_byte:02X})")
print(f"Mid byte: {mid_byte} (0x{mid_byte:02X})")
print(f"Low word: {low_word} (0x{low_word:04X})")

# Common Bambu error categories
print("\n" + "=" * 60)
print("Error Interpretation")
print("=" * 60)

# 0x05 = Print/File related errors
if high_byte == 0x05:
    print("Category: Print/File Error")
    if mid_byte == 0x00:
        print("Subcategory: File not found or invalid")
        print("\nPossible causes:")
        print("  1. File doesn't exist at specified path")
        print("  2. File is 0 bytes (empty)")
        print("  3. File is corrupted/invalid 3MF")
        print("  4. Missing gcode in 3MF archive")

# Check our test file
print("\n" + "=" * 60)
print("Checking Local Test File")
print("=" * 60)

TEST_FILE = "data/uploads/SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf"

if not os.path.exists(TEST_FILE):
    print(f"❌ File not found: {TEST_FILE}")
else:
    file_size = os.path.getsize(TEST_FILE)
    print(f"📄 File: {TEST_FILE}")
    print(f"📄 Size: {file_size:,} bytes")
    
    if file_size == 0:
        print("❌ File is EMPTY!")
    else:
        # Check if it's a valid ZIP/3MF
        print(f"\n🔍 Checking 3MF structure...")
        try:
            with zipfile.ZipFile(TEST_FILE, 'r') as zf:
                print("✅ Valid ZIP archive")
                
                # List contents
                files = zf.namelist()
                print(f"📁 Contains {len(files)} files:")
                
                has_gcode = False
                has_metadata = False
                gcode_path = None
                
                for name in sorted(files):
                    info = zf.getinfo(name)
                    size = info.file_size
                    
                    if '.gcode' in name.lower():
                        has_gcode = True
                        gcode_path = name
                        print(f"   🔧 {name} ({size:,} bytes) <-- GCODE")
                    elif 'plate_' in name.lower() and '.json' in name.lower():
                        print(f"   📋 {name} ({size:,} bytes) <-- PLATE INFO")
                    elif 'slice_info' in name.lower():
                        has_metadata = True
                        print(f"   📋 {name} ({size:,} bytes) <-- SLICE INFO")
                    elif '.png' in name.lower():
                        print(f"   🖼️  {name} ({size:,} bytes)")
                    else:
                        if size > 1000:
                            print(f"      {name} ({size:,} bytes)")
                
                print("\n📊 Summary:")
                if has_gcode:
                    print(f"   ✅ Has GCODE: {gcode_path}")
                else:
                    print("   ❌ NO GCODE FOUND - File may not be sliced!")
                    
                if has_metadata:
                    print("   ✅ Has slice metadata")
                else:
                    print("   ⚠️  No slice metadata")
                
                # Check if gcode has content
                if gcode_path:
                    gcode_content = zf.read(gcode_path)
                    print(f"   📄 GCODE size: {len(gcode_content):,} bytes")
                    if len(gcode_content) > 0:
                        # Show first few lines
                        lines = gcode_content.decode('utf-8', errors='ignore').split('\n')[:10]
                        print(f"   📄 First lines of GCODE:")
                        for line in lines:
                            print(f"      {line[:80]}")
                
        except zipfile.BadZipFile:
            print("❌ NOT a valid ZIP/3MF file!")
            # Show header
            with open(TEST_FILE, 'rb') as f:
                header = f.read(16)
                print(f"   Header (hex): {header.hex()}")
                print(f"   Header (str): {header}")

print("\n" + "=" * 60)
print("Recommendations")
print("=" * 60)

print("""
If the 3MF file doesn't have GCODE:
  - The file is NOT sliced, just a 3D model
  - You need to slice it with Bambu Studio first
  
If the 3MF has GCODE but print fails:
  - Check the 'param' in print command matches the gcode path
  - Ensure file uploaded correctly (check size on SD card)
  
Error 83935248 (0x05000010) typically means:
  - File not found or empty on SD card
  - Invalid/corrupted 3MF file
  - Missing or invalid gcode inside 3MF
""")
