"""
Debug script to test print command with detailed logging
"""
import json
import time
import ssl
import paho.mqtt.client as mqtt

# Printer settings
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
PRINTER_SERIAL = "03900D5A2402051"

# MQTT topics
TOPIC_COMMAND = f"device/{PRINTER_SERIAL}/request"
TOPIC_REPORT = f"device/{PRINTER_SERIAL}/report"

# File to print
FILENAME = "cache/added compensation, 0.16mm layer, 2 walls, 10% infill.3mf"

received_messages = []

def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected with result code {rc}")
    client.subscribe(TOPIC_REPORT)
    print(f"📡 Subscribed to: {TOPIC_REPORT}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        received_messages.append(payload)
        
        # Check for print-related fields
        if 'print' in payload:
            print_data = payload['print']
            gcode_state = print_data.get('gcode_state', 'unknown')
            error = print_data.get('print_error', 0)
            msg_code = print_data.get('msg', 0)
            command = print_data.get('command', '')
            result = print_data.get('result', '')
            
            print(f"📊 State: {gcode_state}, Error: {error}, Msg: {msg_code}")
            if command:
                print(f"   Command response: {command} -> {result}")
            if error != 0:
                print(f"   ⚠️ PRINT ERROR: {error}")
                
    except Exception as e:
        print(f"Error parsing message: {e}")

def on_disconnect(client, userdata, rc):
    print(f"❌ Disconnected with result code {rc}")

def main():
    # Create MQTT client
    client = mqtt.Client()
    client.username_pw_set("bblp", ACCESS_CODE)
    
    # SSL setup
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    client.tls_set_context(context)
    
    # Callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    # Connect
    print(f"🔌 Connecting to {PRINTER_IP}:8883...")
    client.connect(PRINTER_IP, 8883, 60)
    client.loop_start()
    
    # Wait for connection
    time.sleep(3)
    
    # Prepare print command (FDM Monster format)
    sequence_id = str(int(time.time() * 1000))
    import os
    subtask_name = os.path.basename(FILENAME)
    
    project_command = {
        "print": {
            "sequence_id": sequence_id,
            "command": "project_file",
            "param": "Metadata/plate_1.gcode",
            "md5": "",
            "profile_id": "0",
            "project_id": "0",
            "subtask_id": "0",
            "task_id": "0",
            "subtask_name": subtask_name,
            "url": f"file:///{FILENAME}",  # A1 format: file:/// without sdcard
            "bed_type": "auto",
            "timelapse": False,
            "bed_leveling": True,
            "flow_cali": False,
            "vibration_cali": False,
            "layer_inspect": False,
            "use_ams": True,
            "ams_mapping": ""
        }
    }
    
    print(f"\n🚀 Sending print command...")
    print(f"   File: {FILENAME}")
    print(f"   URL: file:///{FILENAME}")
    print(f"   Subtask: {subtask_name}")
    print(f"   Command JSON:")
    print(json.dumps(project_command, indent=2))
    
    result = client.publish(TOPIC_COMMAND, json.dumps(project_command), qos=1)
    print(f"   Publish result: {result.rc}")
    
    # Wait and monitor for responses
    print("\n⏳ Waiting for printer response (10 seconds)...")
    time.sleep(10)
    
    # Show collected messages
    print(f"\n📬 Received {len(received_messages)} messages")
    
    # Check final state
    if received_messages:
        last_msg = received_messages[-1]
        if 'print' in last_msg:
            print(f"\nFinal printer state:")
            print_data = last_msg['print']
            print(f"   gcode_state: {print_data.get('gcode_state', 'unknown')}")
            print(f"   print_error: {print_data.get('print_error', 0)}")
            print(f"   subtask_name: {print_data.get('subtask_name', '')}")
            print(f"   mc_print_stage: {print_data.get('mc_print_stage', '')}")
    
    # Cleanup
    client.loop_stop()
    client.disconnect()
    print("\n🔌 Disconnected")

if __name__ == "__main__":
    main()
