#!/usr/bin/env python
"""
Comprehensive test for printer files API endpoints
Tests all three endpoints: list, print, delete
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from fastapi.testclient import TestClient
from src.main import app

# Create test client
client = TestClient(app)

print("=" * 80)
print("PRINTER FILES API - COMPREHENSIVE TESTING")
print("=" * 80)

# Test 1: List files endpoint
print("\nTEST 1: GET /api/printer-files/list")
print("-" * 80)
response = client.get("/api/printer-files/list")
print(f"Status Code: {response.status_code}")
assert response.status_code == 200, f"Expected 200, got {response.status_code}"

data = response.json()
print(f"Response Keys: {list(data.keys())}")
print(f"Printer ID: {data.get('printer_id')}")
print(f"Printer IP: {data.get('printer_ip')}")
print(f"Total Files: {data.get('total_files')}")
print(f"Status: {data.get('status')}")

assert data.get('status') == 'success', "Expected status='success'"
assert isinstance(data.get('files'), list), "Files should be a list"
assert len(data.get('files', [])) > 0, "Should have at least one file"

# Check file structure
for i, file in enumerate(data.get('files', [])):
    print(f"\n  File {i+1}:")
    print(f"    Name: {file.get('name')}")
    print(f"    Size: {file.get('size')} bytes")
    print(f"    Size (MB): {file.get('size_mb'):.2f}")
    print(f"    Is 3MF: {file.get('is_3mf')}")
    print(f"    Is GCode: {file.get('is_gcode')}")
    
    assert 'name' in file, "File must have 'name'"
    assert 'size' in file, "File must have 'size'"
    assert 'size_mb' in file, "File must have 'size_mb'"
    assert 'is_3mf' in file, "File must have 'is_3mf'"
    assert 'is_gcode' in file, "File must have 'is_gcode'"

print("\n[PASS] List files endpoint")

# Test 2: Print from SD card endpoint
print("\nTEST 2: POST /api/printer-files/print/{filename}")
print("-" * 80)

test_filename = "test_model.3mf"
response = client.post(f"/api/printer-files/print/{test_filename}")
print(f"Status Code: {response.status_code}")
assert response.status_code == 200, f"Expected 200, got {response.status_code}"

data = response.json()
print(f"Status: {data.get('status')}")
print(f"Message: {data.get('message')}")
print(f"Filename: {data.get('filename')}")

assert data.get('status') == 'success', "Expected status='success'"
assert data.get('filename') == test_filename, "Filename mismatch"

print("[PASS] Print from SD card endpoint")

# Test 3: Print with invalid filename extension
print("\nTEST 3: POST /api/printer-files/print/{invalid.txt} (should fail)")
print("-" * 80)

response = client.post("/api/printer-files/print/invalid.txt")
print(f"Status Code: {response.status_code}")
assert response.status_code == 400, f"Expected 400 for invalid file, got {response.status_code}"

data = response.json()
print(f"Error: {data.get('detail')}")
print("[PASS] Invalid filename validation")

# Test 4: Delete file endpoint
print("\nTEST 4: DELETE /api/printer-files/{filename}")
print("-" * 80)

test_filename = "old_model.3mf"
response = client.delete(f"/api/printer-files/{test_filename}")
print(f"Status Code: {response.status_code}")
assert response.status_code == 200, f"Expected 200, got {response.status_code}"

data = response.json()
print(f"Status: {data.get('status')}")
print(f"Message: {data.get('message')}")

assert data.get('status') == 'success', "Expected status='success'"

print("[PASS] Delete file endpoint")

# Test 5: Empty filename validation
print("\nTEST 5: POST /api/printer-files/print/ (empty filename)")
print("-" * 80)

response = client.post("/api/printer-files/print/")
print(f"Status Code: {response.status_code}")
# Note: FastAPI will return 404 for missing path parameter
print(f"Expected 404 for missing path parameter: {response.status_code == 404}")

# Test 6: Verify PrinterFileInfo class
print("\nTEST 6: Testing PrinterFileInfo class")
print("-" * 80)

from src.services.ftps_service import PrinterFileInfo

file_info = PrinterFileInfo("test.3mf", 1048576)
file_dict = file_info.to_dict()

print(f"File name: {file_dict['name']}")
print(f"File size: {file_dict['size']}")
print(f"File size (MB): {file_dict['size_mb']:.2f}")
print(f"Is 3MF: {file_dict['is_3mf']}")
print(f"Is GCode: {file_dict['is_gcode']}")

assert file_dict['name'] == 'test.3mf', "Name should match"
assert file_dict['size'] == 1048576, "Size should match"
assert abs(file_dict['size_mb'] - 1.0) < 0.01, "Size in MB should be ~1.0"
assert file_dict['is_3mf'] == True, "Should detect .3mf file"
assert file_dict['is_gcode'] == False, "Should not be gcode"

print("[PASS] PrinterFileInfo class")

print("\n" + "=" * 80)
print("ALL TESTS PASSED!")
print("=" * 80)
print("\nSummary:")
print("  [PASS] List files endpoint")
print("  [PASS] Print from SD card endpoint")
print("  [PASS] Invalid filename validation")
print("  [PASS] Delete file endpoint")
print("  [PASS] PrinterFileInfo class")
print("\nAPI is ready for integration with frontend!")
print("=" * 80)
