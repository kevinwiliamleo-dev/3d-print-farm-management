"""
Test print the file we just uploaded
"""
import paho.mqtt.client as mqtt
import ssl
import json
import time

PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "03900D5A2402051"

# File we uploaded successfully
FILE_TO_PRINT = "test_octoprint_upload.3mf"

def main():
    print("=" * 60)
    print(f"Test Print: {FILE_TO_PRINT}")
    print("=" * 60)
    
    messages = []
    
    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"✅ MQTT Connected (rc={rc})")
        client.subscribe(f"device/{SERIAL}/report")
    
    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            messages.append(data)
            
            if "print" in data:
                print_data = data["print"]
                
                # Check for result
                if "result" in print_data:
                    print(f"\n📨 Print command result: {print_data.get('result')}")
                    if "reason" in print_data:
                        print(f"   Reason: {print_data.get('reason')}")
                
                # Check for error
                if "print_error" in print_data:
                    error = print_data["print_error"]
                    print(f"\n❌ Print error: {error} (hex: {hex(error)})")
                
                # Check gcode_state
                if "gcode_state" in print_data:
                    state = print_data["gcode_state"]
                    if state not in ["IDLE", ""]:
                        print(f"\n📊 State: {state}")
                        if state == "RUNNING":
                            print("   🎉 Print STARTED!")
        except:
            pass
    
    # Connect MQTT
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
    
    # Send print command - A1 format: file:///filename
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
            "url": f"file:///{FILE_TO_PRINT}",  # A1 format
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
    
    topic = f"device/{SERIAL}/request"
    print(f"\n📤 Sending print command...")
    print(f"   File: {FILE_TO_PRINT}")
    print(f"   URL: file:///{FILE_TO_PRINT}")
    print(f"   Topic: {topic}")
    
    client.publish(topic, json.dumps(print_command))
    
    # Wait for response
    print(f"\n⏳ Waiting for printer response...")
    time.sleep(10)
    
    print(f"\n📊 Received {len(messages)} messages")
    
    # Check last known state
    for msg in messages[-5:]:
        if "print" in msg:
            p = msg["print"]
            if "gcode_state" in p:
                print(f"   Last state: {p['gcode_state']}")
    
    client.loop_stop()
    client.disconnect()
    print("\n✅ Done")


if __name__ == "__main__":
    main()
