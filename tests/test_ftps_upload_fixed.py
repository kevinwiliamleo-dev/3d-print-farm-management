"""
Test FTPS Upload with Fixed Implementation
Based on OctoPrint-BambuPrinter implementation
"""
import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.services.ftps_service import BambuFTPSClient
from src.services.bambu_service import BambuLabMQTTClient
from src.config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE

def progress_callback(bytes_sent, total_size):
    """Progress callback"""
    percent = (bytes_sent / total_size) * 100
    print(f"  📊 Progress: {percent:.1f}% ({bytes_sent}/{total_size} bytes)", end="\r")

def test_ftps_upload():
    """Test FTPS upload with new implementation"""
    
    print("\n" + "="*60)
    print("🧪 TEST: FTPS Upload (Fixed Implementation)")
    print("="*60)
    
    # Test file
    test_file = "data/uploads/test_model.3mf"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    print(f"\n📁 Test file: {test_file}")
    print(f"📏 File size: {os.path.getsize(test_file)} bytes")
    print(f"🖨️  Target printer: {BAMBU_PRINTER_IP}")
    
    try:
        print("\n🔌 Connecting to FTPS...")
        
        with BambuFTPSClient(
            host=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE,
            port=990,
            timeout=30
        ) as client:
            
            print("✅ FTPS connected!\n")
            
            # List existing files
            print("📋 Listing existing files on SD card...")
            files = client.list_files()
            print(f"   Found {len(files)} files: {files[:5]}..." if len(files) > 5 else f"   Found {len(files)} files: {files}")
            
            # Upload test
            remote_name = "test_fixed_upload.3mf"
            print(f"\n📤 Uploading as: {remote_name}")
            
            success = client.upload_file(
                local_path=test_file,
                remote_filename=remote_name,
                progress_callback=progress_callback
            )
            
            if success:
                print(f"\n✅ FTPS upload successful!")
                
                # Verify uploaded
                print("\n📋 Verifying upload...")
                files_after = client.list_files()
                if remote_name in files_after or remote_name in [f.split("/")[-1] for f in files_after]:
                    print(f"✅ File verified on SD card: {remote_name}")
                    return True
                else:
                    print(f"⚠️ File not found in listing after upload")
                    return False
            else:
                print(f"\n❌ Upload failed")
                return False
                
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_workflow():
    """Test full workflow: FTPS upload + MQTT start"""
    
    print("\n" + "="*60)
    print("🧪 TEST: Full Workflow (Upload + Print Start)")
    print("="*60)
    
    test_file = "data/uploads/test_model.3mf"
    remote_name = "test_full_workflow.3mf"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    print(f"\n📁 Test file: {test_file}")
    print(f"🖨️  Target printer: {BAMBU_PRINTER_IP}")
    
    try:
        # Step 1: Upload via FTPS
        print("\n📤 STEP 1: Uploading via FTPS...")
        
        with BambuFTPSClient(
            host=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE
        ) as client:
            
            success = client.upload_file(
                local_path=test_file,
                remote_filename=remote_name,
                progress_callback=progress_callback
            )
            
            if not success:
                print(f"\n❌ Upload failed")
                return False
            
            print(f"\n✅ Upload complete!")
        
        # Step 2: Wait for printer to register file
        print("\n⏳ STEP 2: Waiting 2 seconds for printer to register file...")
        time.sleep(2)
        
        # Step 3: Send print command via MQTT
        print("\n📡 STEP 3: Sending print command via MQTT...")
        
        mqtt_client = BambuLabMQTTClient(
            printer_id="03900D5A2402051",
            printer_ip=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE,
            use_lan_mode=True
        )
        
        mqtt_client.connect()
        
        if not mqtt_client.is_connected():
            print("❌ MQTT connection failed")
            return False
        
        print("✅ MQTT connected!")
        
        # Send start command
        print(f"\n🚀 Sending print start command for: {remote_name}")
        
        # Build print command
        from pybambu import commands
        
        PRINT_COMMAND = {
            "print": {
                "sequence_id": 0,
                "command": "project_file",
                "param": "Metadata/plate_1.gcode",
                "subtask_name": remote_name,
                "url": f"file:///{remote_name}",  # A1 uses file:/// not file:///mnt/sdcard/
                "timelapse": False,
                "bed_leveling": True,
                "flow_cali": False,
                "vibration_cali": False,
                "layer_inspect": False,
                "use_ams": False
            }
        }
        
        mqtt_client._bambu_client.publish(PRINT_COMMAND)
        print("✅ Print command sent!")
        
        print("\n" + "="*60)
        print("✅ FULL WORKFLOW TEST COMPLETE!")
        print("="*60)
        print("\n📝 Check printer LCD to verify print started")
        
        mqtt_client.disconnect()
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 FTPS Upload Tests - Fixed Implementation")
    print("Based on OctoPrint-BambuPrinter plugin\n")
    
    # Test 1: Simple FTPS upload
    result1 = test_ftps_upload()
    
    # Test 2: Full workflow
    if result1:
        print("\n\n")
        result2 = test_full_workflow()
    else:
        result2 = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"  FTPS Upload Test:     {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"  Full Workflow Test:   {'✅ PASS' if result2 else '❌ FAIL'}")
    print("="*60)
    
    if result1 and result2:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  Some tests failed")
