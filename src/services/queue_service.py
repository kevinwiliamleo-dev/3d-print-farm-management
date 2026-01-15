"""
Queue Service - Manage print queue and job ordering
Follows naming conventions from README.md
"""
from datetime import datetime
from pathlib import Path
import shutil
import zipfile
from sqlalchemy.orm import Session
from src.database.db import Queue, Job
from src.models.schemas import QueueItemCreate, QueueItemResponse
from src.config import UPLOAD_DIR, QUEUE_FILES_DIR, OUTPUT_DIR
from src.utils.gcode_parser import extract_gcode_from_3mf, apply_section_modifications, parse_gcode_sections
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
        ams_slot: int = 0, 
        ams_mapping: str = "", 
        use_ams: bool = True,
        filament_already_loaded: bool = False,
        use_template_mode: bool = True,  # NEW: Template mode (recommended)
        skip_preprocessing: bool = False,  # NEW: Skip ALL preprocessing (print as-is)
        # Automation settings
        filament_id: int = None,
        start_machine: bool = True,
        heat_bed_hotend: bool = True,
        auto_bed_leveling: bool = True,
        flow_calibration: bool = False,
        vibration_test: bool = False,
        clean_nozzle: bool = False,
        wipe_nozzle: bool = True,
        nozzle_load_line: bool = True,
        timelapse: bool = False,
        auto_eject: bool = True,
        cooldown_temp: int = 32,
        startup_sound: bool = True,
        end_sound: bool = True,
        # Quick Start options (FactorianDesigns optimization) - ENABLED BY DEFAULT
        quick_start: bool = True,
        preheat_offset: int = 20,
        pre_extrude: bool = True,
        pre_extrude_length: float = 2.2,
        # NEW: Controllable templates
        cog_noise_reduction: bool = True,
        brush_material_wipe: bool = True,
        final_wipe_nozzle: bool = True,
        avoid_end_stop: bool = True,
        reset_machine_status: bool = True,
        home_after_wipe: bool = True,
        prepare_print: bool = True,
        extrude_calibration_test: bool = True,
        turn_off_light: bool = False,
        final_start: bool = True
    ) -> dict:
        """
        Add job to print queue with automation settings
        
        Args:
            job_id: The job to add
            printer_id: Target printer
            loop_count: Number of loops for this job
            ams_slot: AMS tray slot (0-3 for AMS Lite, 255 for external spool)
            ams_mapping: Full AMS mapping string for multi-color prints
            use_ams: Whether to use AMS (False = external spool)
            filament_already_loaded: Skip AMS load sequence if filament already in extruder
            use_template_mode: NEW - Replace all start/end gcode with optimized templates
            filament_id: Optional filament profile for temperature overrides
            auto_bed_leveling: Enable G29 bed leveling before print
            flow_calibration: Enable flow test (disabled if auto_eject is on)
            vibration_test: Enable resonance/vibration test
            clean_nozzle: Enable nozzle cleaning sequence
            nozzle_load_line: Enable nozzle purge line at front of bed
            auto_eject: Auto push-off print after completion
            cooldown_temp: Bed temperature to wait for before eject (default 32°C)
            startup_sound: Play startup melody
            end_sound: Play end melody
            
        Returns:
            Queue entry with queue_id, position_in_queue, and automation settings
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
        
        # Copy and modify the file based on automation settings
        queue_file_path_str = None
        
        # Skip file modification if bypass enabled
        if skip_preprocessing:
            logger.info(f"⏭️ Skipping file preprocessing (bypass enabled - using original file)")
            # Just copy original file without modifications
            if source_file.exists():
                shutil.copy(source_file, queue_file_path)
                queue_file_path_str = str(queue_file_path)
                logger.info(f"✅ Using original file: {queue_file_path_str}")
        elif source_file.exists() and source_file.suffix.lower() == '.3mf':
            try:
                queue_file_path_str = self._create_modified_queue_file(
                    source_file=source_file,
                    dest_file=queue_file_path,
                    use_template_mode=use_template_mode,  # NEW: Template mode
                    start_machine=start_machine,
                    heat_bed_hotend=heat_bed_hotend,
                    auto_bed_leveling=auto_bed_leveling,
                    flow_calibration=flow_calibration,
                    vibration_test=vibration_test,
                    clean_nozzle=clean_nozzle,
                    wipe_nozzle=wipe_nozzle,
                    nozzle_load_line=nozzle_load_line,
                    startup_sound=startup_sound,
                    end_sound=end_sound,
                    use_ams=use_ams,
                    ams_slot=ams_slot,
                    filament_already_loaded=filament_already_loaded,
                    # Quick Start options
                    quick_start=quick_start,
                    preheat_offset=preheat_offset,
                    pre_extrude=pre_extrude,
                    pre_extrude_length=pre_extrude_length,
                    auto_eject=auto_eject,
                    cooldown_temp=cooldown_temp,
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
                    final_start=final_start,
                    # Filament profile for temperature overrides
                    filament_id=filament_id
                )
                logger.info(f"Created modified queue file: {queue_file_path_str}")
            except Exception as e:
                logger.warning(f"Failed to create modified queue file: {e}. Using original.")
                # Fallback: just copy the file
                shutil.copy(source_file, queue_file_path)
                queue_file_path_str = str(queue_file_path)
        else:
            # Just copy for non-3MF files
            if source_file.exists():
                shutil.copy(source_file, queue_file_path)
                queue_file_path_str = str(queue_file_path)
        
        # Create queue entry with AMS and automation settings
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
            use_template_mode=use_template_mode,
            skip_preprocessing=skip_preprocessing,
            # Automation settings
            filament_id=filament_id,
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
            f"Added job to queue: job_id={job_id}, printer_id={printer_id}, "
            f"position={position_in_queue}, ams_slot={ams_slot}, use_ams={use_ams}, "
            f"auto_eject={auto_eject}, queue_file={queue_file_path_str}"
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
            # Automation settings
            "filament_id": queue_record.filament_id,
            "auto_bed_leveling": queue_record.auto_bed_leveling,
            "flow_calibration": queue_record.flow_calibration,
            "vibration_test": queue_record.vibration_test,
            "clean_nozzle": queue_record.clean_nozzle,
            "auto_eject": queue_record.auto_eject,
            "cooldown_temp": queue_record.cooldown_temp,
            "startup_sound": queue_record.startup_sound,
            "end_sound": queue_record.end_sound,
            # Queue file
            "queue_file_path": queue_record.queue_file_path
        }
    
    def _create_modified_queue_file(
        self,
        source_file: Path,
        dest_file: Path,
        use_template_mode: bool = True,  # NEW: Template mode (recommended)
        start_machine: bool = True,
        heat_bed_hotend: bool = True,
        auto_bed_leveling: bool = True,
        flow_calibration: bool = True,
        vibration_test: bool = False,
        clean_nozzle: bool = True,
        wipe_nozzle: bool = True,
        nozzle_load_line: bool = True,
        startup_sound: bool = True,
        end_sound: bool = True,
        use_ams: bool = True,
        ams_slot: int = 0,
        filament_already_loaded: bool = False,
        # Quick Start options (FactorianDesigns optimization)
        quick_start: bool = False,
        preheat_offset: int = 0,
        pre_extrude: bool = False,
        pre_extrude_length: float = 2.2,
        auto_eject: bool = False,
        cooldown_temp: int = 32,
        # Additional controllable templates (from preset)
        cog_noise_reduction: bool = True,
        brush_material_wipe: bool = True,
        final_wipe_nozzle: bool = True,
        avoid_end_stop: bool = True,
        reset_machine_status: bool = True,
        home_after_wipe: bool = True,
        prepare_print: bool = True,
        extrude_calibration_test: bool = True,
        turn_off_light: bool = True,
        final_start: bool = True,
        # Filament profile for temperature overrides
        filament_id: int = None,
    ) -> str:
        """
        Create a modified 3MF file for the queue with G-Code sections disabled/enabled
        based on automation settings and filament settings.
        
        If filament_id is provided, temperatures will be taken from the filament profile
        instead of from the original gcode file.
        
        TWO MODES:
        1. Template Mode (use_template_mode=True) - RECOMMENDED
           - Extract ONLY print layers
           - Generate our own start/end gcode with all settings
           - More predictable and reliable
           
        2. Section Toggle Mode (use_template_mode=False) - LEGACY
           - Comment out specific sections in original gcode
           - Keep all original gcode
           - Less reliable due to complex marker parsing
        
        Args:
            source_file: Path to original 3MF file
            dest_file: Path to save modified file
            use_template_mode: Use template mode (True=recommended) or section toggle (False=legacy)
            auto_bed_leveling: Enable bed leveling
            flow_calibration: Enable flow calibration
            vibration_test: Enable vibration test
            clean_nozzle: Enable nozzle cleaning
            nozzle_load_line: Enable nozzle purge line at front of bed
            startup_sound: Enable startup sound
            end_sound: Enable end sound
            use_ams: Use AMS or external spool
            ams_slot: AMS slot to use (0-3)
            filament_already_loaded: Skip AMS load sequence if True
            quick_start: Skip vibration + flow for faster startup
            preheat_offset: Heat to nozzle_temp - offset (0 = disabled)
            pre_extrude: Add pre-extrude command before print
            pre_extrude_length: Amount to extrude in mm
            auto_eject: Auto eject after print
            cooldown_temp: Bed temp to cool to before eject
        
        Returns the path to the modified file.
        """
        from src.services.gcode_preprocessor import GCodePreprocessor, PrintSettings, FilamentSettings
        
        # Extract G-code from source
        result = extract_gcode_from_3mf(source_file, plate_num=1, max_lines=999999)
        
        if result.get('error'):
            raise ValueError(f"Failed to extract G-code: {result['error']}")
        
        lines = result['gcode']
        selected_plate = result['selected_plate']
        
        # Parse sections to find what can be disabled
        parsed = parse_gcode_sections(lines)
        sections = parsed.get('sections', [])  # Get the actual sections list
        
        # Build modifications list based on automation settings
        modifications = []
        
        for section in sections:
            for sub in section.get('subSections', []):
                if not sub.get('canDisable', False):
                    continue
                    
                sub_name = sub.get('name', '').lower()
                should_disable = False
                
                # Check if this section should be disabled based on settings
                # Bed Leveling: ;===== bed leveling =====
                if 'bed leveling' in sub_name or 'bed_leveling' in sub_name:
                    should_disable = not auto_bed_leveling
                    
                # Flow Calibration: ;===== auto extrude cali ===== or ;===== extrude cali test =====
                elif 'extrude cali' in sub_name or 'auto extrude' in sub_name or 'flow' in sub_name and 'cali' in sub_name:
                    should_disable = not flow_calibration
                    
                # Vibration Test: ;===== mech mode fast check =====
                elif 'mech mode' in sub_name or 'vibr' in sub_name:
                    should_disable = not vibration_test
                    
                # Clean Nozzle: ;===== wipe nozzle ===== or ;===== brush material =====
                elif 'wipe nozzle' in sub_name or 'brush material' in sub_name or 'remove waste' in sub_name:
                    should_disable = not clean_nozzle
                    
                # Startup Sound: ;=====start printer sound =====
                elif 'start' in sub_name and 'sound' in sub_name:
                    should_disable = not startup_sound
                    
                # End Sound: ;=====printer finish sound =====
                elif 'finish' in sub_name and 'sound' in sub_name:
                    should_disable = not end_sound
                
                if should_disable:
                    modifications.append({
                        'sectionId': sub.get('id'),
                        'enabled': False,
                        'startLine': sub.get('startLine'),
                        'endLine': sub.get('endLine')
                    })
        
        # Apply modifications if any
        if modifications:
            modified_lines = apply_section_modifications(lines, modifications)
            modified_content = '\n'.join(modified_lines)
            
            logger.info(f"Applied {len(modifications)} G-code section modifications")
        else:
            # No modifications needed, just use original content
            modified_content = '\n'.join(lines)
            logger.info("No G-code modifications needed")
        
        # ALWAYS apply GCodePreprocessor for section toggling and Quick Start
        # This handles vibration_test, flow_calibration, clean_nozzle, bed_leveling, sounds,
        # as well as AMS settings, preheat offset, and pre-extrude
        preprocessor = GCodePreprocessor()
        print_settings = PrintSettings(
            use_template_mode=use_template_mode,  # NEW: Template mode
            start_machine=start_machine,
            heat_bed_hotend=heat_bed_hotend,
            auto_bed_leveling=auto_bed_leveling,
            flow_calibration=flow_calibration,
            vibration_test=vibration_test,
            clean_nozzle=clean_nozzle,
            wipe_nozzle=wipe_nozzle,
            nozzle_load_line=nozzle_load_line,
            startup_sound=startup_sound,
            end_sound=end_sound,
            ams_slot=ams_slot,
            use_ams=use_ams,
            filament_already_loaded=filament_already_loaded,
            auto_eject=auto_eject,
            cooldown_temp=cooldown_temp,
            # Quick Start options
            quick_start=quick_start,
            preheat_offset=preheat_offset,
            pre_extrude=pre_extrude,
            pre_extrude_length=pre_extrude_length,
            # Additional controllable templates
            cog_noise_reduction=cog_noise_reduction,
            brush_material_wipe=brush_material_wipe,
            final_wipe_nozzle=final_wipe_nozzle,
            avoid_end_stop=avoid_end_stop,
            reset_machine_status=reset_machine_status,
            home_after_wipe=home_after_wipe,
            prepare_print=prepare_print,
            extrude_calibration_test=extrude_calibration_test,
            turn_off_light=turn_off_light,
            final_start=final_start,
        )
        # Validate settings (Quick Start will auto-disable vibration + flow)
        print_settings = print_settings.validate()
        
        # Get filament settings from database if filament_id provided
        filament_settings = FilamentSettings()  # Default
        if filament_id:
            try:
                from src.database.db import FilamentProfile
                filament_profile = self.db.query(FilamentProfile).filter(
                    FilamentProfile.filament_id == filament_id
                ).first()
                if filament_profile:
                    filament_settings = FilamentSettings(
                        filament_type=filament_profile.material_type or "PLA",
                        nozzle_temp=filament_profile.nozzle_temp_default or 220,
                        nozzle_temp_initial=filament_profile.nozzle_temp_default or 220,
                        bed_temp=filament_profile.bed_temp_default or 55,
                        bed_temp_initial=filament_profile.bed_temp_default or 55,
                        max_volumetric_speed=filament_profile.max_volumetric_speed or 12.0,
                        color=filament_profile.color_hex or "#FFFFFF",
                        from_profile=True,
                    )
                    logger.info(f"Using filament profile '{filament_profile.name}': "
                               f"nozzle={filament_settings.nozzle_temp}°C, "
                               f"bed={filament_settings.bed_temp}°C, "
                               f"type={filament_settings.filament_type}")
            except Exception as e:
                logger.warning(f"Failed to fetch filament profile {filament_id}: {e}")
        
        # Process G-code with all settings
        modified_content = preprocessor.process_gcode(
            modified_content,
            print_settings,
            filament_settings
        )
        
        # Log what was applied
        if use_template_mode:
            logger.info("Using TEMPLATE MODE - replaced all start/end gcode with optimized templates")
        else:
            logger.info("Using SECTION TOGGLE MODE (legacy)")
        
        if filament_already_loaded:
            logger.info("Applied filament_already_loaded modification - skipping AMS load sequence")
        elif not use_ams:
            logger.info("Applied external spool modification (T255)")
        else:
            logger.info(f"Applied AMS slot {ams_slot} modification")
        
        if preheat_offset > 0:
            logger.info(f"Applied preheat offset: -{preheat_offset}°C")
        if pre_extrude:
            logger.info(f"Applied pre-extrude: E{pre_extrude_length}mm")
        if quick_start:
            logger.info("Applied quick start mode (skipping vibration + flow calibration)")
        
        # Log section toggles
        if not vibration_test:
            logger.info("Disabled vibration test")
        if not flow_calibration:
            logger.info("Disabled flow calibration")
        if not clean_nozzle:
            logger.info("Disabled clean nozzle")
        if not auto_bed_leveling:
            logger.info("Disabled auto bed leveling")
        
        # Create the modified 3MF file
        with zipfile.ZipFile(source_file, 'r') as zf_in:
            with zipfile.ZipFile(dest_file, 'w', zipfile.ZIP_DEFLATED) as zf_out:
                for item in zf_in.namelist():
                    if item == selected_plate:
                        # Write modified gcode
                        zf_out.writestr(item, modified_content.encode('utf-8'))
                    else:
                        # Copy other files as-is
                        zf_out.writestr(item, zf_in.read(item))
        
        # Also copy to OUTPUT_DIR for user access
        output_filename = f"modified_{source_file.name}"
        output_path = OUTPUT_DIR / output_filename
        shutil.copy(dest_file, output_path)
        logger.info(f"Copied modified file to output folder: {output_path}")
        
        return str(dest_file)

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
        from src.services.gcode_preprocessor import GCodePreprocessor, PrintSettings, FilamentSettings
        from pathlib import Path
        import tempfile
        import shutil
        import zipfile
        
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
        
        # ==================== G-CODE PREPROCESSING ====================
        # Apply automation settings before uploading to printer
        # This removes nozzle_load_line section (purge line at front of bed) when disabled
        logger.info(f"🔧 Preprocessing G-code with automation settings...")
        try:
            # Build PrintSettings from queue item
            print_settings = PrintSettings(
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
            
            filament_settings = FilamentSettings()  # Default settings
            
            logger.info(f"   Settings: nozzle_load_line={print_settings.nozzle_load_line}, "
                       f"flow_cal={print_settings.flow_calibration}, auto_eject={print_settings.auto_eject}")
            
            # Preprocess 3MF file
            if str(file_path).endswith('.3mf'):
                preprocessor = GCodePreprocessor()
                processed_path = Path(tempfile.gettempdir()) / f"processed_{job.filename}"
                
                # Copy original to temp
                shutil.copy(str(file_path), str(processed_path))
                
                # Extract, process, repack
                with zipfile.ZipFile(str(file_path), 'r') as zf_read:
                    gcode_files = [f for f in zf_read.namelist() if f.endswith('.gcode')]
                    
                    if gcode_files:
                        temp_dir = tempfile.mkdtemp()
                        zf_read.extractall(temp_dir)
                        
                        for gcode_file in gcode_files:
                            gcode_full_path = Path(temp_dir) / gcode_file
                            if gcode_full_path.exists():
                                with open(gcode_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    original_gcode = f.read()
                                
                                processed_gcode = preprocessor.process_gcode(
                                    original_gcode, print_settings, filament_settings
                                )
                                
                                with open(gcode_full_path, 'w', encoding='utf-8') as f:
                                    f.write(processed_gcode)
                                
                                logger.info(f"   Preprocessed: {gcode_file}")
                        
                        # Repack 3mf
                        with zipfile.ZipFile(str(processed_path), 'w', zipfile.ZIP_DEFLATED) as zf_write:
                            import os
                            for root, dirs, files in os.walk(temp_dir):
                                for file in files:
                                    full_path = os.path.join(root, file)
                                    arcname = os.path.relpath(full_path, temp_dir)
                                    zf_write.write(full_path, arcname)
                        
                        shutil.rmtree(temp_dir)
                        file_path = processed_path
                        logger.info(f"✅ Preprocessing complete: {processed_path}")
                        
        except Exception as preproc_err:
            logger.warning(f"⚠️ Preprocessing failed, using original file: {preproc_err}")
            # Continue with original file
        # Apply automation settings before uploading to printer
        # logger.info(f"🔧 Preprocessing G-code with automation settings...")
        # try:
        #     # Build PrintSettings from queue item
        #     print_settings = PrintSettings(
        #         auto_bed_leveling=queue_item.auto_bed_leveling if queue_item.auto_bed_leveling is not None else True,
        #         flow_calibration=queue_item.flow_calibration if queue_item.flow_calibration is not None else False,
        #         vibration_test=queue_item.vibration_test if queue_item.vibration_test is not None else False,
        #         clean_nozzle=queue_item.clean_nozzle if queue_item.clean_nozzle is not None else True,
        #         auto_eject=queue_item.auto_eject if queue_item.auto_eject is not None else True,
        #         cooldown_temp=queue_item.cooldown_temp if queue_item.cooldown_temp is not None else 32,
        #         startup_sound=queue_item.startup_sound if queue_item.startup_sound is not None else True,
        #         end_sound=queue_item.end_sound if queue_item.end_sound is not None else True,
        #         ams_slot=queue_item.ams_slot if queue_item.ams_slot is not None else 0,
        #         nozzle_load_line=queue_item.nozzle_load_line if hasattr(queue_item, 'nozzle_load_line') and queue_item.nozzle_load_line is not None else False,
        #         use_ams=queue_item.use_ams if queue_item.use_ams is not None else True,
        #         timelapse=queue_item.timelapse if hasattr(queue_item, 'timelapse') and queue_item.timelapse is not None else False
        #     )
        #     
        #     filament_settings = FilamentSettings()  # Default settings
        #     
        #     logger.info(f"   Settings: nozzle_load_line={print_settings.nozzle_load_line}, "
        #                f"flow_cal={print_settings.flow_calibration}, auto_eject={print_settings.auto_eject}")
        #     
        #     # Preprocess 3MF file
        #     if str(file_path).endswith('.3mf'):
        #         preprocessor = GCodePreprocessor()
        #         processed_path = Path(tempfile.gettempdir()) / f"processed_{job.filename}"
        #         
        #         # Copy original to temp
        #         shutil.copy(str(file_path), str(processed_path))
        #         
        #         # Extract, process, repack
        #         with zipfile.ZipFile(str(file_path), 'r') as zf_read:
        #             gcode_files = [f for f in zf_read.namelist() if f.endswith('.gcode')]
        #             
        #             if gcode_files:
        #                 temp_dir = tempfile.mkdtemp()
        #                 zf_read.extractall(temp_dir)
        #                 
        #                 for gcode_file in gcode_files:
        #                     gcode_full_path = Path(temp_dir) / gcode_file
        #                     if gcode_full_path.exists():
        #                         with open(gcode_full_path, 'r', encoding='utf-8', errors='ignore') as f:
        #                             original_gcode = f.read()
        #                         
        #                         processed_gcode = preprocessor.process_gcode(
        #                             original_gcode, print_settings, filament_settings
        #                         )
        #                         
        #                         with open(gcode_full_path, 'w', encoding='utf-8') as f:
        #                             f.write(processed_gcode)
        #                         
        #                         logger.info(f"   Preprocessed: {gcode_file}")
        #                 
        #                 # Repack 3mf
        #                 with zipfile.ZipFile(str(processed_path), 'w', zipfile.ZIP_DEFLATED) as zf_write:
        #                     import os
        #                     for root, dirs, files in os.walk(temp_dir):
        #                         for file in files:
        #                             full_path = os.path.join(root, file)
        #                             arcname = os.path.relpath(full_path, temp_dir)
        #                             zf_write.write(full_path, arcname)
        #                 
        #                 shutil.rmtree(temp_dir)
        #                 file_path = processed_path
        #                 logger.info(f"✅ Preprocessing complete: {processed_path}")
        #                 
        # except Exception as preproc_err:
        #     logger.warning(f"⚠️ Preprocessing failed, using original file: {preproc_err}")
        #     # Continue with original file
        
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
            
            # Get timelapse from queue item
            timelapse = queue_item.timelapse if hasattr(queue_item, 'timelapse') else False
            
            # IMPORTANT: Always send flow_cali=True, vibration_cali=True, bed_leveling=True
            # to match manual send behavior. Bambu A1 firmware interprets these as:
            # TRUE = "file handles calibration, skip printer's built-in routine"
            # FALSE = "run printer's built-in calibration routine"
            flow_cali = True
            vibration_cali = True
            bed_leveling = True
            
            logger.info(f"   AMS settings: use_ams={use_ams}, ams_slot={ams_slot}")
            logger.info(f"   Calibration: flow_cali={flow_cali}, vibration_cali={vibration_cali}, bed_leveling={bed_leveling}")
            logger.info(f"   NOTE: Always sending TRUE for calibration params to skip printer's built-in routines")
            
            # Start print from SD card with AMS settings and calibration options
            # CRITICAL: Pass ams_slot as integer, bambu_service will convert to proper list format
            print_success = bambu_client.start_print_from_sd(
                filename=job.filename,
                use_ams=use_ams,
                plate_number=1,
                ams_mapping=None,  # Let bambu_service convert from ams_slot
                ams_slot=ams_slot,
                flow_cali=flow_cali,
                vibration_cali=vibration_cali,
                bed_leveling=bed_leveling,
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
