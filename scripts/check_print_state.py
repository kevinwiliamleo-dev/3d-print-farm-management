"""Check printer state via MQTT"""
import paho.mqtt.client as mqtt
import ssl
import json
import time

PRINTER_IP = '192.168.4.101'
ACCESS_CODE = '34782589'
SERIAL = '03900D5A2402051'

def on_connect(client, userdata, flags, rc, properties=None):
    print(f'Connected: {rc}')
    client.subscribe(f'device/{SERIAL}/report')
    client.publish(f'device/{SERIAL}/request', json.dumps({'pushing': {'command': 'pushall'}}))

def on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    if 'print' in data:
        p = data['print']
        state = p.get('gcode_state', '?')
        stage = p.get('mc_print_stage', '?')
        name = p.get('subtask_name', '?')
        pct = p.get('mc_percent', 0)
        print(f'=== PRINTER STATE ===')
        print(f'State: {state}')
        print(f'MC Print Stage: {stage}')
        print(f'Subtask Name: {name}')
        print(f'Progress: {pct}%')
        print(f'=====================')
        client.disconnect()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
client.username_pw_set('bblp', ACCESS_CODE)
client.tls_set(cert_reqs=ssl.CERT_NONE)
client.tls_insecure_set(True)
client.on_connect = on_connect
client.on_message = on_message
client.connect(PRINTER_IP, 8883, 60)
client.loop_start()
time.sleep(3)
client.loop_stop()
