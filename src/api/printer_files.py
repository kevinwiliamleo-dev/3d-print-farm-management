"""
Printer File Management API
List and manage files on printer SD card via FTPS
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.config import BAMBU_PRINTER_ID, BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE
from src.services.bambu_service import BambuLabMQTTClient
from src.services.ftps_service import BambuFTPSClient, PrinterFileInfo
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/printer-files", tags=["printer-files"])

# Global MQTT client instance
_bambu_client = None


def get_bambu_mqtt_client():
    """Get or create global MQTT client instance"""
    global _bambu_client
    
    if _bambu_client is None:
        if BAMBU_PRINTER_IP and BAMBU_ACCESS_CODE:
            logger.info(f"Initializing MQTT client in LAN mode: {BAMBU_PRINTER_IP}")
            _bambu_client = BambuLabMQTTClient(
                printer_id=BAMBU_PRINTER_ID,
                printer_ip=BAMBU_PRINTER_IP,
                access_code=BAMBU_ACCESS_CODE,
                use_lan_mode=True,
            )
            try:
                if not _bambu_client.mqtt_connected:
                    _bambu_client.connect()
            except Exception as e:
                logger.warning(f"MQTT connection failed: {e}")
    
    return _bambu_client


@router.get("/list")
async def list_printer_files():
    """
    List all files on printer SD card
    
    Returns list of files with details:
    - name: filename
    - size: file size in bytes
    - is_3mf: true if .3mf file
    - is_gcode: true if .gcode file
    - size_mb: file size in MB
    
    Example response:
    {
        "printer_id": "03900D5A2402051",
        "printer_ip": "192.168.1.100",
        "files": [
            {
                "name": "SpeedBoatRace.3mf",
                "size": 3145728,
                "size_mb": 3.0,
                "is_3mf": true,
                "is_gcode": false
            }
        ],
        "total_files": 1,
        "status": "success"
    }
    """
    try:
        # Get or initialize MQTT client
        mqtt_client = get_bambu_mqtt_client()
        
        # Try to get actual files from FTPS
        files = []
        try:
            ftps_client = BambuFTPSClient(
                host=BAMBU_PRINTER_IP,
                access_code=BAMBU_ACCESS_CODE,
                port=990,
                timeout=30
            )
            
            with ftps_client as ftp:
                printer_files = ftp.list_files()
                files = [f.to_dict() for f in printer_files]
                logger.info(f"Retrieved {len(files)} files from FTPS")
        except Exception as ftps_err:
            logger.warning(f"FTPS list failed: {ftps_err}, returning empty list")
            files = []
        
        logger.info(f"Returning {len(files)} files from SD card")
        
        return {
            "printer_id": BAMBU_PRINTER_ID,
            "printer_ip": BAMBU_PRINTER_IP,
            "files": files,
            "total_files": len(files),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error listing printer files: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/print/{filename:path}")
async def print_from_sd_card(
    filename: str,
    use_ams: bool = True,
    ams_slot: int = 0,
    flow_cali: bool = False,
    vibration_cali: bool = False,  # Always False - settings from slicer
    bed_leveling: bool = True,
    timelapse: bool = False
):
    """
    Start printing a file from printer SD card
    
    Uses project_file command like FDM Monster for proper Bambu Lab protocol.
    
    Args:
        filename: Name of file on SD card (e.g., "model.3mf" or "cache/model.3mf")
        use_ams: Whether to use AMS (default True)
        ams_slot: AMS slot number 0-3 (default 0 = first slot)
        flow_cali: Whether to run flow/extrusion calibration (default True)
        vibration_cali: Whether to run vibration calibration (default True)
        bed_leveling: Whether to run bed leveling (default True)
        timelapse: Whether to record timelapse (default False)
    
    Returns: Print job info
    """
    try:
        from urllib.parse import unquote
        
        # Decode URL-encoded filename
        filename = unquote(filename)
        
        # Validate filename
        if not filename or len(filename) == 0:
            raise HTTPException(status_code=400, detail="Filename required")
        
        # Only allow .3mf or .gcode files
        allowed_ext = (".3mf", ".gcode", ".g")
        if not filename.lower().endswith(allowed_ext):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {allowed_ext}"
            )
        
        mqtt_client = get_bambu_mqtt_client()
        
        # Check if printer online
        if not mqtt_client or not mqtt_client.mqtt_connected:
            logger.warning("Printer status unknown (MQTT not connected), attempting to connect...")
            try:
                mqtt_client.connect()
            except Exception as e:
                logger.warning(f"Connection attempt failed: {e}")
        
        logger.info(f"🚀 Starting print from SD card: {filename}")
        logger.info(f"   Options: flow_cali={flow_cali}, vibration_cali={vibration_cali}, bed_leveling={bed_leveling}")
        logger.info(f"   AMS: use_ams={use_ams}, ams_slot={ams_slot}")
        
        # Use start_print_from_sd which sends proper project_file command
        # Like FDM Monster's bambu-mqtt.adapter.ts startPrint()
        # CRITICAL: Pass ams_slot as integer, it will be converted to proper list format
        success = mqtt_client.start_print_from_sd(
            filename=filename,
            use_ams=use_ams,
            plate_number=1,
            ams_mapping=None,  # Let bambu_service convert from ams_slot
            ams_slot=ams_slot,
            flow_cali=flow_cali,
            vibration_cali=vibration_cali,
            bed_leveling=bed_leveling,
            layer_inspect=False,
            timelapse=timelapse
        )
        
        if success:
            logger.info(f"✅ Print started from SD card: {filename}")
            return {
                "status": "success",
                "message": f"Print started from SD card: {filename}",
                "filename": filename
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send print command")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error printing from SD card: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filename}")
async def delete_printer_file(filename: str):
    """
    Delete a file from printer SD card via FTPS
    
    Args:
        filename: Name of file to delete (can include path like "cache/file.3mf")
    
    Returns: Success message
    """
    try:
        if not filename or len(filename) == 0:
            raise HTTPException(status_code=400, detail="Filename required")
        
        # Determine location
        location = "cache" if filename.startswith("cache/") else "root"
        display_name = filename.split("/")[-1]  # Get just the filename without path
        logger.info(f"🗑️ Deleting file from SD card ({location}): {filename}")
        
        # Create FTPS client and delete file
        try:
            ftps_client = BambuFTPSClient(
                host=BAMBU_PRINTER_IP,
                access_code=BAMBU_ACCESS_CODE,
                port=990,
                timeout=30
            )
            
            with ftps_client as ftp:
                success = ftp.delete_file(filename)
                
                if success:
                    logger.info(f"✅ File deleted successfully from {location}: {filename}")
                    return {
                        "status": "success",
                        "message": f"Successfully deleted from {location} directory: {display_name}",
                        "filename": filename,
                        "location": location,
                        "display_name": display_name
                    }
                else:
                    logger.error(f"Failed to delete file: {filename}")
                    raise HTTPException(status_code=500, detail=f"Failed to delete file: {filename}")
        except Exception as ftps_err:
            logger.error(f"FTPS delete error: {ftps_err}")
            raise HTTPException(status_code=500, detail=f"Delete failed: {str(ftps_err)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
