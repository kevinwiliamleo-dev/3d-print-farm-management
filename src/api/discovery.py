"""
Printer Discovery API - Auto-detect printers on network
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import logging

from src.database.db import get_db, Printer
from src.services.printer_discovery import BambuPrinterDiscovery, IPRangeScanner

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/discover")
async def discover_printers(timeout: int = 5):
    """
    Scan network for Bambu Lab printers using UDP broadcast
    
    Query Parameters:
        timeout: Discovery timeout in seconds (default: 5)
    
    Returns:
        List of discovered printers (not saved to database yet)
    """
    try:
        logger.info("🔍 Starting printer discovery...")
        discovery = BambuPrinterDiscovery()
        printers = await discovery.discover_printers_async(timeout)
        
        if not printers:
            logger.warning("⚠️ No printers found via UDP broadcast")
            return {
                "success": True,
                "method": "udp_broadcast",
                "printers": [],
                "message": "No printers found. Try IP range scan or manual add."
            }
        
        logger.info(f"✅ Found {len(printers)} printer(s)")
        return {
            "success": True,
            "method": "udp_broadcast",
            "printers": printers,
            "message": f"Found {len(printers)} printer(s)"
        }
        
    except Exception as e:
        logger.error(f"❌ Discovery error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan-subnet")
async def scan_subnet(subnet: str = "192.168.1", timeout: float = 1.0):
    """
    Fallback: Scan IP range for printers
    
    Query Parameters:
        subnet: First 3 octets (e.g., "192.168.1")
        timeout: Socket timeout per IP
    
    Returns:
        List of detected printers
    """
    try:
        logger.info(f"🔍 Scanning subnet {subnet}.0/24...")
        printers = await IPRangeScanner.scan_subnet(subnet, timeout)
        
        if not printers:
            return {
                "success": True,
                "method": "ip_scan",
                "subnet": f"{subnet}.0/24",
                "printers": [],
                "message": "No printers detected in subnet"
            }
        
        logger.info(f"✅ Detected {len(printers)} printer(s)")
        return {
            "success": True,
            "method": "ip_scan",
            "subnet": f"{subnet}.0/24",
            "printers": printers,
            "message": f"Detected {len(printers)} printer(s)"
        }
        
    except Exception as e:
        logger.error(f"❌ Subnet scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-discovered")
async def add_discovered_printer(
    printer_data: dict,
    db: Session = Depends(get_db)
):
    """
    Add discovered printer to database
    
    Body:
        {
            "ip": "192.168.4.101",
            "name": "Bambu A1",
            "model": "A1",
            "serial": "03900D5A2402051",
            "access_code": "34782589"  # Required from user
        }
    """
    try:
        # Validate required fields
        required_fields = ['ip', 'name', 'serial', 'access_code']
        for field in required_fields:
            if not printer_data.get(field):
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Check if printer already exists
        existing = db.query(Printer).filter(
            Printer.printer_id == printer_data['serial']
        ).first()
        
        if existing:
            logger.warning(f"⚠️ Printer {printer_data['serial']} already exists")
            return {
                "success": False,
                "message": "Printer already exists in database",
                "printer_id": existing.printer_id
            }
        
        # Create new printer with correct field names
        new_printer = Printer(
            printer_id=printer_data['serial'],  # Use serial as primary key
            printer_name=printer_data['name'],
            printer_ip=printer_data['ip'],
            access_code=printer_data['access_code'],  # Store access code in DB
            model=printer_data.get('model', 'Bambu Lab A1'),
            status='idle',
            is_active=True,
            mqtt_connected=False
        )
        
        db.add(new_printer)
        db.commit()
        db.refresh(new_printer)
        
        logger.info(f"✅ Added printer: {new_printer.printer_name} ({new_printer.printer_id})")
        
        return {
            "success": True,
            "message": "Printer added successfully",
            "printer": {
                "id": new_printer.printer_id,
                "name": new_printer.printer_name,
                "ip": new_printer.printer_ip,
                "serial": new_printer.printer_id,
                "model": new_printer.model,
                "status": new_printer.status
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error adding printer: {e}")
        raise HTTPException(status_code=500, detail=str(e))
