import requests
import json

print("="*70)
print("TEST DELETE ENDPOINT - FTPS IMPLEMENTATION")
print("="*70)

# Test DELETE
filename = "test_model.3mf"
print(f"\nDeleting: {filename}")

try:
    response = requests.delete(f"http://localhost:5000/api/printer-files/{filename}")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response:")
    print(json.dumps(data, indent=2))
    
    if response.status_code == 200 and data.get("status") == "success":
        print("\n✅ DELETE SUCCESSFUL!")
    else:
        print("\n❌ DELETE FAILED!")
        print(f"Error: {data.get('message', 'Unknown error')}")
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
