"""
List all files on printer SD card
"""
import sys
sys.path.insert(0, 'src')

from services.ftps_service import BambuFTPSClient
from config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE

print('='*60)
print('SD Card Files')
print('='*60)

try:
    client = BambuFTPSClient(BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE)
    
    if not client.connect():
        print('❌ Failed to connect!')
        sys.exit(1)
    
    print('✅ Connected to FTPS\n')
    
    # List root directory files
    print('📂 ROOT DIRECTORY:')
    print('-' * 60)
    try:
        files = client.client.ftp.nlst()
        
        # Separate into files and folders
        folders = []
        files_list = []
        
        for item in files:
            # Check if it's a directory by trying to CWD into it
            try:
                client.client.ftp.cwd(item)
                folders.append(item)
                client.client.ftp.cwd('/')
            except:
                # It's a file
                if item.endswith('.3mf') or item.endswith('.gcode'):
                    files_list.append(item)
        
        # Show folders
        if folders:
            print('\n📁 FOLDERS:')
            for folder in sorted(folders):
                print(f'   📁 {folder}/')
        
        # Show 3MF files
        if files_list:
            print('\n📄 PRINT FILES (.3mf):')
            for f in sorted(files_list):
                try:
                    size = client.client.ftp.size(f)
                    size_mb = size / (1024 * 1024) if size else 0
                    print(f'   ✅ {f} ({size_mb:.2f} MB)')
                except:
                    print(f'   ✅ {f}')
        
        # List cache directory if exists
        if 'cache' in folders:
            print('\n' + '=' * 60)
            print('📂 CACHE DIRECTORY:')
            print('-' * 60)
            try:
                cache_files = client.client.ftp.nlst('cache/')
                cache_3mf = [f for f in cache_files if f.endswith('.3mf')]
                
                if cache_3mf:
                    print('\n📄 CACHE FILES (.3mf):')
                    for f in sorted(cache_3mf):
                        try:
                            size = client.client.ftp.size(f)
                            size_mb = size / (1024 * 1024) if size else 0
                            filename = f.split('/')[-1]
                            print(f'   ✅ {filename} ({size_mb:.2f} MB)')
                        except:
                            filename = f.split('/')[-1]
                            print(f'   ✅ {filename}')
                else:
                    print('   (empty)')
            except Exception as e:
                print(f'   Error: {e}')
        
        print('\n' + '=' * 60)
        print(f'Total printable files found: {len(files_list)}')
        print('=' * 60)
        
    except Exception as e:
        print(f'Error listing files: {e}')
        import traceback
        traceback.print_exc()
    
    client.disconnect()
    
except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
