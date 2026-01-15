"""
Print Control Service - Orchestrate printing workflow
Handles job execution, loop management, and auto-eject
Follows naming conventions from README.md
"""
import logging
import os
import tempfile
import shutil
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.db import Queue, Job, PrintHistory, FilamentProfile
from src.services.bambu_service import BambuLabMQTTClient
from src.services.gcode_preprocessor import (
    GCodePreprocessor, PrintSettings, FilamentSettings, get_gcode_preprocessor
)

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
        self.gcode_preprocessor = get_gcode_preprocessor()
    
    def _get_print_settings(self, queue_item: Queue) -> PrintSettings:
        """Build PrintSettings from queue item automation settings"""
        return PrintSettings(
            auto_bed_leveling=queue_item.auto_bed_leveling if queue_item.auto_bed_leveling is not None else True,
            flow_calibration=queue_item.flow_calibration if queue_item.flow_calibration is not None else False,
            vibration_test=queue_item.vibration_test if queue_item.vibration_test is not None else False,
            clean_nozzle=queue_item.clean_nozzle if queue_item.clean_nozzle is not None else True,
            auto_eject=queue_item.auto_eject if queue_item.auto_eject is not None else True,
            cooldown_temp=queue_item.cooldown_temp if queue_item.cooldown_temp is not None else 32,
            startup_sound=queue_item.startup_sound if queue_item.startup_sound is not None else True,
            end_sound=queue_item.end_sound if queue_item.end_sound is not None else True,
            ams_slot=queue_item.ams_slot if queue_item.ams_slot is not None else 0,
            nozzle_load_line=queue_item.nozzle_load_line if hasattr(queue_item, 'nozzle_load_line') and queue_item.nozzle_load_line is not None else False,
            use_ams=queue_item.use_ams if queue_item.use_ams is not None else True,
            timelapse=queue_item.timelapse if hasattr(queue_item, 'timelapse') and queue_item.timelapse is not None else False
        )

    def _get_filament_settings(self, queue_item: Queue) -> FilamentSettings:
        """Get FilamentSettings from queue's filament profile or defaults"""
        if queue_item.filament_id:
            filament = self.db.query(FilamentProfile).filter(
                FilamentProfile.filament_id == queue_item.filament_id
            ).first()
            
            if filament:
                return FilamentSettings(
                    filament_type=filament.material_type,
                    nozzle_temp=filament.nozzle_temp_default,
                    nozzle_temp_initial=filament.nozzle_temp_default,
                    bed_temp=filament.bed_temp_default,
                    bed_temp_initial=filament.bed_temp_default,
                    max_volumetric_speed=filament.max_volumetric_speed or 12.0,
                    color=filament.color_hex or "#FFFFFF"
                )
        
        # Return default PLA settings
        return FilamentSettings()
    
    def _preprocess_gcode_file(
        self, 
        file_path: str, 
        queue_item: Queue
    ) -> str:
        """
        Preprocess G-code file with automation settings
        
        Args:
            file_path: Original file path (.gcode or .3mf)
            queue_item: Queue item with automation settings
            
        Returns:
            Path to processed file (may be same as input if no processing needed)
        """
        print_settings = self._get_print_settings(queue_item)
        filament_settings = self._get_filament_settings(queue_item)
        
        logger.info(
            f"🔧 Preprocessing G-code: auto_eject={print_settings.auto_eject}, "
            f"flow_cal={print_settings.flow_calibration}, bed_level={print_settings.auto_bed_leveling}, "
            f"cooldown={print_settings.cooldown_temp}°C"
        )
        
        # Check if file is .gcode or .3mf
        if file_path.endswith('.gcode'):
            # Direct gcode file - read, process, write to temp
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_gcode = f.read()
            
            processed_gcode = self.gcode_preprocessor.process_gcode(
                original_gcode,
                print_settings,
                filament_settings
            )
            
            # Write to temp file with same name
            processed_path = os.path.join(
                tempfile.gettempdir(),
                f"processed_{os.path.basename(file_path)}"
            )
            with open(processed_path, 'w', encoding='utf-8') as f:
                f.write(processed_gcode)
            
            logger.info(f"✅ G-code preprocessed: {processed_path}")
            return processed_path
            
        elif file_path.endswith('.3mf'):
            # 3MF file - extract, process gcode, repack
            import zipfile
            from pathlib import Path
            
            processed_path = os.path.join(
                tempfile.gettempdir(),
                f"processed_{os.path.basename(file_path)}"
            )
            
            # Copy original to temp location
            shutil.copy(file_path, processed_path)
            
            # Read 3mf and find gcode plate files
            try:
                with zipfile.ZipFile(file_path, 'r') as zf_read:
                    gcode_files = [f for f in zf_read.namelist() if f.endswith('.gcode')]
                    
                    if gcode_files:
                        # Create new 3mf with processed gcode
                        temp_dir = tempfile.mkdtemp()
                        
                        # Extract all files
                        zf_read.extractall(temp_dir)
                        
                        # Process each gcode file
                        for gcode_file in gcode_files:
                            gcode_full_path = os.path.join(temp_dir, gcode_file)
                            if os.path.exists(gcode_full_path):
                                with open(gcode_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    original_gcode = f.read()
                                
                                processed_gcode = self.gcode_preprocessor.process_gcode(
                                    original_gcode,
                                    print_settings,
                                    filament_settings
                                )
                                
                                with open(gcode_full_path, 'w', encoding='utf-8') as f:
                                    f.write(processed_gcode)
                                
                                logger.info(f"  Processed: {gcode_file}")
                        
                        # Repack 3mf
                        with zipfile.ZipFile(processed_path, 'w', zipfile.ZIP_DEFLATED) as zf_write:
                            for root, dirs, files in os.walk(temp_dir):
                                for file in files:
                                    file_path_full = os.path.join(root, file)
                                    arcname = os.path.relpath(file_path_full, temp_dir)
                                    zf_write.write(file_path_full, arcname)
                        
                        # Cleanup temp dir
                        shutil.rmtree(temp_dir)
                        
                        logger.info(f"✅ 3MF preprocessed: {processed_path}")
                        return processed_path
                    
            except Exception as e:
                logger.warning(f"Failed to preprocess 3MF, using original: {e}")
                return file_path
        
        # Unknown format, return original
        return file_path

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
            
            # ==================== G-CODE PREPROCESSING ====================
            # Apply automation settings before uploading to printer
            # This removes nozzle_load_line section (purge line at front of bed) when disabled
            logger.info(f"🔧 Applying print farm automation settings...")
            try:
                file_path = self._preprocess_gcode_file(file_path, queue_item)
                logger.info(f"✅ Preprocessing complete, using: {file_path}")
            except Exception as preproc_err:
                logger.warning(f"⚠️ Preprocessing failed, using original file: {preproc_err}")
                # Continue with original file
            
            # Upload file to printer SD card via FTPS
            logger.info(f"📤 Uploading file to printer SD card: {file_path}")
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
                print_log(f"Calibration: flow_cali={queue_item.flow_calibration}, vibration={queue_item.vibration_test}", "INFO")
                print_log(f"Options: bed_leveling={queue_item.auto_bed_leveling}, timelapse={queue_item.timelapse}", "INFO")
                
                # Use proper "project_file" MQTT command with full parameters
                # This is the MQTT command that Bambu Lab firmware actually recognizes
                print_success = self.bambu_client.start_print_from_sd(
                    filename=remote_filename,  # e.g., "cache/model.3mf" or full path
                    use_ams=queue_item.use_ams,
                    plate_number=1,
                    ams_slot=queue_item.ams_slot,
                    flow_cali=queue_item.flow_calibration,
                    vibration_cali=queue_item.vibration_test,
                    bed_leveling=queue_item.auto_bed_leveling,
                    timelapse=queue_item.timelapse
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

    def handle_print_completion(self, printer_id: str) -> bool:
        """
        Handle print job completion
        
        Logic:
        1. Check if current job should repeat (current_loop < loop_count)
        2. If yes: increment loop, restart print
        3. If no: mark queue as complete, start next job
        4. Trigger auto-eject
        
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
            if self.print_start_time:
                elapsed = datetime.utcnow() - self.print_start_time
                print_duration_minutes = elapsed.total_seconds() / 60
            
            # Check if job should repeat (loop_count > 1)
            should_repeat = queue_item.current_loop < (job.loop_count - 1)
            
            if should_repeat:
                # Increment loop counter
                queue_item.current_loop += 1
                job.current_loop += 1
                self.db.commit()
                
                logger.info(
                    f"Job repeating: queue_id={self.current_queue_id}, "
                    f"current_loop={queue_item.current_loop + 1}/{job.loop_count}"
                )
                
                # Log this loop in history
                self._log_print_history(
                    job_id=job.job_id,
                    printer_id=printer_id,
                    start_time=self.print_start_time,
                    duration_minutes=print_duration_minutes,
                    print_success=True,
                    completion_status="completed_loop"
                )
                
                # Trigger auto-eject
                self.bambu_client.trigger_auto_eject()
                
                # Wait briefly then start next loop
                import time
                time.sleep(5)  # Wait 5 seconds for eject
                
                # Restart print
                return self.start_next_job(printer_id)
            
            else:
                # Job completed all loops
                queue_item.current_loop = job.loop_count - 1
                queue_item.status = "completed"
                queue_item.completed_at = datetime.utcnow()
                
                job.current_loop = job.loop_count - 1
                job.status = "completed"
                job.updated_at = datetime.utcnow()
                
                self.db.commit()
                
                logger.info(
                    f"Job completed all loops: queue_id={self.current_queue_id}, "
                    f"job_id={job.job_id}, total_loops={job.loop_count}"
                )
                
                # Log final print in history
                self._log_print_history(
                    job_id=job.job_id,
                    printer_id=printer_id,
                    start_time=self.print_start_time,
                    duration_minutes=print_duration_minutes,
                    print_success=True,
                    completion_status="completed_all_loops"
                )
                
                # Trigger auto-eject
                self.bambu_client.trigger_auto_eject()
                
                # Clear current job
                self.current_queue_id = None
                self.current_job_id = None
                self.print_start_time = None
                
                # Start next job from queue
                import time
                time.sleep(5)  # Wait for eject
                
                return self.start_next_job(printer_id)
            
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
            
            logger.info(f"Logged print history: job_id={job_id}, duration={duration_minutes:.1f}min")
            return True
            
        except Exception as e:
            logger.error(f"Error logging print history: {str(e)}")
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
