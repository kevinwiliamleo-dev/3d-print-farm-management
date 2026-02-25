"""
Bed Cooling API Endpoints
Configure and monitor automatic bed cooling with external Kit fan
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging

from src.services.print_control_service import PrintControlService
from src.api.print_control import get_print_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/printers", tags=["bed-cooling"])


class BedCoolingConfig(BaseModel):
    """Request to configure bed cooling"""
    kit_ip: str
    enabled: bool = True


@router.post("/{printer_id}/bed-cooling/configure")
async def configure_bed_cooling(
    printer_id: str,
    config: BedCoolingConfig,
    print_service: PrintControlService = Depends(get_print_service)
):
    """
    Configure automatic bed cooling with external Kit fan
    
    When bed temperature needs to cool down (current > target):
    1. Automatically turn ON Kit fan
    2. Monitor temperature progress
    3. Turn OFF fan when target reached
    
    Args:
        printer_id: Printer ID
        config: Kit IP address and enable/disable flag
    
    Example:
        POST /api/printers/bambu-001/bed-cooling/configure
        {
            "kit_ip": "192.168.1.150",
            "enabled": true
        }
    """
    try:
        # Save to database
        from src.database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            db.execute(
                text("UPDATE printers SET kit_enabled = :enabled, kit_ip = :kit_ip WHERE printer_id = :printer_id"),
                {"enabled": 1 if config.enabled else 0, "kit_ip": config.kit_ip, "printer_id": printer_id}
            )
            db.commit()
        finally:
            db.close()
        
        # Configure cooling service
        print_service.bambu_client.configure_bed_cooling(
            kit_ip=config.kit_ip,
            enabled=config.enabled
        )
        
        logger.info(
            f"✅ Bed cooling configured for {printer_id}: "
            f"Kit IP={config.kit_ip}, Enabled={config.enabled}"
        )
        
        return {
            "message": "Bed cooling configured successfully",
            "printer_id": printer_id,
            "kit_ip": config.kit_ip,
            "enabled": config.enabled
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to configure bed cooling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}/bed-cooling/status")
async def get_bed_cooling_status(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """
    Get current bed cooling status
    
    Returns:
        - is_cooling: Whether fan is currently running for cooling
        - elapsed_seconds: How long cooling has been active
        - start_temp: Temperature when cooling started
        - target_temp: Target temperature
        - kit_ip: Configured Kit IP address
        - kit_enabled: Whether auto-cooling is enabled
    """
    try:
        status = print_service.bambu_client.get_cooling_status()
        
        return {
            "printer_id": printer_id,
            **status
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to get bed cooling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/bed-cooling/force-stop")
async def force_stop_cooling(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """
    Force stop bed cooling (manual override)
    
    This will turn OFF the fan immediately regardless of temperature
    """
    try:
        cooling_service = print_service.bambu_client.cooling_service
        
        if not cooling_service:
            raise HTTPException(
                status_code=400,
                detail="Cooling service not available"
            )
        
        # Force stop in async context
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cooling_service.force_stop())
        loop.close()
        
        logger.info(f"⚠️ Bed cooling force-stopped for {printer_id}")
        
        return {
            "message": "Bed cooling stopped",
            "printer_id": printer_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to force-stop cooling: {e}")
        raise HTTPException(status_code=500, detail=str(e))
