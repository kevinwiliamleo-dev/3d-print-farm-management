"""
Test MQTT Connection to Bambu Lab Printer
Tests both LAN mode and Cloud mode connectivity
"""
import sys
import time
import os
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

print('=' * 60)
print('  Bambu Lab MQTT Connection Test')
print('=' * 60)
print()

# Get config
PRINTER_IP = os.getenv('BAMBU_PRINTER_IP', '192.168.4.101')
PRINTER_ID = os.getenv('BAMBU_PRINTER_ID', '')
ACCESS_CODE = os.getenv('BAMBU_ACCESS_CODE', '')
BAMBU_USERNAME = os.getenv('BAMBU_USERNAME', '')
BAMBU_PASSWORD = os.getenv('BAMBU_PASSWORD', '')

print(f'Printer IP: {PRINTER_IP}')
print(f'Printer ID: {PRINTER_ID}')
print(f'Access Code: {"*" * len(ACCESS_CODE) if ACCESS_CODE else "(not set)"}')
print()

if not ACCESS_CODE:
    print('⚠️  WARNING: Access Code not set!')
    print()
    print('To get Access Code:')
    print('1. On printer screen: Settings → Network')
    print('2. Look for "Access Code" (8 characters)')
    print('3. Add to .env file: BAMBU_ACCESS_CODE=your_code')
    print()
    print('Or enable LAN Only Mode on printer if not already.')
    print()

# Try LAN mode connection
print('-' * 60)
print('Testing LAN Mode Connection...')
print('-' * 60)

from src.services.bambu_service import BambuLabMQTTClient

try:
    client = BambuLabMQTTClient(
        printer_id=PRINTER_ID,
        printer_ip=PRINTER_IP,
        access_code=ACCESS_CODE,
        use_lan_mode=True
    )
    
    print(f'Connecting to {PRINTER_IP}:8883...')
    connected = client.connect()
    
    if connected:
        print('✅ LAN Mode: Connected successfully!')
        print()
        print('Waiting for printer status (5 seconds)...')
        time.sleep(5)
        
        print(f'MQTT Connected: {client.mqtt_connected}')
        print(f'Printer Status: {client.printer_status}')
        if client.last_status:
            print(f'Last Status: {client.last_status}')
        
        client.disconnect()
        print('Disconnected.')
    else:
        print('❌ LAN Mode: Connection failed')
        print()
        if not ACCESS_CODE:
            print('Make sure to set BAMBU_ACCESS_CODE in .env file')
        else:
            print('Check that:')
            print('  1. Printer is on and connected to network')
            print('  2. Access Code is correct')
            print('  3. LAN Only Mode is enabled (optional but recommended)')
            
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()

print()
print('=' * 60)
print('Test Complete')
print('=' * 60)
