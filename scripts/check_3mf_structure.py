"""
Check the internal structure of a .3mf file to find the correct gcode path
"""
import zipfile
import os
from ftplib import FTP_TLS
import ssl
import tempfile
import io

# Printer config
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"

# File to check
FILENAME = "14min44s, Bambu PLA Basic, A1.3mf"

print("=" * 60)
print("3MF File Structure Checker")
print("=" * 60)
print(f"Checking: {FILENAME}")
print()

# Create custom FTP_TLS that allows implicit TLS
class ImplicitFTPS(FTP_TLS):
    def __init__(self, host='', user='', passwd='', timeout=60):
        FTP_TLS.__init__(self, host, user, passwd)
        self.timeout = timeout

    def connect(self, host='', port=990, timeout=-999):
        """Connect to host. Arguments are:
        - host: hostname to connect to (default: 'localhost')
        - port: port to connect to (default: 990 for implicit FTPS)
        """
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout

        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Import socket
        import socket
        
        # Create and wrap socket with SSL immediately (implicit TLS)
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.sock = ssl_context.wrap_socket(self.sock, server_hostname=self.host)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

print("📂 Connecting to printer FTPS...")

try:
    ftp = ImplicitFTPS()
    ftp.connect(PRINTER_IP, 990, timeout=30)
    ftp.login("bblp", ACCESS_CODE)
    ftp.prot_p()  # Enable data encryption
    
    print("✅ FTPS Connected!")
    
    # Check current directory and change to model folder
    print(f"Current directory: {ftp.pwd()}")
    
    # Change to model folder where .3mf files are stored
    try:
        ftp.cwd('/model')
        print(f"Changed to: {ftp.pwd()}")
    except:
        print("Could not change to /model, trying /cache...")
        try:
            ftp.cwd('/cache')
            print(f"Changed to: {ftp.pwd()}")
        except:
            pass
    
    # List all files first
    print()
    print("All files in current directory:")
    files_raw = []
    ftp.retrlines('NLST', lambda x: files_raw.append(x))
    
    for f in files_raw:
        print(f"  - '{f}'")
    
    # Find 3mf files
    print()
    print("Looking for .3mf files with size > 0...")
    
    # Get detailed listing
    files_detail = []
    ftp.retrlines('LIST', lambda x: files_detail.append(x))
    
    for line in files_detail:
        if '.3mf' in line.lower():
            print(f"  {line}")
    
    # Try to download a specific file
    print()
    
    # Find a valid file to download
    target_file = None
    for f in files_raw:
        if '.3mf' in f.lower() and 'plate' not in f.lower():
            target_file = f
            break
    
    if target_file:
        print(f"📥 Trying to download: '{target_file}'...")
        
        file_buffer = io.BytesIO()
        try:
            ftp.retrbinary(f'RETR "{target_file}"', file_buffer.write)
            file_buffer.seek(0)
            
            file_size = len(file_buffer.getvalue())
            print(f"✅ Downloaded {file_size} bytes")
        except Exception as e:
            print(f"❌ Download error: {e}")
            # Try without quotes
            try:
                ftp.retrbinary(f'RETR {target_file}', file_buffer.write)
                file_size = len(file_buffer.getvalue())
                print(f"✅ Downloaded {file_size} bytes (without quotes)")
            except Exception as e2:
                print(f"❌ Still failed: {e2}")
                target_file = None
    else:
        print("No .3mf file found to download")
        file_buffer = None
    
    ftp.quit()
    
    if not target_file or not file_buffer:
        print("Cannot analyze file structure")
        exit(1)
    
    # Check if it's a valid ZIP (3MF is a ZIP archive)
    print()
    print("🔍 Analyzing 3MF structure...")
    
    try:
        with zipfile.ZipFile(file_buffer, 'r') as zf:
            print()
            print("📁 Contents of .3mf file:")
            print("-" * 50)
            
            gcode_files = []
            metadata_files = []
            thumbnail_files = []
            
            for name in sorted(zf.namelist()):
                info = zf.getinfo(name)
                size = info.file_size
                
                if '.gcode' in name.lower():
                    gcode_files.append((name, size))
                    print(f"  🔧 {name} ({size:,} bytes) <-- GCODE")
                elif 'thumbnail' in name.lower() or '.png' in name.lower():
                    thumbnail_files.append((name, size))
                    print(f"  🖼️  {name} ({size:,} bytes) <-- THUMBNAIL")
                elif 'metadata' in name.lower() or '.xml' in name.lower():
                    metadata_files.append((name, size))
                    print(f"  📋 {name} ({size:,} bytes)")
                else:
                    print(f"     {name} ({size:,} bytes)")
            
            print("-" * 50)
            print()
            
            # Summary
            print("📊 Summary:")
            if gcode_files:
                print(f"   GCODE files found: {len(gcode_files)}")
                for gf, size in gcode_files:
                    print(f"   ➡️  Correct param value: \"{gf}\"")
            else:
                print("   ⚠️  No GCODE files found!")
                
            if thumbnail_files:
                print(f"   Thumbnails: {len(thumbnail_files)}")
            else:
                print("   ⚠️  No thumbnails found!")
                
            # Read metadata if exists
            print()
            print("📝 Checking Metadata files...")
            for name in zf.namelist():
                if 'model_settings' in name.lower() or 'slice_info' in name.lower():
                    try:
                        content = zf.read(name).decode('utf-8', errors='ignore')[:500]
                        print(f"\n{name}:")
                        print(content)
                    except:
                        pass
            
    except zipfile.BadZipFile:
        print("❌ File is not a valid ZIP/3MF archive!")
        # Show first few bytes
        file_buffer.seek(0)
        header = file_buffer.read(100)
        print(f"File header (hex): {header[:50].hex()}")
        print(f"File header (str): {header[:50]}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
