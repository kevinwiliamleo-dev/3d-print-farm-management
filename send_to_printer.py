#!/usr/bin/env python3
"""
Send file from output folder to printer and start print
Usage: python send_to_printer.py [filename] [printer_id]
Example: python send_to_printer.py test.gcode.3mf bambu-a1-001
"""

import sys
import os
from pathlib import Path
from src.config import OUTPUT_DIR, BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE, BAMBU_PRINTER_ID
from src.services.ftps_service import BambuFTPSClient
from src.services.bambu_service import BambuLabMQTTClient
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def send_to_printer(filename: str, printer_id: str = None):
    """
    Send file from output folder to printer and start print
    
    Args:
        filename: File in data/3mf_output/ (e.g., "test.gcode.3mf")
        printer_id: Target printer ID (default: BAMBU_PRINTER_ID from config)
    """
    
    if not printer_id:
        printer_id = BAMBU_PRINTER_ID
    
    # Build file path
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        print(f"\n📁 Files in {OUTPUT_DIR}:")
        for f in OUTPUT_DIR.glob("*"):
            print(f"   - {f.name}")
        return False
    
    file_size = file_path.stat().st_size / (1024 * 1024)  # MB
    print(f"\n📤 Sending file to printer...")
    print(f"   File: {filename}")
    print(f"   Size: {file_size:.2f} MB")
    print(f"   Printer: {printer_id}")
    print(f"   IP: {BAMBU_PRINTER_IP}")
    
    # ==================== UPLOAD VIA FTPS ====================
    try:
        print(f"\n1️⃣  Uploading to printer SD card...")
        
        ftps_client = BambuFTPSClient(
            host=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE,
            port=990,
            timeout=60
        )
        
        with ftps_client as ftp:
            # Upload file
            remote_filename = filename
            
            def progress_callback(bytes_sent: int, total_bytes: int):
                percent = int((bytes_sent / total_bytes) * 100) if total_bytes > 0 else 0
                print(f"   Upload: {percent}% ({bytes_sent}/{total_bytes})", end='\r')
            
            upload_success = ftp.upload_file(
                str(file_path), 
                remote_filename, 
                progress_callback
            )
            
            if not upload_success:
                print(f"\n❌ Failed to upload file")
                return False
            
            print(f"\n✅ Upload complete: {remote_filename}")
        
    except Exception as e:
        print(f"❌ FTPS upload failed: {e}")
        return False
    
    # ==================== START PRINT VIA MQTT ====================
    try:
        print(f"\n2️⃣  Starting print via MQTT...")
        
        mqtt_client = BambuLabMQTTClient(
            printer_id=printer_id,
            printer_ip=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE,
            use_lan_mode=True,
            timeout=10,  # 10 second timeout
        )
        
        # Try to connect with timeout handling
        try:
            connected = mqtt_client.connect()
        except Exception as mqtt_err:
            print(f"⚠️  MQTT connection error: {mqtt_err}")
            connected = False
        
        if not connected:
            print(f"\n⚠️  MQTT connection failed (timeout/network issue)")
            print(f"\n✅ File upload was successful!")
            print(f"\n📋 Alternatives to start print:")
            print(f"   1. Manual: Open printer web panel at http://{BAMBU_PRINTER_IP}")
            print(f"   2. Manual: Select file: {remote_filename}")
            print(f"   3. Manual: Click 'Print'")
            print(f"\n   OR use API: curl -X POST http://{BAMBU_PRINTER_IP}/api/v1/print")
            return True  # Return True because upload succeeded
        
        print(f"✅ Connected to printer (MQTT)")
        
        # Start print
        if not mqtt_client.start_print(remote_filename):
            print(f"⚠️  MQTT start print command failed")
            mqtt_client.disconnect()
            # Still return True since upload succeeded
            return True
        
        print(f"✅ Print started!")
        print(f"\n🖨️  Printer is now printing: {remote_filename}")
        
        # Keep connection alive for a moment to ensure command is processed
        import time
        time.sleep(2)
        
        mqtt_client.disconnect()
        
        return True
        
    except Exception as e:
        print(f"⚠️  MQTT error: {e}")
        print(f"\n✅ File upload succeeded, but MQTT connection failed")
        print(f"📋 Please start print manually from printer web panel: http://{BAMBU_PRINTER_IP}")
        return True  # Return True because upload succeeded

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n📋 Usage: python send_to_printer.py <filename> [printer_id]")
        print("\n📁 Files in output folder:")
        for f in OUTPUT_DIR.glob("*"):
            print(f"   - {f.name}")
        print("\n💡 Example:")
        print("   python send_to_printer.py test.gcode.3mf")
        print("   python send_to_printer.py test.gcode.3mf bambu-a1-001")
        sys.exit(1)
    
    filename = sys.argv[1]
    printer_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = send_to_printer(filename, printer_id)
    sys.exit(0 if success else 1)
