"""
Print the uploaded SpeedBoatRace file
"""
import paho.mqtt.client as mqtt
import ssl
import json
import time

PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "03900D5A2402051"

# File we just uploaded successfully
FILE_TO_PRINT = "SpeedBoatRace_Upload.3mf"

def main():
    print("=" * 60)
    print(f"Print: {FILE_TO_PRINT}")
    print("=" * 60)
    
    start_time = time.time()
    error_found = False
    running_found = False
    preparing_found = False
    error_code = 0
    
    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"✅ MQTT Connected")
        client.subscribe(f"device/{SERIAL}/report")
    
    def on_message(client, userdata, msg):
        nonlocal error_found, running_found, preparing_found, error_code
        try:
            data = json.loads(msg.payload.decode())
            if "print" in data:
                p = data["print"]
                elapsed = time.time() - start_time
                
                if "result" in p:
                    result = p['result']
                    reason = p.get('reason', '')
                    print(f"\n[{elapsed:.1f}s] 📨 Result: {result} - {reason}")
                
                if "print_error" in p:
                    error = p["print_error"]
                    if error != 0:
                        error_found = True
                        error_code = error
                        print(f"\n[{elapsed:.1f}s] ❌ ERROR: {error} ({hex(error)})")
                        if error == 83935248:
                            print("         SD Card read/write exception")
                
                if "gcode_state" in p:
                    state = p["gcode_state"]
                    mc_percent = p.get("mc_percent", 0)
                    subtask = p.get("subtask_name", "")
                    
                    if state == "RUNNING":
                        if not running_found:
                            running_found = True
                            print(f"\n[{elapsed:.1f}s] 🎉 PRINTING! File: {subtask}, Progress: {mc_percent}%")
                    elif state == "PREPARE":
                        if not preparing_found:
                            preparing_found = True
                            print(f"\n[{elapsed:.1f}s] ⏳ Preparing to print...")
                    elif state == "IDLE" and preparing_found:
                        print(f"\n[{elapsed:.1f}s] ⚠️ Returned to IDLE")
        except:
            pass
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("bblp", ACCESS_CODE)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"\n🔌 Connecting to MQTT at {PRINTER_IP}:8883...")
    client.connect(PRINTER_IP, 8883, 60)
    client.loop_start()
    
    time.sleep(2)
    
    # For A1: file:///filename (not file:///mnt/sdcard/)
    file_url = f"file:///{FILE_TO_PRINT}"
    
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
    
    print(f"\n⏳ Monitoring (60 seconds max)...")
    
    for i in range(60):
        time.sleep(1)
        if not (i % 10):
            print(f".", end="", flush=True)
        if error_found or running_found:
            time.sleep(5)
            break
    
    print(f"\n\n{'='*60}")
    print("RESULT:")
    print("=" * 60)
    
    if running_found:
        print("✅ SUCCESS! Print started!")
        print("   Printer is now printing the SpeedBoat model.")
    elif error_found:
        print(f"❌ FAILED with error: {error_code} ({hex(error_code)})")
        if error_code == 83935248:
            print("   SD Card read/write exception - SD card may need replacement")
    elif preparing_found:
        print("⏳ Printer entered PREPARE state but didn't start printing")
        print("   Check printer screen for any prompts or errors")
    else:
        print("⚠️ No state change detected")
        print("   Possible reasons:")
        print("   - Printer requires confirmation on screen")
        print("   - File format may not be compatible")
        print("   - Check printer screen for any messages")
    
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
