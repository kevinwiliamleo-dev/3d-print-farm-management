"""
Printer API Routes - Handle printer management and control
Follows naming conventions from README.md
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from src.database import get_db
from src.services.printer_service import PrinterService
from src.services.discovery_service import discovery_service, check_mqtt_status
from src.config import BAMBU_ACCESS_CODE, BAMBU_PRINTER_ID, BAMBU_PRINTER_IP
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/printers", tags=["printers"])


class CreatePrinterRequest(BaseModel):
    """Request to register new printer"""
    printer_id: str
    printer_name: str
    serial_number: str = None  # Actual Bambu serial for MQTT topics (e.g. '03900D5A2402051')


class UpdatePrinterStatusRequest(BaseModel):
    """Request to update printer status"""
    printer_status: str


class UpdateSerialNumberRequest(BaseModel):
    """Request to update printer serial number (for MQTT topic fix)"""
    serial_number: str


@router.post("", status_code=201)
async def register_printer(
    request: CreatePrinterRequest,
    db: Session = Depends(get_db)
):
    """
    Register new printer
    
    - **printer_id**: Unique printer identifier (serial number)
    - **printer_name**: Display name for printer
    
    Returns: printer_id, printer_name, status, mqtt_connected
    """
    try:
        printer_service = PrinterService(db)
        printer = printer_service.create_printer(
            request.printer_id,
            request.printer_name,
            serial_number=request.serial_number
        )
        
        if printer is None:
            raise HTTPException(
                status_code=400,
                detail=f"Printer already exists: printer_id={request.printer_id}"
            )
        
        logger.info(f"Registered printer: printer_id={request.printer_id}, serial={request.serial_number}, printer_name={request.printer_name}")
        
        return printer
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering printer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_all_printers(db: Session = Depends(get_db)):
    """
    Get all registered printers
    
    Returns: List of all printers with status and mqtt_connected
    """
    try:
        printer_service = PrinterService(db)
        printers = printer_service.get_all_printers()
        
        return {
            "total": len(printers),
            "printers": printers
        }
    except Exception as e:
        logger.error(f"Error fetching printers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}")
async def get_printer(printer_id: str, db: Session = Depends(get_db)):
    """Get printer details by printer_id"""
    try:
        printer_service = PrinterService(db)
        printer = printer_service.get_printer_by_id(printer_id)
        
        if not printer:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        return printer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching printer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{printer_id}/status")
async def update_printer_status(
    printer_id: str,
    request: UpdatePrinterStatusRequest,
    db: Session = Depends(get_db)
):
    """
    Update printer status
    
    - **printer_status**: idle | printing | offline
    """
    try:
        # Validate status
        valid_statuses = ["idle", "printing", "offline"]
        if request.printer_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )
        
        printer_service = PrinterService(db)
        success = printer_service.update_printer_status(printer_id, request.printer_status)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        logger.info(f"Updated printer status: printer_id={printer_id}, status={request.printer_status}")
        
        return {"message": f"Updated printer status: {request.printer_status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating printer status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{printer_id}/serial")
async def update_printer_serial(
    printer_id: str,
    request: UpdateSerialNumberRequest,
    db: Session = Depends(get_db)
):
    """
    Update printer serial number (used for MQTT topics)
    
    ⚠️ PENTING: serial_number harus berupa actual Bambu serial, bukan IP-based ID.
    Contoh: '03900D5A2402051' (bukan 'BAMBU_192_168_4_101')
    
    Setelah update, restart container agar MQTT reconnect dengan serial yang benar.
    """
    try:
        from src.database.db import Printer
        printer = db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if not printer:
            raise HTTPException(status_code=404, detail=f"Printer not found: {printer_id}")
        
        old_serial = printer.serial_number
        printer.serial_number = request.serial_number
        db.commit()
        
        logger.info(f"Updated serial_number: printer_id={printer_id}, {old_serial} → {request.serial_number}")
        
        return {
            "message": "Serial number updated. Restart container untuk apply perubahan MQTT.",
            "printer_id": printer_id,
            "old_serial_number": old_serial,
            "new_serial_number": request.serial_number
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating serial: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{printer_id}/auto-continue")
async def toggle_auto_continue(
    printer_id: str,
    auto_continue: bool,
    db: Session = Depends(get_db)
):
    """
    Toggle auto-continue setting for printer
    
    When enabled (True): Automatically start next job after current job completes
    When disabled (False): Wait for manual 'Start Next Job' click after completion
    
    Args:
        printer_id: Printer identifier
        auto_continue: True to enable auto-continue, False to disable
    
    Returns:
        Updated printer with auto_continue status
    """
    try:
        from src.database.db import Printer
        
        printer = db.query(Printer).filter(Printer.printer_id == printer_id).first()
        
        if not printer:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        printer.auto_continue = auto_continue
        db.commit()
        db.refresh(printer)
        
        status_text = "enabled" if auto_continue else "disabled"
        logger.info(f"✅ Auto-continue {status_text} for printer {printer_id}")
        
        return {
            "printer_id": printer_id,
            "auto_continue": auto_continue,
            "message": f"Auto-continue {status_text}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling auto-continue: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{printer_id}/mqtt")
async def update_mqtt_status(
    printer_id: str,
    mqtt_connected: bool,
    db: Session = Depends(get_db)
):
    """Update MQTT connection status for printer"""
    try:
        printer_service = PrinterService(db)
        success = printer_service.update_mqtt_connection(printer_id, mqtt_connected)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        logger.info(f"Updated mqtt_connected: printer_id={printer_id}, mqtt_connected={mqtt_connected}")
        
        return {
            "printer_id": printer_id,
            "mqtt_connected": mqtt_connected
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating MQTT status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/reconnect")
async def reconnect_printer(printer_id: str, db: Session = Depends(get_db)):
    """
    Force MQTT reconnection for a printer
    
    This resets the connection state and forces a new MQTT connection attempt.
    """
    try:
        from src.services.bambu_service import bambu_clients
        
        printer_service = PrinterService(db)
        printer = printer_service.get_printer_by_id(printer_id)
        
        if not printer:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        logger.info(f"Force reconnecting printer {printer_id}...")
        
        # If client exists, reset its connection state and trigger reconnect
        if printer_id in bambu_clients:
            client = bambu_clients[printer_id]
            # Reset reconnect attempts to allow fresh connection
            if client.connection_state:
                client.connection_state.reconnect_attempts = 0
            # Disconnect and reconnect
            try:
                client.disconnect()
            except:
                pass
            # Trigger new connection
            success = client.connect()
            
            if success:
                printer_service.update_mqtt_connection(printer_id, True)
                return {
                    "printer_id": printer_id,
                    "success": True,
                    "message": "Reconnection successful"
                }
        
        # No client exists or reconnect failed, try fresh connection via refresh
        printer_ip = BAMBU_PRINTER_IP or os.getenv("BAMBU_PRINTER_IP", "")
        access_code = BAMBU_ACCESS_CODE or os.getenv("BAMBU_ACCESS_CODE", "")
        
        if printer_ip and access_code:
            mqtt_status = check_mqtt_status(printer_ip, access_code, printer_id, timeout=10.0)
            
            if mqtt_status.get("mqtt_connected"):
                printer_service.update_mqtt_connection(printer_id, True)
                return {
                    "printer_id": printer_id,
                    "success": True,
                    "message": "Reconnection successful"
                }
        
        return {
            "printer_id": printer_id,
            "success": False,
            "message": "Could not reconnect. Printer may be offline."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reconnecting printer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}/online")
async def check_printer_online(printer_id: str, db: Session = Depends(get_db)):
    """Check if printer is online (mqtt_connected and not offline)"""
    try:
        printer_service = PrinterService(db)
        is_online = printer_service.is_printer_online(printer_id)
        
        return {
            "printer_id": printer_id,
            "is_online": is_online
        }
    except Exception as e:
        logger.error(f"Error checking printer online status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}/idle")
async def check_printer_idle(printer_id: str, db: Session = Depends(get_db)):
    """Check if printer is idle (ready to print)"""
    try:
        printer_service = PrinterService(db)
        is_idle = printer_service.is_printer_idle(printer_id)
        
        return {
            "printer_id": printer_id,
            "is_idle": is_idle
        }
    except Exception as e:
        logger.error(f"Error checking printer idle status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/refresh")
async def refresh_printer_status(printer_id: str, db: Session = Depends(get_db)):
    """
    Refresh printer status by connecting to MQTT and getting real-time status
    
    This connects to the printer via MQTT to get the actual current status
    (idle, printing, paused, etc.) and updates the database.
    """
    try:
        printer_service = PrinterService(db)
        printer = printer_service.get_printer_by_id(printer_id)
        
        if not printer:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        # Get printer IP and access code
        printer_ip = BAMBU_PRINTER_IP or os.getenv("BAMBU_PRINTER_IP", "")
        access_code = BAMBU_ACCESS_CODE or os.getenv("BAMBU_ACCESS_CODE", "")
        
        if not printer_ip:
            raise HTTPException(
                status_code=400,
                detail="BAMBU_PRINTER_IP not configured in .env"
            )
        
        if not access_code:
            raise HTTPException(
                status_code=400,
                detail="BAMBU_ACCESS_CODE not configured in .env"
            )
        
        logger.info(f"Refreshing status for printer {printer_id} at {printer_ip}...")
        
        # Check MQTT status
        mqtt_status = check_mqtt_status(printer_ip, access_code, printer_id, timeout=8.0)
        
        if mqtt_status.get("mqtt_connected"):
            # Update printer status in database
            new_status = mqtt_status.get("status", "idle")
            printer_service.update_printer_status(printer_id, new_status)
            printer_service.update_mqtt_connection(printer_id, True)
            
            return {
                "printer_id": printer_id,
                "status": new_status,
                "mqtt_connected": True,
                "printing": mqtt_status.get("printing", False),
                "progress": mqtt_status.get("progress", 0),
                "message": f"Printer is {new_status}"
            }
        else:
            # Could not connect, mark as offline
            printer_service.update_printer_status(printer_id, "offline")
            printer_service.update_mqtt_connection(printer_id, False)
            
            return {
                "printer_id": printer_id,
                "status": "offline",
                "mqtt_connected": False,
                "message": "Could not connect to printer via MQTT. Check access code and network."
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing printer status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{printer_id}")
async def delete_printer(printer_id: str, db: Session = Depends(get_db)):
    """Delete printer registration"""
    try:
        printer_service = PrinterService(db)
        success = printer_service.delete_printer(printer_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        logger.info(f"Deleted printer: printer_id={printer_id}")
        
        return {"message": f"Deleted printer: printer_id={printer_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting printer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover/scan")
async def discover_printers_on_network():
    """
    Scan local network for Bambu Lab printers (auto-discovery)
    
    Returns: List of discovered printers with printer_id, printer_name, ip_address
    """
    try:
        logger.info("Starting network discovery scan...")
        discovered = discovery_service.scan_network()
        
        return {
            "total": len(discovered),
            "printers": discovered,
            "message": f"Found {len(discovered)} Bambu Lab printer(s) on network"
        }
    except Exception as e:
        logger.error(f"Error scanning network: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover/async")
async def start_async_discovery():
    """
    Start async network discovery in background
    Call /discover/results to get discovered printers
    """
    try:
        logger.info("Starting async network discovery...")
        discovery_service.clear_discovered()
        discovery_service.discover_async()
        
        return {
            "message": "Network discovery started in background",
            "status": "scanning"
        }
    except Exception as e:
        logger.error(f"Error starting async discovery: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover/results")
async def get_discovery_results():
    """Get results from async discovery"""
    try:
        printers = discovery_service.get_discovered_printers()
        
        return {
            "total": len(printers),
            "printers": printers,
            "is_discovering": discovery_service.is_discovering
        }
    except Exception as e:
        logger.error(f"Error getting discovery results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lookup-by-id/{printer_id}")
async def lookup_printer_by_id(printer_id: str):
    """
    Lookup printer by ID on network
    
    Tries to find printer on local network by searching for:
    - mDNS hostname: BambuLab_{printer_id}.local
    - Or just lookup the IP address directly
    """
    try:
        import socket
        
        # Try mDNS hostname first
        hostname_patterns = [
            f"BambuLab_{printer_id}.local",
            f"bambu-{printer_id}.local",
            printer_id,
        ]
        
        for hostname in hostname_patterns:
            try:
                ip = socket.gethostbyname(hostname)
                logger.info(f"Found printer {printer_id} at {ip}")
                
                return {
                    "found": True,
                    "printer_id": printer_id,
                    "ip_address": ip,
                    "hostname": hostname,
                    "message": f"Found printer at {ip}"
                }
            except socket.gaierror:
                pass
        
        # If not found, return helpful error message
        return {
            "found": False,
            "printer_id": printer_id,
            "message": f"Could not find printer {printer_id} on network. Make sure it's powered on and connected to WiFi.",
            "hint": f"Try accessing: http://BambuLab_{printer_id}.local or check your printer's IP in router settings"
        }
    except Exception as e:
        logger.error(f"Error looking up printer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class DiscoverByIPRequest(BaseModel):
    """Request to discover printer by IP"""
    ip_address: str


@router.post("/discover/by-ip")
async def discover_printer_by_ip(request: DiscoverByIPRequest):
    """
    Try to discover Bambu Lab printer at specific IP address
    
    Use this if auto-discovery doesn't work.
    You can find your printer's IP in:
    - Router admin page (DHCP leases)
    - Printer display settings > Network
    - Bambu Handy app
    """
    try:
        logger.info(f"Discovering printer at {request.ip_address}...")
        
        result = discovery_service.discover_by_ip(request.ip_address)
        
        if result:
            return {
                "found": True,
                "printer": result,
                "message": f"Found printer at {request.ip_address}"
            }
        else:
            return {
                "found": False,
                "ip_address": request.ip_address,
                "message": f"No Bambu Lab printer found at {request.ip_address}. Check that the printer is on and connected to the same network."
            }
    except Exception as e:
        logger.error(f"Error discovering by IP: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover/status")
async def get_discovery_status():
    """Get current discovery status and found printers"""
    try:
        return discovery_service.get_discovery_status()
    except Exception as e:
        logger.error(f"Error getting discovery status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AMS (Automatic Material System) Endpoints
# ============================================================================

@router.get("/{printer_id}/ams")
async def get_ams_status(printer_id: str, db: Session = Depends(get_db)):
    """
    Get AMS (Automatic Material System) status for a printer.
    
    Returns information about all AMS trays including:
    - slot: Tray slot number (0-3 for AMS Lite)
    - empty: Whether tray is empty
    - type: Filament type (PLA, ABS, PETG, etc.)
    - color: Filament color in RRGGBBAA hex format
    - name: Human-readable filament name
    - remain: Remaining filament percentage (0-100)
    
    Also returns:
    - tray_now: Currently active tray (255=none, 254=external spool)
    - tray_tar: Target tray for next operation
    - external_spool: External spool info if present
    """
    try:
        from src.services.bambu_service import get_bambu_client
        
        # Verify printer exists
        printer_service = PrinterService(db)
        printer = printer_service.get_printer_by_id(printer_id)
        
        if not printer:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        # Get bambu client instance
        bambu_client = get_bambu_client()
        
        if not bambu_client:
            return {
                "printer_id": printer_id,
                "error": "MQTT client not initialized",
                "trays": [],
                "tray_now": 255,
                "tray_tar": 255,
                "external_spool": None
            }
        
        if bambu_client.printer_id != printer_id:
            return {
                "printer_id": printer_id,
                "error": f"Client connected to different printer ({bambu_client.printer_id})",
                "trays": [],
                "tray_now": 255,
                "tray_tar": 255,
                "external_spool": None
            }
        
        if not bambu_client.mqtt_connected:
            return {
                "printer_id": printer_id,
                "error": "MQTT not connected",
                "trays": [],
                "tray_now": 255,
                "tray_tar": 255,
                "external_spool": None
            }
        
        # Get AMS status from client
        ams_status = bambu_client.get_ams_status()
        
        return {
            "printer_id": printer_id,
            **ams_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AMS status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}/ams/trays")
async def get_ams_trays_simple(printer_id: str, db: Session = Depends(get_db)):
    """
    Get simplified list of AMS trays for UI dropdowns.
    
    Returns list of available trays for filament selection:
    [
        {"slot": 0, "name": "Bambu PLA Basic", "color": "#FFFF00", "remain": 80},
        {"slot": 1, "name": "Empty", "color": "#000000", "remain": 0},
        ...
    ]
    
    Also includes external spool option if available.
    """
    try:
        from src.services.bambu_service import get_bambu_client
        
        # Verify printer exists
        printer_service = PrinterService(db)
        printer = printer_service.get_printer_by_id(printer_id)
        
        if not printer:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={printer_id}"
            )
        
        # Get bambu client instance
        bambu_client = get_bambu_client()
        
        if not bambu_client or bambu_client.printer_id != printer_id or not bambu_client.mqtt_connected:
            # Return default trays if not connected
            return {
                "printer_id": printer_id,
                "connected": False,
                "trays": [
                    {"slot": i, "name": "Unknown", "color": "#808080", "remain": 0, "empty": True}
                    for i in range(4)
                ]
            }
        
        # Get AMS status
        ams_status = bambu_client.get_ams_status()
        
        # Check if AMS is actually connected based on ams_exist_bits
        ams_exist_bits = ams_status.get("ams_exist_bits", "0")
        ams_connected = ams_exist_bits != "0" and len(ams_status.get("trays", [])) > 0
        
        # Convert to simplified format for UI
        simple_trays = []
        for tray in ams_status.get("trays", []):
            # Convert RRGGBBAA to #RRGGBB for CSS
            color_hex = tray.get("color", "808080FF")
            if len(color_hex) >= 6:
                css_color = f"#{color_hex[:6]}"
            else:
                css_color = "#808080"
            
            simple_trays.append({
                "slot": tray.get("slot", 0),
                "name": tray.get("name", "Unknown"),
                "type": tray.get("type", "Unknown"),
                "color": css_color,
                "remain": tray.get("remain", 0),
                "empty": tray.get("empty", True),
            })
        
        # Add external spool option
        external = ams_status.get("external_spool")
        if external:
            ext_color = external.get("color", "808080FF")
            if len(ext_color) >= 6:
                css_color = f"#{ext_color[:6]}"
            else:
                css_color = "#808080"
            
            simple_trays.append({
                "slot": 254,  # External spool identifier
                "name": external.get("name", "External Spool"),
                "type": external.get("type", "Unknown"),
                "color": css_color,
                "remain": external.get("remain", 0),
                "empty": external.get("empty", True),
                "is_external": True,
            })
        
        return {
            "printer_id": printer_id,
            "connected": ams_connected,
            "tray_now": ams_status.get("tray_now", 255),
            "trays": simple_trays
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AMS trays: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AMS FILAMENT CONTROL ENDPOINTS
# =============================================================================

class AmsLoadRequest(BaseModel):
    """Request body for AMS load filament"""
    slot: int = Field(..., ge=0, le=254, description="AMS slot number (0-3 for AMS Lite, 254 for external)")
    temperature: int = Field(default=220, ge=180, le=300, description="Target nozzle temperature for loading")

class AmsFilamentSettingRequest(BaseModel):
    """Request body for AMS filament setting"""
    slot: int = Field(..., ge=0, le=3, description="AMS slot number (0-3)")
    tray_color: str = Field(default="", description="Filament color in RRGGBBAA hex format")
    tray_type: str = Field(default="PLA", description="Filament type (PLA, PETG, ABS, etc.)")


@router.post("/{printer_id}/ams/load")
async def ams_load_filament(printer_id: str, request: AmsLoadRequest):
    """
    Load filament from a specific AMS slot.
    
    This command tells the printer to load filament from the specified slot.
    The printer must be idle or paused for this operation.
    
    - **printer_id**: Printer identifier (e.g., "03900D5A2402051")
    - **slot**: AMS slot number (0-3 for AMS Lite, 254 for external spool)
    - **temperature**: Target nozzle temperature for the loading operation
    """
    try:
        # Get Bambu service instance (singleton)
        from src.services.bambu_service import get_bambu_client
        
        bambu_client = get_bambu_client()
        if not bambu_client or not bambu_client.mqtt_connected:
            raise HTTPException(status_code=503, detail="Printer not connected")
        
        # Send load command
        success = bambu_client.ams_load_filament(request.slot)
        
        if success:
            return {
                "success": True,
                "message": f"Loading filament from slot {request.slot}",
                "printer_id": printer_id,
                "slot": request.slot
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send load command")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading AMS filament: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/ams/unload")
async def ams_unload_filament(printer_id: str):
    """
    Unload the currently loaded filament.
    
    This command tells the printer to unload the filament back to the AMS
    or retract it from the extruder.
    
    - **printer_id**: Printer identifier (e.g., "03900D5A2402051")
    """
    try:
        # Get Bambu service instance (singleton)
        from src.services.bambu_service import get_bambu_client
        
        bambu_client = get_bambu_client()
        if not bambu_client or not bambu_client.mqtt_connected:
            raise HTTPException(status_code=503, detail="Printer not connected")
        
        # Send unload command
        success = bambu_client.ams_unload_filament()
        
        if success:
            return {
                "success": True,
                "message": "Unloading filament",
                "printer_id": printer_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send unload command")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unloading AMS filament: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/ams/settings")
async def ams_filament_settings(printer_id: str, request: AmsFilamentSettingRequest):
    """
    Update filament settings for a specific AMS slot.
    
    This allows you to configure the filament type and color for a slot.
    
    - **printer_id**: Printer identifier (e.g., "03900D5A2402051")
    - **slot**: AMS slot number (0-3)
    - **tray_color**: Filament color in RRGGBBAA hex format
    - **tray_type**: Filament type (PLA, PETG, ABS, etc.)
    """
    try:
        # Get Bambu service instance (singleton)
        from src.services.bambu_service import get_bambu_client
        
        bambu_client = get_bambu_client()
        if not bambu_client or not bambu_client.mqtt_connected:
            raise HTTPException(status_code=503, detail="Printer not connected")
        
        # Send settings command
        success = bambu_client.ams_filament_setting(
            slot=request.slot,
            tray_color=request.tray_color,
            tray_type=request.tray_type
        )
        
        if success:
            return {
                "success": True,
                "message": f"Updated filament settings for slot {request.slot}",
                "printer_id": printer_id,
                "slot": request.slot,
                "tray_type": request.tray_type,
                "tray_color": request.tray_color
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update filament settings")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting AMS filament: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}/ams/loading-status")
async def get_ams_loading_status(printer_id: str):
    """
    Get real-time AMS loading/unloading progress status.
    
    Use this endpoint to poll the current state during load/unload operations.
    Poll every 500ms-1s for smooth progress updates.
    
    Returns:
        - **active**: True if load/unload is in progress
        - **is_unload**: True if unloading, False if loading
        - **target_slot**: Target slot number for loading (255 = none)
        - **current_step**: Current step index (0-5 for load, 0-3 for unload)
        - **step_name**: Human-readable step description
        - **nozzle_temp**: Current nozzle temperature
        - **target_temp**: Target nozzle temperature
        - **completed**: True if operation just completed
        - **total_steps**: Total steps (6 for load, 4 for unload)
        - **tray_now**: Currently loaded tray (255 = none)
        - **tray_tar**: Target tray
    """
    try:
        from src.services.bambu_service import get_bambu_client
        
        bambu_client = get_bambu_client()
        if not bambu_client or not bambu_client.mqtt_connected:
            raise HTTPException(status_code=503, detail="Printer not connected")
        
        # Get loading state
        loading_state = bambu_client.get_ams_loading_state()
        
        return {
            "success": True,
            "printer_id": printer_id,
            **loading_state
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AMS loading status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/ams/sync-from-printer")
async def sync_ams_from_printer(printer_id: str):
    """
    Manually sync AMS data from printer to database.
    
    This endpoint triggers a one-time sync of current AMS slot data
    from the printer's MQTT status to the database slot assignments.
    
    Useful when:
    - User changes filament at the printer
    - User wants to refresh slot assignments
    - After loading/unloading filament
    
    Inspired by OrcaSlicer's sync mechanism.
    
    Returns:
        - **synced_slots**: Number of slots synced
        - **timestamp**: When sync occurred
    """
    try:
        from src.services.bambu_service import get_bambu_client
        import datetime
        
        bambu_client = get_bambu_client()
        if not bambu_client or not bambu_client.mqtt_connected:
            raise HTTPException(status_code=503, detail="Printer not connected")
        
        # Trigger manual sync
        bambu_client._sync_ams_to_database()
        
        # Count filled slots
        filled_slots = sum(
            1 for ams in bambu_client.ams_data.get("ams", [])
            for tray in ams.get("trays", [])
            if not tray.get("empty", True)
        )
        
        return {
            "success": True,
            "message": "AMS data synced from printer to database",
            "printer_id": printer_id,
            "synced_slots": filled_slots,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing AMS from printer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
