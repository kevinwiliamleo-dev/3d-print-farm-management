"""
G-code Templates for Bambu Lab A1

This module provides template-based start and end gcode generation.
Instead of trying to parse and modify existing gcode, we:
1. Extract ONLY the print layers from the original file
2. Generate our own optimized start gcode
3. Generate safe end gcode with all necessary shutdown commands

This approach is more reliable and gives us full control over the startup sequence.
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class PrinterConfig:
    """Printer-specific configuration"""
    printer_model: str = "A1"
    bed_size_x: float = 256.0
    bed_size_y: float = 256.0
    max_z: float = 256.0
    has_ams: bool = True


@dataclass
class TemplateSettings:
    """Settings for gcode template generation"""
    # Temperatures (from file metadata or filament profile)
    nozzle_temp: int = 220
    bed_temp: int = 65
    nozzle_temp_initial: int = 220
    
    # AMS settings
    use_ams: bool = True
    ams_slot: int = 0
    filament_already_loaded: bool = False
    current_tray: int = 255  # 255 = none, from printer MQTT status
    
    # Flush settings for filament change
    flush_temp: int = 240
    flush_speed: int = 299
    
    # Quick Start optimization
    preheat_offset: int = 20  # °C below target to start movement
    pre_extrude: bool = True
    pre_extrude_length: float = 2.2
    
    # Optional features
    home_before_print: bool = True
    auto_eject: bool = False
    cooldown_temp: int = 32
    
    # Filament info
    filament_type: str = "PLA"
    max_volumetric_speed: float = 12.0

    # Whether metadata from the source G-code header may override provided settings
    # Set to False when temps/type already come from a filament profile
    prefer_file_metadata: bool = True
    
    # Controllable template settings (maps to setting_key in database)
    start_machine: bool = True        # setting_key: start_machine
    heat_bed_hotend: bool = True      # setting_key: heat_bed_hotend
    # Start sequence controls
    startup_sound: bool = True      # setting_key: startup_sound
    vibration_test: bool = False    # setting_key: vibration_test
    clean_nozzle: bool = True       # setting_key: clean_nozzle
    wipe_nozzle: bool = True        # setting_key: wipe_nozzle
    flow_calibration: bool = False  # setting_key: flow_calibration
    auto_bed_leveling: bool = True  # setting_key: auto_bed_leveling
    nozzle_load_line: bool = False  # setting_key: nozzle_load_line - DEFAULT OFF to avoid purge line at front of bed
    timelapse: bool = False         # setting_key: timelapse
    
    # Additional controllable templates (Quick Print may disable these)
    cog_noise_reduction: bool = True     # setting_key: cog_noise_reduction
    brush_material_wipe: bool = True     # setting_key: brush_material_wipe
    final_wipe_nozzle: bool = True       # setting_key: final_wipe_nozzle
    avoid_end_stop: bool = True          # setting_key: avoid_end_stop
    reset_machine_status: bool = True    # setting_key: reset_machine_status
    home_after_wipe: bool = True         # setting_key: home_after_wipe
    prepare_print: bool = False          # setting_key: prepare_print - DEFAULT OFF to avoid moving to front of bed
    extrude_calibration_test: bool = True # setting_key: extrude_calibration_test
    turn_off_light: bool = True          # setting_key: turn_off_light
    final_start: bool = True             # setting_key: final_start
    
    # End sequence controls
    end_sound: bool = True          # setting_key: end_sound


def load_custom_templates_from_json():
    """Load custom templates from JSON file (DEPRECATED - use database instead)"""
    import json
    from pathlib import Path
    
    templates_file = Path("data/gcode_templates.json")
    if templates_file.exists():
        try:
            with open(templates_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load custom templates from JSON: {e}")
    return None


def load_custom_templates(printer_model: str = None):
    """Load custom templates from database"""
    try:
        from sqlalchemy import text
        from ..database.db import SessionLocal
        
        db = SessionLocal()
        try:
            # Get templates (NULL printer_model = default, or specific printer)
            if printer_model:
                query = text("""
                    SELECT * FROM gcode_templates 
                    WHERE printer_model IS NULL OR printer_model = :model
                    ORDER BY category, "order"
                """)
                result = db.execute(query, {"model": printer_model})
            else:
                query = text("""
                    SELECT * FROM gcode_templates 
                    WHERE printer_model IS NULL
                    ORDER BY category, "order"
                """)
                result = db.execute(query)
            
            templates = {}
            for row in result:
                templates[row.template_key] = {
                    "template_key": row.template_key,
                    "template_id": row.template_id,
                    "name": row.name,
                    "description": row.description,
                    "category": row.category,
                    "order": row.order,
                    "enabled": bool(row.enabled),
                    "controllable": bool(row.controllable),
                    "setting_key": row.setting_key,
                    "gcode": row.gcode,
                    "printer_model": row.printer_model,
                }
            
            if templates:
                logging.info(f"Loaded {len(templates)} templates from database")
                return templates
            
        finally:
            db.close()
            
    except Exception as e:
        logging.warning(f"Failed to load templates from database: {e}")
    
    # Fallback to JSON if database fails
    logging.warning("Falling back to JSON templates")
    return load_custom_templates_from_json()


class GCodeTemplates:
    """Generate start and end gcode templates for Bambu Lab A1"""
    
    def __init__(self, printer_config: Optional[PrinterConfig] = None):
        self.config = printer_config or PrinterConfig()
        self.logger = logging.getLogger(__name__)
        self.custom_templates = load_custom_templates()
    
    def _apply_variables(self, gcode: str, settings: TemplateSettings) -> str:
        """Replace template variables with actual values"""
        preheat_temp = settings.nozzle_temp - settings.preheat_offset if settings.preheat_offset > 0 else settings.nozzle_temp
        nozzle_temp_minus_50 = max(settings.nozzle_temp - 50, 140)  # For clean nozzle section
        
        replacements = {
            "{nozzle_temp}": str(settings.nozzle_temp),
            "{nozzle_temp_minus_50}": str(nozzle_temp_minus_50),
            "{bed_temp}": str(settings.bed_temp),
            "{filament_type}": settings.filament_type,
            "{ams_slot}": str(settings.ams_slot),
            "{current_tray}": str(settings.current_tray),
            "{flush_temp}": str(settings.flush_temp),
            "{flush_speed}": str(settings.flush_speed),
            "{preheat_temp}": str(preheat_temp),
            "{preheat_offset}": str(settings.preheat_offset),
            "{pre_extrude_length}": str(settings.pre_extrude_length),
            "{cooldown_temp}": str(settings.cooldown_temp),
            "{max_volumetric_speed}": str(settings.max_volumetric_speed),
        }
        
        for var, val in replacements.items():
            gcode = gcode.replace(var, val)
        
        return gcode
    
    def _should_skip_ams(self, settings: TemplateSettings) -> tuple[bool, str]:
        """
        Determine if AMS loading should be skipped.
        Returns (should_skip, reason)
        """
        # 1. User explicitly set "filament already loaded"
        if settings.filament_already_loaded:
            return True, "User set 'Filament Already Loaded'"
        
        # 2. Smart skip: current tray already matches selected slot
        if settings.current_tray == settings.ams_slot:
            return True, f"Current tray ({settings.current_tray}) matches selected slot ({settings.ams_slot})"
        
        return False, ""
    
    def _is_template_enabled(self, template: dict, settings: TemplateSettings) -> tuple[bool, str]:
        """
        Check if a template should be enabled based on settings.
        Returns (is_enabled, reason)
        
        Logic:
        1. If template is not controllable, always use template.enabled
        2. If template is controllable, check setting_key against TemplateSettings
        """
        # If not controllable, use the template's enabled flag
        if not template.get("controllable", False):
            template_key = template.get("template_key")
            fallback_map = {
                "start_machine": settings.start_machine,
                "heat_bed_hotend": settings.heat_bed_hotend,
            }
            if template_key in fallback_map:
                if not fallback_map[template_key]:
                    return False, f"Disabled by user setting (fallback): {template_key}=False"
                return True, ""
            if not template.get("enabled", True):
                return False, "Template disabled in database"
            return True, ""
        
        # Controllable template - check setting_key
        setting_key = template.get("setting_key")
        if not setting_key:
            # No setting_key defined, use enabled flag
            if not template.get("enabled", True):
                return False, "Template disabled (no setting_key)"
            return True, ""
        
        # Map setting_key to TemplateSettings attribute
        setting_map = {
            "start_machine": settings.start_machine,
            "heat_bed_hotend": settings.heat_bed_hotend,
            # Original controllable settings
            "startup_sound": settings.startup_sound,
            "vibration_test": settings.vibration_test,
            "clean_nozzle": settings.clean_nozzle,
            "wipe_nozzle": settings.wipe_nozzle,
            "flow_calibration": settings.flow_calibration,
            "auto_bed_leveling": settings.auto_bed_leveling,
            "nozzle_load_line": settings.nozzle_load_line,
            "timelapse": settings.timelapse,
            "auto_eject": settings.auto_eject,
            "end_sound": settings.end_sound,
            "pre_extrude": settings.pre_extrude,
            "preheat_offset": settings.preheat_offset > 0,
            "ams_slot": settings.use_ams,
            # Additional controllable settings (Quick Print control)
            "cog_noise_reduction": settings.cog_noise_reduction,
            "brush_material_wipe": settings.brush_material_wipe,
            "final_wipe_nozzle": settings.final_wipe_nozzle,
            "avoid_end_stop": settings.avoid_end_stop,
            "reset_machine_status": settings.reset_machine_status,
            "home_after_wipe": settings.home_after_wipe,
            "prepare_print": settings.prepare_print,
            "extrude_calibration_test": settings.extrude_calibration_test,
            "turn_off_light": settings.turn_off_light,
            "final_start": settings.final_start,
        }
        
        if setting_key in setting_map:
            enabled = setting_map[setting_key]
            if not enabled:
                return False, f"Disabled by user setting: {setting_key}=False"
            return True, ""
        
        # Unknown setting_key, default to enabled flag
        self.logger.warning(f"Unknown setting_key: {setting_key}, using template enabled flag")
        return template.get("enabled", True), ""
    
    def generate_start_gcode_from_templates(self, settings: TemplateSettings) -> str:
        """Generate start gcode from database templates"""
        if not self.custom_templates:
            return self.generate_start_gcode(settings)
        
        # Check if we should skip AMS loading
        skip_ams, skip_reason = self._should_skip_ams(settings)
        
        lines = [";===== GENERATED START GCODE ====="]
        lines.append(f"; Based on database templates")
        lines.append(f"; Printer: {self.config.printer_model}")
        lines.append(f"; Nozzle Temp: {settings.nozzle_temp}°C")
        lines.append(f"; Bed Temp: {settings.bed_temp}°C")
        lines.append(f"; Filament: {settings.filament_type}")
        lines.append(f"; AMS Slot: {settings.ams_slot if settings.use_ams else 'External'}")
        lines.append(f"; Current Tray: {settings.current_tray} (255=none)")
        if skip_ams:
            lines.append(f"; AMS Loading: SKIP - {skip_reason}")
        else:
            lines.append(f"; AMS Loading: Will load from slot {settings.ams_slot}")
        lines.append(f";")
        lines.append(f"; Controllable Settings:")
        lines.append(f";   start_machine={settings.start_machine}")
        lines.append(f";   heat_bed_hotend={settings.heat_bed_hotend}")
        lines.append(f";   startup_sound={settings.startup_sound}")
        lines.append(f";   vibration_test={settings.vibration_test}")
        lines.append(f";   clean_nozzle={settings.clean_nozzle}")
        lines.append(f";   wipe_nozzle={settings.wipe_nozzle}")
        lines.append(f";   flow_calibration={settings.flow_calibration}")
        lines.append(f";   auto_bed_leveling={settings.auto_bed_leveling}")
        lines.append(f";   nozzle_load_line={settings.nozzle_load_line}")
        lines.append(f";   timelapse={settings.timelapse}")
        lines.append(f";   preheat_offset={settings.preheat_offset}")
        lines.append(f";   pre_extrude={settings.pre_extrude}")
        lines.append("")
        
        # Get start templates and sort by order
        start_templates = [(tid, t) for tid, t in self.custom_templates.items() if t.get("category") != "end"]
        start_templates.sort(key=lambda x: x[1].get("order", 99))
        
        for tid, template in start_templates:
            # Check if template is enabled based on settings
            is_enabled, reason = self._is_template_enabled(template, settings)
            
            if not is_enabled:
                lines.append("")
                lines.append(f";===== SKIP: {template.get('name', tid)} =====")
                lines.append(f"; {reason}")
                continue
            
            # Smart AMS skip
            if tid == "ams_loading" and skip_ams:
                lines.append("")
                lines.append(";===== SMART AMS SKIP =====")
                lines.append(f"; {skip_reason}")
                lines.append("; Skipping AMS load sequence - filament already in extruder")
                continue
            
            gcode = template.get("gcode", "")
            gcode = self._apply_variables(gcode, settings)
            lines.append("")
            lines.append(f";===== {template.get('name', tid)} =====")
            lines.append(gcode)
        
        lines.append("")
        lines.append(";===== END GENERATED START GCODE =====")
        lines.append("")
        
        return '\n'.join(lines)
    
    def generate_end_gcode_from_templates(self, settings: TemplateSettings) -> str:
        """Generate end gcode from database templates"""
        if not self.custom_templates:
            return self.generate_end_gcode(settings)
        
        lines = [""]
        lines.append(";===== GENERATED END GCODE =====")
        lines.append(f"; Controllable Settings:")
        lines.append(f";   auto_eject={settings.auto_eject}")
        lines.append(f";   cooldown_temp={settings.cooldown_temp}")
        lines.append(f";   timelapse={settings.timelapse}")
        lines.append(f";   end_sound={settings.end_sound}")
        
        # Get end templates and sort by order
        end_templates = [(tid, t) for tid, t in self.custom_templates.items() if t.get("category") == "end"]
        end_templates.sort(key=lambda x: x[1].get("order", 99))
        
        for tid, template in end_templates:
            # Check if template is enabled based on settings
            is_enabled, reason = self._is_template_enabled(template, settings)
            
            if not is_enabled:
                lines.append("")
                lines.append(f";===== SKIP: {template.get('name', tid)} =====")
                lines.append(f"; {reason}")
                continue
            
            gcode = template.get("gcode", "")
            gcode = self._apply_variables(gcode, settings)
            lines.append("")
            lines.append(f";===== {template.get('name', tid)} =====")
            lines.append(gcode)
        
        lines.append("")
        lines.append(";===== END GENERATED END GCODE =====")
        
        return '\n'.join(lines)
    
    def generate_start_gcode(self, settings: TemplateSettings) -> str:
        """
        Generate optimized start gcode for Bambu Lab A1
        Based on FactorianDesigns A1 automation gcode.
        
        This replaces ALL original start gcode with a clean, minimal sequence.
        Key optimizations:
        - Skip AMS loading if filament already loaded
        - Preheat offset to prevent oozing
        - Pre-extrude to fill nozzle before first layer
        """
        
        # Use custom templates if available
        if self.custom_templates:
            return self.generate_start_gcode_from_templates(settings)
        
        lines = []
        
        # === HEADER ===
        lines.append(";===== GENERATED START GCODE =====")
        lines.append(f"; Based on FactorianDesigns A1 automation")
        lines.append(f"; Printer: {self.config.printer_model}")
        lines.append(f"; Nozzle Temp: {settings.nozzle_temp}°C")
        lines.append(f"; Bed Temp: {settings.bed_temp}°C")
        lines.append(f"; Filament: {settings.filament_type}")
        lines.append(f"; AMS Slot: {settings.ams_slot if settings.use_ams else 'External'}")
        lines.append(f"; Filament Already Loaded: {settings.filament_already_loaded}")
        lines.append("")
        
        # === MACHINE INIT ===
        lines.append(";===== MACHINE INIT =====")
        lines.append("G392 S0 ; turn off clog detect during startup")
        lines.append("M9833.2")
        lines.append("")
        
        # === START HEATING ===
        lines.append(";===== START HEATING =====")
        lines.append("M1002 gcode_claim_action : 2")
        lines.append(f"M1002 set_filament_type:{settings.filament_type}")
        lines.append("M104 S140 ; preheat nozzle to 140")
        lines.append(f"M140 S{settings.bed_temp} ; start bed heating")
        lines.append("")
        
        # === AVOID END STOP ===
        lines.append(";===== AVOID END STOP =====")
        lines.append("G91")
        lines.append("G380 S2 Z40 F1200")
        lines.append("G380 S3 Z-15 F1200")
        lines.append("G90")
        lines.append("")
        
        # === RESET MACHINE STATUS ===
        lines.append(";===== RESET MACHINE STATUS =====")
        lines.append("M204 S6000")
        lines.append("M630 S0 P0")
        lines.append("G91")
        lines.append("M17 Z0.3 ; lower z-motor current")
        lines.append("G90")
        lines.append("M17 X0.65 Y1.2 Z0.6 ; reset motor current")
        lines.append("M960 S5 P1 ; turn on logo lamp")
        lines.append("G90")
        lines.append("M220 S100 ; reset feedrate")
        lines.append("M221 S100 ; reset flowrate")
        lines.append("M73.2 R1.0 ; reset left time magnitude")
        lines.append("")
        
        # === COG NOISE REDUCTION ===
        lines.append(";===== COG NOISE REDUCTION =====")
        lines.append("M982.2 S1 ; turn on cog noise reduction")
        lines.append("")
        
        # === HOMING ===
        lines.append(";===== HOMING =====")
        lines.append("M1002 gcode_claim_action : 13")
        lines.append("G28 X")
        lines.append("G91")
        lines.append("G1 Z5 F1200")
        lines.append("G90")
        lines.append("G0 X128 F30000")
        lines.append("G0 Y254 F3000")
        lines.append("G91")
        lines.append("G1 Z-5 F1200")
        lines.append("G90")
        lines.append("")
        
        # === SMART TEMP WAIT ===
        lines.append(";===== SMART TEMP WAIT =====")
        lines.append("M109 S25 H140 ; wait until cooled to 25 OR heated to 140")
        lines.append("")
        
        # === INITIAL EXTRUSION ===
        lines.append(";===== INITIAL EXTRUSION =====")
        lines.append("M17 E0.3")
        lines.append("M83")
        lines.append("G1 E10 F1200")
        lines.append("G1 E-0.5 F30")
        lines.append("M17 D")
        lines.append("")
        
        # === HOME Z ===
        lines.append(";===== HOME Z =====")
        lines.append("G28 Z P0 T140 ; home z with low precision, permit 300deg temperature")
        lines.append(f"M104 S{settings.nozzle_temp} ; set target nozzle temp")
        lines.append("")
        
        # === BUILD PLATE DETECTION ===
        lines.append(";===== BUILD PLATE DETECTION =====")
        lines.append("M1002 judge_flag build_plate_detect_flag")
        lines.append("M622 S1")
        lines.append("  G39.4")
        lines.append("  G90")
        lines.append("  G1 Z5 F1200")
        lines.append("M623")
        lines.append("")
        
        # === AMS LOADING (if needed) ===
        if settings.use_ams and not settings.filament_already_loaded:
            lines.append(";===== AMS FILAMENT LOADING =====")
            lines.append("M1002 gcode_claim_action : 24")
            lines.append("M400")
            lines.append("M211 X0 Y0 Z0 ; turn off soft endstop")
            lines.append("M975 S1")
            lines.append("")
            lines.append("G90")
            lines.append("G1 X-28.5 F30000")
            lines.append("G1 X-48.2 F3000")
            lines.append("")
            lines.append("M620 M ; enable AMS remap")
            lines.append(f"M620 S{settings.ams_slot}A ; switch to AMS slot {settings.ams_slot}")
            lines.append("    M1002 gcode_claim_action : 4")
            lines.append("    M400")
            lines.append("    M1002 set_filament_type:UNKNOWN")
            lines.append(f"    M109 S{settings.nozzle_temp}")
            lines.append("    M104 S250")
            lines.append("    M400")
            lines.append(f"    T{settings.ams_slot}")
            lines.append("    G1 X-48.2 F3000")
            lines.append("    M400")
            lines.append("")
            lines.append(f"    M620.1 E F{settings.max_volumetric_speed/2.4053*60:.0f} T{min(settings.nozzle_temp + 20, 300)}")
            lines.append("    M109 S250 ; set nozzle to common flush temp")
            lines.append("    M106 P1 S0")
            lines.append("    G92 E0")
            lines.append("    G1 E50 F200")
            lines.append("    M400")
            lines.append(f"    M1002 set_filament_type:{settings.filament_type}")
            lines.append(f"M621 S{settings.ams_slot}A ; finish AMS load")
            lines.append("")
            lines.append(f"M109 S{min(settings.nozzle_temp + 20, 300)} H300")
            lines.append("G92 E0")
            lines.append("G1 E50 F200 ; lower extrusion speed to avoid clog")
            lines.append("M400")
            lines.append("M106 P1 S178")
            lines.append("G92 E0")
            lines.append("G1 E5 F200")
            lines.append(f"M104 S{settings.nozzle_temp}")
            lines.append("G92 E0")
            lines.append("G1 E-0.5 F300")
            lines.append("")
            lines.append("G1 X-28.5 F30000")
            lines.append("G1 X-48.2 F3000")
            lines.append("G1 X-28.5 F30000 ; wipe and shake")
            lines.append("G1 X-48.2 F3000")
            lines.append("G1 X-28.5 F30000 ; wipe and shake")
            lines.append("G1 X-48.2 F3000")
            lines.append("")
            lines.append("M400")
            lines.append("M106 P1 S0")
            lines.append(";===== AMS LOADING END =====")
            lines.append("")
        elif settings.filament_already_loaded:
            lines.append(";===== FILAMENT ALREADY LOADED - SKIP AMS =====")
            lines.append("; Skipping AMS load sequence - filament already in nozzle")
            lines.append("M211 X0 Y0 Z0 ; turn off soft endstop")
            lines.append("M975 S1")
            lines.append("")
        else:
            # External spool
            lines.append(";===== EXTERNAL SPOOL MODE =====")
            lines.append("T255 ; select external spool")
            lines.append("M211 X0 Y0 Z0 ; turn off soft endstop")
            lines.append("M975 S1")
            lines.append("")
        
        # === FILAMENT DETECTION ===
        lines.append(";===== FILAMENT DETECTION =====")
        lines.append("M412 S1 ; turn on filament runout detection")
        lines.append("M400 P10")
        lines.append("M620.3 W1 ; turn on filament tangle detection")
        lines.append("M400 S2")
        lines.append(f"M1002 set_filament_type:{settings.filament_type}")
        lines.append("")
        
        # === PREPARE NOZZLE TEMP ===
        lines.append(";===== PREPARE NOZZLE TEMP =====")
        lines.append("M104 S170 ; prepare to wipe nozzle")
        lines.append("M106 S255 ; turn on fan")
        lines.append("")
        
        # === BED LEVELING ===
        lines.append(";===== BED LEVELING =====")
        lines.append("M1002 judge_flag g29_before_print_flag")
        lines.append("G90")
        lines.append("G1 Z5 F1200")
        lines.append("G1 X0 Y0 F30000")
        lines.append("G29.2 S1 ; turn on ABL")
        lines.append(f"M190 S{settings.bed_temp} ; ensure bed temp")
        lines.append("M109 S140")
        lines.append("M106 S0 ; turn off fan, too noisy")
        lines.append("")
        lines.append("M622 J1")
        lines.append("    M1002 gcode_claim_action : 1")
        lines.append("    G29 A1 X0 Y0 I256 J256")
        lines.append("    M400")
        lines.append("    M500 ; save cali data")
        lines.append("M623")
        lines.append("")
        
        # === HOME AFTER WIPE ===
        lines.append(";===== HOME AFTER WIPE =====")
        lines.append("M1002 judge_flag g29_before_print_flag")
        lines.append("M622 J0")
        lines.append("    M1002 gcode_claim_action : 13")
        lines.append("    G28")
        lines.append("M623")
        lines.append("")
        
        # === FINAL POSITIONING ===
        lines.append(";===== FINAL POSITIONING =====")
        lines.append("G1 X108.000 Y-0.500 F30000")
        lines.append("G1 Z0.300 F1200")
        lines.append("M400")
        lines.append("G2814 Z0.32")
        lines.append(f"M104 S{settings.nozzle_temp} ; prepare to print")
        lines.append("")
        
        # === FINAL TEMP WAIT AND PRE-EXTRUDE ===
        lines.append(";===== FINAL TEMP WAIT =====")
        lines.append("M1002 gcode_claim_action : 0")
        lines.append("M400")
        lines.append("G1 Z3 F800 ; move nozzle up a little")
        lines.append("M106 P1 S255 ; turn on fan to cool tip, prevents oozing")
        # Calculate preheat temp
        preheat_temp = settings.nozzle_temp - settings.preheat_offset if settings.preheat_offset > 0 else settings.nozzle_temp
        lines.append(f"M109 S{preheat_temp} ; wait for temp (offset -{settings.preheat_offset}°C)")
        lines.append("")
        
        # === READY TO PRINT ===
        lines.append(";===== READY TO PRINT =====")
        lines.append("M960 S1 P0 ; turn off laser")
        lines.append("M960 S2 P0 ; turn off laser")
        lines.append("M106 S0 ; turn off fan")
        lines.append("M106 P2 S0 ; turn off big fan")
        lines.append("M106 P3 S0 ; turn off chamber fan")
        lines.append("")
        lines.append("M975 S1 ; turn on mech mode suppression")
        lines.append("G90")
        lines.append("M83")
        lines.append("T1000")
        lines.append("")
        lines.append("M211 X0 Y0 Z0 ; turn off soft endstop")
        lines.append("M1007 S1 ; turn on mass estimation")
        lines.append("G29.4")
        lines.append("")
        
        # === PRE-EXTRUDE ===
        if settings.pre_extrude:
            lines.append(";===== PRE-EXTRUDE =====")
            lines.append(f"G1 E{settings.pre_extrude_length} F800 ; extrude to fill nozzle")
            lines.append(f"M104 S{settings.nozzle_temp} ; heat up to full temp in first few moves")
            lines.append("")
        
        lines.append(";===== END GENERATED START GCODE =====")
        lines.append("")
        
        return '\n'.join(lines)
    
    def generate_end_gcode(self, settings: TemplateSettings) -> str:
        """
        Generate safe end gcode for Bambu Lab A1
        
        CRITICAL: This must include all safety commands to:
        - Turn off heaters
        - Turn off fans
        - Disable motors
        - Optionally auto-eject
        """
        
        # Use custom templates if available
        if self.custom_templates:
            return self.generate_end_gcode_from_templates(settings)
        
        lines = []
        
        lines.append("")
        lines.append(";===== GENERATED END GCODE =====")
        lines.append("")
        
        # === FINISH CURRENT MOVE ===
        lines.append(";===== FINISH MOVES =====")
        lines.append("M400 ; Wait for all moves to complete")
        lines.append("G392 S0 ; Disable clog detection")
        lines.append("")
        
        # === RETRACT AND RAISE ===
        lines.append(";===== RETRACT AND RAISE =====")
        lines.append("G92 E0")
        lines.append("G1 E-2 F2400 ; Retract")
        lines.append("G91 ; Relative positioning")
        lines.append("G1 Z10 F3000 ; Raise Z by 10mm")
        lines.append("G90 ; Absolute positioning")
        lines.append("")
        
        # === MOVE TO BACK ===
        lines.append(";===== MOVE TO SAFE POSITION =====")
        lines.append(f"G1 X0 Y{self.config.bed_size_y} F9000 ; Move to back")
        lines.append("")
        
        # === AUTO EJECT (if enabled) ===
        if settings.auto_eject:
            lines.append(";===== AUTO EJECT =====")
            lines.append(f"; Waiting for bed to cool to {settings.cooldown_temp}°C")
            lines.append(f"M140 S{settings.cooldown_temp} ; Set bed target")
            lines.append(f"M190 R{settings.cooldown_temp} ; Wait for cooldown (R = wait for temp or below)")
            lines.append("")
            lines.append("; Push off print")
            lines.append("G28 X ; Home X to push print off")
            lines.append("G1 X128 F12000 ; Return to center")
            lines.append("")
        
        # === TURN OFF HEATERS (CRITICAL SAFETY) ===
        lines.append(";===== SAFETY: TURN OFF HEATERS =====")
        lines.append("M104 S0 ; *** TURN OFF HOTEND ***")
        lines.append("M140 S0 ; *** TURN OFF BED ***")
        lines.append("")
        
        # === TURN OFF FANS ===
        lines.append(";===== TURN OFF FANS =====")
        lines.append("M106 S0 ; Part cooling fan OFF")
        lines.append("M106 P1 S0 ; Aux fan OFF")
        lines.append("M106 P2 S0 ; Chamber fan OFF")
        lines.append("")
        
        # === DISABLE MOTORS ===
        lines.append(";===== DISABLE MOTORS =====")
        lines.append("M400 ; Wait for completion")
        lines.append("M18 X Y Z ; Disable motors")
        lines.append("")
        
        # === PROGRESS COMPLETE ===
        lines.append(";===== PRINT COMPLETE =====")
        lines.append("M73 P100 R0 ; Progress 100%")
        lines.append("; EXECUTABLE_BLOCK_END")
        lines.append("")
        lines.append(";===== END GENERATED END GCODE =====")
        
        return '\n'.join(lines)


class GCodeLayerExtractor:
    """
    Extract and preserve gcode structure for Bambu Lab printers.
    
    Bambu/OrcaSlicer gcode structure:
    1. HEADER_BLOCK (lines 1-10): Contains print time, layer count, filament info
    2. CONFIG_BLOCK (lines 12-541): Contains all slicer settings (~530 lines)
    3. EXECUTABLE_BLOCK: Contains start gcode, print layers, end gcode
    4. Filament footer: Usage summary at end of file
    
    This extractor PRESERVES HEADER_BLOCK, CONFIG_BLOCK and footer,
    only replacing the START GCODE portion within EXECUTABLE_BLOCK.
    """
    
    # Block markers for Bambu/OrcaSlicer gcode
    HEADER_BLOCK_START = '; HEADER_BLOCK_START'
    HEADER_BLOCK_END = '; HEADER_BLOCK_END'
    CONFIG_BLOCK_START = '; CONFIG_BLOCK_START'
    CONFIG_BLOCK_END = '; CONFIG_BLOCK_END'
    EXECUTABLE_BLOCK_START = '; EXECUTABLE_BLOCK_START'
    EXECUTABLE_BLOCK_END = '; EXECUTABLE_BLOCK_END'
    
    # Markers that indicate start of actual printing (after start gcode)
    # These must be exact line matches (stripped) to avoid matching comments in header
    PRINT_START_MARKERS = [
        '; CHANGE_LAYER',           # Bambu/Orca standard layer change
        ';LAYER_CHANGE',            # PrusaSlicer
        ';LAYER:0',                 # Cura style first layer
    ]
    
    # Markers that indicate end of printing (before end gcode)
    PRINT_END_MARKERS = [
        '; EXECUTABLE_BLOCK_END',   # Bambu end marker
        ';===== date:',             # Bambu end section in some files
        '; filament end gcode',     # End gcode marker
    ]
    
    # Commands that should be in start gcode (skip these)
    START_GCODE_PATTERNS = [
        'G28',      # Homing
        'M104',     # Set hotend temp (before print)
        'M109',     # Wait for hotend temp (before print)
        'M140',     # Set bed temp
        'M190',     # Wait for bed temp
        'M620',     # AMS commands
        'M621',     # AMS commands
        'G29',      # Bed leveling
        'M970',     # Vibration test
        'M983',     # Flow calibration
        'M984',     # Flow calibration
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_preserving_blocks(self, gcode: str) -> dict:
        """
        Extract gcode while preserving Bambu block structure.
        
        Returns dict with:
            - header_block: HEADER_BLOCK content (print time, layer count, etc)
            - config_block: CONFIG_BLOCK content (all slicer settings)
            - executable_start_marker: Everything from EXECUTABLE_BLOCK_START to first CHANGE_LAYER
            - print_layers: The actual printing gcode (from first CHANGE_LAYER onwards)
            - executable_end_marker: From last print command to EXECUTABLE_BLOCK_END
            - filament_footer: Filament usage summary after EXECUTABLE_BLOCK_END
            - has_bambu_blocks: True if file has proper Bambu block structure
        """
        lines = gcode.split('\n')
        total_lines = len(lines)
        
        result = {
            'header_block': '',
            'config_block': '',
            'executable_preamble': '',  # M73, M201, M203 etc before start gcode
            'original_start_gcode': '',
            'print_layers': '',
            'original_end_gcode': '',
            'filament_footer': '',
            'has_bambu_blocks': False,
            'metadata': {}
        }
        
        # Find block markers
        header_start = header_end = -1
        config_start = config_end = -1
        exec_start = exec_end = -1
        first_layer = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == self.HEADER_BLOCK_START:
                header_start = i
            elif stripped == self.HEADER_BLOCK_END:
                header_end = i
            elif stripped == self.CONFIG_BLOCK_START:
                config_start = i
            elif stripped == self.CONFIG_BLOCK_END:
                config_end = i
            elif stripped == self.EXECUTABLE_BLOCK_START:
                exec_start = i
            elif stripped == self.EXECUTABLE_BLOCK_END:
                exec_end = i
            elif first_layer == -1:
                for marker in self.PRINT_START_MARKERS:
                    if stripped == marker or stripped.startswith(marker):
                        # Verify actual layer marker
                        has_gcode = any(
                            lines[j].strip().startswith('G1 ') or lines[j].strip().startswith('G0 ')
                            for j in range(i, min(i + 20, total_lines))
                        )
                        if has_gcode:
                            first_layer = i
                            break
        
        # Check if we have proper Bambu block structure
        has_blocks = (header_start >= 0 and header_end > header_start and
                      config_start >= 0 and config_end > config_start and
                      exec_start >= 0)
        
        result['has_bambu_blocks'] = has_blocks
        
        if has_blocks:
            self.logger.info(f"Found Bambu block structure: HEADER({header_start}-{header_end}), "
                           f"CONFIG({config_start}-{config_end}), EXEC_START({exec_start}), "
                           f"EXEC_END({exec_end}), FIRST_LAYER({first_layer})")
            
            # Extract HEADER_BLOCK (includes markers)
            result['header_block'] = '\n'.join(lines[header_start:header_end + 1])
            
            # Extract CONFIG_BLOCK (includes markers)
            config_block_lines = lines[config_start:config_end + 1]
            
            # ✂️ REMOVE machine_start_gcode, machine_end_gcode, and change_filament_gcode lines
            filtered_config_lines = []
            for line in config_block_lines:
                stripped = line.strip()
                # Skip lines containing machine_start_gcode, machine_end_gcode, or change_filament_gcode
                if 'machine_start_gcode' in stripped or 'machine_end_gcode' in stripped or 'change_filament_gcode' in stripped:
                    self.logger.info(f"🗑️ Removing line from CONFIG_BLOCK: {stripped[:80]}...")
                    continue
                filtered_config_lines.append(line)
            
            result['config_block'] = '\n'.join(filtered_config_lines)
            self.logger.info(f"✂️ Removed {len(config_block_lines) - len(filtered_config_lines)} lines from CONFIG_BLOCK")
            
            # Extract extrusion width comments (between CONFIG_BLOCK_END and EXECUTABLE_BLOCK_START)
            if config_end + 1 < exec_start:
                result['executable_preamble'] = '\n'.join(lines[config_end + 1:exec_start])
            
            # Extract executable preamble (M73, M201, etc before start gcode)
            # Find where start gcode actually begins (look for ;===== or ;FEATURE: Custom)
            start_gcode_begin = exec_start + 1
            for i in range(exec_start + 1, min(exec_start + 20, first_layer if first_layer > 0 else total_lines)):
                stripped = lines[i].strip()
                # M73 P0 Rxxx - initial progress, M201/M203/M204/M205 - machine limits
                if stripped.startswith('M73 ') or stripped.startswith('M201 ') or \
                   stripped.startswith('M203 ') or stripped.startswith('M204 ') or stripped.startswith('M205 '):
                    continue
                elif stripped.startswith('; FEATURE:') or stripped.startswith(';====='):
                    start_gcode_begin = i
                    break
                elif stripped and not stripped.startswith(';'):
                    start_gcode_begin = i
                    break
            
            # Extract the preamble (M73, M201, etc)
            exec_preamble_lines = lines[exec_start:start_gcode_begin]
            result['executable_preamble'] += '\n' + '\n'.join(exec_preamble_lines) if result['executable_preamble'] else '\n'.join(exec_preamble_lines)
            
            # Original start gcode (from start_gcode_begin to first_layer)
            if first_layer > start_gcode_begin:
                result['original_start_gcode'] = '\n'.join(lines[start_gcode_begin:first_layer])
            
            # Print layers (from first_layer to exec_end or end of file)
            if first_layer >= 0:
                if exec_end > first_layer:
                    result['print_layers'] = '\n'.join(lines[first_layer:exec_end])
                else:
                    result['print_layers'] = '\n'.join(lines[first_layer:])
            
            # Original end gcode - look for end markers
            # Find where print layers actually end (before end sound, safe position, etc)
            last_print_line = exec_end if exec_end > 0 else total_lines - 1
            for i in range(last_print_line, first_layer, -1):
                stripped = lines[i].strip()
                # End gcode markers
                if any(stripped.startswith(m) for m in [';=====start end', ';===== start end', 
                                                          ';===== safe position', ';=====printer finish']):
                    result['original_end_gcode'] = '\n'.join(lines[i:exec_end + 1] if exec_end > 0 else lines[i:last_print_line])
                    result['print_layers'] = '\n'.join(lines[first_layer:i])
                    break
            
            # Filament footer (after EXECUTABLE_BLOCK_END)
            if exec_end > 0 and exec_end < total_lines - 1:
                result['filament_footer'] = '\n'.join(lines[exec_end + 1:])
                self.logger.info(f"Preserved filament footer: {len(lines) - exec_end - 1} lines")
        
        else:
            self.logger.warning("No Bambu block structure found, using legacy extraction")
            # Fall back to legacy extraction
            print_layers, metadata = self.extract_print_layers(gcode)
            result['print_layers'] = print_layers
            result['metadata'] = metadata
        
        # Extract metadata from header
        result['metadata'] = self._extract_metadata(lines[:first_layer if first_layer > 0 else 100])
        result['metadata']['original_lines'] = total_lines
        result['metadata']['first_layer_line'] = first_layer
        result['metadata']['has_bambu_blocks'] = has_blocks
        
        return result
    
    def extract_print_layers(self, gcode: str) -> tuple[str, dict]:
        """
        Extract only the print layers from gcode
        
        Returns:
            tuple: (print_layers_gcode, metadata_dict)
            
        metadata_dict contains:
            - original_lines: total lines in original
            - extracted_lines: lines in extracted portion
            - first_layer_line: line number where layers start
            - last_layer_line: line number where layers end
            - nozzle_temp: detected nozzle temperature
            - bed_temp: detected bed temperature
            - filament_type: detected filament type
        """
        lines = gcode.split('\n')
        total_lines = len(lines)
        
        # Find start of print layers - use EXACT line match
        first_layer_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Must be exact match on the stripped line (not substring in comment)
            for marker in self.PRINT_START_MARKERS:
                if stripped == marker or stripped.startswith(marker):
                    # Verify this is actual layer marker (not in header comments)
                    # Check if next few lines have actual gcode commands (G0, G1)
                    has_gcode_nearby = False
                    for j in range(i, min(i + 20, total_lines)):
                        next_stripped = lines[j].strip()
                        if next_stripped.startswith('G1 ') or next_stripped.startswith('G0 '):
                            has_gcode_nearby = True
                            break
                    
                    if has_gcode_nearby:
                        first_layer_line = i
                        break
            if first_layer_line is not None:
                break
        
        if first_layer_line is None:
            self.logger.warning("Could not find start of print layers, using line 0")
            first_layer_line = 0
        
        # Find end of print layers
        last_layer_line = total_lines - 1
        for i in range(total_lines - 1, first_layer_line, -1):
            stripped = lines[i].strip()
            for marker in self.PRINT_END_MARKERS:
                if stripped.startswith(marker):
                    last_layer_line = i - 1  # Line before the end marker
                    break
            if last_layer_line != total_lines - 1:
                break
        
        # Also check for last CHANGE_LAYER as a better end point
        for i in range(last_layer_line, first_layer_line, -1):
            stripped = lines[i].strip()
            if stripped == '; CHANGE_LAYER' or stripped == ';LAYER_CHANGE':
                # Find the actual end of this layer's gcode (look for end markers or M400)
                for j in range(i + 1, min(i + 1000, total_lines)):
                    next_stripped = lines[j].strip()
                    if any(lines[j].strip().startswith(marker) for marker in self.PRINT_END_MARKERS):
                        last_layer_line = j - 1
                        break
                    if next_stripped.startswith('M400') and j > i + 100:  # M400 near end of layer
                        last_layer_line = j
                        break
                break
        
        # Extract metadata from header comments
        metadata = self._extract_metadata(lines[:first_layer_line])
        
        # Extract print layers
        print_layers = lines[first_layer_line:last_layer_line + 1]
        
        metadata['original_lines'] = total_lines
        metadata['extracted_lines'] = len(print_layers)
        metadata['first_layer_line'] = first_layer_line
        metadata['last_layer_line'] = last_layer_line
        
        self.logger.info(
            f"Extracted print layers: lines {first_layer_line}-{last_layer_line} "
            f"({len(print_layers)} of {total_lines} lines)"
        )
        
        return '\n'.join(print_layers), metadata
    
    def _extract_metadata(self, header_lines: list) -> dict:
        """Extract temperature and filament metadata from header comments"""
        metadata = {
            'nozzle_temp': 220,
            'bed_temp': 65,
            'filament_type': 'PLA',
            'first_layer_nozzle_temp': None,
            'first_layer_bed_temp': None,
        }
        
        for line in header_lines:
            # Nozzle temperature
            if 'nozzle_temperature =' in line:
                try:
                    temp = int(line.split('=')[1].strip().split()[0])
                    metadata['nozzle_temp'] = temp
                except:
                    pass
            
            if 'nozzle_temperature_initial_layer =' in line:
                try:
                    temp = int(line.split('=')[1].strip().split()[0])
                    metadata['first_layer_nozzle_temp'] = temp
                except:
                    pass
            
            # Bed temperature
            if 'bed_temperature =' in line and 'hot_plate' not in line:
                try:
                    temp = int(line.split('=')[1].strip().split()[0])
                    metadata['bed_temp'] = temp
                except:
                    pass
            
            if 'bed_temperature_initial_layer =' in line:
                try:
                    temp = int(line.split('=')[1].strip().split()[0])
                    metadata['first_layer_bed_temp'] = temp
                except:
                    pass
            
            # Filament type
            if 'filament_type =' in line:
                try:
                    ftype = line.split('=')[1].strip().split()[0].strip('"')
                    metadata['filament_type'] = ftype
                except:
                    pass
        
        # Use first layer temps if available
        if metadata['first_layer_nozzle_temp']:
            metadata['nozzle_temp'] = metadata['first_layer_nozzle_temp']
        if metadata['first_layer_bed_temp']:
            metadata['bed_temp'] = metadata['first_layer_bed_temp']
        
        return metadata


def process_gcode_with_templates(
    gcode: str,
    settings: TemplateSettings,
    printer_config: Optional[PrinterConfig] = None
) -> str:
    """
    Process gcode by replacing start/end gcode with templates while PRESERVING
    the Bambu block structure (HEADER_BLOCK, CONFIG_BLOCK, filament footer).
    
    This ensures the printer can still read:
    - Print time estimate
    - Total layer count
    - Filament usage
    - Thumbnail preview (stored separately in 3MF)
    
    Args:
        gcode: Original gcode string
        settings: Template settings for generation
        printer_config: Printer configuration
        
    Returns:
        Processed gcode string with template start/end
    """
    extractor = GCodeLayerExtractor()
    templates = GCodeTemplates(printer_config)
    
    # Try to extract with block preservation first
    extracted = extractor.extract_preserving_blocks(gcode)
    
    if extracted['has_bambu_blocks']:
        logger.info("Using block-preserving extraction (Bambu format detected)")
        
        # Update settings with metadata from file ONLY if caller allows it
        metadata = extracted['metadata']
        if settings.prefer_file_metadata:
            if settings.nozzle_temp == 220:  # Default value
                settings.nozzle_temp = metadata.get('nozzle_temp', 220)
                settings.nozzle_temp_initial = settings.nozzle_temp
            
            if settings.bed_temp == 65:  # Default value
                settings.bed_temp = metadata.get('bed_temp', 65)
            
            if settings.filament_type == 'PLA':  # Default value
                settings.filament_type = metadata.get('filament_type', 'PLA')
        
        # Generate our custom start/end gcode
        start_gcode = templates.generate_start_gcode(settings)
        end_gcode = templates.generate_end_gcode(settings)
        
        # Build result preserving block structure:
        # 1. HEADER_BLOCK (preserved)
        # 2. Empty line
        # 3. CONFIG_BLOCK (preserved)
        # 4. Preamble (extrusion widths, M73, M201, etc)
        # 5. Our generated START GCODE (replaces original)
        # 6. PRINT LAYERS (preserved)
        # 7. Our generated END GCODE (replaces original)
        # 8. EXECUTABLE_BLOCK_END marker
        # 9. Filament footer (preserved)
        
        result_parts = []
        
        # 1. HEADER_BLOCK
        if extracted['header_block']:
            result_parts.append(extracted['header_block'])
            result_parts.append('')
        
        # 2. CONFIG_BLOCK  
        if extracted['config_block']:
            result_parts.append(extracted['config_block'])
            result_parts.append('')
        
        # 3. Preamble (extrusion widths comments)
        if extracted['executable_preamble']:
            result_parts.append(extracted['executable_preamble'])
        
        # 4. Our START GCODE
        result_parts.append(start_gcode)
        result_parts.append('')
        
        # 5. PRINT LAYERS
        result_parts.append(extracted['print_layers'])
        result_parts.append('')
        
        # 6. Our END GCODE
        result_parts.append(end_gcode)
        
        # 7. EXECUTABLE_BLOCK_END marker
        result_parts.append('; EXECUTABLE_BLOCK_END')
        result_parts.append('')
        
        # 8. Filament footer
        if extracted['filament_footer']:
            result_parts.append(extracted['filament_footer'])
        
        result = '\n'.join(result_parts)
        
        logger.info(
            f"Processed gcode with block preservation: "
            f"{metadata.get('original_lines', 0)} lines -> {len(result.split(chr(10)))} lines"
        )
        
        return result
    
    else:
        # Fallback to legacy extraction for non-Bambu files
        logger.info("Using legacy extraction (non-Bambu format)")
        
        # Extract print layers and metadata
        print_layers, metadata = extractor.extract_print_layers(gcode)
        
        # Update settings with metadata from file if not already set
        if settings.nozzle_temp == 220:  # Default value
            settings.nozzle_temp = metadata.get('nozzle_temp', 220)
            settings.nozzle_temp_initial = settings.nozzle_temp
        
        if settings.bed_temp == 65:  # Default value
            settings.bed_temp = metadata.get('bed_temp', 65)
        
        if settings.filament_type == 'PLA':  # Default value
            settings.filament_type = metadata.get('filament_type', 'PLA')
        
        # Generate templates
        start_gcode = templates.generate_start_gcode(settings)
        end_gcode = templates.generate_end_gcode(settings)
        
        # Combine: START + PRINT_LAYERS + END
        result = start_gcode + '\n' + print_layers + '\n' + end_gcode
        
        logger.info(
            f"Processed gcode: {metadata['original_lines']} lines -> "
            f"{len(result.split(chr(10)))} lines (extracted {metadata['extracted_lines']} print layer lines)"
        )
        
        return result
