"""
Test script to manually send print command to Bambu Lab A1
"""
import json
import time
import ssl
import paho.mqtt.client as mqtt

# Printer config
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
PRINTER_ID = "03900D5A2402051"

# File to print (must be on SD card) - Use one that exists and has size > 0
# FILENAME = "SpeedBoatRace_Bambu Pla Basic_A1_Mini.3mf"  # This is 0 bytes!
# FILENAME = "14min44s, Bambu PLA Basic, A1.3mf"  # In /cache folder

# Use file from /model folder - these have proper format
FILENAME = "3DBenchy by Creative Tool.gcode.3mf"
FILE_PATH = "/model"  # Location of the file

connected = False
messages = []

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        print(f"✅ MQTT Connected!")
        # Subscribe to get responses
        client.subscribe(f"device/{PRINTER_ID}/report")
        print(f"Subscribed to device/{PRINTER_ID}/report")
    else:
        print(f"❌ Connection failed: rc={rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        if "print" in data:
            print(f"📨 Print response: {json.dumps(data['print'], indent=2)}")
            messages.append(data)
    except:
        pass

def on_disconnect(client, userdata, rc):
    print(f"⚠️ Disconnected: rc={rc}")

print("=" * 50)
print("Bambu Lab A1 Print Test")
print("=" * 50)
print(f"IP: {PRINTER_IP}")
print(f"Printer ID: {PRINTER_ID}")
print(f"File: {FILENAME}")
print()

# Create MQTT client - Use MQTTv311 for Bambu Lab
client = mqtt.Client(
    client_id=f"test_print_{int(time.time())}",
    protocol=mqtt.MQTTv311
)

client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

# TLS setup for LAN mode
client.tls_set(cert_reqs=ssl.CERT_NONE)
client.tls_insecure_set(True)
client.username_pw_set("bblp", ACCESS_CODE)

print("🔌 Connecting to printer...")
try:
    client.connect(PRINTER_IP, 8883, keepalive=60)
    client.loop_start()
    
    # Wait for connection
    for i in range(10):
        if connected:
            break
        time.sleep(0.5)
        print(f"  Waiting... {i+1}/10")
    
    if not connected:
        print("❌ Connection timeout!")
        client.loop_stop()
        exit(1)
    
    time.sleep(1)  # Let subscription settle
    
    # Send print command
    print()
    print("🚀 Sending print command...")
    
    # For files in /model folder, use the full path
    # Format: file:///sdcard/model/filename.gcode.3mf OR file:///model/filename.gcode.3mf
    file_url = f"file:///{FILENAME}" if not FILE_PATH else f"file://{FILE_PATH}/{FILENAME}"
    
    project_command = {
        "print": {
            "sequence_id": "0",
            "command": "project_file",
            "param": "Metadata/plate_1.gcode",
            "md5": "",
            "profile_id": "0",
            "project_id": "0",
            "subtask_id": "0",
            "task_id": "0",
            "subtask_name": FILENAME,
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
    payload = json.dumps(project_command)
    
    print(f"Topic: {topic}")
    print(f"Command: {payload[:200]}...")
    
    result = client.publish(topic, payload, qos=1)
    print(f"Publish result: rc={result.rc}")
    
    # Wait for response
    print()
    print("⏳ Waiting for printer response (10 seconds)...")
    time.sleep(10)
    
    print()
    print(f"📬 Received {len(messages)} messages")
    
    client.loop_stop()
    client.disconnect()
    print("✅ Done!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
