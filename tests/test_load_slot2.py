"""
Manual Load Filament Test - Track MQTT Progress
Load slot 2 and watch all MQTT data during the operation
"""
import json
import ssl
import time
import paho.mqtt.client as mqtt

# Printer configuration
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "AC1F20C170104873"

# Track state
start_time = None
last_data = {}
command_sent = False

def on_connect(client, userdata, flags, rc):
    global start_time, command_sent
    if rc == 0:
        print(f"✅ Connected to printer")
        topic = f"device/{SERIAL}/report"
        client.subscribe(topic)
        print(f"📡 Subscribed to: {topic}")
        
        if not command_sent:
            command_sent = True
            # Send load command for slot 2 (tray_id = 2)
            print("\n" + "="*60)
            print("🔄 SENDING LOAD COMMAND FOR SLOT 2...")
            print("="*60 + "\n")
            
            load_cmd = {
                "print": {
                    "sequence_id": "12345",
                    "command": "ams_change_filament",
                    "target": 2,  # Slot 2
                    "curr_temp": 220,
                    "tar_temp": 220
                }
            }
            
            cmd_topic = f"device/{SERIAL}/request"
            client.publish(cmd_topic, json.dumps(load_cmd))
            print(f"✅ Load command sent to slot 2")
            start_time = time.time()
            print("\nWatching MQTT data... (Ctrl+C to stop)\n")
    else:
        print(f"❌ Connection failed: {rc}")

def on_message(client, userdata, msg):
    global last_data, start_time
    
    try:
        payload = json.loads(msg.payload.decode())
        
        if "print" in payload:
            print_data = payload["print"]
            elapsed = time.time() - start_time if start_time else 0
            
            # Key fields to track
            fields = {
                "gcode_state": print_data.get("gcode_state"),
                "mc_print_stage": print_data.get("mc_print_stage"),
                "mc_print_sub_stage": print_data.get("mc_print_sub_stage"),
                "mc_print_error_code": print_data.get("mc_print_error_code"),
                "hw_switch_state": print_data.get("hw_switch_state"),
                "ams_status": print_data.get("ams_status"),
                "nozzle_temper": print_data.get("nozzle_temper"),
                "nozzle_target_temper": print_data.get("nozzle_target_temper"),
            }
            
            # AMS data
            ams = print_data.get("ams", {})
            if ams:
                fields["tray_now"] = ams.get("tray_now")
                fields["tray_tar"] = ams.get("tray_tar")
            
            # Only print if something changed
            changed = {}
            for k, v in fields.items():
                if v is not None and (k not in last_data or last_data[k] != v):
                    changed[k] = v
                    last_data[k] = v
            
            if changed:
                print(f"[{elapsed:6.1f}s] {changed}")
                
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("="*60)
    print("MANUAL LOAD FILAMENT TEST - SLOT 2")
    print("="*60)
    print(f"Printer: {PRINTER_IP}")
    print(f"Target Slot: 2")
    print()
    
    # Use newer callback API version
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.username_pw_set("bblp", ACCESS_CODE)
    client.on_connect = on_connect
    client.on_message = on_message
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    client.tls_set_context(ssl_context)
    
    try:
        client.connect(PRINTER_IP, 8883, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
