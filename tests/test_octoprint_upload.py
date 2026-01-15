"""
Test FTPS upload using EXACT OctoPrint-BambuPrinter implementation
This copies the upload method character-by-character from the working plugin
"""
import ftplib
import ssl
import socket
import os
from dataclasses import dataclass

# Printer credentials
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"


class ImplicitTLS(ftplib.FTP_TLS):
    """ftplib.FTP_TLS sub-class to support implicit SSL FTPS"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sock = None

    @property
    def sock(self):
        """return socket"""
        return self._sock

    @sock.setter
    def sock(self, value):
        """wrap and set SSL socket"""
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)

        if self._prot_p:
            conn = self.context.wrap_socket(
                conn, server_hostname=self.host, session=self.sock.session
            )  # this is the fix
        return conn, size


@dataclass
class IoTFTPSConnection:
    """iot ftps ftpsclient - EXACT COPY from OctoPrint-BambuPrinter"""

    ftps_session: ftplib.FTP | ImplicitTLS

    def close(self) -> None:
        """close the current session from the ftps server"""
        self.ftps_session.close()

    def upload_file(self, source: str, dest: str, callback=None) -> bool:
        """upload a file to a path inside the FTPS server"""

        file_size = os.path.getsize(source)
        block_size = max(file_size // 100, 8192)
        rest = None

        try:
            # Taken from ftplib.storbinary but with custom ssl handling
            # due to the shitty bambu p1p ftps server TODO fix properly.
            with open(source, "rb") as fp:
                self.ftps_session.voidcmd("TYPE I")

                with self.ftps_session.transfercmd(f"STOR {dest}", rest) as conn:
                    while 1:
                        buf = fp.read(block_size)

                        if not buf:
                            break

                        conn.sendall(buf)

                        if callback:
                            callback(buf)

                    # shutdown ssl layer
                    if ftplib._SSLSocket is not None and isinstance(
                        conn, ftplib._SSLSocket
                    ):
                        # Yeah this is suposed to be conn.unwrap
                        # But since we operate in prot p mode
                        # we can close the connection always.
                        # This is cursed but it works.
                        if "vsFTPd" in self.ftps_session.welcome:
                            conn.unwrap()
                        else:
                            conn.shutdown(socket.SHUT_RDWR)

                return True
        except Exception as ex:
            print(f"unexpected exception occurred: {ex}")
            import traceback
            traceback.print_exc()
            pass
        return False


@dataclass
class IoTFTPSClient:
    ftps_host: str
    ftps_port: int = 21
    ftps_user: str = ""
    ftps_pass: str = ""
    ssl_implicit: bool = False
    welcome: str = ""
    _connection: 'IoTFTPSConnection | None' = None

    def __enter__(self):
        session = self.open_ftps_session()
        self._connection = IoTFTPSConnection(session)
        return self._connection

    def __exit__(self, type, value, traceback):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def open_ftps_session(self) -> ftplib.FTP | ImplicitTLS:
        """init ftps_session based on input params"""
        ftps_session = ImplicitTLS() if self.ssl_implicit else ftplib.FTP()
        ftps_session.set_debuglevel(2)  # Debug level 2 for verbose output

        self.welcome = ftps_session.connect(host=self.ftps_host, port=self.ftps_port)

        if self.ftps_user and self.ftps_pass:
            ftps_session.login(user=self.ftps_user, passwd=self.ftps_pass)
        else:
            ftps_session.login()

        if self.ssl_implicit:
            ftps_session.prot_p()

        return ftps_session


def create_test_file():
    """Create a small test 3mf file"""
    import zipfile
    import tempfile
    import json
    
    # Create minimal 3MF file
    temp_path = os.path.join(tempfile.gettempdir(), "test_upload.3mf")
    
    with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add required content types
        content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>'''
        zf.writestr('[Content_Types].xml', content_types)
        
        # Add a simple 3D model XML
        model_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
    <resources>
        <object id="1" type="model">
            <mesh>
                <vertices>
                    <vertex x="0" y="0" z="0"/>
                    <vertex x="10" y="0" z="0"/>
                    <vertex x="5" y="10" z="0"/>
                    <vertex x="5" y="5" z="10"/>
                </vertices>
                <triangles>
                    <triangle v1="0" v2="1" v3="2"/>
                    <triangle v1="0" v2="1" v3="3"/>
                    <triangle v1="1" v2="2" v3="3"/>
                    <triangle v1="0" v2="2" v3="3"/>
                </triangles>
            </mesh>
        </object>
    </resources>
    <build>
        <item objectid="1"/>
    </build>
</model>'''
        zf.writestr('3D/3dmodel.model', model_xml)
        
        # Add _rels folder
        rels_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''
        zf.writestr('_rels/.rels', rels_content)
    
    print(f"📄 Created test file: {temp_path} ({os.path.getsize(temp_path)} bytes)")
    return temp_path


def main():
    print("=" * 60)
    print("OctoPrint-BambuPrinter EXACT Upload Test")
    print("=" * 60)
    
    # Create test file
    local_file = create_test_file()
    remote_filename = "test_octoprint_upload.3mf"
    
    print(f"\n📋 Printer: {PRINTER_IP}")
    print(f"📋 Local file: {local_file}")
    print(f"📋 Remote filename: {remote_filename}")
    
    # Use EXACT same client setup as OctoPrint-BambuPrinter
    print(f"\n🔌 Connecting to FTPS...")
    
    bytes_uploaded = [0]
    
    def progress(buf):
        bytes_uploaded[0] += len(buf)
        print(f"  ⬆️ Sent {bytes_uploaded[0]} bytes...", end='\r')
    
    try:
        client = IoTFTPSClient(
            ftps_host=PRINTER_IP,
            ftps_port=990,
            ftps_user="bblp",
            ftps_pass=ACCESS_CODE,
            ssl_implicit=True
        )
        
        with client as ftp:
            print(f"✅ Connected!")
            print(f"📋 Welcome: {client.welcome}")
            
            # List files before
            print(f"\n📂 Files before upload:")
            try:
                files = ftp.ftps_session.nlst("")
                for f in files:
                    print(f"   - {f}")
            except:
                pass
            
            # Upload using EXACT OctoPrint method
            print(f"\n⬆️ Uploading {remote_filename}...")
            success = ftp.upload_file(local_file, remote_filename, callback=progress)
            
            if success:
                print(f"\n✅ Upload reported SUCCESS")
            else:
                print(f"\n❌ Upload reported FAILURE")
            
            # List files after
            print(f"\n📂 Files after upload:")
            try:
                files = ftp.ftps_session.nlst("")
                for f in files:
                    # Get file size
                    try:
                        size = ftp.ftps_session.size(f)
                        if f == remote_filename:
                            print(f"   - {f} ({size} bytes) ⭐ JUST UPLOADED")
                        else:
                            print(f"   - {f} ({size} bytes)")
                    except:
                        print(f"   - {f}")
            except Exception as e:
                print(f"Error listing: {e}")
        
        print(f"\n✅ Test complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
