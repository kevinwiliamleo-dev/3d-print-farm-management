"""
List all folders on Bambu printer SD card
"""
from ftplib import FTP_TLS
import ssl

# Printer config
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"

class ImplicitFTPS(FTP_TLS):
    def __init__(self, host='', user='', passwd='', timeout=60):
        FTP_TLS.__init__(self, host, user, passwd)
        self.timeout = timeout

    def connect(self, host='', port=990, timeout=-999):
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        import socket
        self.sock = socket.create_connection((self.host, self.port), self.timeout)
        self.sock = ssl_context.wrap_socket(self.sock, server_hostname=self.host)
        self.af = self.sock.family
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

print("=" * 60)
print("Exploring Bambu Printer SD Card")
print("=" * 60)

ftp = ImplicitFTPS()
ftp.connect(PRINTER_IP, 990, timeout=30)
ftp.login("bblp", ACCESS_CODE)
ftp.prot_p()

print("✅ Connected!")

def list_dir(path):
    """List directory contents with details"""
    print(f"\n📁 {path}:")
    print("-" * 50)
    try:
        ftp.cwd(path)
        files = []
        ftp.retrlines('LIST', lambda x: files.append(x))
        for f in files:
            print(f"  {f}")
        if not files:
            print("  (empty)")
        return files
    except Exception as e:
        print(f"  Error: {e}")
        return []

# List root
list_dir('/')

# List key folders
for folder in ['model', 'cache', 'timelapse', 'ipcam']:
    list_dir(f'/{folder}')

# Check cache subfolder
try:
    ftp.cwd('/cache')
    subfolders = []
    ftp.retrlines('NLST', lambda x: subfolders.append(x))
    for sf in subfolders[:5]:  # First 5 subfolders
        try:
            list_dir(f'/cache/{sf}')
        except:
            pass
except:
    pass

ftp.quit()
print("\n✅ Done!")
