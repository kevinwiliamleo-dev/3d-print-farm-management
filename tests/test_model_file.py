"""
Test print file from /model folder (factory files)
These files should work if SD card read is still OK
"""
import json
import time
import ssl
import paho.mqtt.client as mqtt

PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
PRINTER_ID = "03900D5A2402051"

# Use factory file from /model folder
# Format is different: namafile.gcode.3mf
FILENAME = "3DBenchy by Creative Tool.gcode.3mf"

print("=" * 60)
print("Test Print from /model folder")
print("=" * 60)
print(f"File: {FILENAME}")
print()

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
            # Show relevant fields
            relevant = {}
            for k in ["print_error", "gcode_state", "result", "reason", "mc_percent", 
                      "subtask_name", "print_type", "nozzle_temper", "bed_temper"]:
                if k in p:
                    relevant[k] = p[k]
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

try:
    client.connect(PRINTER_IP, 8883, keepalive=60)
    client.loop_start()
    
    for _ in range(10):
        if connected:
            break
        time.sleep(0.5)
    
    if not connected:
        print("❌ Connection timeout!")
        exit(1)
    
    time.sleep(1)
    
    # For files in /model, try different URL formats
    # Based on OctoPrint-BambuPrinter: A1 uses file:/// 
    
    # Try 1: Direct file URL (root)
    url = f"file:///{FILENAME}"
    
    print(f"\n🚀 Attempt 1: {url}")
    
    print_cmd = {
        "print": {
            "sequence_id": "0",
            "command": "project_file",
            "param": "Metadata/plate_1.gcode",
            "subtask_name": FILENAME,
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
    time.sleep(10)
    
    # Check if still getting error
    has_error = any(
        m.get("print", {}).get("print_error", 0) != 0 
        for m in messages
    )
    
    if has_error:
        print(f"\n⚠️ Still getting SD card error!")
        print("The SD card needs to be fixed first.")
        print("\nOptions:")
        print("1. Format SD card via printer menu")
        print("2. Remove SD card and format on computer (FAT32)")
        print("3. Replace with new SD card (SanDisk/Samsung, max 32GB)")
    else:
        # Check if print started
        is_printing = any(
            m.get("print", {}).get("gcode_state") == "RUNNING"
            for m in messages
        )
        if is_printing:
            print("\n✅ Print started successfully!")
        else:
            print("\n📋 No error, but print may not have started")
    
    client.loop_stop()
    client.disconnect()
    
    print(f"\n📬 Total messages: {len(messages)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
