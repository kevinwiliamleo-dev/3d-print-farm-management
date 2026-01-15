"""
Test FTPS upload with proper SSL handling for Bambu printers
Based on OctoPrint-BambuPrinter ftps_client.py
"""
import ftplib
import ssl
import socket
import os
import json
import time
import paho.mqtt.client as mqtt

# Printer config
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
PRINTER_ID = "03900D5A2402051"

# Test file
TEST_FILE = "data/uploads/SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf"

class ImplicitTLS(ftplib.FTP_TLS):
    """FTP_TLS subclass for implicit SSL (port 990)"""
    
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


def upload_with_manual_transfer(ftp, local_path, remote_name):
    """
    Upload file using manual transfer to handle Bambu's FTPS quirks
    Based on OctoPrint-BambuPrinter implementation
    """
    file_size = os.path.getsize(local_path)
    block_size = max(file_size // 100, 8192)
    
    print(f"📤 Uploading {remote_name} ({file_size:,} bytes)")
    print(f"   Block size: {block_size:,} bytes")
    
    with open(local_path, "rb") as fp:
        # Set binary mode
        ftp.voidcmd("TYPE I")
        
        # Start transfer
        conn, size = ftp.ntransfercmd(f"STOR {remote_name}")
        
        bytes_sent = 0
        try:
            while True:
                buf = fp.read(block_size)
                if not buf:
                    break
                
                conn.sendall(buf)
                bytes_sent += len(buf)
                
                pct = (bytes_sent / file_size) * 100
                print(f"\r   Progress: {pct:.1f}% ({bytes_sent:,}/{file_size:,})", end="", flush=True)
            
            print()  # New line
            
            # CRITICAL: Shutdown SSL properly for Bambu printers
            # They don't like unwrap(), need shutdown instead
            if isinstance(conn, ssl.SSLSocket):
                try:
                    # Try shutdown first (works for Bambu)
                    conn.shutdown(socket.SHUT_RDWR)
                except Exception as e:
                    print(f"   ⚠️ Shutdown warning: {e}")
                    try:
                        conn.close()
                    except:
                        pass
            else:
                conn.close()
        
        except Exception as e:
            print(f"\n   ❌ Transfer error: {e}")
            try:
                conn.close()
            except:
                pass
            raise
        
        # Get server response to complete transfer
        try:
            resp = ftp.voidresp()
            print(f"   📋 Server: {resp}")
        except Exception as e:
            # Sometimes server doesn't respond properly but file is uploaded
            print(f"   ⚠️ Response warning (may be OK): {e}")
    
    return bytes_sent


def verify_upload(ftp, filename):
    """Verify file was uploaded correctly"""
    try:
        size = ftp.size(filename)
        print(f"   ✅ Verified on SD: {filename} ({size:,} bytes)")
        return size
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return None


print("=" * 60)
print("Bambu FTPS Upload Test (OctoPrint Method)")
print("=" * 60)

# Check file
if not os.path.exists(TEST_FILE):
    print(f"❌ File not found: {TEST_FILE}")
    exit(1)

file_size = os.path.getsize(TEST_FILE)
print(f"📄 File: {TEST_FILE}")
print(f"📄 Size: {file_size:,} bytes")

if file_size == 0:
    print("❌ File is empty!")
    exit(1)

remote_name = os.path.basename(TEST_FILE)

# Connect FTPS
print(f"\n🔌 Connecting to {PRINTER_IP}:990...")
try:
    ftp = ImplicitTLS()
    ftp.connect(PRINTER_IP, 990, timeout=60)  # Longer timeout
    print(f"✅ Connected: {ftp.welcome[:50]}...")
    
    ftp.login("bblp", ACCESS_CODE)
    print("✅ Logged in")
    
    ftp.prot_p()
    print("✅ Protected mode")
    
    # Try uploading to root first
    print(f"\n📁 Current directory: {ftp.pwd()}")
    
    # Upload
    uploaded = upload_with_manual_transfer(ftp, TEST_FILE, remote_name)
    
    if uploaded:
        # Verify
        remote_size = verify_upload(ftp, remote_name)
        
        if remote_size == 0:
            print("\n⚠️ File is 0 bytes! Trying /cache directory...")
            
            ftp.cwd("/cache")
            print(f"📁 Changed to: {ftp.pwd()}")
            
            # Upload to cache
            uploaded = upload_with_manual_transfer(ftp, TEST_FILE, remote_name)
            remote_size = verify_upload(ftp, remote_name)
    
    ftp.quit()
    print("\n✅ FTPS session closed")
    
    if remote_size and remote_size > 0:
        print(f"\n✅ Upload SUCCESS! File size on SD: {remote_size:,} bytes")
        
        # Now try print
        print("\n" + "=" * 60)
        print("Sending Print Command...")
        print("=" * 60)
        
        connected = False
        messages = []
        
        def on_connect(client, userdata, flags, rc):
            global connected
            if rc == 0:
                connected = True
                client.subscribe(f"device/{PRINTER_ID}/report")
        
        def on_message(client, userdata, msg):
            try:
                data = json.loads(msg.payload.decode())
                if "print" in data:
                    p = data["print"]
                    if any(k in p for k in ["print_error", "gcode_state", "result", "reason"]):
                        print(f"📨 {json.dumps(p, indent=2)}")
                    messages.append(data)
            except:
                pass
        
        client = mqtt.Client(client_id=f"test_{int(time.time())}", protocol=mqtt.MQTTv311)
        client.on_connect = on_connect
        client.on_message = on_message
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        client.username_pw_set("bblp", ACCESS_CODE)
        
        client.connect(PRINTER_IP, 8883, keepalive=60)
        client.loop_start()
        
        for _ in range(10):
            if connected:
                break
            time.sleep(0.5)
        
        time.sleep(1)
        
        # Try file:// URL for A1
        url = f"file:///{remote_name}"
        print(f"🚀 Print URL: {url}")
        
        print_cmd = {
            "print": {
                "sequence_id": "0",
                "command": "project_file",
                "param": "Metadata/plate_1.gcode",
                "subtask_name": remote_name,
                "url": url,
                "timelapse": False,
                "bed_leveling": True,
                "flow_cali": False,
                "vibration_cali": False,
                "layer_inspect": True,
                "use_ams": True
            }
        }
        
        client.publish(f"device/{PRINTER_ID}/request", json.dumps(print_cmd), qos=1)
        
        time.sleep(15)
        
        client.loop_stop()
        client.disconnect()
        
        print(f"\n📬 Messages: {len(messages)}")
        
    else:
        print("\n❌ Upload FAILED - file not properly saved on SD card")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
