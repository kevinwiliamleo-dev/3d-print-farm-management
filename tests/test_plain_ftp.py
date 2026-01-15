"""
Test FTP upload using plain FTP (port 21) - based on darkorb/bambu-ftp-and-print
Some Bambu printers support both plain FTP (21) and FTPS (990)
"""
import ftplib
import os
import json
import time
import ssl
import paho.mqtt.client as mqtt

# Printer config
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
PRINTER_ID = "03900D5A2402051"

# Test file
TEST_FILE = "data/uploads/SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf"

print("=" * 60)
print("Testing Plain FTP Upload (Port 21)")
print("=" * 60)

# Check if file exists and has content
if not os.path.exists(TEST_FILE):
    print(f"❌ File not found: {TEST_FILE}")
    exit(1)

file_size = os.path.getsize(TEST_FILE)
print(f"📄 Local file: {TEST_FILE}")
print(f"📄 Size: {file_size:,} bytes")

if file_size == 0:
    print("❌ File is empty!")
    exit(1)

remote_name = os.path.basename(TEST_FILE)

# Try plain FTP first
print(f"\n🔌 Trying plain FTP (port 21)...")
try:
    ftp = ftplib.FTP(PRINTER_IP, timeout=30)
    ftp.login("bblp", ACCESS_CODE)
    print(f"✅ Connected via plain FTP!")
    print(f"   Welcome: {ftp.welcome}")
    
    # List files
    print("\n📂 Files in root:")
    files = ftp.nlst()
    for f in files[:10]:
        print(f"   {f}")
    
    # Upload
    print(f"\n📤 Uploading {remote_name}...")
    with open(TEST_FILE, 'rb') as fp:
        ftp.storbinary(f"STOR {remote_name}", fp)
    
    print("✅ Upload complete!")
    
    # Verify
    try:
        uploaded_size = ftp.size(remote_name)
        print(f"📄 Uploaded file size: {uploaded_size:,} bytes")
        if uploaded_size == file_size:
            print("✅ Size matches!")
        else:
            print(f"⚠️ Size mismatch: local={file_size}, remote={uploaded_size}")
    except Exception as e:
        print(f"⚠️ Cannot verify size: {e}")
    
    ftp.quit()
    
except Exception as e:
    print(f"❌ Plain FTP failed: {e}")
    print("\n🔌 Trying FTPS (port 990) with storbinary...")
    
    # Try FTPS with simpler approach
    try:
        from ftplib import FTP_TLS
        
        class ImplicitFTPS(FTP_TLS):
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
        
        ftp = ImplicitFTPS()
        ftp.connect(PRINTER_IP, 990, timeout=30)
        ftp.login("bblp", ACCESS_CODE)
        ftp.prot_p()
        print(f"✅ Connected via FTPS!")
        
        # Try to change to cache directory first
        try:
            ftp.cwd("/cache")
            print("📁 Changed to /cache directory")
        except:
            print("📁 Staying in root directory")
        
        # Upload using simple storbinary
        print(f"\n📤 Uploading {remote_name} using storbinary...")
        with open(TEST_FILE, 'rb') as fp:
            result = ftp.storbinary(f"STOR {remote_name}", fp, blocksize=8192)
            print(f"   Result: {result}")
        
        print("✅ Upload complete!")
        
        # Verify
        try:
            uploaded_size = ftp.size(remote_name)
            print(f"📄 Uploaded file size: {uploaded_size:,} bytes")
        except Exception as e:
            print(f"⚠️ Cannot verify size: {e}")
        
        ftp.quit()
        
    except Exception as e2:
        print(f"❌ FTPS also failed: {e2}")
        import traceback
        traceback.print_exc()
        exit(1)

print("\n" + "=" * 60)
print("Now testing print command...")
print("=" * 60)

# Send print command
connected = False
messages = []

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        print("✅ MQTT Connected!")
        client.subscribe(f"device/{PRINTER_ID}/report")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        if "print" in data:
            p = data["print"]
            # Only show relevant info
            if "print_error" in p or "gcode_state" in p or "result" in p:
                print(f"📨 {p}")
            messages.append(data)
    except:
        pass

client = mqtt.Client(client_id=f"test_{int(time.time())}", protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_message = on_message
client.tls_set(cert_reqs=ssl.CERT_NONE)
client.tls_insecure_set(True)
client.username_pw_set("bblp", ACCESS_CODE)

try:
    client.connect(PRINTER_IP, 8883, keepalive=60)
    client.loop_start()
    
    for i in range(10):
        if connected:
            break
        time.sleep(0.5)
    
    if not connected:
        print("❌ MQTT timeout!")
        exit(1)
    
    time.sleep(1)
    
    # Print command - using ftp:// URL like darkorb repo
    print_cmd = {
        "print": {
            "sequence_id": "0",
            "command": "project_file",
            "param": "Metadata/plate_1.gcode",
            "subtask_name": remote_name,
            "url": f"ftp://{remote_name}",  # Try ftp:// protocol
            "timelapse": False,
            "bed_leveling": True,
            "flow_cali": False,
            "vibration_cali": False,
            "layer_inspect": True,
            "use_ams": True
        }
    }
    
    print(f"\n🚀 Sending print command with URL: ftp://{remote_name}")
    client.publish(f"device/{PRINTER_ID}/request", json.dumps(print_cmd), qos=1)
    
    time.sleep(10)
    
    # If that failed, try file:// URL
    has_error = any("print_error" in str(m) and m.get("print", {}).get("print_error", 0) != 0 for m in messages)
    
    if has_error:
        print("\n⚠️ ftp:// URL failed, trying file:// URL...")
        messages.clear()
        
        print_cmd["print"]["url"] = f"file:///{remote_name}"
        print(f"🚀 Sending print command with URL: file:///{remote_name}")
        client.publish(f"device/{PRINTER_ID}/request", json.dumps(print_cmd), qos=1)
        
        time.sleep(10)
    
    client.loop_stop()
    client.disconnect()
    
    print(f"\n📬 Total messages: {len(messages)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
