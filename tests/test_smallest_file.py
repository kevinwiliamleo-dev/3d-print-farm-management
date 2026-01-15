"""
Find the smallest file on SD card and print it
"""
import json
import time
import ssl
import socket
import ftplib
import paho.mqtt.client as mqtt

PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
PRINTER_ID = "03900D5A2402051"

class ImplicitTLS(ftplib.FTP_TLS):
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

print("=" * 60)
print("Find Smallest File and Print")
print("=" * 60)

# Connect FTPS to list files
print("\n📂 Connecting to list files...")
ftp = ImplicitTLS()
ftp.connect(PRINTER_IP, 990, timeout=30)
ftp.login("bblp", ACCESS_CODE)
ftp.prot_p()

all_files = []

# List /model folder (factory files - best quality)
print("\n📁 /model folder:")
try:
    ftp.cwd("/model")
    for name in ftp.nlst():
        if name.endswith('.3mf'):
            try:
                size = ftp.size(name)
                if size and size > 0:
                    all_files.append({"name": name, "size": size, "path": "/model"})
                    print(f"   📄 {name} ({size:,} bytes)")
            except:
                pass
except Exception as e:
    print(f"   Error: {e}")

# List /cache folder
print("\n📁 /cache folder:")
try:
    ftp.cwd("/cache")
    for name in ftp.nlst():
        if name.endswith('.3mf') and not name.endswith('.gcode'):
            try:
                size = ftp.size(name)
                if size and size > 0:
                    all_files.append({"name": name, "size": size, "path": "/cache"})
                    print(f"   📄 {name} ({size:,} bytes)")
            except:
                pass
except Exception as e:
    print(f"   Error: {e}")

ftp.quit()

if not all_files:
    print("\n❌ No valid .3mf files found!")
    exit(1)

# Find smallest file
smallest = min(all_files, key=lambda x: x["size"])
print(f"\n✅ Smallest file: {smallest['name']}")
print(f"   Size: {smallest['size']:,} bytes")
print(f"   Path: {smallest['path']}")

# Now print it
print("\n" + "=" * 60)
print("Sending Print Command...")
print("=" * 60)

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
            relevant = {k: p[k] for k in ["print_error", "gcode_state", "result", "reason", 
                        "mc_percent", "subtask_name", "nozzle_temper", "bed_temper"] if k in p}
            if relevant:
                print(f"📨 {relevant}")
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

# Build URL based on path
filename = smallest["name"]
if smallest["path"] == "/model":
    # Model files use format: file:///model/filename.gcode.3mf
    url = f"file:///model/{filename}"
else:
    # Cache files: file:///cache/filename.3mf  
    url = f"file:///cache/{filename}"

print(f"\n🚀 Print URL: {url}")

print_cmd = {
    "print": {
        "sequence_id": "0",
        "command": "project_file",
        "param": "Metadata/plate_1.gcode",
        "subtask_name": filename,
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

print("\n⏳ Waiting for response (15 seconds)...")
time.sleep(15)

client.loop_stop()
client.disconnect()

# Summary
print(f"\n📬 Messages received: {len(messages)}")

has_error = any(m.get("print", {}).get("print_error", 0) != 0 for m in messages)
if has_error:
    print("\n⚠️ SD Card error detected! Please format SD card first.")
else:
    is_printing = any(m.get("print", {}).get("gcode_state") == "RUNNING" for m in messages)
    if is_printing:
        print("\n✅ Print started successfully!")
