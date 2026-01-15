"""
Test delete file from SD card via API
"""
import requests

print('='*60)
print('Testing Delete File from SD Card')
print('='*60)

# File to delete (salah satu file test yang kecil)
filename = "TEST_ROOT.3mf"

print(f'\nDeleting file: {filename}')

try:
    # Call API delete endpoint
    response = requests.delete(f'http://localhost:5000/api/printer-files/{filename}')
    
    print(f'\nStatus code: {response.status_code}')
    print(f'Response: {response.json()}')
    
    if response.status_code == 200:
        print('\n✅ Delete SUCCESS!')
        
        # Verify by listing files
        print('\nVerifying - listing files after delete...')
        list_response = requests.get('http://localhost:5000/api/printer-files/list')
        files = list_response.json()['files']
        
        deleted_file_found = any(f['name'] == filename for f in files)
        
        if not deleted_file_found:
            print(f'✅ Verified: {filename} no longer in list')
        else:
            print(f'⚠️  Warning: {filename} still in list')
    else:
        print(f'\n❌ Delete FAILED: {response.json()}')

except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()

print('\n' + '='*60)
