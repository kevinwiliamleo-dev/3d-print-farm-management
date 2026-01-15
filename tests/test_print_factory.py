"""
Test print factory file from /model folder (the SpeedBoatRace)
These files have proper .gcode.3mf format
"""
import paho.mqtt.client as mqtt
import ssl
import json
import time

PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "03900D5A2402051"

# Factory file from /model folder - these should always work
FILE_TO_PRINT = "SpeedBoatRace_Bambu Pla Basic.gcode.3mf"

def main():
    print("=" * 60)
    print(f"Print Factory File: {FILE_TO_PRINT}")
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
                
                # Result
                if "result" in p:
                    print(f"\n[{elapsed:.1f}s] 📨 Result: {p['result']} - {p.get('reason', '')}")
                
                # Error
                if "print_error" in p:
                    error = p["print_error"]
                    if error != 0:
                        error_found = True
                        error_code = error
                        print(f"\n[{elapsed:.1f}s] ❌ ERROR: {error} ({hex(error)})")
                
                # State
                if "gcode_state" in p:
                    state = p["gcode_state"]
                    if state == "RUNNING" and not running_found:
                        running_found = True
                        print(f"\n[{elapsed:.1f}s] 🎉 RUNNING!")
                    elif state == "PREPARE":
                        print(f"\n[{elapsed:.1f}s] ⏳ Preparing...")
                        
        except:
            pass
    
    # Connect
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
    
    # For /model files, use model/ prefix
    file_url = f"file:///model/{FILE_TO_PRINT}"
    
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
    
    print(f"\n📤 URL: {file_url}")
    client.publish(f"device/{SERIAL}/request", json.dumps(print_command))
    
    print(f"\n⏳ Waiting...")
    
    for i in range(30):
        time.sleep(1)
        print(".", end="", flush=True)
        if error_found or running_found:
            time.sleep(5)
            break
    
    print(f"\n\n📊 Result:")
    if running_found:
        print("   ✅ Print started!")
    elif error_found:
        print(f"   ❌ Error: {error_code} ({hex(error_code)})")
    else:
        print("   ⚠️ No change")
    
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
