#!/usr/bin/env python3
"""
Send file from output folder to printer and start print (Simple Version)
Usage: python send_to_printer_simple.py [filename]
Example: python send_to_printer_simple.py test.gcode.3mf
"""

import sys
import os
from pathlib import Path
from src.config import OUTPUT_DIR, BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE, BAMBU_PRINTER_ID
from src.services.ftps_service import BambuFTPSClient
from src.services.bambu_service import BambuLabMQTTClient
import logging
import time

logging.basicConfig(
    level=logging.WARNING  # Suppress debug logs
)
logger = logging.getLogger(__name__)

def send_to_printer(filename: str):
    """Send file to printer and start print"""
    
    # Build file path
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        print(f"\n📁 Files in {OUTPUT_DIR}:")
        for f in OUTPUT_DIR.glob("*"):
            print(f"   - {f.name}")
        return False
    
    file_size = file_path.stat().st_size / (1024 * 1024)  # MB
    
    print(f"\n╔════════════════════════════════════════╗")
    print(f"║    SENDING FILE TO PRINTER             ║")
    print(f"╚════════════════════════════════════════╝")
    print(f"\n📋 File Info:")
    print(f"   Filename: {filename}")
    print(f"   Size: {file_size:.2f} MB")
    print(f"   Path: {file_path}")
    
    print(f"\n🖨️  Printer Info:")
    print(f"   Printer ID: {BAMBU_PRINTER_ID}")
    print(f"   IP Address: {BAMBU_PRINTER_IP}")
    
    # ==================== UPLOAD VIA FTPS ====================
    print(f"\n{'='*40}")
    print(f"STEP 1: Upload to Printer SD Card")
    print(f"{'='*40}")
    
    try:
        ftps_client = BambuFTPSClient(
            host=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE,
            port=990,
            timeout=60
        )
        
        with ftps_client as ftp:
            remote_filename = filename
            bytes_uploaded = 0
            
            def progress_callback(bytes_sent: int, total_bytes: int):
                percent = int((bytes_sent / total_bytes) * 100) if total_bytes > 0 else 0
                bar_len = 30
                filled = int(bar_len * percent / 100)
                bar = '█' * filled + '░' * (bar_len - filled)
                print(f"\r📤 [{bar}] {percent}% ({bytes_sent}/{total_bytes} bytes)", end='', flush=True)
            
            upload_success = ftp.upload_file(
                str(file_path), 
                remote_filename, 
                progress_callback
            )
            
            if not upload_success:
                print(f"\n❌ Upload failed!")
                return False
            
            print(f"\n✅ Upload complete!")
        
    except Exception as e:
        print(f"\n❌ FTPS error: {e}")
        return False
    
    # ==================== START PRINT VIA MQTT ====================
    print(f"\n{'='*40}")
    print(f"STEP 2: Start Print")
    print(f"{'='*40}")
    
    try:
        print(f"🔌 Connecting to printer (MQTT)...")
        
        mqtt_client = BambuLabMQTTClient(
            printer_id=BAMBU_PRINTER_ID,
            printer_ip=BAMBU_PRINTER_IP,
            access_code=BAMBU_ACCESS_CODE,
            use_lan_mode=True,
            auto_reconnect=False  # Don't auto-reconnect for this script
        )
        
        # Try to connect with short timeout
        mqtt_client.MQTT_CONNECT_TIMEOUT = 5  # 5 second timeout
        
        if mqtt_client.connect():
            print(f"✅ Connected!")
            print(f"🖨️  Starting print: {remote_filename}")
            
            # Start print from SD card
            # File is at /cache/{filename} on printer
            if mqtt_client.start_print_from_sd(remote_filename, use_ams=True):
                print(f"✅ Print command sent!")
                print(f"\n🎉 SUCCESS! Printer is now printing: {remote_filename}")
                time.sleep(1)
                mqtt_client.disconnect()
                return True
            else:
                print(f"⚠️  Print command failed")
                mqtt_client.disconnect()
                return False
        else:
            print(f"⚠️  MQTT connection failed (timeout/network issue)")
            print(f"\n✅ File upload succeeded!")
            print(f"\n📋 Alternative: Start print manually from printer web panel:")
            print(f"   1. Open: http://{BAMBU_PRINTER_IP}")
            print(f"   2. Go to: Files")
            print(f"   3. Find: {remote_filename}")
            print(f"   4. Click: Print")
            return True
        
    except Exception as e:
        print(f"⚠️  Error: {e}")
        print(f"\n✅ File upload succeeded!")
        print(f"📋 Please start print manually from printer web panel: http://{BAMBU_PRINTER_IP}")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"\n📋 Usage: python send_to_printer_simple.py <filename>")
        print(f"\n📁 Available files in output folder:")
        for f in OUTPUT_DIR.glob("*"):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   - {f.name} ({size_mb:.2f} MB)")
        print(f"\n💡 Example:")
        print(f"   python send_to_printer_simple.py test.gcode.3mf")
        sys.exit(1)
    
    filename = sys.argv[1]
    success = send_to_printer(filename)
    sys.exit(0 if success else 1)
