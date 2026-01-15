"""
Verify uploaded file on printer SD card
"""
import ftplib
import ssl


class ImplicitTLS(ftplib.FTP_TLS):
    """ftplib.FTP_TLS sub-class to support implicit SSL FTPS"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sock = None

    @property
    def sock(self):
        return self._sock

    @sock.setter
    def sock(self, value):
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(
                conn, server_hostname=self.host, session=self.sock.session
            )
        return conn, size


def main():
    print("=" * 60)
    print("Verify Uploaded File on SD Card")
    print("=" * 60)
    
    ftp = ImplicitTLS()
    ftp.set_debuglevel(0)
    ftp.connect("192.168.4.101", 990)
    ftp.login("bblp", "34782589")
    ftp.prot_p()
    
    print("\n📂 Root directory:")
    files = ftp.nlst("")
    for f in files:
        try:
            size = ftp.size(f)
            print(f"  📁 {f}: {size} bytes")
        except:
            print(f"  📁 {f}: (directory)")
    
    # Check for our uploaded file
    print("\n🔍 Looking for test_octoprint_upload.3mf...")
    try:
        size = ftp.size("test_octoprint_upload.3mf")
        print(f"  ✅ FOUND! Size: {size} bytes")
    except Exception as e:
        print(f"  ❌ NOT FOUND in root: {e}")
    
    # Check cache folder
    print("\n📂 Cache folder:")
    try:
        files = ftp.nlst("cache")
        for f in files:
            try:
                size = ftp.size(f"cache/{f}")
                if "test" in f.lower() or "octoprint" in f.lower():
                    print(f"  ⭐ {f}: {size} bytes")
                else:
                    print(f"  📄 {f}: {size} bytes")
            except:
                print(f"  📄 {f}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # List all .3mf files everywhere
    print("\n📂 All .3mf files:")
    for folder in ["", "cache", "model"]:
        try:
            files = ftp.nlst(folder) if folder else ftp.nlst("")
            for f in files:
                if f.endswith(".3mf"):
                    full_path = f"{folder}/{f}" if folder else f
                    try:
                        size = ftp.size(full_path)
                        mark = "⭐" if "test" in f.lower() else "📄"
                        print(f"  {mark} {full_path}: {size} bytes")
                    except:
                        pass
        except:
            pass
    
    ftp.quit()
    print("\n✅ Done")


if __name__ == "__main__":
    main()
