#!/usr/bin/env python3
"""
Test Direct FTPS Upload to Bambu Lab Printer A1
Based on OctoPrint-BambuPrinter implementation
"""
import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_ftps_connection():
    """Test FTPS connection to printer"""
    logger.info("=" * 60)
    logger.info("Test 1: FTPS Connection")
    logger.info("=" * 60)
    
    from src.services.ftps_service import BambuFTPSClient
    
    PRINTER_IP = "192.168.4.101"
    ACCESS_CODE = "34782589"
    
    try:
        logger.info(f"Connecting to {PRINTER_IP}:990 (FTPS implicit SSL)...")
        
        client = BambuFTPSClient(PRINTER_IP, ACCESS_CODE)
        
        if client.connect():
            logger.info("✅ FTPS connection successful!")
            client.disconnect()
            return True
        else:
            logger.error("❌ FTPS connection failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mqtt_connection():
    """Test MQTT connection to printer"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: MQTT Connection")
    logger.info("=" * 60)
    
    from src.services.bambu_service import BambuLabMQTTClient
    
    PRINTER_IP = "192.168.4.101"
    PRINTER_SERIAL = "03900D5A2402051"
    ACCESS_CODE = "34782589"
    
    try:
        logger.info(f"Connecting to MQTT at {PRINTER_IP}:8883...")
        
        mqtt_client = BambuLabMQTTClient(
            printer_id=PRINTER_SERIAL,
            printer_ip=PRINTER_IP,
            access_code=ACCESS_CODE,
            use_lan_mode=True
        )
        
        mqtt_client.connect()
        
        # Wait for connection
        import time
        time.sleep(3)
        
        if mqtt_client.mqtt_connected:
            logger.info("✅ MQTT connection successful!")
            logger.info(f"Printer status: {mqtt_client.printer_status}")
            return True
        else:
            logger.error("❌ MQTT connection failed (timeout)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_direct_upload_and_print():
    """Test full direct upload and print workflow"""
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Direct Upload + Print (Full Workflow)")
    logger.info("=" * 60)
    
    from src.services.bambu_service import BambuLabMQTTClient
    
    PRINTER_IP = "192.168.4.101"
    PRINTER_SERIAL = "03900D5A2402051"
    ACCESS_CODE = "34782589"
    
    # Use test file if available
    TEST_FILE = PROJECT_ROOT / "data" / "uploads" / "test_model.3mf"
    
    if not TEST_FILE.exists():
        logger.warning(f"Test file not found: {TEST_FILE}")
        logger.info("Creating minimal test file...")
        
        TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        TEST_FILE.write_bytes(b"MINIMAL TEST FILE")
    
    try:
        logger.info(f"Test file: {TEST_FILE}")
        logger.info(f"File size: {TEST_FILE.stat().st_size} bytes")
        
        # Connect to printer
        mqtt_client = BambuLabMQTTClient(
            printer_id=PRINTER_SERIAL,
            printer_ip=PRINTER_IP,
            access_code=ACCESS_CODE,
            use_lan_mode=True
        )
        
        mqtt_client.connect()
        
        # Wait for MQTT
        import time
        time.sleep(2)
        
        if not mqtt_client.mqtt_connected:
            logger.error("❌ MQTT not connected")
            return False
        
        if not mqtt_client.is_printer_online():
            logger.error("❌ Printer offline")
            return False
        
        logger.info("✅ Printer online, starting direct upload...")
        logger.info("")
        logger.info("⏳ This will:")
        logger.info("  1. Upload file via FTPS to printer SD card")
        logger.info("  2. Send MQTT start command")
        logger.info("")
        
        # Skip confirmation for automated testing
        import os
        auto_test = os.environ.get('AUTO_TEST', '').lower() == 'true'
        
        if not auto_test:
            response = input("Continue? (yes/no): ").strip().lower()
            if response != "yes":
                logger.info("Cancelled by user")
                return False
        else:
            logger.info("Auto-test mode: proceeding...")
        
        # Send direct upload + print
        logger.info("Starting upload...")
        success = mqtt_client.send_print_file_direct(str(TEST_FILE))
        
        if success:
            logger.info("✅ Direct upload + print successful!")
            logger.info("Check printer LCD to see print starting...")
            return True
        else:
            logger.error("❌ Direct upload failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║  Direct FTPS Upload Test Suite                           ║")
    logger.info("║  Bambu Lab A1 Printer - No HTTP Server Required          ║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("\n")
    
    results = {
        "FTPS Connection": test_ftps_connection(),
        "MQTT Connection": test_mqtt_connection(),
        "Direct Upload + Print": test_direct_upload_and_print(),
    }
    
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{test_name:.<40} {status}")
    
    all_passed = all(results.values())
    
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✅ All tests passed!")
    else:
        logger.warning("⚠️  Some tests failed - check output above")
    logger.info("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
