"""
Monitor printer after sending print command - longer wait
"""
import paho.mqtt.client as mqtt
import ssl
import json
import time

PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "03900D5A2402051"

FILE_TO_PRINT = "test_octoprint_upload.3mf"

def main():
    print("=" * 60)
    print(f"Print Monitor: {FILE_TO_PRINT}")
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
                if "result" in p and p.get("sequence_id") == "0":
                    print(f"\n[{elapsed:.1f}s] 📨 Command result: {p['result']} - {p.get('reason', '')}")
                
                # Print error
                if "print_error" in p:
                    error = p["print_error"]
                    if error != 0:
                        error_found = True
                        print(f"\n[{elapsed:.1f}s] ❌ PRINT ERROR: {error} (hex: {hex(error)})")
                        if error == 83935248:
                            print("         ⚠️ SD Card read/write exception!")
                        elif error == 50331905:
                            print("         ⚠️ File not found or invalid!")
                
                # State changes
                if "gcode_state" in p:
                    state = p["gcode_state"]
                    mc_print = p.get("mc_print_stage", "")
                    percent = p.get("mc_percent", 0)
                    
                    if state == "RUNNING":
                        if not running_found:
                            running_found = True
                            print(f"\n[{elapsed:.1f}s] 🎉 PRINT RUNNING! Stage: {mc_print}, Progress: {percent}%")
                    elif state == "PREPARE":
                        print(f"\n[{elapsed:.1f}s] ⏳ Preparing print...")
                    elif state == "FAILED":
                        print(f"\n[{elapsed:.1f}s] ❌ PRINT FAILED!")
                
                # Subtask name
                if "subtask_name" in p and p["subtask_name"]:
                    name = p["subtask_name"]
                    if name != "":
                        print(f"\n[{elapsed:.1f}s] 📄 Current file: {name}")
                        
        except:
            pass
    
    # Connect MQTT
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
    
    # Send print command
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
            "url": f"file:///{FILE_TO_PRINT}",
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
    
    print(f"\n📤 Sending print command for: {FILE_TO_PRINT}")
    client.publish(f"device/{SERIAL}/request", json.dumps(print_command))
    
    # Monitor for 30 seconds
    print(f"\n⏳ Monitoring for 30 seconds...")
    print("   (Press Ctrl+C to stop)")
    
    try:
        for i in range(30):
            time.sleep(1)
            print(".", end="", flush=True)
            if error_found or running_found:
                time.sleep(5)  # Extra time to see result
                break
    except KeyboardInterrupt:
        pass
    
    print(f"\n\n📊 Summary:")
    if running_found:
        print("   ✅ Print started successfully!")
    elif error_found:
        print("   ❌ Print failed with error")
    else:
        print("   ⚠️ No definitive result received")
    
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
