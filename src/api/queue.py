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
from src.database.db import PrintPreset
from src.services.queue_service import QueueService
from src.services.printer_service import PrinterService
from src.models.schemas import QueueResponse, PrintAutomationSettings
from src.config import QUEUE_FILES_DIR, UPLOAD_DIR
import logging

logger_obj = logging.getLogger(__name__)
router = APIRouter(prefix="/api/queue", tags=["queue"])


class AddToQueueRequest(BaseModel):
    """Request to add job to queue with automation settings"""
    job_id: int
    printer_id: str
    
    # Preset ID - if provided, ALL settings will be loaded from preset
    preset_id: Optional[int] = Field(default=None, description="Preset ID to use - if provided, ignores individual settings")
    
    # AMS settings
    ams_slot: int = Field(default=0, ge=0, le=255, description="AMS tray slot (0-3, or 255 for external spool)")
    ams_mapping: str = ""  # Full mapping for multi-color prints, e.g., "[0,1,2,3]"
    use_ams: bool = True  # Whether to use AMS (False = external spool)
    filament_already_loaded: bool = Field(default=False, description="Skip AMS load - filament already in extruder")
    
    # Template mode (NEW - RECOMMENDED)
    use_template_mode: bool = Field(default=True, description="Replace all start/end gcode with optimized templates")
    
    # Filament profile (optional - for temperature overrides)
    filament_id: Optional[int] = None
    
    # Print automation settings (ignored if preset_id is provided)
    start_machine: bool = Field(default=True, description="Enable start machine initialization")
    heat_bed_hotend: bool = Field(default=True, description="Preheat bed and hotend")
    auto_bed_leveling: bool = Field(default=True, description="Enable G29 bed leveling")
    flow_calibration: bool = Field(default=True, description="Enable flow test")
    vibration_test: bool = Field(default=False, description="Enable resonance test")
    clean_nozzle: bool = Field(default=True, description="Enable nozzle cleaning")
    wipe_nozzle: bool = Field(default=True, description="Enable wipe nozzle section (contains M109 S140 wait)")
    nozzle_load_line: bool = Field(default=True, description="Enable nozzle purge line at front of bed")
    timelapse: bool = Field(default=False, description="Enable timelapse recording during print")
    auto_eject: bool = Field(default=False, description="Auto push-off after print")
    cooldown_temp: int = Field(default=32, ge=25, le=50, description="Bed temp before eject")
    startup_sound: bool = Field(default=True, description="Play startup melody")
    end_sound: bool = Field(default=True, description="Play completion melody")
    
    # Quick Start options (FactorianDesigns optimization) - ENABLED BY DEFAULT
    quick_start: bool = Field(default=True, description="Skip vibration + flow for faster startup")
    preheat_offset: int = Field(default=20, ge=0, le=50, description="Preheat to nozzle_temp - offset (0=disabled, 20=recommended)")
    pre_extrude: bool = Field(default=True, description="Add pre-extrude command before print")
    pre_extrude_length: float = Field(default=2.2, ge=0.5, le=10.0, description="Pre-extrude length in mm")


class UpdateQueuePositionRequest(BaseModel):
    """Request to update queue position"""
    new_position: int


class UpdateQueueSettingsRequest(BaseModel):
    """Request to update queue item settings"""
    # AMS settings
    ams_slot: Optional[int] = None
    ams_mapping: Optional[str] = None
    use_ams: Optional[bool] = None
    filament_already_loaded: Optional[bool] = None
    
    # Filament profile
    filament_id: Optional[int] = None
    
    # Print automation settings
    auto_bed_leveling: Optional[bool] = None
    flow_calibration: Optional[bool] = None
    vibration_test: Optional[bool] = None
    clean_nozzle: Optional[bool] = None
    wipe_nozzle: Optional[bool] = None
    nozzle_load_line: Optional[bool] = None
    timelapse: Optional[bool] = None
    auto_eject: Optional[bool] = None
    cooldown_temp: Optional[int] = None
    startup_sound: Optional[bool] = None
    end_sound: Optional[bool] = None
    
    # Quick Start options (FactorianDesigns optimization)
    quick_start: Optional[bool] = None
    preheat_offset: Optional[int] = None
    pre_extrude: Optional[bool] = None
    pre_extrude_length: Optional[float] = None


@router.post("/add")
async def add_job_to_queue(
    request: AddToQueueRequest,
    db: Session = Depends(get_db)
):
    """
    Add job to print queue with automation settings
    
    - **job_id**: The job to queue
    - **printer_id**: Target printer
    - **preset_id**: Preset ID - if provided, ALL template settings are loaded from preset
    - **ams_slot**: AMS tray slot (0-3 for AMS Lite, 255 for external spool)
    - **ams_mapping**: Full AMS mapping string for multi-color prints
    - **use_ams**: Whether to use AMS (False = external spool)
    - **filament_id**: Optional filament profile for temperature overrides
    
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
        
        # Initialize settings with request values as defaults
        start_machine = request.start_machine
        heat_bed_hotend = request.heat_bed_hotend
        auto_bed_leveling = request.auto_bed_leveling
        flow_calibration = request.flow_calibration
        vibration_test = request.vibration_test
        clean_nozzle = request.clean_nozzle
        wipe_nozzle = request.wipe_nozzle
        nozzle_load_line = request.nozzle_load_line
        timelapse = request.timelapse
        auto_eject = request.auto_eject
        cooldown_temp = request.cooldown_temp
        startup_sound = request.startup_sound
        end_sound = request.end_sound
        quick_start = request.quick_start
        preheat_offset = request.preheat_offset
        pre_extrude = request.pre_extrude
        pre_extrude_length = request.pre_extrude_length
        
        # NEW controllable templates - default values
        cog_noise_reduction = True
        brush_material_wipe = True
        final_wipe_nozzle = True
        avoid_end_stop = True
        reset_machine_status = True
        home_after_wipe = True
        prepare_print = True
        extrude_calibration_test = True
        turn_off_light = False  # Default off
        final_start = True
        
        # If preset_id is provided, load ALL settings from preset
        if request.preset_id:
            preset = db.query(PrintPreset).filter(PrintPreset.preset_id == request.preset_id).first()
            if not preset:
                raise HTTPException(
                    status_code=404,
                    detail=f"Preset not found: preset_id={request.preset_id}"
                )
            
            logger_obj.info(f"📋 Loading settings from preset: {preset.name} (preset_id={preset.preset_id})")
            
            # Load ALL settings from preset
            start_machine = getattr(preset, 'start_machine', True)
            heat_bed_hotend = getattr(preset, 'heat_bed_hotend', True)
            auto_bed_leveling = getattr(preset, 'auto_bed_leveling', True)
            flow_calibration = getattr(preset, 'flow_calibration', True)
            vibration_test = getattr(preset, 'vibration_test', False)
            clean_nozzle = getattr(preset, 'clean_nozzle', True)
            wipe_nozzle = getattr(preset, 'wipe_nozzle', True)
            nozzle_load_line = getattr(preset, 'nozzle_load_line', True)
            timelapse = getattr(preset, 'timelapse', False)
            auto_eject = getattr(preset, 'auto_eject', False)
            cooldown_temp = getattr(preset, 'cooldown_temp', 32)
            startup_sound = getattr(preset, 'startup_sound', True)
            end_sound = getattr(preset, 'end_sound', True)
            quick_start = getattr(preset, 'quick_start', False)
            preheat_offset = getattr(preset, 'preheat_offset', 20)
            pre_extrude = getattr(preset, 'pre_extrude', True)
            pre_extrude_length = getattr(preset, 'pre_extrude_length', 2.2)
            
            # NEW controllable templates from preset
            cog_noise_reduction = getattr(preset, 'cog_noise_reduction', True)
            brush_material_wipe = getattr(preset, 'brush_material_wipe', True)
            final_wipe_nozzle = getattr(preset, 'final_wipe_nozzle', True)
            avoid_end_stop = getattr(preset, 'avoid_end_stop', True)
            reset_machine_status = getattr(preset, 'reset_machine_status', True)
            home_after_wipe = getattr(preset, 'home_after_wipe', True)
            prepare_print = getattr(preset, 'prepare_print', True)
            extrude_calibration_test = getattr(preset, 'extrude_calibration_test', True)
            turn_off_light = getattr(preset, 'turn_off_light', False)
            final_start = getattr(preset, 'final_start', True)
            
            logger_obj.info(f"📋 Preset settings: quick_start={quick_start}, flow_calibration={flow_calibration}, "
                          f"cog_noise_reduction={cog_noise_reduction}, brush_material_wipe={brush_material_wipe}")
        
        # Validate: auto_eject requires flow_calibration OFF
        if auto_eject and flow_calibration:
            logger_obj.info("Auto eject enabled, disabling flow_calibration to prevent debris")
            flow_calibration = False
        
        # Add to queue with AMS and automation settings
        queue_service = QueueService(db)
        queue_item = queue_service.add_job_to_queue(
            job_id=request.job_id,
            printer_id=request.printer_id,
            loop_count=1,  # Will be set based on job's loop_count
            ams_slot=request.ams_slot,
            ams_mapping=request.ams_mapping,
            use_ams=request.use_ams,
            filament_already_loaded=request.filament_already_loaded,
            use_template_mode=request.use_template_mode,  # NEW: Template mode
            filament_id=request.filament_id,
            # Automation settings (from preset or request)
            start_machine=start_machine,
            heat_bed_hotend=heat_bed_hotend,
            auto_bed_leveling=auto_bed_leveling,
            flow_calibration=flow_calibration,
            vibration_test=vibration_test,
            clean_nozzle=clean_nozzle,
            wipe_nozzle=wipe_nozzle,
            nozzle_load_line=nozzle_load_line,
            timelapse=timelapse,
            auto_eject=auto_eject,
            cooldown_temp=cooldown_temp,
            startup_sound=startup_sound,
            end_sound=end_sound,
            # Quick Start options
            quick_start=quick_start,
            preheat_offset=preheat_offset,
            pre_extrude=pre_extrude,
            pre_extrude_length=pre_extrude_length,
            # NEW: Controllable templates
            cog_noise_reduction=cog_noise_reduction,
            brush_material_wipe=brush_material_wipe,
            final_wipe_nozzle=final_wipe_nozzle,
            avoid_end_stop=avoid_end_stop,
            reset_machine_status=reset_machine_status,
            home_after_wipe=home_after_wipe,
            prepare_print=prepare_print,
            extrude_calibration_test=extrude_calibration_test,
            turn_off_light=turn_off_light,
            final_start=final_start
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
            # Automation settings
            "filament_id": queue_item.filament_id,
            "auto_bed_leveling": queue_item.auto_bed_leveling,
            "flow_calibration": queue_item.flow_calibration,
            "vibration_test": queue_item.vibration_test,
            "clean_nozzle": queue_item.clean_nozzle,
            "nozzle_load_line": queue_item.nozzle_load_line,
            "auto_eject": queue_item.auto_eject,
            "cooldown_temp": queue_item.cooldown_temp,
            "startup_sound": queue_item.startup_sound,
            "end_sound": queue_item.end_sound,
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
    Update queue item settings (AMS slot, automation settings)
    Only works for pending status items.
    When automation settings change, regenerates the queue file with updated G-code.
    """
    from src.database.db import Queue, Job
    
    try:
        queue_item = db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            raise HTTPException(status_code=404, detail=f"Queue item not found: queue_id={queue_id}")
        
        if queue_item.status != "pending":
            raise HTTPException(status_code=400, detail="Can only edit pending queue items")
        
        # Track if automation settings changed (need to regenerate queue file)
        automation_changed = False
        
        # Update only provided fields
        if request.ams_slot is not None:
            if request.ams_slot != queue_item.ams_slot:
                automation_changed = True
            queue_item.ams_slot = request.ams_slot
        if request.ams_mapping is not None:
            queue_item.ams_mapping = request.ams_mapping
        if request.use_ams is not None:
            if request.use_ams != queue_item.use_ams:
                automation_changed = True
            queue_item.use_ams = request.use_ams
        if request.filament_already_loaded is not None:
            if request.filament_already_loaded != queue_item.filament_already_loaded:
                automation_changed = True
            queue_item.filament_already_loaded = request.filament_already_loaded
        if request.filament_id is not None:
            queue_item.filament_id = request.filament_id
        
        # Automation settings - track changes
        if request.auto_bed_leveling is not None and request.auto_bed_leveling != queue_item.auto_bed_leveling:
            queue_item.auto_bed_leveling = request.auto_bed_leveling
            automation_changed = True
        if request.flow_calibration is not None and request.flow_calibration != queue_item.flow_calibration:
            queue_item.flow_calibration = request.flow_calibration
            automation_changed = True
        if request.vibration_test is not None and request.vibration_test != queue_item.vibration_test:
            queue_item.vibration_test = request.vibration_test
            automation_changed = True
        if request.clean_nozzle is not None and request.clean_nozzle != queue_item.clean_nozzle:
            queue_item.clean_nozzle = request.clean_nozzle
            automation_changed = True
        if request.wipe_nozzle is not None and request.wipe_nozzle != queue_item.wipe_nozzle:
            queue_item.wipe_nozzle = request.wipe_nozzle
            automation_changed = True
        if request.nozzle_load_line is not None and request.nozzle_load_line != queue_item.nozzle_load_line:
            queue_item.nozzle_load_line = request.nozzle_load_line
            automation_changed = True
        if request.auto_eject is not None:
            queue_item.auto_eject = request.auto_eject
        if request.cooldown_temp is not None:
            queue_item.cooldown_temp = request.cooldown_temp
        if request.startup_sound is not None and request.startup_sound != queue_item.startup_sound:
            queue_item.startup_sound = request.startup_sound
            automation_changed = True
        if request.end_sound is not None and request.end_sound != queue_item.end_sound:
            queue_item.end_sound = request.end_sound
            automation_changed = True
        
        # Regenerate queue file if automation settings changed
        queue_file_regenerated = False
        if automation_changed:
            try:
                # Get the job to find source file
                job = db.query(Job).filter(Job.job_id == queue_item.job_id).first()
                if job:
                    source_file = UPLOAD_DIR / job.filename
                    if source_file.exists() and source_file.suffix.lower() == '.3mf':
                        queue_service = QueueService(db)
                        
                        # Generate new queue filename
                        queue_filename = f"queue_{queue_item.position_in_queue}_{job.filename}"
                        queue_file_path = QUEUE_FILES_DIR / queue_filename
                        
                        # Delete old queue file if exists
                        if queue_item.queue_file_path:
                            old_path = Path(queue_item.queue_file_path)
                            if old_path.exists():
                                old_path.unlink()
                        
                        # Create new modified file with all settings
                        new_path = queue_service._create_modified_queue_file(
                            source_file=source_file,
                            dest_file=queue_file_path,
                            auto_bed_leveling=queue_item.auto_bed_leveling,
                            flow_calibration=queue_item.flow_calibration,
                            vibration_test=queue_item.vibration_test,
                            clean_nozzle=queue_item.clean_nozzle,
                            wipe_nozzle=queue_item.wipe_nozzle,
                            nozzle_load_line=queue_item.nozzle_load_line,
                            startup_sound=queue_item.startup_sound,
                            end_sound=queue_item.end_sound,
                            use_ams=queue_item.use_ams,
                            ams_slot=queue_item.ams_slot,
                            filament_already_loaded=queue_item.filament_already_loaded,
                            # Filament profile for temperature overrides
                            filament_id=queue_item.filament_id
                        )
                        queue_item.queue_file_path = new_path
                        queue_file_regenerated = True
                        logger_obj.info(f"Regenerated queue file: {new_path}")
            except Exception as e:
                logger_obj.warning(f"Failed to regenerate queue file: {e}")
        
        db.commit()
        
        msg = f"Updated settings for queue_id={queue_id}"
        if queue_file_regenerated:
            msg += " (queue file regenerated)"
        
        logger_obj.info(msg)
        return {
            "message": msg,
            "queue_file_path": queue_item.queue_file_path,
            "queue_file_regenerated": queue_file_regenerated
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
