"""
Complete test: Upload file and print via MQTT
Based on OctoPrint-BambuPrinter and darkorb/bambu-ftp-and-print
"""
import json
import time
import ssl
import socket
import ftplib
import os
import paho.mqtt.client as mqtt
from pathlib import Path

# Printer config
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
PRINTER_ID = "03900D5A2402051"
DEVICE_TYPE = "A1"  # A1, P1P, P1S, X1, X1C

# Test file - use a local file
TEST_FILE = "data/uploads/SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf"

# ============= FTPS Implementation =============
class ImplicitTLS(ftplib.FTP_TLS):
    """FTP_TLS sub-class for implicit SSL (port 990)"""
    
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


def upload_file_to_printer(local_path: str, remote_filename: str) -> bool:
    """
    Upload file to Bambu printer using FTPS
    Implementation from OctoPrint-BambuPrinter
    """
    print(f"\n📤 FTPS Upload")
    print("=" * 50)
    
    if not os.path.exists(local_path):
        print(f"❌ File not found: {local_path}")
        return False
    
    file_size = os.path.getsize(local_path)
    print(f"📄 Local file: {local_path} ({file_size:,} bytes)")
    print(f"📄 Remote name: {remote_filename}")
    
    try:
        # Create FTPS connection with implicit SSL
        ftp = ImplicitTLS()
        ftp.set_debuglevel(0)
        
        # Connect
        print(f"\n🔌 Connecting to {PRINTER_IP}:990...")
        ftp.connect(host=PRINTER_IP, port=990, timeout=30)
        print(f"✅ Connected: {ftp.welcome[:50]}...")
        
        # Login
        ftp.login(user="bblp", passwd=ACCESS_CODE)
        print("✅ Logged in as bblp")
        
        # Enable protected data transfer
        ftp.prot_p()
        print("✅ Protected mode enabled")
        
        # Check current directory
        pwd = ftp.pwd()
        print(f"📁 Current directory: {pwd}")
        
        # List existing files
        print("\n📂 Files in root:")
        root_files = ftp.nlst()
        for f in root_files:
            if '.3mf' in f.lower():
                try:
                    size = ftp.size(f)
                    print(f"   📄 {f} ({size:,} bytes)")
                except:
                    print(f"   📄 {f}")
        
        # Upload file using STORBINARY
        print(f"\n📤 Uploading {remote_filename}...")
        
        block_size = max(file_size // 100, 8192)
        bytes_sent = 0
        
        with open(local_path, "rb") as fp:
            # Set binary mode
            ftp.voidcmd("TYPE I")
            
            # Start transfer
            conn, size = ftp.ntransfercmd(f"STOR {remote_filename}")
            
            try:
                while True:
                    buf = fp.read(block_size)
                    if not buf:
                        break
                    
                    conn.sendall(buf)
                    bytes_sent += len(buf)
                    
                    # Progress
                    pct = (bytes_sent / file_size) * 100
                    print(f"\r   Progress: {pct:.1f}% ({bytes_sent:,}/{file_size:,} bytes)", end="")
                
                print()  # New line
                
                # Shutdown SSL layer - CRITICAL for Bambu printers
                if ftplib._SSLSocket is not None and isinstance(conn, ftplib._SSLSocket):
                    # Bambu printers need shutdown, not unwrap
                    try:
                        conn.shutdown(socket.SHUT_RDWR)
                    except:
                        pass
                
                conn.close()
                
            finally:
                # Get server response - CRITICAL to complete transfer
                try:
                    resp = ftp.voidresp()
                    print(f"   📋 Server response: {resp}")
                except Exception as e:
                    print(f"   ⚠️ Response error (may be OK): {e}")
        
        # Verify upload by listing again
        print(f"\n📂 Verifying upload...")
        try:
            uploaded_size = ftp.size(remote_filename)
            print(f"✅ File on printer: {remote_filename} ({uploaded_size:,} bytes)")
            
            if uploaded_size == 0:
                print("❌ WARNING: File is 0 bytes on printer!")
                return False
            elif uploaded_size != file_size:
                print(f"⚠️ Size mismatch: local={file_size}, remote={uploaded_size}")
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
        
        ftp.quit()
        print("✅ Upload complete!")
        return True
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_print_command(filename: str) -> bool:
    """
    Send print command via MQTT
    """
    print(f"\n🖨️ MQTT Print Command")
    print("=" * 50)
    
    connected = False
    messages = []
    
    def on_connect(client, userdata, flags, rc):
        nonlocal connected
        if rc == 0:
            connected = True
            print("✅ MQTT Connected!")
            client.subscribe(f"device/{PRINTER_ID}/report")
        else:
            print(f"❌ Connection failed: rc={rc}")

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            if "print" in data:
                print(f"📨 Response: {json.dumps(data['print'], indent=2)}")
                messages.append(data)
        except:
            pass

    # Create MQTT client
    client = mqtt.Client(
        client_id=f"print_test_{int(time.time())}",
        protocol=mqtt.MQTTv311
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    # TLS setup
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.username_pw_set("bblp", ACCESS_CODE)
    
    print(f"🔌 Connecting to MQTT {PRINTER_IP}:8883...")
    
    try:
        client.connect(PRINTER_IP, 8883, keepalive=60)
        client.loop_start()
        
        # Wait for connection
        for i in range(10):
            if connected:
                break
            time.sleep(0.5)
        
        if not connected:
            print("❌ Connection timeout!")
            return False
        
        time.sleep(1)
        
        # Build print command
        # URL format differs by printer type:
        # X1/X1C: "file:///mnt/sdcard/filename.3mf"
        # A1/P1P/P1S: "file:///filename.3mf"
        
        if DEVICE_TYPE in ["X1", "X1C"]:
            file_url = f"file:///mnt/sdcard/{filename}"
        else:
            # A1, P1P, P1S
            file_url = f"file:///{filename}"
        
        print(f"📄 File URL: {file_url}")
        
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
                "subtask_name": filename,
                "url": file_url,
                "bed_type": "auto",
                "timelapse": False,
                "bed_leveling": True,
                "flow_cali": False,
                "vibration_cali": False,
                "layer_inspect": True,
                "use_ams": True,
                "ams_mapping": ""
            }
        }
        
        topic = f"device/{PRINTER_ID}/request"
        payload = json.dumps(print_command)
        
        print(f"\n🚀 Sending print command...")
        print(f"   Topic: {topic}")
        
        result = client.publish(topic, payload, qos=1)
        print(f"   Publish rc={result.rc}")
        
        # Wait for response
        print("\n⏳ Waiting for response (15 seconds)...")
        time.sleep(15)
        
        print(f"\n📬 Received {len(messages)} messages")
        
        # Check for errors
        for msg in messages:
            if "print" in msg:
                if msg["print"].get("print_error", 0) != 0:
                    print(f"❌ Print error: {msg['print'].get('print_error')}")
                if msg["print"].get("gcode_state") == "RUNNING":
                    print("✅ Print started successfully!")
        
        client.loop_stop()
        client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Bambu Lab Upload & Print Test")
    print("=" * 60)
    print(f"Printer: {PRINTER_IP} ({DEVICE_TYPE})")
    print(f"Serial: {PRINTER_ID}")
    print()
    
    # Check test file
    if not os.path.exists(TEST_FILE):
        print(f"❌ Test file not found: {TEST_FILE}")
        print("\nLooking for available .3mf files...")
        
        # Find any .3mf file
        for root, dirs, files in os.walk("data/uploads"):
            for f in files:
                if f.endswith(".3mf"):
                    full_path = os.path.join(root, f)
                    size = os.path.getsize(full_path)
                    print(f"   📄 {full_path} ({size:,} bytes)")
        return
    
    file_size = os.path.getsize(TEST_FILE)
    if file_size == 0:
        print(f"❌ Test file is empty: {TEST_FILE}")
        return
    
    print(f"📄 Test file: {TEST_FILE} ({file_size:,} bytes)")
    
    # Generate remote filename
    remote_name = Path(TEST_FILE).name
    
    # Upload
    if upload_file_to_printer(TEST_FILE, remote_name):
        # Print
        send_print_command(remote_name)
    else:
        print("\n❌ Upload failed, skipping print command")


if __name__ == "__main__":
    main()
