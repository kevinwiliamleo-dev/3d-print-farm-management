"""
Test script to monitor AMS loading/unloading MQTT messages from printer.
Run this BEFORE triggering load/unload to see what data the printer sends.
"""
import json
import ssl
import time
import paho.mqtt.client as mqtt

# Printer configuration (from PRINTER_DISCOVERY_GUIDE.md)
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "AC1F20C170104873"  # Get from printer info or discovery

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Connected to printer at {PRINTER_IP}")
        # Subscribe to all device topics
        topic = f"device/{SERIAL}/report"
        client.subscribe(topic)
        print(f"📡 Subscribed to: {topic}")
    else:
        print(f"❌ Connection failed with code: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        
        # Only process print messages (they contain AMS data)
        if "print" in payload:
            print_data = payload["print"]
            
            # Key fields for AMS loading/unloading
            fields_to_watch = [
                "hw_switch_state",
                "mc_print_sub_stage", 
                "mc_print_stage",
                "ams_status",
                "gcode_state",
                "nozzle_temper",
                "nozzle_target_temper",
            ]
            
            # Get AMS specific data
            ams = print_data.get("ams", {})
            tray_now = ams.get("tray_now", "?")
            tray_tar = ams.get("tray_tar", "?")
            
            # Print status line
            status_parts = []
            for field in fields_to_watch:
                if field in print_data:
                    status_parts.append(f"{field}={print_data[field]}")
            
            if tray_now != "?" or tray_tar != "?":
                status_parts.append(f"tray_now={tray_now}")
                status_parts.append(f"tray_tar={tray_tar}")
            
            if status_parts:
                print(f"📊 {time.strftime('%H:%M:%S')} | {', '.join(status_parts)}")
            
    except Exception as e:
        print(f"Error parsing message: {e}")

def main():
    print("=" * 60)
    print("AMS Loading/Unloading MQTT Monitor")
    print("=" * 60)
    print(f"Printer: {PRINTER_IP}")
    print(f"Serial: {SERIAL}")
    print()
    print("Instructions:")
    print("1. Keep this script running")
    print("2. Go to the web UI and click Load or Unload on AMS slot")
    print("3. Watch the MQTT messages here to see what printer sends")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Setup MQTT client
    client = mqtt.Client()
    client.username_pw_set("bblp", ACCESS_CODE)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # SSL context for Bambu Lab
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    client.tls_set_context(ssl_context)
    
    try:
        client.connect(PRINTER_IP, 8883, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
