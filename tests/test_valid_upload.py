"""
Upload valid 3MF file test
"""
import sys
sys.path.insert(0, 'src')

from services.ftps_service import BambuFTPSClient
from config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE

print('='*60)
print('Uploading VALID 3MF File Test')
print('='*60)

try:
    client = BambuFTPSClient(BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE)
    
    if not client.connect():
        print('Failed to connect!')
        sys.exit(1)
    
    print('Connected to FTPS')
    
    # Upload the valid SpeedBoat file
    file_path = 'data/uploads/SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf'
    remote_name = 'SPEEDBOAT_TEST.3mf'
    
    print(f'\nFile: SpeedBoatRace (3MB - Valid Bambu 3MF)')
    print(f'Target: {remote_name}')
    print(f'\nUploading...')
    
    success = client.upload_file(file_path, remote_name)
    
    client.disconnect()
    
    print('\n' + '='*60)
    if success:
        print('SUCCESS! Upload completed')
        print('='*60)
        print('\nNOW CHECK PRINTER LCD!')
        print(f'Look for: {remote_name}')
        print('It should appear in "SD Card Files" section')
    else:
        print('FAILED!')
    print('='*60)
    
except Exception as e:
    print(f'\nError: {e}')
    import traceback
    traceback.print_exc()
