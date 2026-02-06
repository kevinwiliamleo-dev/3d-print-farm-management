"""
Print Control API Routes - Manage printing workflow
Follows naming conventions from README.md
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.database import get_db
from src.services.print_control_service import PrintControlService
from src.services.bambu_service import get_bambu_client  # Use global client getter
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/print-control", tags=["print-control"])


def get_print_service(db: Session = Depends(get_db)):
    """Get print control service with global MQTT client"""
    # Use global MQTT client from main.py (initialized at startup)
    bambu_client = get_bambu_client()
    
    if bambu_client is None:
        logger.error("❌ Global Bambu MQTT client not initialized! Check main.py startup.")
        raise HTTPException(
            status_code=503,
            detail="MQTT client not available. Printer may be offline or not configured."
        )
    
    if not bambu_client.mqtt_connected:
        logger.warning("⚠️ MQTT client exists but not connected. Check printer status.")
    
    # Always create new service with fresh db session
    return PrintControlService(db, bambu_client)


@router.post("/{printer_id}/start-print")
async def start_print_job(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """
    Start printing next job in queue
    
    - **printer_id**: Target printer ID
    
    Returns: Current print status and queue info
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    try:
        # Run the synchronous start_next_job in a thread pool
        # This keeps the event loop free for WebSocket broadcasts
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as executor:
            success = await loop.run_in_executor(
                executor, 
                print_service.start_next_job, 
                printer_id
            )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to start print job (no jobs in queue or printer error)"
            )
        
        status = print_service.get_current_print_status()
        
        logger.info(f"Started print job on printer_id={printer_id}")
        
        return {
            "message": "Print job started",
            "printer_id": printer_id,
            "status": status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting print job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/complete-print")
async def complete_print_job(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """
    Handle print job completion
    
    Automatically:
    1. Checks if job should repeat (loop management)
    2. Triggers auto-eject if enabled
    3. Logs to history
    4. Starts next job if queue not empty
    """
    try:
        success = print_service.handle_print_completion(printer_id)
        
        if not success:
            logger.warning("Print completion handled but with issues")
        
        status = print_service.get_current_print_status()
        
        logger.info(f"Completed print job on printer_id={printer_id}")
        
        return {
            "message": "Print job completion processed",
            "printer_id": printer_id,
            "next_status": status
        }
    
    except Exception as e:
        logger.error(f"Error completing print job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/pause")
async def pause_print(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """Pause current printing job"""
    logger.info(f"[API] PAUSE request received for printer: {printer_id}")
    try:
        success = print_service.pause_current_print()
        
        if not success:
            logger.warning(f"[API] PAUSE failed for printer: {printer_id} - no active print")
            raise HTTPException(
                status_code=400,
                detail="Failed to pause print (no active print or printer error)"
            )
        
        logger.info(f"[API] PAUSE successful for printer: {printer_id}")
        return {"message": "Print paused", "printer_id": printer_id, "success": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] PAUSE error for printer {printer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/resume")
async def resume_print(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """Resume paused printing job"""
    logger.info(f"[API] RESUME request received for printer: {printer_id}")
    try:
        success = print_service.resume_current_print()
        
        if not success:
            logger.warning(f"[API] RESUME failed for printer: {printer_id} - no paused print")
            raise HTTPException(
                status_code=400,
                detail="Failed to resume print (no paused print or printer error)"
            )
        
        logger.info(f"[API] RESUME successful for printer: {printer_id}")
        return {"message": "Print resumed", "printer_id": printer_id, "success": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] RESUME error for printer {printer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/cancel")
async def cancel_print(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """Cancel current printing job"""
    logger.info(f"[API] CANCEL request received for printer: {printer_id}")
    try:
        success = print_service.cancel_current_print()
        
        if not success:
            logger.warning(f"[API] CANCEL failed for printer: {printer_id} - no active print")
            raise HTTPException(
                status_code=400,
                detail="Failed to cancel print (no active print)"
            )
        
        logger.info(f"[API] CANCEL successful for printer: {printer_id}")
        return {"message": "Print cancelled", "printer_id": printer_id, "success": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] CANCEL error for printer {printer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}/status")
async def get_print_status(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """
    Get current print status
    
    Returns:
    - status: idle | printing
    - job_name, current_loop, total_loops
    - print_progress: 0-100%
    """
    try:
        status = print_service.get_current_print_status()
        
        # Also get printer connection status
        printer_status = print_service.bambu_client.get_printer_status()
        
        return {
            "printer_id": printer_id,
            "printer_info": printer_status,
            "print_info": status
        }
    
    except Exception as e:
        logger.error(f"Error getting print status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{printer_id}/eject")
async def manual_eject(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """Manually trigger auto-eject"""
    try:
        success = print_service.bambu_client.trigger_auto_eject()
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to trigger eject (printer error)"
            )
        
        logger.info(f"Manual eject triggered on printer_id={printer_id}")
        
        return {
            "message": "Auto-eject triggered",
            "printer_id": printer_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering eject: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}/mqtt-status")
async def get_mqtt_status(
    printer_id: str,
    print_service: PrintControlService = Depends(get_print_service)
):
    """
    Get MQTT connection status and temperature data
    
    Returns:
    - mqtt_connected: True/False
    - printer_status: idle | printing | offline
    - current_print_progress: 0-100%
    - nozzle_temp, nozzle_target_temp, bed_temp, bed_target_temp, chamber_temp
    - current_layer, total_layers: Layer tracking info
    - current_file: Current printing file name
    """
    try:
        status = print_service.bambu_client.get_printer_status()
        
        return {
            "printer_id": printer_id,
            "mqtt_connected": status["mqtt_connected"],
            "printer_status": status["printer_status"],
            "print_progress": status["current_print_progress"],
            "remaining_time": status.get("mc_remaining_time", 0),
            "nozzle_temp": status.get("nozzle_temp", 0),
            "nozzle_target_temp": status.get("nozzle_target_temp", 0),
            "bed_temp": status.get("bed_temp", 0),
            "bed_target_temp": status.get("bed_target_temp", 0),
            "chamber_temp": status.get("chamber_temp", 0),
            "current_layer": status.get("current_layer", 0),
            "total_layers": status.get("total_layers", 0),
            "current_file": status.get("current_subtask_name", ""),
            "print_error": status.get("print_error", 0),
            "print_stage": status.get("print_stage", 0),  # Print stage tracking (stg_cur from MQTT)
        }
    
    except Exception as e:
        logger.error(f"Error getting MQTT status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
