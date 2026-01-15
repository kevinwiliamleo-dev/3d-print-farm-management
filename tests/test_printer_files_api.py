#!/usr/bin/env python
"""
Test script for printer files API
"""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.cwd()))

from fastapi.testclient import TestClient
from src.main import app

# Create test client
client = TestClient(app)

print("=" * 70)
print("TESTING PRINTER FILES API")
print("=" * 70)

# Test 1: List printer files
print("\n✓ Testing GET /api/printer-files/list")
response = client.get("/api/printer-files/list")
print(f"   Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Files returned: {len(data.get('files', []))}")
    if data.get('files'):
        for file in data['files'][:2]:
            print(f"     - {file['name']} ({file['size_mb']:.1f} MB)")
    print("   ✅ PASS")
else:
    print(f"   Response: {response.text}")
    print("   ❌ FAIL")

# Test 2: Health check
print("\n✓ Testing GET /health")
response = client.get("/health")
print(f"   Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Status: {data.get('status')}")
    print("   ✅ PASS")
else:
    print("   ❌ FAIL")

# Test 3: Root endpoint
print("\n✓ Testing GET /")
response = client.get("/")
print(f"   Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Application: {data.get('application')}")
    print("   ✅ PASS")
else:
    print("   ❌ FAIL")

print("\n" + "=" * 70)
print("TESTS COMPLETE")
print("=" * 70)
