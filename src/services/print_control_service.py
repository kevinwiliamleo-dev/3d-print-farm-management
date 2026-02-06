"""
Print Control Service - Orchestrate printing workflow
Handles job execution and loop management
Follows naming conventions from README.md
"""
import logging
import os
import tempfile
import shutil
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.db import Queue, Job, PrintHistory
from src.services.bambu_service import BambuLabMQTTClient

logger = logging.getLogger(__name__)

def print_log(message: str, level: str = "INFO"):
    """Print logging for printing operations - always prints to console"""
    prefix = {
        "INFO": "🖨️",
        "START": "▶️",
        "PAUSE": "⏸️",
        "RESUME": "▶️",
        "STOP": "⏹️",
        "CANCEL": "❌",
        "SUCCESS": "✅",
        "ERROR": "🔴",
        "WARNING": "⚠️",
        "PROGRESS": "📊",
    }.get(level, "📋")
    print(f"{prefix} [PRINT] {message}")
    logger.info(f"[PRINT] {message}")


class PrintControlService:
    """Service for managing print execution workflow"""

    def __init__(self, db: Session, bambu_client: BambuLabMQTTClient):
        """
        Initialize print control service
        
        Args:
            db: Database session
            bambu_client: Bambu Lab MQTT client
        """
        self.db = db
        self.bambu_client = bambu_client
        self.current_queue_id = None
        self.current_job_id = None
        self.print_start_time = None
        self._processing_completion = False  # Guard flag to prevent re-entry
        self._last_running_time = {}  # Track when each queue started running (queue_id -> timestamp)
        
        # Setup print completion callback
        self.bambu_client.on_print_complete = self._on_print_complete_callback
    
    def _on_print_complete_callback(self):
        """
        Called by MQTT client when printer becomes idle after printing
        Simple logic: printer went from printing/paused → idle, so handle completion
        
        Guard against multiple callbacks for same event
        """
        # Prevent re-entry if already processing a completion
        if self._processing_completion:
            logger.warning("⚠️ Already processing completion, ignoring duplicate callback")
            return
        
        try:
            self._processing_completion = True  # Set guard flag
            logger.info("🎉 Printer became idle - checking for job completion")
            
            # Find any running/paused queue item
            active_queue = self.db.query(Queue).filter(
                Queue.status.in_(["running", "paused"])
            ).first()
            
            if active_queue:
                # Validate print has been running for minimum duration (prevent false completion during upload/start)
                from datetime import datetime, timezone
                import time
                
                queue_id = active_queue.queue_id
                current_time = time.time()
                
                # Check if we have tracked start time for this queue
                if queue_id in self._last_running_time:
                    elapsed_time = current_time - self._last_running_time[queue_id]
                    
                    # Require minimum 30 seconds of runtime before allowing completion
                    # This prevents false completion during upload->start transition
                    if elapsed_time < 30:
                        logger.warning(f"⚠️ Print only ran for {elapsed_time:.1f}s, ignoring premature completion")
                        return
                
                logger.info(f"Found active queue {queue_id}, marking as completed")
                self.current_queue_id = queue_id
                self.current_job_id = active_queue.job_id
                self.handle_print_completion(active_queue.printer_id)
                
                # Clear tracked start time after completion
                if queue_id in self._last_running_time:
                    del self._last_running_time[queue_id]
            else:
                # No active job, but printer is idle - check if there's pending job
                logger.info("No active job, checking for pending jobs to start")
                pending_queue = self.db.query(Queue).filter(
                    Queue.status == "pending"
                ).order_by(Queue.position_in_queue).first()
                
                if pending_queue:
                    logger.info(f"Found pending job {pending_queue.queue_id}, starting it")
                    self.start_next_job(pending_queue.printer_id)
                else:
                    logger.info("No pending jobs in queue")
                    
        except Exception as e:
            logger.error(f"Error in print complete callback: {str(e)}")
            logger.error(f"Error in print completion callback: {e}")
        finally:
            # Always clear guard flag when done (even on error)
            self._processing_completion = False
    
    # Print settings removed - use values from slicer
    
    # File preprocessing removed - files sent AS-IS from slicer

    def start_next_job(self, printer_id: str) -> bool:
        """
        Get next job from queue and start printing
        
        Args:
            printer_id: Target printer ID
            
        Returns: True if job started successfully
        """
        try:
            # Get next job from queue
            queue_item = self.db.query(Queue).filter(
                Queue.printer_id == printer_id,
                Queue.status == "pending"
            ).order_by(Queue.position_in_queue).first()
            
            if not queue_item:
                print_log(f"No pending jobs in queue for printer_id={printer_id}", "INFO")
                return False
            
            # Get job details
            job = self.db.query(Job).filter(Job.job_id == queue_item.job_id).first()
            if not job:
                print_log(f"Job not found: job_id={queue_item.job_id}", "ERROR")
                return False
            
            print_log(f"========================================", "START")
            print_log(f"STARTING PRINT JOB", "START")
            print_log(f"========================================", "START")
            print_log(f"Job Name: {job.job_name}", "INFO")
            print_log(f"Printer ID: {printer_id}", "INFO")
            print_log(f"Queue ID: {queue_item.queue_id}", "INFO")
            print_log(f"Loop: {queue_item.current_loop + 1}/{job.loop_count}", "INFO")
            
            # Update queue status to UPLOADING first (not running)
            queue_item.status = "uploading"
            queue_item.started_at = datetime.utcnow()
            self.db.commit()
            
            # Update job status to uploading
            job.status = "uploading"
            job.updated_at = datetime.utcnow()
            self.db.commit()
            
            print_log(f"Status changed to UPLOADING", "PROGRESS")
            
            # Store current job info
            self.current_queue_id = queue_item.queue_id
            self.current_job_id = job.job_id
            self.print_start_time = datetime.utcnow()
            
            # Determine file path - check for both .gcode and .3mf
            gcode_path = f"data/gcode/{job.job_name}.gcode"
            threemf_path = f"data/uploads/{job.filename}"
            
            # Prefer .gcode if exists, otherwise use original .3mf
            if os.path.exists(gcode_path):
                file_path = gcode_path
                logger.info(f"Using gcode file: {gcode_path}")
            elif os.path.exists(threemf_path):
                file_path = threemf_path
                logger.info(f"Using 3mf file directly: {threemf_path}")
            else:
                logger.error(f"No print file found for job: {job.job_name}")
                job.status = "failed"
                queue_item.status = "failed"
                self.db.commit()
                return False
            
            # ==================== FILE UPLOAD ====================
            # Files are sent AS-IS from slicer without modification
            logger.info(f"📤 Using original file from slicer (no preprocessing)")
            print_log(f"Sending file as-is without modifications", "INFO")
            
            # Upload file to printer SD card via FTPS
            logger.info(f"📤 Uploading file to printer SD card: {file_path}")
            from src.services.ftps_service import BambuFTPSClient
            from src.api.websocket import broadcast_upload_progress_sync
            from src.database.db import Printer
            
            # Get printer details from database (don't use empty config values)
            printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
            if not printer or not printer.ip or not printer.access_code:
                logger.error(f"❌ Printer not found or missing IP/access_code: {printer_id}")
                job.status = "failed"
                queue_item.status = "failed"
                self.db.commit()
                return False
            
            try:
                ftps_client = BambuFTPSClient(
                    host=printer.ip,
                    access_code=printer.access_code,
                    port=990,
                    timeout=60
                )
                
                with ftps_client as ftp:
                    remote_filename = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    # Progress callback that broadcasts to WebSocket
                    def upload_progress_callback(bytes_sent: int, total_bytes: int):
                        percent = int((bytes_sent / total_bytes) * 100) if total_bytes > 0 else 0
                        progress_data = {
                            "percent": percent,
                            "bytes_sent": bytes_sent,
                            "total_bytes": total_bytes,
                            "filename": remote_filename,
                            "status": "uploading" if percent < 100 else "complete"
                        }
                        logger.info(f"📤 Upload progress: {percent}% ({bytes_sent}/{total_bytes})")
                        broadcast_upload_progress_sync(printer_id, progress_data)
                    
                    # Broadcast upload start
                    broadcast_upload_progress_sync(printer_id, {
                        "percent": 0,
                        "bytes_sent": 0,
                        "total_bytes": file_size,
                        "filename": remote_filename,
                        "status": "starting"
                    })
                    
                    upload_success = ftp.upload_file(file_path, remote_filename, upload_progress_callback)
                    
                    if not upload_success:
                        logger.error(f"❌ Failed to upload file to printer: {file_path}")
                        # Broadcast upload failed
                        broadcast_upload_progress_sync(printer_id, {
                            "percent": 0,
                            "bytes_sent": 0,
                            "total_bytes": file_size,
                            "filename": remote_filename,
                            "status": "failed"
                        })
                        job.status = "failed"
                        queue_item.status = "failed"
                        self.db.commit()
                        return False
                    
                    # Broadcast upload complete
                    broadcast_upload_progress_sync(printer_id, {
                        "percent": 100,
                        "bytes_sent": file_size,
                        "total_bytes": file_size,
                        "filename": remote_filename,
                        "status": "complete"
                    })
                    logger.info(f"✅ File uploaded successfully: {remote_filename}")
                
                # Small delay to ensure file is registered on SD card
                import time
                
                # Broadcast starting print status
                broadcast_upload_progress_sync(printer_id, {
                    "percent": 100,
                    "bytes_sent": file_size,
                    "total_bytes": file_size,
                    "filename": remote_filename,
                    "status": "starting_print"
                })
                
                time.sleep(2)
                
                # Send MQTT command to start printing from SD card using correct format
                print_log(f"Sending MQTT command to start print...", "START")
                print_log(f"File: {remote_filename}", "INFO")
                print_log(f"AMS: use_ams={queue_item.use_ams}, slot={queue_item.ams_slot}", "INFO")
                print_log(f"Settings: bed_leveling={queue_item.auto_bed_leveling}, flow_cali={queue_item.flow_calibration}, timelapse={queue_item.timelapse}", "INFO")
                
                # Use proper "project_file" MQTT command with full parameters
                # This is the MQTT command that Bambu Lab firmware actually recognizes
                # Calibration settings: True = RUN calibration, False = SKIP calibration
                print_success = self.bambu_client.start_print_from_sd(
                    filename=remote_filename,  # e.g., "cache/model.3mf" or full path
                    use_ams=queue_item.use_ams,
                    plate_number=1,
                    ams_slot=queue_item.ams_slot,
                    flow_cali=queue_item.flow_calibration,  # True=run, False=skip
                    vibration_cali=False,  # Always False = skip (use settings from slicer)
                    bed_leveling=queue_item.auto_bed_leveling,  # True=run, False=skip
                    timelapse=queue_item.timelapse  # True=enable video
                )
                
                if not print_success:
                    print_log(f"Failed to send MQTT print command!", "ERROR")
                    broadcast_upload_progress_sync(printer_id, {
                        "percent": 100,
                        "filename": remote_filename,
                        "status": "print_failed"
                    })
                    job.status = "failed"
                    queue_item.status = "failed"
                    self.db.commit()
                    return False
                
                # Broadcast print started
                broadcast_upload_progress_sync(printer_id, {
                    "percent": 100,
                    "filename": remote_filename,
                    "status": "print_started"
                })
                print_log(f"========================================", "SUCCESS")
                print_log(f"PRINT STARTED SUCCESSFULLY!", "SUCCESS")
                print_log(f"========================================", "SUCCESS")
                print_log(f"Job: {job.job_name}", "INFO")
                print_log(f"File: {remote_filename}", "INFO")
                
                # Update status to RUNNING after print started
                queue_item.status = "running"
                job.status = "running"
                self.db.commit()
                print_log(f"Status changed to RUNNING", "PROGRESS")
                
                # Track start time for this queue to prevent premature completion
                import time
                self._last_running_time[queue_item.queue_id] = time.time()
                logger.info(f"📊 Tracking print start time for queue_id={queue_item.queue_id}")
                
            except Exception as ftps_err:
                print_log(f"FTPS upload error: {ftps_err}", "ERROR")
                import traceback
                traceback.print_exc()
                job.status = "failed"
                queue_item.status = "failed"
                self.db.commit()
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting next job: {str(e)}")
            return False

    def _restart_print_for_loop(self, queue_id: int, printer_id: str) -> bool:
        """
        Restart print for loop continuation (reuse existing queue)
        
        This method is used when continuing a loop - it doesn't look for 
        a "pending" queue but reuses the current running queue.
        
        Args:
            queue_id: The queue item to restart
            printer_id: Target printer ID
            
        Returns: True if print restarted successfully
        """
        try:
            # Get the specific queue item (should be status="running")
            queue_item = self.db.query(Queue).filter(Queue.queue_id == queue_id).first()
            
            if not queue_item:
                logger.error(f"Queue item not found: queue_id={queue_id}")
                print_log(f"Queue item not found for loop restart: {queue_id}", "ERROR")
                return False
            
            # Get job details
            job = self.db.query(Job).filter(Job.job_id == queue_item.job_id).first()
            if not job:
                logger.error(f"Job not found: job_id={queue_item.job_id}")
                print_log(f"Job not found: job_id={queue_item.job_id}", "ERROR")
                return False
            
            print_log(f"========================================", "START")
            print_log(f"RESTARTING PRINT FOR LOOP CONTINUATION", "START")
            print_log(f"========================================", "START")
            print_log(f"Job Name: {job.job_name}", "INFO")
            print_log(f"Printer ID: {printer_id}", "INFO")
            print_log(f"Queue ID: {queue_item.queue_id}", "INFO")
            print_log(f"Loop: {queue_item.current_loop + 1}/{job.loop_count}", "INFO")
            
            # Update status to UPLOADING
            queue_item.status = "uploading"
            queue_item.started_at = datetime.utcnow()
            self.db.commit()
            
            job.status = "uploading"
            job.updated_at = datetime.utcnow()
            self.db.commit()
            
            print_log(f"Status changed to UPLOADING", "PROGRESS")
            
            # Store current job info
            self.current_queue_id = queue_item.queue_id
            self.current_job_id = job.job_id
            self.print_start_time = datetime.utcnow()
            
            # Determine file path - check for both .gcode and .3mf
            gcode_path = f"data/gcode/{job.job_name}.gcode"
            threemf_path = f"data/uploads/{job.filename}"
            
            # Prefer .gcode if exists, otherwise use original .3mf
            if os.path.exists(gcode_path):
                file_path = gcode_path
                logger.info(f"Using gcode file: {gcode_path}")
            elif os.path.exists(threemf_path):
                file_path = threemf_path
                logger.info(f"Using 3mf file directly: {threemf_path}")
            else:
                logger.error(f"No print file found for job: {job.job_name}")
                job.status = "failed"
                queue_item.status = "failed"
                self.db.commit()
                return False
            
            # Upload file and start print (same as start_next_job)
            logger.info(f"📤 Uploading file to printer for loop continuation: {file_path}")
            from src.services.ftps_service import BambuFTPSClient
            from src.config import BAMBU_PRINTER_IP, BAMBU_ACCESS_CODE
            from src.api.websocket import broadcast_upload_progress_sync
            
            try:
                ftps_client = BambuFTPSClient(
                    host=BAMBU_PRINTER_IP,
                    access_code=BAMBU_ACCESS_CODE,
                    port=990,
                    timeout=60
                )
                
                with ftps_client as ftp:
                    remote_filename = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    # Progress callback
                    def upload_progress_callback(bytes_sent: int, total_bytes: int):
                        percent = int((bytes_sent / total_bytes) * 100) if total_bytes > 0 else 0
                        progress_data = {
                            "percent": percent,
                            "bytes_sent": bytes_sent,
                            "total_bytes": total_bytes,
                            "filename": remote_filename,
                            "status": "uploading" if percent < 100 else "complete"
                        }
                        logger.info(f"📤 Upload progress: {percent}% ({bytes_sent}/{total_bytes})")
                        broadcast_upload_progress_sync(printer_id, progress_data)
                    
                    # Broadcast upload start
                    broadcast_upload_progress_sync(printer_id, {
                        "percent": 0,
                        "bytes_sent": 0,
                        "total_bytes": file_size,
                        "filename": remote_filename,
                        "status": "starting"
                    })
                    
                    upload_success = ftp.upload_file(file_path, remote_filename, upload_progress_callback)
                    
                    if not upload_success:
                        logger.error(f"❌ Failed to upload file to printer: {file_path}")
                        broadcast_upload_progress_sync(printer_id, {
                            "percent": 0,
                            "bytes_sent": 0,
                            "total_bytes": file_size,
                            "filename": remote_filename,
                            "status": "failed"
                        })
                        job.status = "failed"
                        queue_item.status = "failed"
                        self.db.commit()
                        return False
                    
                    # Broadcast upload complete
                    broadcast_upload_progress_sync(printer_id, {
                        "percent": 100,
                        "bytes_sent": file_size,
                        "total_bytes": file_size,
                        "filename": remote_filename,
                        "status": "complete"
                    })
                    logger.info(f"✅ File uploaded successfully: {remote_filename}")
                
                # Small delay
                import time
                broadcast_upload_progress_sync(printer_id, {
                    "percent": 100,
                    "bytes_sent": file_size,
                    "total_bytes": file_size,
                    "filename": remote_filename,
                    "status": "starting_print"
                })
                time.sleep(2)
                
                # Send MQTT command to start printing
                print_log(f"Sending MQTT command to start print...", "START")
                print_log(f"File: {remote_filename}", "INFO")
                print_log(f"AMS: use_ams={queue_item.use_ams}, slot={queue_item.ams_slot}", "INFO")
                print_log(f"Settings: bed_leveling={queue_item.auto_bed_leveling}, flow_cali={queue_item.flow_calibration}, timelapse={queue_item.timelapse}", "INFO")
                
                # Calibration settings: True = RUN calibration, False = SKIP calibration
                print_success = self.bambu_client.start_print_from_sd(
                    filename=remote_filename,
                    use_ams=queue_item.use_ams,
                    plate_number=1,
                    ams_slot=queue_item.ams_slot,
                    flow_cali=queue_item.flow_calibration,  # True=run, False=skip
                    vibration_cali=False,  # Always False = skip (use settings from slicer)
                    bed_leveling=queue_item.auto_bed_leveling,  # True=run, False=skip
                    timelapse=queue_item.timelapse  # True=enable video
                )
                
                if not print_success:
                    print_log(f"Failed to send MQTT print command!", "ERROR")
                    broadcast_upload_progress_sync(printer_id, {
                        "percent": 100,
                        "filename": remote_filename,
                        "status": "print_failed"
                    })
                    job.status = "failed"
                    queue_item.status = "failed"
                    self.db.commit()
                    return False
                
                # Broadcast print started
                broadcast_upload_progress_sync(printer_id, {
                    "percent": 100,
                    "filename": remote_filename,
                    "status": "print_started"
                })
                print_log(f"========================================", "SUCCESS")
                print_log(f"LOOP PRINT RESTARTED SUCCESSFULLY!", "SUCCESS")
                print_log(f"========================================", "SUCCESS")
                print_log(f"Loop: {queue_item.current_loop + 1}/{job.loop_count}", "INFO")
                
                # Update status to RUNNING
                queue_item.status = "running"
                job.status = "running"
                self.db.commit()
                print_log(f"Status changed to RUNNING", "PROGRESS")
                
                # Track start time for loop restart to prevent premature completion
                import time
                self._last_running_time[queue_id] = time.time()
                logger.info(f"📊 Tracking loop restart time for queue_id={queue_id}")
                
            except Exception as ftps_err:
                print_log(f"FTPS upload error: {ftps_err}", "ERROR")
                import traceback
                traceback.print_exc()
                job.status = "failed"
                queue_item.status = "failed"
                self.db.commit()
                return False
            
            logger.info(f"✅ Loop {queue_item.current_loop + 1}/{job.loop_count} print restarted for queue_id={queue_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error restarting print for loop: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def handle_print_completion(self, printer_id: str) -> bool:
        """
        Handle print job completion
        
        Logic:
        1. Check if current job should repeat (current_loop < loop_count)
        2. If yes: increment loop, restart print
        3. If no: mark queue as complete, start next job
        
        Args:
            printer_id: Printer that completed print
            
        Returns: True if handled successfully
        """
        try:
            if not self.current_queue_id or not self.current_job_id:
                logger.warning("No current job to handle completion")
                return False
            
            # Get current queue item and job
            queue_item = self.db.query(Queue).filter(
                Queue.queue_id == self.current_queue_id
            ).first()
            
            job = self.db.query(Job).filter(Job.job_id == self.current_job_id).first()
            
            if not queue_item or not job:
                logger.error("Queue item or job not found during completion")
                return False
            
            # Calculate print duration
            print_duration_minutes = 0
            actual_start_time = self.print_start_time or queue_item.started_at
            
            if actual_start_time:
                elapsed = datetime.utcnow() - actual_start_time
                print_duration_minutes = elapsed.total_seconds() / 60
            else:
                # Fallback: use current time as start (estimate 0 duration)
                actual_start_time = datetime.utcnow()
                logger.warning("⚠️ No start_time found, using current time as fallback")
            
            # Log this completed loop in history first (with error handling)
            try:
                self._log_print_history(
                    job_id=job.job_id,
                    printer_id=printer_id,
                    start_time=actual_start_time,
                    duration_minutes=print_duration_minutes,
                    print_success=True,
                    completion_status=f"completed_loop_{queue_item.current_loop + 1}"
                )
            except Exception as e:
                logger.error(f"Failed to log print history (continuing anyway): {e}")
                # Don't stop loop continuation due to history logging failure
            
            # Increment loop counter (we just finished current_loop, moving to next)
            queue_item.current_loop += 1
            job.current_loop += 1
            
            logger.info(
                f"✅ Loop {queue_item.current_loop}/{job.loop_count} completed for queue_id={self.current_queue_id}"
            )
            print_log(
                f"Loop {queue_item.current_loop}/{job.loop_count} completed",
                "SUCCESS"
            )
            
            # Check if there are more loops to do
            if queue_item.current_loop < job.loop_count:
                # Save current state before restarting
                self.db.commit()
                # More loops remaining - restart print
                logger.info(
                    f"🔄 Starting loop {queue_item.current_loop + 1}/{job.loop_count}"
                )
                print_log(
                    f"Starting next loop: {queue_item.current_loop + 1}/{job.loop_count}",
                    "START"
                )
                
                # Restart print for the SAME queue (loop continuation)
                # Don't look for pending queue - reuse current queue_id
                return self._restart_print_for_loop(queue_item.queue_id, printer_id)
            
            else:
                # All loops completed
                # Ensure loop counter doesn't exceed loop_count
                if queue_item.current_loop > job.loop_count:
                    queue_item.current_loop = job.loop_count
                    job.current_loop = job.loop_count
                
                # Mark as completed
                queue_item.status = "completed"
                queue_item.completed_at = datetime.utcnow()
                
                job.status = "completed"
                job.updated_at = datetime.utcnow()
                
                self.db.commit()
                
                logger.info(
                    f"🎉 All {job.loop_count} loops completed for job_id={job.job_id}"
                )
                print_log(
                    f"All {job.loop_count} loops completed!",
                    "SUCCESS"
                )
                
                # DELETE completed queue item from queue table
                # (already logged in history during loop completion)
                try:
                    self.db.delete(queue_item)
                    self.db.commit()
                    logger.info(f"✅ Removed completed queue item #{queue_item.queue_id} from queue")
                except Exception as e:
                    logger.error(f"Failed to delete queue item: {e}")
                    # Continue anyway
                
                # Clear current job
                self.current_queue_id = None
                self.current_job_id = None
                self.print_start_time = None
                
                # Check auto_continue setting before starting next job
                from src.database.db import Printer
                printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
                
                if printer and printer.auto_continue:
                    # Auto continue enabled - start next job immediately
                    logger.info(f"✅ Auto-continue enabled, starting next job...")
                    return self.start_next_job(printer_id)
                else:
                    # Auto continue disabled - wait for manual start
                    logger.info(f"⏸️ Auto-continue disabled, waiting for manual start")
                    print_log("Auto-continue disabled. Click 'Start Next Job' to continue.", "INFO")
                    return True
            
        except Exception as e:
            logger.error(f"Error handling print completion: {str(e)}")
            return False

    def pause_current_print(self) -> bool:
        """Pause current printing job"""
        try:
            # Find running queue item from database (not instance variable)
            running_queue = self.db.query(Queue).filter(
                Queue.status == "running"
            ).first()
            
            if not running_queue:
                print_log("No current job to pause (no running queue in DB)", "WARNING")
                return False
            
            print_log(f"========================================", "PAUSE")
            print_log(f"PAUSING PRINT", "PAUSE")
            print_log(f"========================================", "PAUSE")
            print_log(f"Queue ID: {running_queue.queue_id}", "INFO")
            print_log(f"Job ID: {running_queue.job_id}", "INFO")
            
            success = self.bambu_client.pause_print()
            if success:
                print_log(f"Print paused successfully", "SUCCESS")
                # Update status to paused
                running_queue.status = "paused"
                self.db.commit()
                print_log(f"Status updated to PAUSED", "PROGRESS")
            else:
                print_log(f"Failed to pause print", "ERROR")
            return success
            
        except Exception as e:
            print_log(f"Error pausing print: {str(e)}", "ERROR")
            return False

    def resume_current_print(self) -> bool:
        """Resume current printing job"""
        try:
            # Find paused queue item from database
            paused_queue = self.db.query(Queue).filter(
                Queue.status == "paused"
            ).first()
            
            if not paused_queue:
                print_log("No paused job to resume (no paused queue in DB)", "WARNING")
                return False
            
            print_log(f"========================================", "RESUME")
            print_log(f"RESUMING PRINT", "RESUME")
            print_log(f"========================================", "RESUME")
            print_log(f"Queue ID: {paused_queue.queue_id}", "INFO")
            print_log(f"Job ID: {paused_queue.job_id}", "INFO")
            
            success = self.bambu_client.resume_print()
            if success:
                print_log(f"Print resumed successfully", "SUCCESS")
                # Update status back to running
                paused_queue.status = "running"
                self.db.commit()
                print_log(f"Status updated to RUNNING", "PROGRESS")
            else:
                print_log(f"Failed to resume print", "ERROR")
            return success
            
        except Exception as e:
            print_log(f"Error resuming print: {str(e)}", "ERROR")
            return False

    def cancel_current_print(self) -> bool:
        """Cancel current printing job"""
        try:
            # Find running or paused queue item from database
            active_queue = self.db.query(Queue).filter(
                Queue.status.in_(["running", "paused"])
            ).first()
            
            if not active_queue:
                print_log("No current job to cancel (no running/paused queue in DB)", "WARNING")
                return False
            
            print_log(f"========================================", "CANCEL")
            print_log(f"CANCELLING PRINT", "CANCEL")
            print_log(f"========================================", "CANCEL")
            print_log(f"Queue ID: {active_queue.queue_id}", "INFO")
            print_log(f"Job ID: {active_queue.job_id}", "INFO")
            
            # Stop printer
            self.bambu_client.stop_print()
            print_log(f"Stop command sent to printer", "STOP")
            
            # Update queue status
            active_queue.status = "cancelled"
            self.db.commit()
            
            # Update job status
            job = self.db.query(Job).filter(Job.job_id == active_queue.job_id).first()
            if job:
                job.status = "cancelled"
                self.db.commit()
            
            print_log(f"Print cancelled successfully", "SUCCESS")
            print_log(f"Status updated to CANCELLED", "PROGRESS")
            
            return True
            
        except Exception as e:
            print_log(f"Error cancelling print: {str(e)}", "ERROR")
            return False

    def _log_print_history(
        self,
        job_id: int,
        printer_id: str,
        start_time: datetime,
        duration_minutes: float,
        print_success: bool,
        completion_status: str
    ) -> bool:
        """
        Log print job to history
        
        Args:
            job_id: The job that was printed
            printer_id: Printer that ran the job
            start_time: When print started
            duration_minutes: How long print took
            print_success: Whether print succeeded
            completion_status: Description of completion
        """
        try:
            # Validate start_time (must not be None)
            if start_time is None:
                logger.error("Cannot log print history: start_time is None!")
                raise ValueError("start_time cannot be None")
            
            history_record = PrintHistory(
                job_id=job_id,
                printer_id=printer_id,
                start_time=start_time,
                end_time=datetime.utcnow(),
                duration_minutes=duration_minutes,
                material_used_grams=0.0,  # TODO: Get from printer
                print_success=print_success,
                eject_time=datetime.utcnow(),
                completion_status=completion_status,
                created_at=datetime.utcnow()
            )
            
            self.db.add(history_record)
            self.db.commit()
            
            logger.info(f"✅ Logged print history: job_id={job_id}, duration={duration_minutes:.1f}min")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error logging print history: {str(e)}")
            # Rollback the failed transaction
            self.db.rollback()
            return False

    def get_current_print_status(self) -> dict:
        """Get status of currently printing job"""
        if not self.current_queue_id:
            return {"status": "idle"}
        
        try:
            queue_item = self.db.query(Queue).filter(
                Queue.queue_id == self.current_queue_id
            ).first()
            
            job = self.db.query(Job).filter(Job.job_id == self.current_job_id).first()
            
            if not queue_item or not job:
                return {"status": "unknown"}
            
            print_progress = self.bambu_client.get_print_progress()
            
            return {
                "status": "printing",
                "queue_id": self.current_queue_id,
                "job_id": self.current_job_id,
                "job_name": job.job_name,
                "current_loop": queue_item.current_loop + 1,
                "total_loops": job.loop_count,
                "print_progress": print_progress,
                "start_time": self.print_start_time,
            }
            
        except Exception as e:
            logger.error(f"Error getting print status: {str(e)}")
            return {"status": "error"}
