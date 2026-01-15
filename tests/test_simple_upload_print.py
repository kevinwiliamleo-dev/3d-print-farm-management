"""
Simple test: Upload + Start Print (Skip verification)
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.services.bambu_service import BambuLabMQTTClient
from src.config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE

def test_direct_print():
    """Test: Upload via method yang sudah ada + start print"""
    
    print("\n" + "="*60)
    print("🧪 TEST: Direct Upload + Print")
    print("="*60)
    
    test_file = "data/uploads/test_model.3mf"
    
    if not os.path.exists(test_file):
        print(f"❌ File not found: {test_file}")
        return False
    
    print(f"\n📁 File: {test_file} ({os.path.getsize(test_file)} bytes)")
    print(f"🖨️  Printer: {BAMBU_PRINTER_IP}")
    
    try:
        # Create MQTT client
        print("\n📡 Creating MQTT client...")
        
        mqtt_client = BambuLabMQTTClient(
            printer_id="03900D5A2402051",
            printer_ip=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE,
            use_lan_mode=True
        )
        
        mqtt_client.connect()
        
        if not mqtt_client.mqtt_connected:
            print("❌ MQTT not connected")
            return False
        
        print("✅ MQTT connected!")
        
        # Use existing send_print_file_direct method
        print(f"\n📤 Uploading + starting print: {test_file}")
        
        success = mqtt_client.send_print_file_direct(test_file)
        
        if success:
            print("\n✅ Upload + print start successful!")
            print("📺 Check printer LCD to verify print started")
            
            # Wait a bit and check status
            print("\n⏳ Waiting 5 seconds to check status...")
            time.sleep(5)
            
            status = mqtt_client.get_printer_status()
            if status:
                print(f"\n📊 Printer status: {status.get('gcode_state', 'UNKNOWN')}")
            
            mqtt_client.disconnect()
            return True
        else:
            print("\n❌ Upload/print failed")
            mqtt_client.disconnect()
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 Simple Upload + Print Test\n")
    
    result = test_direct_print()
    
    print("\n" + "="*60)
    if result:
        print("✅ TEST PASSED!")
    else:
        print("❌ TEST FAILED")
    print("="*60)
