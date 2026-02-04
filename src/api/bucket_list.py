"""
Bucket List API Routes - Save jobs for later printing
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from src.database import get_db
from src.database.db import BucketList, Queue, Job
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bucket-list", tags=["bucket-list"])


class AddToBucketRequest(BaseModel):
    """Request to add job to bucket list with settings"""
    job_id: int
    printer_id: str
    
    # AMS settings
    ams_slot: int = Field(default=0)
    ams_mapping: str = ""
    use_ams: bool = True
    filament_already_loaded: bool = False
    
    # Simplified automation (3 settings only)
    auto_bed_leveling: bool = True
    flow_calibration: bool = True
    timelapse: bool = False
    
    # Loop count
    loop_count: int = 1
    
    # Notes
    notes: Optional[str] = None


class MoveToQueueRequest(BaseModel):
    """Request to move bucket item to queue"""
    printer_id: Optional[str] = None  # Override printer if needed


@router.post("/add")
async def add_to_bucket_list(request: AddToBucketRequest, db: Session = Depends(get_db)):
    """
    Add job to bucket list with all settings saved
    """
    try:
        # Check if job exists
        job = db.query(Job).filter(Job.job_id == request.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={request.job_id}")
        
        # Create bucket list item
        bucket_item = BucketList(
            job_id=request.job_id,
            printer_id=request.printer_id,
            ams_slot=request.ams_slot,
            ams_mapping=request.ams_mapping,
            use_ams=request.use_ams,
            filament_already_loaded=request.filament_already_loaded,
            auto_bed_leveling=request.auto_bed_leveling,
            flow_calibration=request.flow_calibration,
            timelapse=request.timelapse,
            loop_count=request.loop_count,
            notes=request.notes
        )
        
        db.add(bucket_item)
        db.commit()
        db.refresh(bucket_item)
        
        logger.info(f"Added to bucket list: bucket_id={bucket_item.bucket_id}, job_id={request.job_id}")
        
        return {
            "bucket_id": bucket_item.bucket_id,
            "job_id": request.job_id,
            "job_name": job.job_name,
            "message": "Job saved to bucket list"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to bucket list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/from-queue/{queue_id}")
async def move_queue_to_bucket(queue_id: int, db: Session = Depends(get_db)):
    """
    Move a pending queue item to bucket list (saves all settings)
    """
    try:
        # Get queue item
        queue_item = db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: queue_id={queue_id}")
        
        if queue_item.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending items can be moved to bucket list")
        
        # Get job info
        job = db.query(Job).filter(Job.job_id == queue_item.job_id).first()
        
        # Create bucket item with simplified settings from queue (3 checkboxes + AMS)
        bucket_item = BucketList(
            job_id=queue_item.job_id,
            printer_id=queue_item.printer_id,
            ams_slot=queue_item.ams_slot,
            ams_mapping=queue_item.ams_mapping,
            use_ams=queue_item.use_ams,
            filament_already_loaded=queue_item.filament_already_loaded,
            auto_bed_leveling=queue_item.auto_bed_leveling,
            flow_calibration=queue_item.flow_calibration,
            timelapse=queue_item.timelapse,
            loop_count=job.loop_count if job else 1
        )
        
        db.add(bucket_item)
        
        # Remove from queue
        old_position = queue_item.position_in_queue
        db.delete(queue_item)
        
        # Reorder remaining queue items
        remaining_items = db.query(Queue).filter(
            Queue.printer_id == queue_item.printer_id,
            Queue.position_in_queue > old_position
        ).all()
        for item in remaining_items:
            item.position_in_queue -= 1
        
        db.commit()
        db.refresh(bucket_item)
        
        logger.info(f"Moved queue to bucket: queue_id={queue_id} -> bucket_id={bucket_item.bucket_id}")
        
        return {
            "bucket_id": bucket_item.bucket_id,
            "job_id": bucket_item.job_id,
            "job_name": job.job_name if job else "Unknown",
            "message": "Job moved to bucket list"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving to bucket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{printer_id}")
async def get_bucket_list(printer_id: str, db: Session = Depends(get_db)):
    """
    Get all bucket list items for a printer
    """
    try:
        bucket_items = db.query(BucketList).filter(
            BucketList.printer_id == printer_id
        ).order_by(BucketList.created_at.desc()).all()
        
        result = []
        for item in bucket_items:
            job = db.query(Job).filter(Job.job_id == item.job_id).first()
            result.append({
                "bucket_id": item.bucket_id,
                "job_id": item.job_id,
                "job_name": job.job_name if job else "Unknown",
                "printer_id": item.printer_id,
                "ams_slot": item.ams_slot,
                "use_ams": item.use_ams,
                "loop_count": item.loop_count,
                "auto_bed_leveling": item.auto_bed_leveling,
                "flow_calibration": item.flow_calibration,
                "vibration_test": item.vibration_test,
                "clean_nozzle": item.clean_nozzle,
                "auto_eject": item.auto_eject,
                "cooldown_temp": item.cooldown_temp,
                "startup_sound": item.startup_sound,
                "end_sound": item.end_sound,
                "notes": item.notes,
                "created_at": item.created_at.isoformat() if item.created_at else None
            })
        
        return {"bucket_items": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Error getting bucket list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{bucket_id}/to-queue")
async def move_bucket_to_queue(
    bucket_id: int, 
    request: MoveToQueueRequest = None,
    db: Session = Depends(get_db)
):
    """
    Move bucket item back to queue for printing
    """
    try:
        bucket_item = db.query(BucketList).filter(BucketList.bucket_id == bucket_id).first()
        if not bucket_item:
            raise HTTPException(status_code=404, detail=f"Bucket item not found: bucket_id={bucket_id}")
        
        # Get job info
        job = db.query(Job).filter(Job.job_id == bucket_item.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={bucket_item.job_id}")
        
        # Determine printer
        printer_id = request.printer_id if request and request.printer_id else bucket_item.printer_id
        
        # Get next position in queue
        max_position = db.query(Queue).filter(
            Queue.printer_id == printer_id
        ).count()
        new_position = max_position + 1
        
        # Create queue item with simplified settings from bucket
        queue_item = Queue(
            job_id=bucket_item.job_id,
            printer_id=printer_id,
            position_in_queue=new_position,
            ams_slot=bucket_item.ams_slot,
            ams_mapping=bucket_item.ams_mapping,
            use_ams=bucket_item.use_ams,
            filament_already_loaded=bucket_item.filament_already_loaded,
            auto_bed_leveling=bucket_item.auto_bed_leveling,
            flow_calibration=bucket_item.flow_calibration,
            timelapse=bucket_item.timelapse,
            status="pending"
        )
        
        db.add(queue_item)
        
        # Remove from bucket list
        db.delete(bucket_item)
        
        db.commit()
        db.refresh(queue_item)
        
        logger.info(f"Moved bucket to queue: bucket_id={bucket_id} -> queue_id={queue_item.queue_id}")
        
        return {
            "queue_id": queue_item.queue_id,
            "job_id": queue_item.job_id,
            "job_name": job.job_name,
            "position_in_queue": new_position,
            "message": "Job moved to queue"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving bucket to queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{bucket_id}")
async def remove_from_bucket(bucket_id: int, delete_file: bool = False, db: Session = Depends(get_db)):
    """
    Remove item from bucket list
    Optionally delete the job file as well
    """
    try:
        bucket_item = db.query(BucketList).filter(BucketList.bucket_id == bucket_id).first()
        if not bucket_item:
            raise HTTPException(status_code=404, detail=f"Bucket item not found: bucket_id={bucket_id}")
        
        job_id = bucket_item.job_id
        
        db.delete(bucket_item)
        db.commit()
        
        result = {"message": f"Removed from bucket list: bucket_id={bucket_id}", "file_deleted": False}
        
        # Optionally delete job file
        if delete_file:
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if job:
                # Check if job is not used elsewhere
                queue_count = db.query(Queue).filter(Queue.job_id == job_id).count()
                bucket_count = db.query(BucketList).filter(BucketList.job_id == job_id).count()
                
                if queue_count == 0 and bucket_count == 0:
                    from src.config import UPLOAD_DIR
                    import os
                    
                    file_path = UPLOAD_DIR / job.filename
                    if file_path.exists():
                        os.remove(str(file_path))
                        result["file_deleted"] = True
                    
                    db.delete(job)
                    db.commit()
        
        logger.info(f"Removed from bucket: bucket_id={bucket_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from bucket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{bucket_id}/notes")
async def update_bucket_notes(bucket_id: int, notes: str, db: Session = Depends(get_db)):
    """
    Update notes for a bucket item
    """
    try:
        bucket_item = db.query(BucketList).filter(BucketList.bucket_id == bucket_id).first()
        if not bucket_item:
            raise HTTPException(status_code=404, detail=f"Bucket item not found: bucket_id={bucket_id}")
        
        bucket_item.notes = notes
        db.commit()
        
        return {"message": "Notes updated", "bucket_id": bucket_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
