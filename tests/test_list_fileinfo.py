"""
Test FTPS list files with PrinterFileInfo
"""
import sys
sys.path.insert(0, 'src')

from services.ftps_service import BambuFTPSClient, PrinterFileInfo
from config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE

print('='*60)
print('Testing FTPS list_files() with PrinterFileInfo')
print('='*60)

try:
    client = BambuFTPSClient(BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE)
    
    if not client.connect():
        print('❌ Failed to connect!')
        sys.exit(1)
    
    print('✅ Connected to FTPS\n')
    
    print('Calling client.list_files()...')
    files = client.list_files()
    
    print(f'\nResult type: {type(files)}')
    print(f'Files count: {len(files)}\n')
    
    if len(files) > 0:
        print('Files found:')
        for f in files[:10]:  # Show first 10
            file_dict = f.to_dict()
            print(f'  ✅ {f.name} ({f.size} bytes, {file_dict["size_mb"]} MB)')
            print(f'     to_dict(): {file_dict}')
    else:
        print('❌ No files found!')
    
    client.disconnect()
    
    print('\n' + '='*60)
    print('Test completed')
    print('='*60)
    
except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
