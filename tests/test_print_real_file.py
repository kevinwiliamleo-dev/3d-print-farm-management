"""
Test print a REAL file from cache folder
"""
import paho.mqtt.client as mqtt
import ssl
import json
import time

PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "03900D5A2402051"

# Real file from cache with gcode - using the smallest one
FILE_TO_PRINT = "14min44s, Bambu PLA Basic, A1.3mf"

def main():
    print("=" * 60)
    print(f"Print Test: {FILE_TO_PRINT}")
    print("=" * 60)
    
    start_time = time.time()
    error_found = False
    running_found = False
    
    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"✅ MQTT Connected")
        client.subscribe(f"device/{SERIAL}/report")
    
    def on_message(client, userdata, msg):
        nonlocal error_found, running_found
        try:
            data = json.loads(msg.payload.decode())
            
            if "print" in data:
                p = data["print"]
                elapsed = time.time() - start_time
                
                # Result from print command
                if "result" in p:
                    result = p['result']
                    reason = p.get('reason', '')
                    print(f"\n[{elapsed:.1f}s] 📨 Result: {result} - {reason}")
                
                # Print error
                if "print_error" in p:
                    error = p["print_error"]
                    if error != 0:
                        error_found = True
                        print(f"\n[{elapsed:.1f}s] ❌ ERROR: {error} ({hex(error)})")
                
                # State changes
                if "gcode_state" in p:
                    state = p["gcode_state"]
                    percent = p.get("mc_percent", 0)
                    
                    if state == "RUNNING":
                        if not running_found:
                            running_found = True
                            print(f"\n[{elapsed:.1f}s] 🎉 PRINT RUNNING! {percent}%")
                    elif state == "PREPARE":
                        print(f"\n[{elapsed:.1f}s] ⏳ Preparing...")
                    elif state == "FAILED":
                        print(f"\n[{elapsed:.1f}s] ❌ FAILED!")
                        
        except:
            pass
    
    # Connect MQTT
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("bblp", ACCESS_CODE)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"\n🔌 Connecting...")
    client.connect(PRINTER_IP, 8883, 60)
    client.loop_start()
    
    time.sleep(2)
    
    # Use cache/ prefix because file is in cache folder
    file_url = f"file:///cache/{FILE_TO_PRINT}"
    
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
            "subtask_name": FILE_TO_PRINT,
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
    
    print(f"\n📤 Sending print command:")
    print(f"   File: {FILE_TO_PRINT}")
    print(f"   URL: {file_url}")
    
    client.publish(f"device/{SERIAL}/request", json.dumps(print_command))
    
    print(f"\n⏳ Monitoring...")
    
    try:
        for i in range(30):
            time.sleep(1)
            print(".", end="", flush=True)
            if error_found or running_found:
                time.sleep(5)
                break
    except KeyboardInterrupt:
        pass
    
    print(f"\n\n📊 Result:")
    if running_found:
        print("   ✅ SUCCESS! Print started!")
    elif error_found:
        print("   ❌ FAILED with error")
    else:
        print("   ⚠️ No state change detected")
    
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
