"""
Full workflow test: Upload real sliced 3MF file and print it
"""
import ftplib
import ssl
import socket
import os
from dataclasses import dataclass
import paho.mqtt.client as mqtt
import json
import time

# Printer credentials
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "03900D5A2402051"

# Real sliced 3MF file
LOCAL_FILE = r"c:\Users\GIGABYTE\Documents\3d Print farm\cooking-ai-agent\data\uploads\SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf"
REMOTE_FILENAME = "SpeedBoatRace_Upload.3mf"


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


@dataclass
class IoTFTPSConnection:
    ftps_session: ftplib.FTP | ImplicitTLS

    def close(self) -> None:
        self.ftps_session.close()

    def upload_file(self, source: str, dest: str, callback=None) -> bool:
        file_size = os.path.getsize(source)
        block_size = max(file_size // 100, 8192)
        rest = None

        try:
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
                    if ftplib._SSLSocket is not None and isinstance(conn, ftplib._SSLSocket):
                        if "vsFTPd" in self.ftps_session.welcome:
                            conn.unwrap()
                        else:
                            conn.shutdown(socket.SHUT_RDWR)
                return True
        except Exception as ex:
            print(f"Upload error: {ex}")
            import traceback
            traceback.print_exc()
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
        ftps_session = ImplicitTLS() if self.ssl_implicit else ftplib.FTP()
        ftps_session.set_debuglevel(0)
        self.welcome = ftps_session.connect(host=self.ftps_host, port=self.ftps_port)
        if self.ftps_user and self.ftps_pass:
            ftps_session.login(user=self.ftps_user, passwd=self.ftps_pass)
        else:
            ftps_session.login()
        if self.ssl_implicit:
            ftps_session.prot_p()
        return ftps_session


def upload_file():
    """Upload sliced 3MF to printer"""
    print("=" * 60)
    print("STEP 1: Upload sliced 3MF file")
    print("=" * 60)
    
    file_size = os.path.getsize(LOCAL_FILE)
    print(f"📄 Local file: {LOCAL_FILE}")
    print(f"📄 Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    print(f"📤 Remote: {REMOTE_FILENAME}")
    
    bytes_sent = [0]
    def progress(buf):
        bytes_sent[0] += len(buf)
        pct = bytes_sent[0] * 100 // file_size
        print(f"\r   ⬆️ {pct}% ({bytes_sent[0]:,}/{file_size:,} bytes)", end="")
    
    client = IoTFTPSClient(
        ftps_host=PRINTER_IP,
        ftps_port=990,
        ftps_user="bblp",
        ftps_pass=ACCESS_CODE,
        ssl_implicit=True
    )
    
    with client as ftp:
        print(f"\n✅ Connected to FTPS")
        success = ftp.upload_file(LOCAL_FILE, REMOTE_FILENAME, callback=progress)
        
        if success:
            print(f"\n✅ Upload successful!")
            # Verify file size
            try:
                size = ftp.ftps_session.size(REMOTE_FILENAME)
                print(f"📋 Verified on SD: {size:,} bytes")
                if size == file_size:
                    print("✅ Size matches!")
                    return True
                else:
                    print(f"⚠️ Size mismatch! Expected {file_size}, got {size}")
            except Exception as e:
                print(f"⚠️ Could not verify size: {e}")
        else:
            print(f"\n❌ Upload failed!")
    
    return False


def print_file():
    """Send print command for uploaded file"""
    print("\n" + "=" * 60)
    print("STEP 2: Start print")
    print("=" * 60)
    
    start_time = time.time()
    error_found = False
    running_found = False
    error_code = 0
    
    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"✅ MQTT Connected")
        client.subscribe(f"device/{SERIAL}/report")
    
    def on_message(client, userdata, msg):
        nonlocal error_found, running_found, error_code
        try:
            data = json.loads(msg.payload.decode())
            if "print" in data:
                p = data["print"]
                elapsed = time.time() - start_time
                
                if "result" in p:
                    print(f"\n[{elapsed:.1f}s] 📨 Result: {p['result']} - {p.get('reason', '')}")
                
                if "print_error" in p:
                    error = p["print_error"]
                    if error != 0:
                        error_found = True
                        error_code = error
                        print(f"\n[{elapsed:.1f}s] ❌ ERROR: {error} ({hex(error)})")
                
                if "gcode_state" in p:
                    state = p["gcode_state"]
                    if state == "RUNNING" and not running_found:
                        running_found = True
                        print(f"\n[{elapsed:.1f}s] 🎉 PRINT RUNNING!")
                    elif state == "PREPARE":
                        print(f"\n[{elapsed:.1f}s] ⏳ Preparing...")
        except:
            pass
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("bblp", ACCESS_CODE)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"\n🔌 Connecting to MQTT...")
    client.connect(PRINTER_IP, 8883, 60)
    client.loop_start()
    
    time.sleep(2)
    
    # File is in root, so use file:///filename
    file_url = f"file:///{REMOTE_FILENAME}"
    
    print_command = {
        "print": {
            "sequence_id": "0",
            "command": "project_file",
            "param": "Metadata/plate_1.gcode",
            "md5": "",
            "profile_id": "0",
            "project_id": "0",
            "subtask_id": "0",
            "task_id": "0",
            "subtask_name": REMOTE_FILENAME,
            "url": file_url,
            "timelapse": False,
            "bed_type": "auto",
            "bed_leveling": True,
            "flow_cali": False,
            "vibration_cali": False,
            "layer_inspect": False,
            "ams_mapping": [],
            "use_ams": False
        }
    }
    
    print(f"\n📤 Print command:")
    print(f"   URL: {file_url}")
    
    client.publish(f"device/{SERIAL}/request", json.dumps(print_command))
    
    print(f"\n⏳ Waiting for response...")
    
    for i in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        if error_found or running_found:
            time.sleep(5)
            break
    
    print(f"\n\n{'='*60}")
    print("RESULT:")
    print("=" * 60)
    if running_found:
        print("✅ SUCCESS! Print started!")
    elif error_found:
        print(f"❌ FAILED with error: {error_code} ({hex(error_code)})")
    else:
        print("⚠️ No state change detected - printer may need manual confirmation")
    
    client.loop_stop()
    client.disconnect()
    
    return running_found


def main():
    print("\n" + "=" * 60)
    print("FULL WORKFLOW TEST: Upload + Print")
    print("=" * 60 + "\n")
    
    # Step 1: Upload
    if not upload_file():
        print("\n❌ Upload failed, aborting")
        return
    
    # Step 2: Print
    print_file()


if __name__ == "__main__":
    main()
