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
            
            # CRITICAL: Expire all cached objects to get fresh data from database
            # This fixes stale session issues in container/Docker environments
            self.db.expire_all()
            logger.info("🔄 Database session refreshed (expire_all)")
            
            # Find any running/paused queue item
            active_queue = self.db.query(Queue).filter(
                Queue.status.in_(["running", "paused"])
            ).first()
            
            logger.info(f"📊 Active queue search result: {active_queue.queue_id if active_queue else 'None'}")
            
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
                logger.info("No active job found, checking for pending jobs to auto-start...")
                
                # Refresh session again before querying pending jobs
                self.db.expire_all()
                
                pending_queue = self.db.query(Queue).filter(
                    Queue.status == "pending"
                ).order_by(Queue.position_in_queue).first()
                
                if pending_queue:
                    logger.info(f"✅ Found pending job queue_id={pending_queue.queue_id}, printer_id={pending_queue.printer_id}")
                    logger.info(f"🚀 Auto-starting next job in queue...")
                    self.start_next_job(pending_queue.printer_id)
                else:
                    logger.info("📭 No pending jobs in queue - queue is empty")
                    
        except Exception as e:
            logger.error(f"Error in print complete callback: {str(e)}")
            logger.error(f"Error in print completion callback: {e}")
        finally:
            # Always clear guard flag when done (even on error)
            self._processing_completion = False
    
    # Print settings removed - use values from slicer
    
    # File preprocessing removed - files sent AS-IS from slicer

    def _upload_and_start_print(self, queue_item, job, printer_id: str, is_loop_restart: bool = False) -> bool:
        """
        Common logic for uploading file to printer and starting print via MQTT.
        Used by both start_next_job and _restart_print_for_loop to avoid code duplication.
        
        Args:
            queue_item: Queue database object
            job: Job database object
            printer_id: Target printer ID
            is_loop_restart: If True, log messages indicate loop restart
            
        Returns: True if print started successfully
        """
        import re
        import time
        from src.services.ftps_service import BambuFTPSClient
        from src.api.websocket import broadcast_upload_progress_sync
        from src.database.db import Printer

        label = "RESTARTING PRINT FOR LOOP CONTINUATION" if is_loop_restart else "STARTING PRINT JOB"
        success_label = "LOOP PRINT RESTARTED SUCCESSFULLY!" if is_loop_restart else "PRINT STARTED SUCCESSFULLY!"

        print_log(f"========================================", "START")
        print_log(f"{label}", "START")
        print_log(f"========================================", "START")
        print_log(f"Job Name: {job.job_name}", "INFO")
        print_log(f"Printer ID: {printer_id}", "INFO")
        print_log(f"Queue ID: {queue_item.queue_id}", "INFO")
        print_log(f"Loop: {queue_item.current_loop + 1}/{job.loop_count}", "INFO")

        # Update queue status to UPLOADING
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

        # Files are sent AS-IS from slicer without modification
        logger.info(f"📤 Uploading file to printer: {file_path}")
        print_log(f"Sending file as-is without modifications", "INFO")

        # ==================== FILAMENT COMPATIBILITY CHECK ====================
        # Compare filament type in file metadata vs what's loaded in the AMS slot
        # This is a WARNING only - does not block printing
        if queue_item.use_ams:
            try:
                from src.utils.gcode_parser import parse_3mf_metadata, parse_gcode_metadata
                from src.database.db import AMSSlotAssignment

                # Extract filament type from print file
                file_filament_type = None
                if file_path.endswith('.3mf'):
                    file_meta = parse_3mf_metadata(file_path)
                elif file_path.endswith('.gcode'):
                    with open(file_path, 'r', errors='ignore') as f:
                        # Read only first 2000 lines for metadata (header area)
                        header_lines = ''.join(f.readline() for _ in range(2000))
                    file_meta = parse_gcode_metadata(header_lines)
                else:
                    file_meta = {}
                file_filament_type = file_meta.get('filament_type')

                if file_filament_type:
                    # Check AMS slot assignment in database
                    ams_assignment = self.db.query(AMSSlotAssignment).filter(
                        AMSSlotAssignment.printer_id == printer_id,
                        AMSSlotAssignment.slot_number == queue_item.ams_slot
                    ).first()

                    if ams_assignment and ams_assignment.filament_name:
                        loaded_type = ams_assignment.filament_name.upper()
                        expected_type = file_filament_type.upper()
                        # Check if the loaded filament type contains or matches the expected type
                        # e.g. loaded="PLA Basic" should match expected="PLA"
                        if expected_type not in loaded_type and loaded_type not in expected_type:
                            print_log(
                                f"FILAMENT MISMATCH! File expects '{file_filament_type}' "
                                f"but AMS slot {queue_item.ams_slot} has '{ams_assignment.filament_name}'",
                                "WARNING"
                            )
                            logger.warning(
                                f"⚠️ Filament mismatch: file={file_filament_type}, "
                                f"AMS slot {queue_item.ams_slot}={ams_assignment.filament_name}"
                            )
                        else:
                            print_log(
                                f"Filament check OK: {file_filament_type} matches AMS slot {queue_item.ams_slot}",
                                "INFO"
                            )
                    elif ams_assignment:
                        logger.info(f"ℹ️ AMS slot {queue_item.ams_slot} has no filament name synced, skipping check")
                    else:
                        logger.info(f"ℹ️ No AMS assignment found for slot {queue_item.ams_slot}, skipping check")
                else:
                    logger.info(f"ℹ️ No filament_type found in file metadata, skipping compatibility check")
            except Exception as e:
                logger.warning(f"⚠️ Filament compatibility check failed (non-blocking): {e}")

        # Get printer details from database
        printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
        if not printer or not printer.printer_ip or not printer.access_code:
            logger.error(f"❌ Printer not found or missing printer_ip/access_code: {printer_id}")
            job.status = "failed"
            queue_item.status = "failed"
            self.db.commit()
            return False

        # Compute sanitized filename (needed for both upload and MQTT start)
        raw_filename = os.path.basename(file_path)
        remote_filename = re.sub(r'[^\w\-\.]', '_', raw_filename)
        if remote_filename != raw_filename:
            logger.info(f"📝 Filename sanitized: '{raw_filename}' → '{remote_filename}'")
        file_size = os.path.getsize(file_path)

        # For loop restarts, skip FTPS re-upload (file already on printer SD card)
        if is_loop_restart:
            print_log(f"⏭️ Skipping FTPS re-upload (loop restart, file already on SD card): {remote_filename}", "INFO")
        else:
            try:
                ftps_client = BambuFTPSClient(
                    host=printer.printer_ip,
                    access_code=printer.access_code,
                    port=990,
                    timeout=60
                )

                with ftps_client as ftp:
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
                broadcast_upload_progress_sync(printer_id, {
                    "percent": 100,
                    "bytes_sent": file_size,
                    "total_bytes": file_size,
                    "filename": remote_filename,
                    "status": "starting_print"
                })
                time.sleep(2)

            except Exception as ftps_err:
                print_log(f"FTPS upload error: {ftps_err}", "ERROR")
                import traceback
                traceback.print_exc()
                job.status = "failed"
                queue_item.status = "failed"
                self.db.commit()
                return False

        # Send MQTT command to start printing from SD card
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
        print_log(f"{success_label}", "SUCCESS")
        print_log(f"========================================", "SUCCESS")
        if is_loop_restart:
            print_log(f"Loop: {queue_item.current_loop + 1}/{job.loop_count}", "INFO")
        else:
            print_log(f"Job: {job.job_name}", "INFO")
            print_log(f"File: {remote_filename}", "INFO")

        # Update status to RUNNING
        queue_item.status = "running"
        job.status = "running"
        self.db.commit()
        print_log(f"Status changed to RUNNING", "PROGRESS")

        # Track start time to prevent premature completion
        self._last_running_time[queue_item.queue_id] = time.time()
        logger.info(f"📊 Tracking print start time for queue_id={queue_item.queue_id}")

        return True

    def start_next_job(self, printer_id: str) -> bool:
        """
        Get next job from queue and start printing
        
        Args:
            printer_id: Target printer ID
            
        Returns: True if job started successfully
        """
        try:
            # CRITICAL: Expire all cached objects to get fresh data from database
            # This fixes stale session issues in container/Docker environments
            self.db.expire_all()
            logger.info(f"🔄 start_next_job: Database session refreshed for printer_id={printer_id}")
            
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
            
            return self._upload_and_start_print(queue_item, job, printer_id, is_loop_restart=False)
            
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
            # CRITICAL: Expire all cached objects to get fresh data from database
            self.db.expire_all()
            logger.info(f"🔄 _restart_print_for_loop: Database session refreshed")
            
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
            
            result = self._upload_and_start_print(queue_item, job, printer_id, is_loop_restart=True)
            if result:
                logger.info(f"✅ Loop {queue_item.current_loop + 1}/{job.loop_count} print restarted for queue_id={queue_id}")
            return result
            
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
            # CRITICAL: Expire all cached objects to get fresh data from database
            self.db.expire_all()
            logger.info(f"🔄 handle_print_completion: Database session refreshed")
            
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
                
                # Refresh session before querying printer settings
                self.db.expire_all()
                printer = self.db.query(Printer).filter(Printer.printer_id == printer_id).first()
                
                # Handle auto_continue: default to True if None (for backwards compatibility)
                # This ensures queue continues if field was added after printer was created
                auto_continue = printer.auto_continue if (printer and printer.auto_continue is not None) else True
                
                logger.info(f"📊 Printer auto_continue setting: {auto_continue} (raw value: {printer.auto_continue if printer else 'None'})")
                
                if auto_continue:
                    # Auto continue enabled - start next job immediately
                    logger.info(f"✅ Auto-continue enabled, checking for next job in queue...")
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
