"""
G-code Preprocessor Service for Bambu Lab A1

Modifies G-code before sending to printer based on:
- Filament settings from inventory
- Per-job print settings (bed leveling, flow test, auto eject, etc.)

TWO MODES OF OPERATION:
1. Section Toggle Mode (default): Comment out/uncomment sections using markers
2. Template Mode (new): Replace ALL start/end gcode with our own templates

Template Mode is recommended for cleaner, more predictable results.

Based on FactorianDesigns A1 automation G-codes:
https://www.youtube.com/watch?v=SFd0sxN2eqk

Author: Print Farm Management System
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PrintSettings:
    """Per-job print settings"""
    # MODE SELECTION (New!)
    use_template_mode: bool = True  # True = template mode (recommended), False = section toggle mode
    
    # Calibration options
    start_machine: bool = True
    heat_bed_hotend: bool = True
    auto_bed_leveling: bool = True
    flow_calibration: bool = True
    vibration_test: bool = False
    clean_nozzle: bool = True
    wipe_nozzle: bool = True  # Wipe nozzle section (contains M109 S140 wait)
    nozzle_load_line: bool = False  # Nozzle purge line at front of bed before print - DEFAULT OFF to avoid unwanted purge
    
    # Automation options
    auto_eject: bool = False
    cooldown_temp: int = 32  # Target bed temp before eject (30-35°C for room temp)
    timelapse: bool = False  # Enable timelapse recording during print
    
    # Sound options
    startup_sound: bool = True
    end_sound: bool = True
    
    # AMS options
    ams_slot: int = 0  # 0-3 for AMS slots, 255 for no AMS/external
    use_ams: bool = True  # If False, use external spool
    filament_already_loaded: bool = False  # If True, skip AMS load sequence (filament sudah di extruder)
    
    # Quick Start options (FactorianDesigns optimization) - ENABLED BY DEFAULT
    quick_start: bool = True  # Skip vibration test + flow cali for faster startup
    preheat_offset: int = 20  # Heat to nozzle_temp - offset first to prevent oozing (0 = disabled, 20 = recommended)
    pre_extrude: bool = True  # Add pre-extrude command before print to fill nozzle
    pre_extrude_length: float = 2.2  # Length to extrude (mm)
    
    # Additional controllable templates (from preset/queue)
    cog_noise_reduction: bool = True
    brush_material_wipe: bool = True
    final_wipe_nozzle: bool = True
    avoid_end_stop: bool = True
    reset_machine_status: bool = True
    home_after_wipe: bool = True
    prepare_print: bool = False  # DEFAULT OFF - avoid moving to front of bed
    extrude_calibration_test: bool = True
    turn_off_light: bool = True
    final_start: bool = True
    
    def validate(self):
        """Validate settings - auto_eject requires flow_calibration OFF"""
        if self.auto_eject and self.flow_calibration:
            logger.warning("Auto eject enabled, disabling flow calibration to prevent debris")
            self.flow_calibration = False
        # Quick start disables calibration and slow templates
        if self.quick_start:
            if self.vibration_test:
                logger.info("Quick start enabled, disabling vibration test")
                self.vibration_test = False
            if self.flow_calibration:
                logger.info("Quick start enabled, disabling flow calibration")
                self.flow_calibration = False
            # Also disable slow preparation steps for Quick Start
            if self.cog_noise_reduction:
                logger.info("Quick start enabled, disabling cog noise reduction")
                self.cog_noise_reduction = False
            if self.wipe_nozzle:
                logger.info("Quick start enabled, disabling wipe nozzle")
                self.wipe_nozzle = False
            if self.clean_nozzle:
                logger.info("Quick start enabled, disabling clean nozzle")
                self.clean_nozzle = False
            if self.brush_material_wipe:
                logger.info("Quick start enabled, disabling brush material wipe")
                self.brush_material_wipe = False
            if self.final_wipe_nozzle:
                logger.info("Quick start enabled, disabling final wipe nozzle")
                self.final_wipe_nozzle = False
            if self.extrude_calibration_test:
                logger.info("Quick start enabled, disabling extrude calibration test")
                self.extrude_calibration_test = False
            if self.home_after_wipe:
                logger.info("Quick start enabled, disabling home after wipe")
                self.home_after_wipe = False
            if self.auto_bed_leveling:
                logger.info("Quick start enabled, disabling auto bed leveling")
                self.auto_bed_leveling = False
        return self


@dataclass 
class FilamentSettings:
    """Filament settings from inventory"""
    filament_type: str = "PLA"
    nozzle_temp: int = 220
    nozzle_temp_initial: int = 220
    bed_temp: int = 55
    bed_temp_initial: int = 55
    max_volumetric_speed: float = 12.0
    color: str = "#FFFFFF"
    from_profile: bool = False  # True when populated from filament_profiles table


class GCodePreprocessor:
    """
    G-code preprocessor for Bambu Lab A1 print farm automation
    """
    
    # Sections that can be toggled
    # NOTE: For startup_sound and end_sound, Bambu Studio uses the SAME marker for start and end
    # The section ends when the marker appears the SECOND time
    SECTION_MARKERS = {
        'startup_sound': (';=====start printer sound', ';=====start printer sound'),  # Same marker - ends on 2nd occurrence
        'end_sound': (';=====printer finish  sound', ';=====printer finish  sound'),  # Same marker - ends on 2nd occurrence
        'vibration_test': (';===== mech mode fast check start', ';===== mech mode fast check end'),
        'flow_calibration': (';===== auto extrude cali start', ';===== auto extrude cali end'),
        'bed_leveling': (';===== bed leveling ==', ';===== bed leveling end'),
        'clean_nozzle': (';===== brush material wipe nozzle', ';===== brush material wipe nozzle end'),  # Brush cleaning
        'wipe_nozzle': (';===== wipe nozzle ===', ';===== wipe nozzle end'),  # Full wipe nozzle section (M109 S140)
        'nozzle_load_line': (';===== nozzle load line', ';===== nozzle load line end'),  # Purge line at front of bed
        'ams_load': (';===== prepare print temperature and material', ';===== prepare print temperature and material end'),
    }
    
    # AMS command patterns (M620 = start AMS operation, M621 = finish AMS operation)
    AMS_COMMANDS = [
        r'M620\s+S\d+A',      # M620 S[slot]A - switch to AMS slot
        r'M620\.1\s+E',       # M620.1 E - filament load settings
        r'M620\.3\s+W',       # M620.3 W - tangle detection
        r'M620\.10\s+',       # M620.10 - flush settings
        r'M620\.11\s+',       # M620.11 - retraction settings
        r'M621\s+S\d+A',      # M621 S[slot]A - finish AMS material
        r'M628\s+',           # M628 - AMS buffer control
        r'M629\s*',           # M629 - AMS operation end
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_gcode(
        self,
        gcode_content: str,
        print_settings: PrintSettings,
        filament_settings: FilamentSettings
    ) -> str:
        """
        Process G-code with given settings
        
        Args:
            gcode_content: Original G-code string
            print_settings: Per-job print settings
            filament_settings: Filament settings from inventory
            
        Returns:
            Modified G-code string
        """
        # Validate settings (auto_eject disables flow_calibration)
        print_settings.validate()
        
        self.logger.info(f"Processing G-code with settings: template_mode={print_settings.use_template_mode}, "
                        f"auto_eject={print_settings.auto_eject}, "
                        f"flow_cal={print_settings.flow_calibration}, bed_level={print_settings.auto_bed_leveling}")
        
        # =========================================================
        # TEMPLATE MODE (NEW - RECOMMENDED)
        # =========================================================
        if print_settings.use_template_mode:
            return self._process_with_templates(gcode_content, print_settings, filament_settings)
        
        # =========================================================
        # SECTION TOGGLE MODE (LEGACY)
        # =========================================================
        return self._process_with_section_toggle(gcode_content, print_settings, filament_settings)
    
    def _process_with_templates(
        self,
        gcode_content: str,
        print_settings: PrintSettings,
        filament_settings: FilamentSettings
    ) -> str:
        """
        Process G-code using template mode with BLOCK PRESERVATION:
        
        Preserves Bambu block structure:
        1. HEADER_BLOCK - Contains print time, layer count (preserved)
        2. CONFIG_BLOCK - Contains slicer settings (preserved)
        3. EXECUTABLE_BLOCK - Contains start/print/end gcode
           - Start gcode: REPLACED with our templates
           - Print layers: PRESERVED
           - End gcode: REPLACED with our templates
        4. Filament footer - Usage summary (preserved)
        
        This ensures printer can still display:
        - Print time estimate
        - Total layer count
        - Filament weight/length
        """
        from .gcode_templates import (
            GCodeTemplates, GCodeLayerExtractor, TemplateSettings, PrinterConfig,
            process_gcode_with_templates
        )
        
        self.logger.info("Processing G-code in TEMPLATE MODE with BLOCK PRESERVATION")
        
        # Configure template settings from print/filament settings
        template_settings = TemplateSettings(
            # Temperatures
            nozzle_temp=filament_settings.nozzle_temp,
            bed_temp=filament_settings.bed_temp,
            nozzle_temp_initial=filament_settings.nozzle_temp_initial,
            # Respect filament profile temps by skipping file-metadata override
            prefer_file_metadata=not getattr(filament_settings, "from_profile", False),
            # AMS
            use_ams=print_settings.use_ams,
            ams_slot=print_settings.ams_slot,
            filament_already_loaded=print_settings.filament_already_loaded,
            # Quick Start
            preheat_offset=print_settings.preheat_offset if print_settings.quick_start else 0,
            pre_extrude=print_settings.pre_extrude,
            pre_extrude_length=print_settings.pre_extrude_length,
            # Features
            home_before_print=True,
            auto_eject=print_settings.auto_eject,
            cooldown_temp=print_settings.cooldown_temp,
            # Filament
            filament_type=filament_settings.filament_type,
            max_volumetric_speed=filament_settings.max_volumetric_speed,
            # Controllable template settings (from queue/print settings)
            start_machine=print_settings.start_machine,
            heat_bed_hotend=print_settings.heat_bed_hotend,
            startup_sound=print_settings.startup_sound,
            vibration_test=print_settings.vibration_test,
            clean_nozzle=print_settings.clean_nozzle,
            wipe_nozzle=print_settings.wipe_nozzle,
            flow_calibration=print_settings.flow_calibration,
            auto_bed_leveling=print_settings.auto_bed_leveling,
            nozzle_load_line=print_settings.nozzle_load_line,
            timelapse=print_settings.timelapse,
            end_sound=print_settings.end_sound,
            # Additional controllable templates (from preset/queue)
            cog_noise_reduction=print_settings.cog_noise_reduction,
            brush_material_wipe=print_settings.brush_material_wipe,
            final_wipe_nozzle=print_settings.final_wipe_nozzle,
            avoid_end_stop=print_settings.avoid_end_stop,
            reset_machine_status=print_settings.reset_machine_status,
            home_after_wipe=print_settings.home_after_wipe,
            prepare_print=print_settings.prepare_print,
            extrude_calibration_test=print_settings.extrude_calibration_test,
            turn_off_light=print_settings.turn_off_light,
            final_start=print_settings.final_start,
        )
        
        self.logger.info(f"Template settings: startup_sound={template_settings.startup_sound}, "
                        f"vibration_test={template_settings.vibration_test}, "
                        f"clean_nozzle={template_settings.clean_nozzle}, "
                        f"auto_bed_leveling={template_settings.auto_bed_leveling}")
        
        printer_config = PrinterConfig(
            printer_model="A1",
            bed_size_x=256.0,
            bed_size_y=256.0,
            max_z=256.0,
            has_ams=print_settings.use_ams,
        )
        
        # Use the new block-preserving function
        result = process_gcode_with_templates(gcode_content, template_settings, printer_config)
        
        # IMPORTANT: Also replace OrcaSlicer placeholders in the preserved sections
        # This ensures print_layers section gets proper temperature values
        # Pass print_settings for filament_already_loaded replacement
        result = self._replace_filament_variables(result, filament_settings, print_settings)
        
        self.logger.info(f"Template mode complete with block preservation")
        
        return result
    
    def _process_with_section_toggle(
        self,
        gcode_content: str,
        print_settings: PrintSettings,
        filament_settings: FilamentSettings
    ) -> str:
        """
        Process G-code using legacy section toggle mode.
        Finds and comments out specific sections based on markers.
        """
        self.logger.info("Processing G-code in SECTION TOGGLE MODE (legacy)")
        
        # Step 1: Replace filament template variables
        # Pass print_settings for filament_already_loaded replacement
        gcode = self._replace_filament_variables(gcode_content, filament_settings, print_settings)
        
        # Step 2: Apply preheat offset BEFORE toggle sections
        # (toggle sections may disable M109 commands, so we need to modify them first)
        if print_settings.preheat_offset > 0:
            gcode = self._apply_preheat_offset(gcode, print_settings.preheat_offset, filament_settings)
            self.logger.info(f"Applied preheat offset: -{print_settings.preheat_offset}°C")
        
        # Step 3: Add pre-extrude command BEFORE toggle sections
        # (ensures pre-extrude is added to the correct position before sections are disabled)
        if print_settings.pre_extrude:
            gcode = self._add_pre_extrude(gcode, print_settings.pre_extrude_length)
            self.logger.info(f"Added pre-extrude command: E{print_settings.pre_extrude_length}")
        
        # Step 4: Toggle sections based on settings
        # (this may disable calibration sections that contain M109 commands)
        gcode = self._toggle_sections(gcode, print_settings)
        
        # Step 5: Add auto-eject end code if enabled
        if print_settings.auto_eject:
            gcode = self._add_auto_eject(gcode, print_settings.cooldown_temp)
        
        # Step 6: Handle AMS/filament settings
        if print_settings.filament_already_loaded:
            # Skip AMS load sequence - filament sudah di extruder
            gcode = self._skip_ams_load_sequence(gcode)
            self.logger.info("Skipping AMS load sequence - filament already loaded in extruder")
        elif not print_settings.use_ams:
            # Using external spool (T255)
            gcode = self._set_external_spool(gcode)
            self.logger.info("Set to external spool mode (T255)")
        elif print_settings.ams_slot >= 0:
            # Normal AMS mode - set specific slot
            gcode = self._set_ams_slot(gcode, print_settings.ams_slot)
            self.logger.info(f"Set AMS slot to {print_settings.ams_slot}")
        
        return gcode
    
    def _replace_filament_variables(self, gcode: str, filament: FilamentSettings, print_settings: PrintSettings = None) -> str:
        """Replace Bambu Studio template variables with actual values"""
        
        replacements = {
            # Filament type
            r'\{filament_type\[initial_no_support_extruder\]\}': filament.filament_type,
            r'\{filament_type\[initial_extruder\]\}': filament.filament_type,
            r'\{filament_type\[0\]\}': filament.filament_type,
            
            # Nozzle temperatures
            r'\{nozzle_temperature_initial_layer\[initial_extruder\]\}': str(filament.nozzle_temp_initial),
            r'\{nozzle_temperature_initial_layer\[initial_no_support_extruder\]\}': str(filament.nozzle_temp_initial),
            r'\{nozzle_temperature_initial_layer\[0\]\}': str(filament.nozzle_temp_initial),
            r'\{nozzle_temperature\[initial_extruder\]\}': str(filament.nozzle_temp),
            r'\{nozzle_temperature\[0\]\}': str(filament.nozzle_temp),
            
            # Bed temperatures  
            r'\[bed_temperature_initial_layer_single\]': str(filament.bed_temp_initial),
            r'\{bed_temperature_initial_layer_single\}': str(filament.bed_temp_initial),
            r'\{bed_temperature\[0\]\}': str(filament.bed_temp),
            
            # Volumetric speed
            r'\{filament_max_volumetric_speed\[initial_no_support_extruder\]\}': str(filament.max_volumetric_speed),
            r'\{filament_max_volumetric_speed\[0\]\}': str(filament.max_volumetric_speed),
            
            # Flush/purge temperatures (use nozzle temp)
            r'\{flush_temperatures\[initial_no_support_extruder\]\}': str(filament.nozzle_temp),
            r'\{nozzle_temperature_range_high\[initial_no_support_extruder\]\}': str(min(filament.nozzle_temp + 20, 300)),
            r'\{nozzle_temperature_range_high\[initial_extruder\]\}': str(min(filament.nozzle_temp + 20, 300)),
        }
        
        # Add print settings related replacements if available
        if print_settings:
            replacements[r'\{filament_already_loaded\}'] = '1' if print_settings.filament_already_loaded else '0'
        
        result = gcode
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result)
        
        # Also handle temperature math expressions like {nozzle_temp - 50}
        result = self._evaluate_temp_expressions(result, filament)
        
        return result
    
    def _evaluate_temp_expressions(self, gcode: str, filament: FilamentSettings) -> str:
        """Evaluate temperature expressions like {nozzle_temperature_initial_layer[initial_extruder]-50}"""
        
        # Pattern: {variable-number} or {variable+number}
        pattern = r'\{nozzle_temperature_initial_layer\[initial_extruder\]([+-])(\d+)\}'
        
        def replace_expr(match):
            op = match.group(1)
            value = int(match.group(2))
            if op == '-':
                return str(filament.nozzle_temp_initial - value)
            else:
                return str(filament.nozzle_temp_initial + value)
        
        return re.sub(pattern, replace_expr, gcode)
    
    def _toggle_sections(self, gcode: str, settings: PrintSettings) -> str:
        """Comment out or enable sections based on settings"""
        
        toggles = {
            'startup_sound': settings.startup_sound,
            'end_sound': settings.end_sound,
            'vibration_test': settings.vibration_test,
            'flow_calibration': settings.flow_calibration,
            'bed_leveling': settings.auto_bed_leveling,
            'clean_nozzle': settings.clean_nozzle,
            'wipe_nozzle': settings.wipe_nozzle,
            'nozzle_load_line': settings.nozzle_load_line,
        }
        
        result = gcode
        
        for section, enabled in toggles.items():
            if section in self.SECTION_MARKERS:
                start_marker, end_marker = self.SECTION_MARKERS[section]
                
                if not enabled:
                    # Comment out the section
                    result = self._comment_section(result, start_marker, end_marker)
                else:
                    # Uncomment the section if it was commented
                    result = self._uncomment_section(result, start_marker, end_marker)
        
        return result
    
    def _comment_section(self, gcode: str, start_marker: str, end_marker: str) -> str:
        """Comment out lines between markers, but NEVER disable safety commands or Quick Start sections"""
        lines = gcode.split('\n')
        in_section = False
        in_pre_extrude_block = False  # Only for PRE-EXTRUDE multi-line block
        result = []
        
        # Check if start and end markers are the same (Bambu style - section ends on 2nd occurrence)
        same_marker = start_marker == end_marker
        
        # Markers for multi-line protected blocks (have start and end)
        # These match the actual markers used in _add_pre_extrude()
        pre_extrude_start = ';===== PRE-EXTRUDE'
        pre_extrude_end = ';===== END PRE-EXTRUDE'
        
        # Single-line markers that protect only their own line AND subsequent lines until next section
        single_line_protected_markers = [
            'PREHEAT-OFFSET',
            'preheat offset',  # The modified M109 command comment
        ]
        
        # SAFETY COMMANDS - NEVER disable these (risk of fire/damage)
        safety_commands = [
            'M104 S0',   # Turn off hotend
            'M140 S0',   # Turn off bed
            'M106 S0',   # Turn off part cooling fan
            'M106 P1 S0', # Turn off aux fan
            'M106 P2 S0', # Turn off chamber fan
            'M107',      # Turn off fan (legacy)
            'M84',       # Disable motors
            'M18',       # Disable motors (alternative)
            'M400',      # Wait for moves to finish (needed before shutdown)
        ]
        
        for line in lines:
            stripped = line.strip()
            
            # Check if entering PRE-EXTRUDE block (multi-line)
            if pre_extrude_start in line:
                in_pre_extrude_block = True
            
            # Check if exiting PRE-EXTRUDE block
            if pre_extrude_end in line:
                result.append(line)
                in_pre_extrude_block = False
                continue
            
            # Check if line is protected:
            # 1. Inside PRE-EXTRUDE block, OR
            # 2. Line contains single-line protected marker
            is_in_block = in_pre_extrude_block
            is_single_protected = any(marker.lower() in line.lower() for marker in single_line_protected_markers)
            
            # Check if line is a SAFETY command (NEVER disable)
            is_safety_command = any(cmd in stripped for cmd in safety_commands)
            
            is_protected = is_in_block or is_single_protected or is_safety_command
            
            # Only match markers at the START of line (after whitespace)
            # This prevents matching markers embedded in long comment strings like machine_start_gcode
            # Also check if line was already disabled by another section
            clean_stripped = stripped
            while clean_stripped.startswith(';[DISABLED] '):
                clean_stripped = clean_stripped[12:]  # Remove '[DISABLED] ' prefix
            
            line_starts_with_marker = clean_stripped.startswith(start_marker)
            line_starts_with_end = clean_stripped.startswith(end_marker)
            
            # Handle same marker for start/end (Bambu style: section ends on 2nd occurrence)
            if same_marker and line_starts_with_marker:
                # Toggle section state
                if in_section:
                    # This is the END marker (2nd occurrence)
                    if not stripped.startswith(';[DISABLED]'):
                        result.append(';[DISABLED] ' + line)
                    else:
                        result.append(line)  # Already disabled
                    in_section = False
                else:
                    # This is the START marker (1st occurrence)
                    in_section = True
                    if not stripped.startswith(';[DISABLED]'):
                        result.append(';[DISABLED] ' + line)
                    else:
                        result.append(line)  # Already disabled
            elif line_starts_with_marker:
                in_section = True
                if not stripped.startswith(';[DISABLED]'):
                    result.append(';[DISABLED] ' + line)
                else:
                    result.append(line)  # Already disabled
            elif line_starts_with_end:
                if not stripped.startswith(';[DISABLED]'):
                    result.append(';[DISABLED] ' + line)
                else:
                    result.append(line)  # Already disabled
                in_section = False
            elif in_section and not is_protected:
                # Disable ALL lines in section, including comments (sub-section markers)
                if not stripped.startswith(';[DISABLED]'):
                    result.append(';[DISABLED] ' + line)
                else:
                    result.append(line)  # Already disabled
            else:
                result.append(line)
        
        return '\n'.join(result)
    
    def _uncomment_section(self, gcode: str, start_marker: str, end_marker: str) -> str:
        """Uncomment lines between markers (remove ;[DISABLED] prefix) - only within the specified section"""
        lines = gcode.split('\n')
        in_section = False
        result = []
        
        # Check if start and end markers are the same (Bambu style - section ends on 2nd occurrence)
        same_marker = start_marker == end_marker
        
        for line in lines:
            stripped = line.strip()
            
            # Check if this line starts with the start marker (possibly with DISABLED prefix)
            clean_stripped = stripped.replace(';[DISABLED] ', '')
            line_starts_with_marker = clean_stripped.startswith(start_marker)
            line_starts_with_end = clean_stripped.startswith(end_marker)
            
            # Handle same marker for start/end (Bambu style: section ends on 2nd occurrence)
            if same_marker and line_starts_with_marker:
                # Toggle section state
                if in_section:
                    # This is the END marker (2nd occurrence)
                    if line.startswith(';[DISABLED] '):
                        result.append(line[12:])
                    else:
                        result.append(line)
                    in_section = False
                else:
                    # This is the START marker (1st occurrence)
                    in_section = True
                    if line.startswith(';[DISABLED] '):
                        result.append(line[12:])
                    else:
                        result.append(line)
            elif line_starts_with_marker:
                in_section = True
                # Remove DISABLED prefix if present
                if line.startswith(';[DISABLED] '):
                    result.append(line[12:])  # Remove ';[DISABLED] ' prefix
                else:
                    result.append(line)
            elif line_starts_with_end:
                # Remove DISABLED prefix if present
                if line.startswith(';[DISABLED] '):
                    result.append(line[12:])
                else:
                    result.append(line)
                in_section = False
            elif in_section:
                # Remove DISABLED prefix only within section
                if line.startswith(';[DISABLED] '):
                    result.append(line[12:])
                else:
                    result.append(line)
            else:
                result.append(line)
        
        return '\n'.join(result)
        
        return '\n'.join(result)
    
    def _add_auto_eject(self, gcode: str, cooldown_temp: int = 32) -> str:
        """
        Add auto-eject sequence to end of G-code
        Based on FactorianDesigns End_A1.txt
        https://www.youtube.com/watch?v=SFd0sxN2eqk
        """
        
        # Generate multiple M190 commands (Bambu firmware quirk - needs many calls)
        m190_commands = '\n'.join([f'M190 S{cooldown_temp}\t;wait for bed temp' for _ in range(45)])
        
        auto_eject_code = f'''
;===== AUTO EJECT SEQUENCE (Print Farm - FactorianDesigns) =====
;Based on https://www.youtube.com/watch?v=SFd0sxN2eqk

M400 ; wait for buffer to clear
G92 E0 ; zero the extruder
G1 E-0.8 F1800 ; retract

M140 S0 ; turn off bed
M106 S0 ; turn off fan
M106 P2 S0 ; turn off remote part cooling fan
M106 P3 S0 ; turn off chamber cooling fan
M104 S0 ; turn off hotend

M400 ;wait for all print moves to be done

;===== Cool Down =======
G90   
G1 X-48 Y262 F3600 ; move to safe limit position on the left
			  
{m190_commands}

M140 S0 ; turn off bed (ensure it's off)

;======= Cool Down Done, Start Push Off =============
; calculate a good z-pushoff height
; parts below 41mm height: nozzle at Z1
; taller parts: nozzle 40mm below top layer

; Using conditional: if max_layer_z > 41, use max_layer_z - 40, else use Z1
; Note: This will be processed with actual max_layer_z from gcode
G1 Z{{max_layer_z - 40 > 1 ? max_layer_z - 40 : 1}} F600

M400 P100											
G1 Y-0.5 F300		; very slow push off using the Y gantry

;======== Push off complete, start safety clear / side sweep ======
G1 Y262 F800	;move bed forward again
G1 Z1 F600		;move nozzle closer to the bed

G1 Y210 F2000	;move bed back a little
G1 X256 F800	;move to the right
G1 X-48	F2000	;move back to the left

G1 Y165 F2000	;move bed back a little
G1 X256 F800	;move to the right
G1 X-48	F2000	;move back to the left

G1 Y120 F2000	;move bed back a little
G1 X256 F800	;move to the right
G1 X-48	F2000	;move back to the left

G1 Y75 F2000	;move bed back a little
G1 X256 F800	;move to the right
G1 X-48	F2000	;move back to the left

G1 Y30 F2000	;move bed back a little
G1 X256 F800	;move to the right
G1 X-48	F2000	;move back to the left

G1 Y0 F2000		;move bed back a little
G1 X256 F800	;move to the right
G1 X-48	F2000	;move back to the left

G1 Y262 F2000	;push bed forward one last time

;====== Safety clear complete =======
																							
M17 R ; restore z current

M220 S100  ; Reset feedrate magnitude
M201.2 K1.0 ; Reset acc magnitude
M73.2   R1.0 ;Reset left time magnitude
M1002 set_gcode_claim_speed_level : 0

;=====printer finish sound (FactorianDesigns)=========
M17
M400 S1
M1006 S1
M1006 A0 B20 L100 C37 D20 M40 E42 F20 N60
M1006 A0 B10 L100 C44 D10 M60 E44 F10 N60
M1006 A0 B10 L100 C46 D10 M80 E46 F10 N80
M1006 A44 B20 L100 C39 D20 M60 E48 F20 N60
M1006 A0 B10 L100 C44 D10 M60 E44 F10 N60
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N60
M1006 A0 B10 L100 C39 D10 M60 E39 F10 N60
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N60
M1006 A0 B10 L100 C44 D10 M60 E44 F10 N60
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N60
M1006 A0 B10 L100 C39 D10 M60 E39 F10 N60
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N60
M1006 A0 B10 L100 C48 D10 M60 E44 F10 N80
M1006 A0 B10 L100 C0 D10 M60 E0 F10 N80
M1006 A44 B20 L100 C49 D20 M80 E41 F20 N80
M1006 A0 B20 L100 C0 D20 M60 E0 F20 N80
M1006 A0 B20 L100 C37 D20 M30 E37 F20 N60
M1006 W
;=====printer finish sound=========

M400
M18 X Y Z ; disable motors

;===== AUTO EJECT COMPLETE - READY FOR NEXT JOB =====
'''
        
        # Find the original end G-code section and replace/append
        # Look for common end patterns
        end_patterns = [
            'M400 ; wait for buffer to clear',
            '; END_GCODE',
            ';END',
        ]
        
        for pattern in end_patterns:
            if pattern in gcode:
                # Insert before the end pattern
                gcode = gcode.replace(pattern, auto_eject_code + '\n' + pattern)
                return gcode
        
        # If no pattern found, just append
        return gcode + '\n' + auto_eject_code
    
    def _set_ams_slot(self, gcode: str, slot: int) -> str:
        """Set the AMS slot to use"""
        
        # Replace [initial_no_support_extruder] and [initial_extruder] with slot number
        replacements = {
            r'\[initial_no_support_extruder\]': str(slot),
            r'\[initial_extruder\]': str(slot),
            r'T\[initial_no_support_extruder\]': f'T{slot}',
            r'T\[initial_extruder\]': f'T{slot}',
        }
        
        result = gcode
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result)
        
        # Also update M620/M621 commands with the new slot
        result = re.sub(r'M620\s+S\d+A', f'M620 S{slot}A', result)
        result = re.sub(r'M621\s+S\d+A', f'M621 S{slot}A', result)
        
        return result
    
    def _set_external_spool(self, gcode: str) -> str:
        """
        Set to external spool mode (T255 - bypass AMS)
        Used when filament is loaded manually from external spool holder
        """
        # Replace all AMS slot references with 255 (external)
        replacements = {
            r'\[initial_no_support_extruder\]': '255',
            r'\[initial_extruder\]': '255',
            r'T\[initial_no_support_extruder\]': 'T255',
            r'T\[initial_extruder\]': 'T255',
            r'M620\s+S\d+A': 'M620 S255',  # Switch to external
            r'M621\s+S\d+A': 'M621 S255',  # Finish with external
        }
        
        result = gcode
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result)
        
        return result
    
    def _apply_preheat_offset(self, gcode: str, offset: int, filament: FilamentSettings) -> str:
        """
        Apply preheat offset to prevent oozing during startup.
        Based on FactorianDesigns optimization:
        - Heat nozzle to target_temp - offset first
        - This prevents excessive oozing during homing/calibration
        - Full temperature is reached later just before printing starts
        
        Args:
            gcode: G-code content
            offset: Temperature offset (e.g., 20 means heat to target - 20°C first)
            filament: Filament settings for temperature info
        """
        lines = gcode.split('\n')
        result = []
        modified_first_heat = False
        in_startup = True  # We're in startup until we see LAYER_CHANGE or print features
        
        # Markers that indicate printing has started
        print_start_markers = [
            ';LAYER_CHANGE',
            '; CHANGE_LAYER',
            '; FEATURE: Outer wall',
            '; FEATURE: Inner wall',
            ';TYPE:',
        ]
        
        for line in lines:
            stripped = line.strip()
            
            # Exit startup mode when we reach actual printing
            for marker in print_start_markers:
                if marker in stripped:
                    in_startup = False
                    break
            
            # Only modify during startup phase
            if in_startup and not modified_first_heat:
                # Look for first nozzle heat command (M109 - wait for temp)
                # Pattern: M109 S220 - only modify if temp >= 180 (actual nozzle temp, not bed/idle)
                # Use original line (not stripped) to preserve indentation
                m109_match = re.match(r'^(\s*)M109\s+S(\d+)', line)
                if m109_match:
                    original_temp = int(m109_match.group(2))
                    # Only apply offset to actual print temperatures (>= 180°C)
                    # Skip low temps like M109 S25 (bed wait) or M109 S140 (idle)
                    if original_temp >= 180:
                        reduced_temp = max(original_temp - offset, 150)  # Min 150°C for safety
                        indent = m109_match.group(1)
                        
                        # Add comment explaining the preheat offset
                        result.append(f'{indent};[PREHEAT-OFFSET] Original: M109 S{original_temp}, Offset: -{offset}°C')
                        result.append(f'{indent}M109 S{reduced_temp}\t;preheat offset -{offset}°C (prevent oozing)')
                        modified_first_heat = True
                        continue
            
            result.append(line)
        
        if modified_first_heat:
            self.logger.info(f"Applied preheat offset: reduced initial nozzle temp by {offset}°C")
        else:
            self.logger.warning("Could not find M109 command (>=180°C) to apply preheat offset")
        
        return '\n'.join(result)
    
    def _add_pre_extrude(self, gcode: str, extrude_length: float) -> str:
        """
        Add pre-extrude command before printing starts.
        Based on FactorianDesigns optimization:
        - Extrude a small amount to fill nozzle after long moves/calibration
        - Helps ensure consistent first layer adhesion
        
        This command is inserted just before the first actual print feature
        (Outer wall, Inner wall, Solid infill, etc.)
        
        Supports multiple G-code formats:
        - Bambu Studio: ; FEATURE: Outer wall, etc.
        - OrcaSlicer/PrusaSlicer: ;TYPE:External perimeter
        
        Args:
            gcode: G-code content
            extrude_length: Amount to extrude in mm (e.g., 2.2)
        """
        lines = gcode.split('\n')
        result = []
        added_pre_extrude = False
        
        # Actual print feature markers (not startup/custom features)
        actual_print_features = [
            '; FEATURE: Outer wall',
            '; FEATURE: Inner wall', 
            '; FEATURE: Solid infill',
            '; FEATURE: Sparse infill',
            '; FEATURE: Top surface',
            '; FEATURE: Bottom surface',
            '; FEATURE: Bridge',
            '; FEATURE: Overhang wall',
            ';TYPE:External perimeter',  # PrusaSlicer/OrcaSlicer
            ';TYPE:Perimeter',
            ';TYPE:Solid infill',
        ]
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Look for first actual print feature
            if not added_pre_extrude:
                for feature in actual_print_features:
                    if feature in stripped:
                        # Insert pre-extrude command before this feature line
                        # NOTE: Must use G1 (not G0) for extrusion - G0 is rapid move only!
                        pre_extrude_code = f""";===== PRE-EXTRUDE (FactorianDesigns optimization) =====
G92 E0\t\t;zero extruder
G1 E{extrude_length} F800\t;pre-extrude to fill nozzle
G92 E0\t\t;zero extruder again
;===== END PRE-EXTRUDE ====="""
                        result.append(pre_extrude_code)
                        added_pre_extrude = True
                        self.logger.info(f"Added pre-extrude E{extrude_length} before '{feature}' at line {i}")
                        break
            
            result.append(line)
        
        if not added_pre_extrude:
            self.logger.warning("Could not find suitable position for pre-extrude command")
        
        return '\n'.join(result)
    
    def _skip_ams_load_sequence(self, gcode: str) -> str:
        """
        Skip AMS load sequence when filament is already loaded in extruder.
        
        This is useful when:
        - User has manually loaded filament
        - Previous print used same filament and it's still loaded
        - Using external spool that's already threaded through
        
        This will:
        1. Comment out the prepare material section
        2. Comment out M620/M621 AMS commands
        3. Keep temperature commands active
        """
        lines = gcode.split('\n')
        result = []
        in_prepare_section = False
        skip_section = False
        
        for line in lines:
            stripped = line.strip()
            
            # Check for prepare material section start
            if ';===== prepare print temperature and material' in line and 'end' not in line.lower():
                in_prepare_section = True
                skip_section = True
                result.append(';[SKIP-AMS] ' + line + ' ; Skipped - filament already loaded')
                continue
            
            # Check for prepare material section end
            if ';===== prepare print temperature and material end' in line:
                in_prepare_section = False
                skip_section = False
                result.append(';[SKIP-AMS] ' + line)
                continue
            
            # Inside prepare section - comment out most commands since filament already loaded
            if in_prepare_section and skip_section:
                # Keep ONLY essential temperature commands for final print temp
                # Skip high temp commands (250°C flush temp, etc.)
                temp_match = re.match(r'^\s*M10[49]\s+S(\d+)', stripped)
                if temp_match:
                    temp_value = int(temp_match.group(1))
                    # Keep lower temps (under 240), skip flush temps (250+)
                    if temp_value < 240:
                        result.append(line)  # Keep reasonable temp commands
                    else:
                        result.append(';[SKIP-AMS] ' + line + ' ; Skip flush temp')
                    continue
                
                # Keep bed temperature commands
                if re.match(r'^\s*M1[49]0\s+S\d+', stripped):
                    result.append(line)
                    continue
                
                # Comment out AMS-related commands
                if any(re.match(pattern, stripped) for pattern in self.AMS_COMMANDS):
                    result.append(';[SKIP-AMS] ' + line)
                    continue
                    
                # Comment out T commands (tool change)
                if re.match(r'^\s*T\d+', stripped):
                    result.append(';[SKIP-AMS] ' + line)
                    continue
                    
                # Comment out M620 M (enable remap)
                if stripped.startswith('M620 M'):
                    result.append(';[SKIP-AMS] ' + line)
                    continue
                
                # Comment out extrusion commands in prepare section (purge/flush)
                if re.match(r'^\s*G1\s+E\d+', stripped):
                    result.append(';[SKIP-AMS] ' + line + ' ; Skip purge extrusion')
                    continue
                
                # Keep other commands (movement, fan, etc.)
                result.append(line)
                continue
            
            # Outside prepare section - check for stray AMS commands
            # Only comment out in start gcode area (before actual printing)
            if any(re.match(pattern, stripped) for pattern in self.AMS_COMMANDS):
                # Check if we're still in start gcode (before layer 0)
                if ';LAYER_CHANGE' not in ''.join(result[-100:]) if len(result) > 100 else True:
                    result.append(';[SKIP-AMS] ' + line)
                    continue
            
            result.append(line)
        
        return '\n'.join(result)
    
    def process_3mf_gcode(
        self,
        file_path: Path,
        print_settings: PrintSettings,
        filament_settings: FilamentSettings,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Process G-code from a 3MF file
        
        Args:
            file_path: Path to 3MF file
            print_settings: Per-job print settings
            filament_settings: Filament settings from inventory
            output_path: Optional output path (default: same name with _processed suffix)
            
        Returns:
            Path to processed file
        """
        import zipfile
        import tempfile
        import shutil
        
        if output_path is None:
            output_path = file_path.parent / f"{file_path.stem}_processed{file_path.suffix}"
        
        # Copy original file
        shutil.copy(file_path, output_path)
        
        # Open and modify G-code inside 3MF
        with zipfile.ZipFile(output_path, 'a') as zf:
            # Find G-code files in the archive
            gcode_files = [f for f in zf.namelist() if f.endswith('.gcode')]
            
            for gcode_file in gcode_files:
                # Read original G-code
                with zf.open(gcode_file) as f:
                    original_gcode = f.read().decode('utf-8')
                
                # Process G-code
                processed_gcode = self.process_gcode(
                    original_gcode,
                    print_settings,
                    filament_settings
                )
                
                # Write back (need to recreate archive for this)
                # For now, we'll create a separate processed file
                self.logger.info(f"Processed G-code file: {gcode_file}")
        
        return output_path


# Singleton instance
gcode_preprocessor = GCodePreprocessor()


def get_gcode_preprocessor() -> GCodePreprocessor:
    """Get the G-code preprocessor instance"""
    return gcode_preprocessor
