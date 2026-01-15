"""
Debug script to monitor MQTT messages sent to printer
Run this alongside the server to see actual MQTT commands
"""
import json
import ssl
import time
import paho.mqtt.client as mqtt
from src.config import BAMBU_PRINTER_IP, BAMBU_PRINTER_ID, BAMBU_ACCESS_CODE

def on_connect(client, userdata, flags, rc):
    print(f"\n✅ Connected to MQTT (rc={rc})")
    # Subscribe to ALL device topics with wildcard
    all_topic = f"device/{BAMBU_PRINTER_ID}/#"
    client.subscribe(all_topic)
    print(f"📡 Subscribed to: {all_topic}")
    print("\n⏳ Waiting for MQTT messages...\n")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        
        # Check for project_file command
        if "print" in data and "command" in data.get("print", {}):
            command = data["print"]["command"]
            if command == "project_file":
                print("="*60)
                print("🖨️  PROJECT_FILE COMMAND DETECTED!")
                print("="*60)
                print(f"flow_cali: {data['print'].get('flow_cali')}")
                print(f"vibration_cali: {data['print'].get('vibration_cali')}")
                print(f"bed_leveling: {data['print'].get('bed_leveling')}")
                print(f"use_ams: {data['print'].get('use_ams')}")
                print(f"ams_mapping: {data['print'].get('ams_mapping')}")
                print(f"url: {data['print'].get('url')}")
                print(f"subtask_name: {data['print'].get('subtask_name')}")
                print("-"*60)
                print("Full command:")
                print(json.dumps(data, indent=2))
                print("="*60)
            else:
                print(f"📨 Command: {command}")
                print(json.dumps(data, indent=2))
    except:
        pass

def main():
    print("="*60)
    print("MQTT Debug Monitor")
    print("="*60)
    print(f"Printer IP: {BAMBU_PRINTER_IP}")
    print(f"Printer ID: {BAMBU_PRINTER_ID}")
    print("="*60)
    
    client = mqtt.Client()
    client.username_pw_set("bblp", BAMBU_ACCESS_CODE)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"\n🔌 Connecting to {BAMBU_PRINTER_IP}:8883...")
    client.connect(BAMBU_PRINTER_IP, 8883, 60)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n👋 Stopped")
        client.disconnect()

if __name__ == "__main__":
    main()
