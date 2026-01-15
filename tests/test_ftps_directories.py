"""
Test FTPS directory structure and file operations
"""
import sys
sys.path.insert(0, 'src')

from services.ftps_service import BambuFTPSClient
from config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE

print('='*60)
print('FTPS Directory Structure Test')
print('='*60)

try:
    client = BambuFTPSClient(BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE)
    
    if not client.connect():
        print('❌ Failed to connect!')
        sys.exit(1)
    
    print('✅ Connected to FTPS')
    
    # Test 1: Check current directory
    print('\n1. Current directory:')
    try:
        pwd = client.client.ftp.pwd()
        print(f'   PWD: {pwd}')
    except Exception as e:
        print(f'   Error: {e}')
    
    # Test 2: Check if cache directory exists
    print('\n2. Checking cache directory:')
    try:
        client.client.ftp.cwd('cache')
        print('   ✅ Cache directory EXISTS!')
        client.client.ftp.cwd('/')
    except Exception as e:
        print(f'   ❌ No cache directory: {e}')
    
    # Test 3: List root files
    print('\n3. Listing root directory files:')
    try:
        files = client.client.ftp.nlst()
        if files:
            print(f'   Found {len(files)} items:')
            for f in files[:10]:  # Show first 10
                print(f'     - {f}')
        else:
            print('   No files found')
    except Exception as e:
        print(f'   Error: {e}')
    
    # Test 4: Upload to root
    print('\n4. Uploading test file to ROOT:')
    test_file = 'data/uploads/test_model.3mf'
    success = client.upload_file(test_file, 'TEST_ROOT.3mf')
    print(f'   Result: {"✅ SUCCESS" if success else "❌ FAILED"}')
    
    # Test 5: Upload to cache
    print('\n5. Uploading test file to CACHE:')
    try:
        success = client.upload_file(test_file, 'cache/TEST_CACHE.3mf')
        print(f'   Result: {"✅ SUCCESS" if success else "❌ FAILED"}')
    except Exception as e:
        print(f'   Error: {e}')
    
    # Test 6: Try to list files again
    print('\n6. Listing files after upload:')
    try:
        files = client.client.ftp.nlst()
        test_files = [f for f in files if 'TEST' in f.upper()]
        if test_files:
            print(f'   Found our test files: {test_files}')
        else:
            print('   Our test files NOT found in list')
    except Exception as e:
        print(f'   Error: {e}')
    
    client.disconnect()
    
    print('\n' + '='*60)
    print('Test completed!')
    print('='*60)
    print('\n⚠️  IMPORTANT: Check printer LCD to see if files appear!')
    
except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
