"""
Queue API Routes - Handle print queue management
Follows naming conventions from README.md
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
from src.database import get_db, SessionLocal
from src.services.queue_service import QueueService
from src.services.printer_service import PrinterService
from src.models.schemas import QueueResponse
from src.config import QUEUE_FILES_DIR, UPLOAD_DIR
import logging

logger_obj = logging.getLogger(__name__)
router = APIRouter(prefix="/api/queue", tags=["queue"])


class AddToQueueRequest(BaseModel):
    """Request to add job to queue - simplified (no presets, no templates)"""
    job_id: int
    printer_id: str
    
    # AMS settings (from UI preview modal)
    ams_slot: int = Field(default=0, ge=0, le=255, description="AMS tray slot (0-3, or 255 for external spool)")
    ams_mapping: str = ""  # Full mapping for multi-color prints
    use_ams: bool = True  # Whether to use AMS
    filament_already_loaded: bool = Field(default=False, description="Skip AMS load - filament already in extruder")
    
    # Print settings (only 3 checkboxes from UI preview modal)
    auto_bed_leveling: bool = Field(default=True, description="Enable G29 bed leveling")
    flow_calibration: bool = Field(default=False, description="Enable flow test")
    timelapse: bool = Field(default=False, description="Enable timelapse recording during print")


class UpdateQueuePositionRequest(BaseModel):
    """Request to update queue position"""
    new_position: int


class UpdateQueueSettingsRequest(BaseModel):
    """Request to update queue item settings - simplified"""
    # AMS settings
    ams_slot: Optional[int] = None
    ams_mapping: Optional[str] = None
    use_ams: Optional[bool] = None
    filament_already_loaded: Optional[bool] = None
    
    # Print settings (3 checkboxes only)
    auto_bed_leveling: Optional[bool] = None
    flow_calibration: Optional[bool] = None
    timelapse: Optional[bool] = None


@router.post("/add")
async def add_job_to_queue(
    request: AddToQueueRequest,
    db: Session = Depends(get_db)
):
    """
    Add job to print queue - simplified (file sudah dari slicer, skip processing)
    
    - **job_id**: The job to queue
    - **printer_id**: Target printer
    - **ams_slot**: AMS tray slot (0-3 for AMS Lite)
    - **use_ams**: Whether to use AMS
    - **filament_already_loaded**: Skip AMS loading sequence
    - **auto_bed_leveling**: Enable bed leveling
    - **flow_calibration**: Enable flow calibration
    - **timelapse**: Enable timelapse recording
    
    Returns: queue_id, position_in_queue
    """
    try:
        # Verify printer exists
        printer_service = PrinterService(db)
        printer = printer_service.get_printer_by_id(request.printer_id)
        
        if not printer:
            raise HTTPException(
                status_code=404,
                detail=f"Printer not found: printer_id={request.printer_id}"
            )
        
        # Get job to retrieve loop_count
        from src.database.db import Job
        job = db.query(Job).filter(Job.job_id == request.job_id).first()
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job not found: job_id={request.job_id}"
            )
        
        loop_count = job.loop_count if job.loop_count else 1
        logger_obj.info(f"📋 Adding job to queue with loop_count={loop_count}")
        
        # Add to queue - skip all preprocessing, kirim file as-is dari slicer
        queue_service = QueueService(db)
        queue_item = queue_service.add_job_to_queue(
            job_id=request.job_id,
            printer_id=request.printer_id,
            loop_count=loop_count,
            # AMS settings
            ams_slot=request.ams_slot,
            ams_mapping=request.ams_mapping,
            use_ams=request.use_ams,
            filament_already_loaded=request.filament_already_loaded,
            # Print settings (3 checkboxes)
            auto_bed_leveling=request.auto_bed_leveling,
            flow_calibration=request.flow_calibration,
            timelapse=request.timelapse,
            # Skip ALL preprocessing - file sudah dari slicer
            skip_preprocessing=True
        )
        
        return queue_item
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}")
async def get_printer_queue(printer_id: str, db: Session = Depends(get_db)):
    """
    Get queue for specific printer (FIFO order)
    
    Returns: List of queued jobs with position_in_queue
    """
    try:
        queue_service = QueueService(db)
        queue_items = queue_service.get_printer_queue(printer_id)
        
        return {
            "printer_id": printer_id,
            "queue_items": queue_items,
            "total": len(queue_items)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}/status")
async def get_queue_status(printer_id: str, db: Session = Depends(get_db)):
    """
    Get queue statistics for printer
    
    Returns: pending_items, running_items, completed_items
    """
    try:
        queue_service = QueueService(db)
        status = queue_service.get_queue_status(printer_id)
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{queue_id}/start")
async def start_queue_job(queue_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Start printing queue job (async).
    
    The actual upload and print start happens in background so frontend
    can see status updates (uploading -> running).
    """
    from src.database.db import Queue
    
    try:
        # Check if queue item exists
        queue_item = db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            raise HTTPException(
                status_code=404,
                detail=f"Queue item not found: queue_id={queue_id}"
            )
        
        # Set status to uploading immediately
        queue_item.status = "uploading"
        db.commit()
        
        logger_obj.info(f"📤 Queue item {queue_id} status set to 'uploading', starting background task...")
        
        # Run the actual upload and print in background
        background_tasks.add_task(run_queue_job_background, queue_id)
        
        return {"message": f"Started queue job: queue_id={queue_id}", "status": "uploading"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_queue_job_background(queue_id: int):
    """Background task to upload file and start print"""
    db = SessionLocal()
    try:
        logger_obj.info(f"🔄 Background task started for queue_id={queue_id}")
        queue_service = QueueService(db)
        success = queue_service.start_queue_job(queue_id)
        
        if success:
            logger_obj.info(f"✅ Background task completed successfully for queue_id={queue_id}")
        else:
            logger_obj.error(f"❌ Background task failed for queue_id={queue_id}")
    except Exception as e:
        logger_obj.error(f"❌ Background task error for queue_id={queue_id}: {str(e)}")
        import traceback
        logger_obj.error(traceback.format_exc())
    finally:
        db.close()


@router.post("/{queue_id}/next-loop")
async def next_loop(queue_id: int, db: Session = Depends(get_db)):
    """Increment current_loop for queue job"""
    try:
        queue_service = QueueService(db)
        success = queue_service.increment_current_loop(queue_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Queue item not found: queue_id={queue_id}"
            )
        
        # Check if should repeat
        should_repeat = queue_service.should_repeat_queue_job(queue_id)
        
        return {
            "queue_id": queue_id,
            "should_repeat": should_repeat
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{queue_id}/complete")
async def complete_queue_job(queue_id: int, db: Session = Depends(get_db)):
    """Mark queue job as completed"""
    try:
        queue_service = QueueService(db)
        success = queue_service.complete_queue_job(queue_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Queue item not found: queue_id={queue_id}"
            )
        
        return {"message": f"Completed queue job: queue_id={queue_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{queue_id}/remove")
async def remove_from_queue(queue_id: int, db: Session = Depends(get_db)):
    """Remove job from queue and delete associated file"""
    try:
        queue_service = QueueService(db)
        result = queue_service.remove_from_queue(queue_id, delete_file=True)
        
        if not result["success"]:
            raise HTTPException(
                status_code=404,
                detail=f"Queue item not found: queue_id={queue_id}"
            )
        
        return {
            "message": f"Removed from queue: queue_id={queue_id}",
            "file_deleted": result.get("file_deleted", False),
            "job_deleted": result.get("job_deleted", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{queue_id}/position")
async def update_queue_position(
    queue_id: int, 
    request: UpdateQueuePositionRequest,
    db: Session = Depends(get_db)
):
    """
    Update queue item position for reordering
    Only works for pending status items
    """
    try:
        queue_service = QueueService(db)
        success = queue_service.update_queue_position(queue_id, request.new_position)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Queue item not found or cannot be reordered: queue_id={queue_id}"
            )
        
        return {
            "message": f"Updated position for queue_id={queue_id}",
            "new_position": request.new_position
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{queue_id}/details")
async def get_queue_item_details(queue_id: int, db: Session = Depends(get_db)):
    """
    Get detailed settings for a queue item
    Used for editing pending jobs
    """
    from src.database.db import Queue, Job
    
    try:
        queue_item = db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: queue_id={queue_id}")
        
        job = db.query(Job).filter(Job.job_id == queue_item.job_id).first()
        
        return {
            "queue_id": queue_item.queue_id,
            "job_id": queue_item.job_id,
            "job_name": job.job_name if job else "Unknown",
            "filename": job.filename if job else None,
            "printer_id": queue_item.printer_id,
            "position_in_queue": queue_item.position_in_queue,
            "status": queue_item.status,
            "current_loop": queue_item.current_loop,
            "loop_count": job.loop_count if job else 1,
            # AMS settings
            "ams_slot": queue_item.ams_slot,
            "ams_mapping": queue_item.ams_mapping,
            "use_ams": queue_item.use_ams,
            "filament_already_loaded": queue_item.filament_already_loaded,
            # Print settings (3 checkboxes)
            "auto_bed_leveling": queue_item.auto_bed_leveling,
            "flow_calibration": queue_item.flow_calibration,
            "timelapse": queue_item.timelapse,
            # Queue file path
            "queue_file_path": queue_item.queue_file_path
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{queue_id}/download")
async def download_queue_file(queue_id: int, db: Session = Depends(get_db)):
    """
    Download the modified queue file (3MF with G-code modifications applied)
    This is the actual file that will be sent to the printer
    """
    from fastapi.responses import FileResponse
    from src.database.db import Queue, Job
    
    try:
        queue_item = db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: queue_id={queue_id}")
        
        if not queue_item.queue_file_path:
            raise HTTPException(status_code=404, detail="No queue file available for this item")
        
        file_path = Path(queue_item.queue_file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Queue file not found on disk")
        
        # Get job for filename
        job = db.query(Job).filter(Job.job_id == queue_item.job_id).first()
        download_name = f"queue_{queue_id}_{job.filename if job else 'file.3mf'}"
        
        return FileResponse(
            path=str(file_path),
            filename=download_name,
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{queue_id}/settings")
async def update_queue_settings(
    queue_id: int,
    request: UpdateQueueSettingsRequest,
    db: Session = Depends(get_db)
):
    """
    Update queue item settings - simplified (no file regeneration)
    Only works for pending status items.
    Settings are for display only - file remains as-is from slicer.
    """
    from src.database.db import Queue
    
    try:
        queue_item = db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: queue_id={queue_id}")
        
        if queue_item.status != "pending":
            raise HTTPException(status_code=400, detail="Can only edit pending queue items")
        
        # Update AMS settings
        if request.ams_slot is not None:
            queue_item.ams_slot = request.ams_slot
        if request.ams_mapping is not None:
            queue_item.ams_mapping = request.ams_mapping
        if request.use_ams is not None:
            queue_item.use_ams = request.use_ams
        if request.filament_already_loaded is not None:
            queue_item.filament_already_loaded = request.filament_already_loaded
        
        # Update print settings (3 checkboxes - for display only)
        if request.auto_bed_leveling is not None:
            queue_item.auto_bed_leveling = request.auto_bed_leveling
        if request.flow_calibration is not None:
            queue_item.flow_calibration = request.flow_calibration
        if request.timelapse is not None:
            queue_item.timelapse = request.timelapse
        
        db.commit()
        
        logger_obj.info(f"✅ Updated settings for queue_id={queue_id} (no file modification)")
        return {
            "message": f"Updated settings for queue_id={queue_id}",
            "queue_file_path": queue_item.queue_file_path,
            "note": "Settings updated for display - file remains as-is from slicer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
