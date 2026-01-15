"""
Test AMS API endpoint
"""
import requests
import json

url = "http://localhost:5000/api/printers/03900D5A2402051/ams/trays"
print(f"Testing: {url}")

try:
    response = requests.get(url, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
