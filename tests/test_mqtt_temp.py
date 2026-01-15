"""
Test script to debug MQTT temperature data from Bambu Lab printer
"""
import json
import ssl
import time
import paho.mqtt.client as mqtt
from src.config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE, BAMBU_PRINTER_ID

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    # Subscribe to all topics
    topic = f"device/{BAMBU_PRINTER_ID}/report"
    client.subscribe(topic)
    print(f"Subscribed to: {topic}")
    
    # Request status push
    request_topic = f"device/{BAMBU_PRINTER_ID}/request"
    push_request = {
        "pushing": {
            "sequence_id": "0",
            "command": "pushall"
        }
    }
    client.publish(request_topic, json.dumps(push_request))
    print(f"Requested pushall on: {request_topic}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        
        # Check for print data with temperature
        if "print" in payload:
            print_data = payload.get("print", {})
            
            # Look for temperature fields
            nozzle = print_data.get("nozzle_temper")
            bed = print_data.get("bed_temper")
            chamber = print_data.get("chamber_temper")
            gcode_state = print_data.get("gcode_state")
            
            if nozzle is not None or bed is not None:
                print(f"\n=== TEMPERATURE DATA ===")
                print(f"Nozzle: {nozzle}°C (target: {print_data.get('nozzle_target_temper')})")
                print(f"Bed: {bed}°C (target: {print_data.get('bed_target_temper')})")
                print(f"Chamber: {chamber}°C")
                print(f"State: {gcode_state}")
                print(f"========================\n")
            else:
                # Print some keys to understand structure
                keys = list(print_data.keys())[:15]
                print(f"Print data keys (no temp): {keys}")
        else:
            # Print top-level keys
            keys = list(payload.keys())
            print(f"Message keys (no print): {keys}")
            
    except json.JSONDecodeError:
        print(f"Failed to decode: {msg.payload[:100]}")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print(f"Connecting to printer at {BAMBU_PRINTER_IP}")
    print(f"Printer ID: {BAMBU_PRINTER_ID}")
    
    # Create client with callback API version
    try:
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    except TypeError:
        client = mqtt.Client()
    
    client.username_pw_set("bblp", BAMBU_ACCESS_CODE)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(BAMBU_PRINTER_IP, 8883, 60)
        print("Starting MQTT loop... Press Ctrl+C to stop")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        client.disconnect()
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    main()
