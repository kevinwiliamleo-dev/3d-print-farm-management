"""
Check current printer status
"""
import paho.mqtt.client as mqtt
import ssl
import json
import time

PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"
SERIAL = "03900D5A2402051"

def main():
    print("=" * 60)
    print("Printer Status Check")
    print("=" * 60)
    
    status_received = False
    
    def on_connect(client, userdata, flags, rc, properties=None):
        print(f"✅ Connected")
        client.subscribe(f"device/{SERIAL}/report")
    
    def on_message(client, userdata, msg):
        nonlocal status_received
        try:
            data = json.loads(msg.payload.decode())
            
            if "print" in data:
                p = data["print"]
                status_received = True
                
                print("\n📊 Printer Status:")
                print(f"   State: {p.get('gcode_state', 'N/A')}")
                print(f"   Print Stage: {p.get('mc_print_stage', 'N/A')}")
                print(f"   Subtask: {p.get('subtask_name', 'N/A')}")
                print(f"   Progress: {p.get('mc_percent', 0)}%")
                print(f"   Print Error: {p.get('print_error', 0)}")
                
                # Temperatures
                print(f"\n🌡️ Temperatures:")
                print(f"   Nozzle: {p.get('nozzle_temper', 'N/A')}°C / {p.get('nozzle_target_temper', 'N/A')}°C")
                print(f"   Bed: {p.get('bed_temper', 'N/A')}°C / {p.get('bed_target_temper', 'N/A')}°C")
                
                # HMS (Health Management System) errors
                if "hms" in p:
                    hms = p["hms"]
                    if hms:
                        print(f"\n⚠️ HMS Errors: {hms}")
                
                # Print error details
                if p.get('print_error', 0) != 0:
                    error = p['print_error']
                    print(f"\n❌ Active Error: {error} ({hex(error)})")
                        
        except Exception as e:
            pass
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("bblp", ACCESS_CODE)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print(f"\n🔌 Connecting to {PRINTER_IP}...")
    client.connect(PRINTER_IP, 8883, 60)
    client.loop_start()
    
    # Request push all data
    push_cmd = {"pushing": {"sequence_id": "0", "command": "pushall"}}
    time.sleep(2)
    client.publish(f"device/{SERIAL}/request", json.dumps(push_cmd))
    
    for i in range(10):
        time.sleep(1)
        if status_received:
            break
    
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
