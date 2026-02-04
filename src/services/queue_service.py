"""
Queue Service - Manage print queue and job ordering
Follows naming conventions from README.md
"""
from datetime import datetime
from pathlib import Path
import shutil
from sqlalchemy.orm import Session
from src.database.db import Queue, Job
from src.models.schemas import QueueItemCreate, QueueItemResponse
from src.config import UPLOAD_DIR, QUEUE_FILES_DIR, OUTPUT_DIR
import logging
import os

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing print queue"""

    def __init__(self, db: Session):
        self.db = db

    def add_job_to_queue(
        self, 
        job_id: int, 
        printer_id: str, 
        loop_count: int, 
        # AMS settings
        ams_slot: int = 0, 
        ams_mapping: str = "", 
        use_ams: bool = True,
        filament_already_loaded: bool = False,
        # Print settings (3 checkboxes from UI)
        auto_bed_leveling: bool = True,
        flow_calibration: bool = False,
        timelapse: bool = False,
        # Skip preprocessing (file sudah dari slicer)
        skip_preprocessing: bool = True
    ) -> dict:
        """
        Add job to print queue - simplified (no templates, no presets)
        
        File dari slicer langsung dikirim ke printer tanpa modifikasi.
        Hanya simpan 3 setting untuk display di queue: bed leveling, flow cal, timelapse.
        
        Args:
            job_id: The job to add
            printer_id: Target printer
            loop_count: Number of loops for this job
            ams_slot: AMS tray slot (0-3 for AMS Lite)
            use_ams: Whether to use AMS
            filament_already_loaded: Skip AMS load sequence
            auto_bed_leveling: Enable bed leveling (for display only)
            flow_calibration: Enable flow calibration (for display only)
            timelapse: Enable timelapse (for display only)
            skip_preprocessing: Always True - skip all file modification
            
        Returns:
            Queue entry with queue_id, position_in_queue
        """
        # Get current queue size to determine position_in_queue
        queue_size = self.db.query(Queue).filter(Queue.printer_id == printer_id).count()
        position_in_queue = queue_size + 1
        
        # Generate ams_mapping if not provided but ams_slot is set
        if not ams_mapping and use_ams:
            # Simple single-color mapping: "[slot]"
            ams_mapping = f"[{ams_slot}]"
        
        # Get job to find source file
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            raise ValueError(f"Job not found: job_id={job_id}")
        
        # Create queue file path - unique per queue entry
        source_file = UPLOAD_DIR / job.filename
        queue_filename = f"queue_{position_in_queue}_{job.filename}"
        queue_file_path = QUEUE_FILES_DIR / queue_filename
        
        # SKIP ALL PREPROCESSING - Just copy file as-is dari slicer
        logger.info(f"✅ Skip preprocessing - copying file as-is from slicer: {source_file.name}")
        if source_file.exists():
            shutil.copy(source_file, queue_file_path)
            queue_file_path_str = str(queue_file_path)
        else:
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        # Create queue entry - simplified (only 3 settings + AMS)
        queue_record = Queue(
            job_id=job_id,
            printer_id=printer_id,
            position_in_queue=position_in_queue,
            current_loop=0,
            status="pending",
            # AMS settings
            ams_slot=ams_slot,
            ams_mapping=ams_mapping,
            use_ams=use_ams,
            filament_already_loaded=filament_already_loaded,
            # Print settings (3 checkboxes)
            auto_bed_leveling=auto_bed_leveling,
            flow_calibration=flow_calibration,
            timelapse=timelapse,
            # Skip preprocessing (always True)
            skip_preprocessing=skip_preprocessing,
            # Queue file path
            queue_file_path=queue_file_path_str,
            # Timestamps
            created_at=datetime.utcnow(),
            started_at=None,
            completed_at=None
        )
        
        self.db.add(queue_record)
        self.db.commit()
        self.db.refresh(queue_record)
        
        logger.info(
            f"✅ Added job to queue: job_id={job_id}, printer_id={printer_id}, "
            f"position={position_in_queue}, ams_slot={ams_slot}, use_ams={use_ams}, "
            f"bed_level={auto_bed_leveling}, flow_cal={flow_calibration}, timelapse={timelapse}"
        )
        
        return {
            "queue_id": queue_record.queue_id,
            "job_id": queue_record.job_id,
            "position_in_queue": queue_record.position_in_queue,
            "status": queue_record.status,
            # AMS settings
            "ams_slot": queue_record.ams_slot,
            "ams_mapping": queue_record.ams_mapping,
            "use_ams": queue_record.use_ams,
            "filament_already_loaded": queue_record.filament_already_loaded,
            # Print settings (3 checkboxes)
            "auto_bed_leveling": queue_record.auto_bed_leveling,
            "flow_calibration": queue_record.flow_calibration,
            "timelapse": queue_record.timelapse,
            # Queue file
            "queue_file_path": queue_record.queue_file_path
        }

    def get_next_job(self, printer_id: str) -> dict:
        """
        Get next job from queue for printer (FIFO order)
        
        Returns next job with smallest position_in_queue
        """
        queue_item = self.db.query(Queue).filter(
            Queue.printer_id == printer_id,
            Queue.status == "pending"
        ).order_by(Queue.position_in_queue).first()
        
        if not queue_item:
            return None
        
        # Get job details
        job = self.db.query(Job).filter(Job.job_id == queue_item.job_id).first()
        
        return {
            "queue_id": queue_item.queue_id,
            "job_id": queue_item.job_id,
            "job_name": job.job_name,
            "position_in_queue": queue_item.position_in_queue,
            "current_loop": queue_item.current_loop,
            "loop_count": job.loop_count,
            "status": queue_item.status
        }

    def start_queue_job(self, queue_id: int) -> bool:
        """
        Start queue job: Upload file to SD card via FTPS, then start printing
        
        Workflow:
        1. Preprocess G-code with automation settings
        2. Upload 3MF file to printer SD card via FTPS
        3. Send MQTT project_file command to start printing
        """
        from src.services.ftps_service import BambuFTPSClient
        from src.services.bambu_service import get_bambu_client
        from src.config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE
        from pathlib import Path
        import tempfile
        import shutil
        
        queue_item = self.db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            logger.error(f"Queue item not found: queue_id={queue_id}")
            return False
        
        # Get job details
        job = self.db.query(Job).filter(Job.job_id == queue_item.job_id).first()
        if not job:
            logger.error(f"Job not found: job_id={queue_item.job_id}")
            return False
        
        # Get file path
        upload_dir = Path(__file__).parent.parent.parent / "data" / "uploads"
        file_path = upload_dir / job.filename
        
        logger.info(f"📋 Starting queue job: queue_id={queue_id}, job={job.job_name}, file={job.filename}")
        
        if not file_path.exists():
            logger.error(f"❌ File not found: {file_path}")
            queue_item.status = "error"
            self.db.commit()
            return False
        
        # ==================== FILE HANDLING ====================
        # Files are sent AS-IS from slicer without modification
        logger.info(f"📤 Using file as-is from slicer (no preprocessing)")
        
        # ==================== FTPS UPLOAD ====================
        try:
            # Status should already be 'uploading' (set by API before background task)
            # Just ensure it's set
            if queue_item.status != "uploading":
                queue_item.status = "uploading"
                self.db.commit()
                logger.info(f"📤 Status changed to 'uploading' for queue_id={queue_id}")
            
            # Step 1: Upload file to printer SD card via FTPS
            logger.info(f"📤 Step 1: Uploading file to SD card: {job.filename}")
            
            ftps_client = BambuFTPSClient(
                host=BAMBU_PRINTER_IP,
                access_code=BAMBU_ACCESS_CODE,
                port=990,
                timeout=60
            )
            
            with ftps_client as ftp:
                logger.info(f"FTPS connected to {BAMBU_PRINTER_IP}:990")
                success = ftp.upload_file(str(file_path), job.filename)
                logger.info(f"FTPS upload result: {success}")
                
                if not success:
                    logger.error(f"❌ FTPS upload failed: {job.filename}")
                    queue_item.status = "error"
                    self.db.commit()
                    return False
            
            logger.info(f"✅ File uploaded to SD card: {job.filename}")
            
            # Step 2: Send MQTT command to start printing
            logger.info(f"🚀 Step 2: Sending print command via MQTT...")
            
            bambu_client = get_bambu_client()
            if not bambu_client or not bambu_client.mqtt_connected:
                logger.error("❌ MQTT client not connected")
                queue_item.status = "error"
                self.db.commit()
                return False
            
            # Get AMS settings from queue item
            use_ams = queue_item.use_ams if hasattr(queue_item, 'use_ams') else True
            ams_slot = queue_item.ams_slot if hasattr(queue_item, 'ams_slot') else 0
            
            # Get calibration settings from queue item (3 checkboxes only)
            auto_bed_leveling = queue_item.auto_bed_leveling if hasattr(queue_item, 'auto_bed_leveling') else True
            flow_calibration = queue_item.flow_calibration if hasattr(queue_item, 'flow_calibration') else False
            timelapse = queue_item.timelapse if hasattr(queue_item, 'timelapse') else False
            
            logger.info(f"   AMS settings: use_ams={use_ams}, ams_slot={ams_slot}")
            logger.info(f"   Calibration: bed_leveling={auto_bed_leveling}, flow_cali={flow_calibration}, timelapse={timelapse}")
            logger.info(f"   vibration_cali=False (always) - settings from slicer")
            
            # Start print from SD card with simplified settings
            # CRITICAL: Pass ams_slot as integer, bambu_service will convert to proper list format
            print_success = bambu_client.start_print_from_sd(
                filename=job.filename,
                use_ams=use_ams,
                plate_number=1,
                ams_mapping=None,  # Let bambu_service convert from ams_slot
                ams_slot=ams_slot,
                flow_cali=flow_calibration,
                vibration_cali=False,  # Always False - settings from slicer
                bed_leveling=auto_bed_leveling,
                layer_inspect=False,
                timelapse=timelapse
            )
            
            if not print_success:
                logger.error(f"❌ Failed to start print: {job.filename}")
                queue_item.status = "error"
                self.db.commit()
                return False
            
            # Mark queue item as running AFTER print command sent successfully
            queue_item.status = "running"
            queue_item.started_at = datetime.utcnow()
            
            # Increment current_loop when starting print (not after completion)
            queue_item.current_loop += 1
            logger.info(f"📊 Starting loop {queue_item.current_loop}")
            
            # Also update Job table current_loop for display consistency
            job.current_loop = queue_item.current_loop
            
            self.db.commit()
            
            logger.info(f"✅ Print started successfully: queue_id={queue_id}, file={job.filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error uploading to SD card: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            queue_item.status = "error"
            self.db.commit()
            return False

    def increment_current_loop(self, queue_id: int) -> bool:
        """Increment current_loop for queue item"""
        queue_item = self.db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            return False
        
        queue_item.current_loop += 1
        self.db.commit()
        
        logger.info(f"Incremented loop: queue_id={queue_id}, current_loop={queue_item.current_loop}")
        return True

    def should_repeat_queue_job(self, queue_id: int) -> bool:
        """Check if queue job should repeat (current_loop < loop_count)"""
        queue_item = self.db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            return False
        
        job = self.db.query(Job).filter(Job.job_id == queue_item.job_id).first()
        
        return queue_item.current_loop < job.loop_count

    def complete_queue_job(self, queue_id: int) -> bool:
        """Mark queue item as completed"""
        queue_item = self.db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            return False
        
        queue_item.status = "completed"
        queue_item.completed_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Completed queue job: queue_id={queue_id}")
        return True

    def get_printer_queue(self, printer_id: str) -> list:
        """Get all queue items for printer, ordered by position_in_queue"""
        queue_items = self.db.query(Queue).filter(
            Queue.printer_id == printer_id
        ).order_by(Queue.position_in_queue).all()
        
        result = []
        for item in queue_items:
            job = self.db.query(Job).filter(Job.job_id == item.job_id).first()
            result.append({
                "queue_id": item.queue_id,
                "job_id": item.job_id,
                "job_name": job.job_name,
                "position_in_queue": item.position_in_queue,
                "current_loop": item.current_loop,
                "loop_count": job.loop_count,
                "status": item.status
            })
        
        return result

    def update_queue_position(self, queue_id: int, new_position: int) -> bool:
        """
        Update position_in_queue for queue item (for manual reordering)
        Swaps positions with the item currently at new_position
        """
        queue_item = self.db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            return False
        
        # Only allow reordering pending items
        if queue_item.status != "pending":
            return False
        
        old_position = queue_item.position_in_queue
        
        # Find the item at the target position (same printer)
        target_item = self.db.query(Queue).filter(
            Queue.printer_id == queue_item.printer_id,
            Queue.position_in_queue == new_position,
            Queue.queue_id != queue_id
        ).first()
        
        # Swap positions
        if target_item:
            target_item.position_in_queue = old_position
        
        queue_item.position_in_queue = new_position
        self.db.commit()
        
        logger.info(f"Updated queue position: queue_id={queue_id}, old={old_position}, new={new_position}")
        return True

    def remove_from_queue(self, queue_id: int, delete_file: bool = False) -> dict:
        """
        Remove item from queue
        
        Args:
            queue_id: Queue item ID to remove
            delete_file: If True, also delete the job and its file from server
            
        Returns:
            dict with success status and what was deleted
        """
        queue_item = self.db.query(Queue).filter(Queue.queue_id == queue_id).first()
        if not queue_item:
            return {"success": False}
        
        result = {
            "success": True,
            "queue_deleted": True,
            "job_deleted": False,
            "file_deleted": False
        }
        
        # Get job info before deleting queue item
        job_id = queue_item.job_id
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        
        # Delete queue item first
        self.db.delete(queue_item)
        self.db.commit()
        logger.info(f"Removed from queue: queue_id={queue_id}")
        
        # If delete_file is True, also delete the job and file
        if delete_file and job:
            filename = job.filename
            
            # Check if this job is used by other queue items
            other_queue_items = self.db.query(Queue).filter(Queue.job_id == job_id).count()
            
            if other_queue_items == 0:
                # Delete the file from server
                try:
                    file_path = UPLOAD_DIR / filename
                    if file_path.exists():
                        os.remove(str(file_path))
                        result["file_deleted"] = True
                        logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete file {filename}: {e}")
                
                # Delete the job from database
                try:
                    self.db.delete(job)
                    self.db.commit()
                    result["job_deleted"] = True
                    logger.info(f"Deleted job: job_id={job_id}")
                except Exception as e:
                    logger.error(f"Failed to delete job {job_id}: {e}")
        
        return result

    def get_queue_status(self, printer_id: str) -> dict:
        """Get queue statistics for printer"""
        total_items = self.db.query(Queue).filter(Queue.printer_id == printer_id).count()
        pending_items = self.db.query(Queue).filter(
            Queue.printer_id == printer_id,
            Queue.status == "pending"
        ).count()
        running_items = self.db.query(Queue).filter(
            Queue.printer_id == printer_id,
            Queue.status == "running"
        ).count()
        completed_items = self.db.query(Queue).filter(
            Queue.printer_id == printer_id,
            Queue.status == "completed"
        ).count()
        
        return {
            "printer_id": printer_id,
            "total_items": total_items,
            "pending_items": pending_items,
            "running_items": running_items,
            "completed_items": completed_items
        }
