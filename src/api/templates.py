"""
API endpoints for managing gcode templates
Templates yang dapat diedit untuk mengubah start/end gcode
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from pathlib import Path
import json

router = APIRouter(prefix="/api/templates", tags=["templates"])

# Templates file location
TEMPLATES_FILE = Path("data/gcode_templates.json")

# Default templates structure
DEFAULT_TEMPLATES = {
    # ==================== START TEMPLATES ====================
    "machine_init": {
        "name": "Machine Init",
        "description": "Initialize machine, turn off clog detect",
        "enabled": True,
        "order": 1,
        "category": "start",
        "controllable": False,
        "gcode": """;===== MACHINE INIT =====
G392 S0 ; turn off clog detect during startup
M9833.2"""
    },
    "start_sound": {
        "name": "Start Sound",
        "description": "Beep on print start",
        "enabled": True,
        "order": 2,
        "category": "start",
        "controllable": True,
        "setting_key": "startup_sound",
        "gcode": """;===== START SOUND =====
M17 ; enable motors for sound
M400
M1002 gcode_claim_action : 2
; Startup beep sequence
M400 S1
M17
M400 S1"""
    },
    "start_heating": {
        "name": "Start Heating",
        "description": "Start nozzle and bed heating",
        "enabled": True,
        "order": 3,
        "category": "start",
        "controllable": False,
        "gcode": """;===== START HEATING =====
M1002 gcode_claim_action : 2
M1002 set_filament_type:{filament_type}
M104 S140 ; preheat nozzle to 140
M140 S{bed_temp} ; start bed heating"""
    },
    "vibration_test": {
        "name": "Vibration Test",
        "description": "M970 resonance compensation test",
        "enabled": True,
        "order": 4,
        "category": "start",
        "controllable": True,
        "setting_key": "vibration_test",
        "gcode": """;===== VIBRATION TEST =====
M1002 gcode_claim_action : 7
M970 Q1 A7 K0 ; vibration compensation test
M970 Q0 A7 K0
M974 S1 ; apply compensation
M400"""
    },
    "avoid_endstop": {
        "name": "Avoid End Stop",
        "description": "Move Z to avoid end stop during homing",
        "enabled": True,
        "order": 5,
        "category": "start",
        "controllable": False,
        "gcode": """;===== AVOID END STOP =====
G91
G380 S2 Z40 F1200
G380 S3 Z-15 F1200
G90"""
    },
    "reset_machine": {
        "name": "Reset Machine Status",
        "description": "Reset motor currents, feedrate, flowrate",
        "enabled": True,
        "order": 6,
        "category": "start",
        "controllable": False,
        "gcode": """;===== RESET MACHINE STATUS =====
M204 S6000
M630 S0 P0
G91
M17 Z0.3 ; lower z-motor current
G90
M17 X0.65 Y0.65 Z0.65 ; reset motor current
M220 S100 ; reset feedrate
M221 S100 ; reset flowrate"""
    },
    "cog_noise_reduction": {
        "name": "Cog Noise Reduction",
        "description": "Enable silent motor mode",
        "enabled": True,
        "order": 7,
        "category": "start",
        "controllable": False,
        "gcode": """;===== COG NOISE REDUCTION =====
M982.2 S1 ; turn on cog noise reduction"""
    },
    "homing": {
        "name": "Homing",
        "description": "Home XY axes",
        "enabled": True,
        "order": 8,
        "category": "start",
        "controllable": False,
        "gcode": """;===== HOMING =====
M1002 gcode_claim_action : 8
M211 X1 Y1 Z1 ; turn on soft end stops
G28 X Y ; home XY"""
    },
    "smart_temp_wait": {
        "name": "Smart Temp Wait",
        "description": "Wait for bed while nozzle heats",
        "enabled": True,
        "order": 9,
        "category": "start",
        "controllable": False,
        "gcode": """;===== SMART TEMP WAIT =====
M400
M190 S{bed_temp} ; wait for bed temp
M109 S140 ; wait for nozzle preheat"""
    },
    "clean_nozzle": {
        "name": "Clean Nozzle",
        "description": "Wipe nozzle on wiper arm",
        "enabled": True,
        "order": 10,
        "category": "start",
        "controllable": True,
        "setting_key": "clean_nozzle",
        "gcode": """;===== CLEAN NOZZLE =====
M1002 gcode_claim_action : 6
G1 X25 Y160 F18000 ; move to wiper position
G1 Z4 F1200 ; lower to wiper
G1 X60 F18000 ; wipe across
G1 X25 F18000 ; wipe back
G1 Z10 F1200 ; raise"""
    },
    "wipe_nozzle": {
        "name": "Wipe Nozzle",
        "description": "Extended nozzle wipe sequence",
        "enabled": True,
        "order": 11,
        "category": "start",
        "controllable": True,
        "setting_key": "wipe_nozzle",
        "gcode": """;===== WIPE NOZZLE =====
; Position at wiper
G1 X25 Y160 F18000
G1 Z4 F1200

; Wipe pattern - 3 passes
G1 X65 F18000
G1 X25 F18000
G1 X65 F18000
G1 X25 F18000
G1 X65 F18000
G1 X25 F18000
G1 Z10 F1200"""
    },
    "initial_extrusion": {
        "name": "Initial Extrusion",
        "description": "Prime nozzle with small extrusion",
        "enabled": True,
        "order": 12,
        "category": "start",
        "controllable": False,
        "gcode": """;===== INITIAL EXTRUSION =====
M83 ; relative extrusion
G1 E3 F300 ; extrude 3mm
G1 E-1 F800 ; small retract
G92 E0 ; reset E"""
    },
    "home_z": {
        "name": "Home Z",
        "description": "Home Z axis after bed is hot",
        "enabled": True,
        "order": 13,
        "category": "start",
        "controllable": False,
        "gcode": """;===== HOME Z =====
M1002 gcode_claim_action : 8
G28 Z ; home Z
G1 Z5 F1200 ; raise Z slightly"""
    },
    "build_plate_detection": {
        "name": "Build Plate Detection",
        "description": "Detect build plate type",
        "enabled": True,
        "order": 14,
        "category": "start",
        "controllable": False,
        "gcode": """;===== BUILD PLATE DETECTION =====
M1002 gcode_claim_action : 10
M960 S2 P1
G29.2 S0 ; Reset build plate type
M1002 judge_flag finish_sensor_check=1"""
    },
    "ams_loading": {
        "name": "AMS Loading",
        "description": "Load filament from AMS slot (smart skip if same filament)",
        "enabled": True,
        "order": 15,
        "category": "start",
        "controllable": True,
        "setting_key": "ams_slot",
        "gcode": """;===== AMS LOADING =====
; Selected AMS slot: {ams_slot}
; Current loaded tray: {current_tray}
; NOTE: If current_tray == ams_slot, this will be SKIPPED
M620 S{ams_slot}A ; Select AMS slot
M400
T{ams_slot} ; Load filament from slot
M400
M621 S{ams_slot}A ; Confirm loaded"""
    },
    "filament_detection": {
        "name": "Filament Detection",
        "description": "Verify filament is loaded properly",
        "enabled": True,
        "order": 16,
        "category": "start",
        "controllable": False,
        "gcode": """;===== FILAMENT DETECTION =====
M412 S1 ; Enable filament runout detection
M400"""
    },
    "flow_calibration": {
        "name": "Flow Calibration",
        "description": "Auto flow rate calibration",
        "enabled": True,
        "order": 17,
        "category": "start",
        "controllable": True,
        "setting_key": "flow_calibration",
        "gcode": """;===== FLOW CALIBRATION =====
M1002 gcode_claim_action : 4
; K factor calculation for flow
M900 K0 ; Linear advance off
M221 S100 ; Reset flow rate"""
    },
    "bed_leveling": {
        "name": "Bed Leveling",
        "description": "Auto bed leveling mesh",
        "enabled": True,
        "order": 18,
        "category": "start",
        "controllable": True,
        "setting_key": "auto_bed_leveling",
        "gcode": """;===== BED LEVELING =====
M1002 gcode_claim_action : 3
M969 S1 ; Auto bed leveling
G29 ; Run bed leveling mesh
M400"""
    },
    "final_positioning": {
        "name": "Final Positioning",
        "description": "Move to start position",
        "enabled": True,
        "order": 19,
        "category": "start",
        "controllable": False,
        "gcode": """;===== FINAL POSITIONING =====
G1 X60 Y60 Z5 F12000 ; Move to start area
M400"""
    },
    "final_temp_wait": {
        "name": "Final Temp Wait",
        "description": "Wait for final nozzle temperature",
        "enabled": True,
        "order": 20,
        "category": "start",
        "controllable": False,
        "gcode": """;===== FINAL TEMP WAIT =====
M1002 gcode_claim_action : 0
M400
G1 Z3 F800 ; move nozzle up a little
M106 P1 S255 ; turn on fan to cool tip, prevents oozing
M109 S{preheat_temp} ; wait for temp (offset -{preheat_offset}C)"""
    },
    "ready_to_print": {
        "name": "Ready to Print",
        "description": "Final prep before first layer",
        "enabled": True,
        "order": 21,
        "category": "start",
        "controllable": False,
        "gcode": """;===== READY TO PRINT =====
M960 S1 P0 ; turn off laser
M960 S2 P0
M106 P1 S0 ; turn off aux fan
M106 S255 ; part cooling fan ON
M109 S{nozzle_temp} ; wait for print temp
G392 S1 ; turn on clog detect
M400"""
    },
    "nozzle_load_line": {
        "name": "Nozzle Load Line",
        "description": "Draw line at edge of bed to prime nozzle",
        "enabled": True,
        "order": 22,
        "category": "start",
        "controllable": True,
        "setting_key": "nozzle_load_line",
        "gcode": """;===== NOZZLE LOAD LINE =====
G1 Z0.4 F1200 ; Move to first layer height
G1 X5 Y5 F12000 ; Move to start corner
M83 ; Relative extrusion
G1 X180 E20 F1500 ; Draw line while extruding
G1 E-1 F1800 ; Small retract
G1 Z1 F1200 ; Lift
G92 E0 ; Reset E"""
    },
    "pre_extrude": {
        "name": "Pre-Extrude",
        "description": "Final extrusion before print (Quick Start mode)",
        "enabled": True,
        "order": 23,
        "category": "start",
        "controllable": True,
        "setting_key": "pre_extrude",
        "gcode": """;===== PRE-EXTRUDE (Quick Start) =====
M83 ; Relative extrusion mode
G1 E5 F300 ; Extrude 5mm to prime
G1 E-2 F1800 ; Retract 2mm
G92 E0 ; Reset extrusion position
M400"""
    },
    "timelapse_start": {
        "name": "Timelapse",
        "description": "Enable timelapse recording",
        "enabled": False,
        "order": 24,
        "category": "start",
        "controllable": True,
        "setting_key": "timelapse_recording",
        "gcode": """;===== TIMELAPSE START =====
M991 S0 P-1 ; close last timelapse if any
M400
M991 S1 P1 ; start timelapse recording"""
    },

    # ==================== END TEMPLATES ====================
    "end_finish_moves": {
        "name": "Finish Moves",
        "description": "Wait for all moves to complete",
        "enabled": True,
        "order": 1,
        "category": "end",
        "controllable": False,
        "gcode": """;===== FINISH MOVES =====
M400 ; wait for buffer to clear
G92 E0 ; reset E"""
    },
    "end_timelapse": {
        "name": "Timelapse Finish",
        "description": "Stop timelapse recording",
        "enabled": False,
        "order": 2,
        "category": "end",
        "controllable": True,
        "setting_key": "timelapse_recording",
        "gcode": """;===== TIMELAPSE FINISH =====
M991 S0 ; stop timelapse and save video
M400"""
    },
    "end_retract_raise": {
        "name": "Retract and Raise",
        "description": "Retract filament and raise Z",
        "enabled": True,
        "order": 3,
        "category": "end",
        "controllable": False,
        "gcode": """;===== RETRACT AND RAISE =====
G92 E0
G1 E-2 F2400 ; Retract
G91 ; Relative positioning
G1 Z10 F3000 ; Raise Z by 10mm
G90 ; Absolute positioning"""
    },
    "end_safe_position": {
        "name": "Move to Safe Position",
        "description": "Move to back of bed",
        "enabled": True,
        "order": 4,
        "category": "end",
        "controllable": False,
        "gcode": """;===== MOVE TO SAFE POSITION =====
G1 X0 Y256 F9000 ; Move to back"""
    },
    "end_auto_eject": {
        "name": "Auto Eject",
        "description": "Wait for bed to cool then push off print",
        "enabled": False,
        "order": 5,
        "category": "end",
        "controllable": True,
        "setting_key": "auto_eject",
        "gcode": """;===== AUTO EJECT =====
; Waiting for bed to cool to {cooldown_temp}C
M140 S{cooldown_temp} ; Set bed target
M190 R{cooldown_temp} ; Wait for cooldown (R = wait for temp or below)

; Push off print
G28 X ; Home X to push print off
G1 X128 F12000 ; Return to center"""
    },
    "end_heaters_off": {
        "name": "Turn Off Heaters",
        "description": "CRITICAL: Turn off hotend and bed heaters",
        "enabled": True,
        "order": 6,
        "category": "end",
        "controllable": False,
        "gcode": """;===== SAFETY: TURN OFF HEATERS =====
M104 S0 ; *** TURN OFF HOTEND ***
M140 S0 ; *** TURN OFF BED ***"""
    },
    "end_fans_off": {
        "name": "Turn Off Fans",
        "description": "Turn off all fans",
        "enabled": True,
        "order": 7,
        "category": "end",
        "controllable": False,
        "gcode": """;===== TURN OFF FANS =====
M106 S0 ; Part cooling fan OFF
M106 P1 S0 ; Aux fan OFF
M106 P2 S0 ; Chamber fan OFF"""
    },
    "end_motors_off": {
        "name": "Disable Motors",
        "description": "Disable stepper motors",
        "enabled": True,
        "order": 8,
        "category": "end",
        "controllable": False,
        "gcode": """;===== DISABLE MOTORS =====
M400 ; Wait for completion
M18 X Y Z ; Disable motors"""
    },
    "end_sound": {
        "name": "End Sound",
        "description": "Melody on print completion",
        "enabled": True,
        "order": 9,
        "category": "end",
        "controllable": True,
        "setting_key": "completion_sound",
        "gcode": """;===== END SOUND =====
M400
; Success melody - 3 notes
M400 S1
M17
M400 S1
M17
M400 S2"""
    },
    "end_complete": {
        "name": "Print Complete",
        "description": "Final cleanup and message",
        "enabled": True,
        "order": 10,
        "category": "end",
        "controllable": False,
        "gcode": """;===== PRINT COMPLETE =====
M400
M1002 gcode_claim_action : 0
; Print finished successfully!
; Total time: Check slicer estimate"""
    }
}


def load_templates() -> Dict[str, Any]:
    """Load templates from file or return defaults"""
    if TEMPLATES_FILE.exists():
        try:
            with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_TEMPLATES.copy()


def save_templates(templates: Dict[str, Any]) -> None:
    """Save templates to file"""
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TEMPLATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)


class TemplateUpdate(BaseModel):
    """Model for updating a template"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    order: Optional[int] = None
    gcode: Optional[str] = None


class TemplateReorder(BaseModel):
    """Model for reordering templates"""
    template_id: str
    new_order: int
    category: str  # "start" or "end"


@router.get("")
async def get_templates():
    """Get all templates"""
    templates = load_templates()
    
    # Convert dict to arrays for frontend
    start_templates = []
    end_templates = []
    
    for tid, template in templates.items():
        template_with_id = {**template, "id": tid}
        if template.get("category") == "start":
            start_templates.append(template_with_id)
        elif template.get("category") == "end":
            end_templates.append(template_with_id)
    
    # Sort by order
    start_templates.sort(key=lambda x: x.get("order", 999))
    end_templates.sort(key=lambda x: x.get("order", 999))
    
    return {
        "start_templates": start_templates,
        "end_templates": end_templates,
        "variables": [
            {"name": "{nozzle_temp}", "description": "Target nozzle temperature"},
            {"name": "{bed_temp}", "description": "Target bed temperature"},
            {"name": "{filament_type}", "description": "Filament type (PLA, PETG, etc)"},
            {"name": "{ams_slot}", "description": "AMS slot to use (0-3)"},
            {"name": "{current_tray}", "description": "Currently loaded tray"},
            {"name": "{preheat_offset}", "description": "Preheat offset value"},
            {"name": "{preheat_temp}", "description": "Calculated preheat temp"},
            {"name": "{cooldown_temp}", "description": "Bed cooldown temperature"},
        ]
    }


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get a specific template"""
    templates = load_templates()
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"template": templates[template_id], "id": template_id}


@router.put("/{template_id}")
async def update_template(template_id: str, update: TemplateUpdate):
    """Update a specific template"""
    templates = load_templates()
    
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    
    if update.name is not None:
        template["name"] = update.name
    if update.description is not None:
        template["description"] = update.description
    if update.enabled is not None:
        template["enabled"] = update.enabled
    if update.order is not None:
        template["order"] = update.order
    if update.gcode is not None:
        template["gcode"] = update.gcode
    
    templates[template_id] = template
    save_templates(templates)
    
    return {"success": True, "template": template}


@router.post("/reorder")
async def reorder_template(reorder: TemplateReorder):
    """Reorder a template within its category"""
    templates = load_templates()
    
    if reorder.template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Get templates in same category, sorted by current order
    category_templates = [
        (tid, t) for tid, t in templates.items()
        if t.get("category") == reorder.category
    ]
    category_templates.sort(key=lambda x: x[1].get("order", 999))
    
    # Find the template being moved
    old_order = templates[reorder.template_id].get("order", 1)
    new_order = reorder.new_order
    
    # Reorder all templates in the category
    for tid, t in category_templates:
        current = t.get("order", 1)
        if tid == reorder.template_id:
            t["order"] = new_order
        elif old_order < new_order:
            # Moving down: shift items up
            if old_order < current <= new_order:
                t["order"] = current - 1
        else:
            # Moving up: shift items down
            if new_order <= current < old_order:
                t["order"] = current + 1
        templates[tid] = t
    
    save_templates(templates)
    return {"success": True, "templates": templates}


@router.post("/reset")
async def reset_templates():
    """Reset templates to defaults"""
    save_templates(DEFAULT_TEMPLATES.copy())
    return {"success": True, "templates": DEFAULT_TEMPLATES}


@router.get("/variables/list")
async def get_variables():
    """Get list of available template variables"""
    return {
        "variables": [
            {"name": "{nozzle_temp}", "description": "Target nozzle temperature from file"},
            {"name": "{bed_temp}", "description": "Target bed temperature from file"},
            {"name": "{filament_type}", "description": "Filament type (PLA, PETG, ABS, etc)"},
            {"name": "{ams_slot}", "description": "AMS slot to use (0-3)"},
            {"name": "{current_tray}", "description": "Currently loaded tray (255=none, 254=external)"},
            {"name": "{preheat_offset}", "description": "Preheat offset value"},
            {"name": "{preheat_temp}", "description": "Calculated preheat temp (nozzle - offset)"},
            {"name": "{cooldown_temp}", "description": "Bed cooldown temperature for auto-eject"},
            {"name": "{flush_temp}", "description": "Temperature for filament flush/change"},
            {"name": "{flush_speed}", "description": "Speed for filament flush"},
            {"name": "{max_volumetric_speed}", "description": "Maximum volumetric extrusion speed"},
        ]
    }


@router.post("/preview")
async def preview_gcode(settings: Dict[str, Any]):
    """Generate preview of gcode with current templates and settings"""
    templates = load_templates()
    
    # Default variable values
    vars_dict = {
        "nozzle_temp": settings.get("nozzle_temp", 220),
        "bed_temp": settings.get("bed_temp", 60),
        "filament_type": settings.get("filament_type", "PLA"),
        "ams_slot": settings.get("ams_slot", 0),
        "current_tray": settings.get("current_tray", 255),
        "preheat_offset": settings.get("preheat_offset", 20),
        "cooldown_temp": settings.get("cooldown_temp", 35),
        "flush_temp": settings.get("flush_temp", 240),
        "flush_speed": settings.get("flush_speed", 299),
        "max_volumetric_speed": settings.get("max_volumetric_speed", 12),
    }
    
    # Calculate preheat temp
    vars_dict["preheat_temp"] = vars_dict["nozzle_temp"] - vars_dict["preheat_offset"]
    
    def apply_variables(gcode: str) -> str:
        result = gcode
        for key, value in vars_dict.items():
            result = result.replace("{" + key + "}", str(value))
        return result
    
    def should_skip_ams() -> tuple:
        """Check if AMS loading should be skipped"""
        current = vars_dict["current_tray"]
        selected = vars_dict["ams_slot"]
        
        # External spool indicator
        if current == 254:
            return False, "External spool, need to load from AMS"
        
        # No filament loaded
        if current == 255:
            return False, "No filament loaded, need to load from AMS"
        
        # Same slot already loaded
        if current == selected:
            return True, f"Slot {selected} already loaded, skipping AMS load"
        
        return False, f"Need to change from slot {current} to slot {selected}"
    
    # Build start gcode
    start_templates = [
        (tid, t) for tid, t in templates.items()
        if t.get("category") == "start" and t.get("enabled", True)
    ]
    start_templates.sort(key=lambda x: x[1].get("order", 999))
    
    start_gcode_parts = [";========== TEMPLATE MODE START GCODE =========="]
    
    for tid, template in start_templates:
        # Smart AMS skip
        if tid == "ams_loading":
            skip, reason = should_skip_ams()
            start_gcode_parts.append(f"\n; AMS Check: {reason}")
            if skip:
                start_gcode_parts.append("; >>> SKIPPING AMS LOADING (same filament)")
                continue
        
        gcode = apply_variables(template.get("gcode", ""))
        start_gcode_parts.append(f"\n{gcode}")
    
    start_gcode_parts.append("\n;========== END START GCODE ==========\n")
    
    # Build end gcode
    end_templates = [
        (tid, t) for tid, t in templates.items()
        if t.get("category") == "end" and t.get("enabled", True)
    ]
    end_templates.sort(key=lambda x: x[1].get("order", 999))
    
    end_gcode_parts = [";========== TEMPLATE MODE END GCODE =========="]
    
    for tid, template in end_templates:
        gcode = apply_variables(template.get("gcode", ""))
        end_gcode_parts.append(f"\n{gcode}")
    
    end_gcode_parts.append("\n;========== END END GCODE ==========\n")
    
    return {
        "start_gcode": "\n".join(start_gcode_parts),
        "end_gcode": "\n".join(end_gcode_parts),
        "variables": vars_dict
    }
