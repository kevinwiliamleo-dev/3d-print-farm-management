"""
API endpoints for managing print presets
User-defined automation setting profiles
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.db import get_db, PrintPreset
from datetime import datetime

router = APIRouter(prefix="/api/presets", tags=["presets"])


# ==================== Pydantic Models ====================

class PresetBase(BaseModel):
    """Base preset fields"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: str = "⚡"
    color: str = "3b82f6"
    
    # Start GCode (21 templates)
    start_machine: bool = False
    heat_bed_hotend: bool = False
    startup_sound: bool = False
    avoid_end_stop: bool = False
    reset_machine_status: bool = False
    cog_noise_reduction: bool = False
    ams_slot: bool = False
    flow_calibration: bool = False
    vibration_test: bool = False
    wipe_nozzle: bool = False
    clean_nozzle: bool = False
    brush_material_wipe: bool = False
    final_wipe_nozzle: bool = False
    auto_bed_leveling: bool = False
    home_after_wipe: bool = False
    prepare_print: bool = False
    nozzle_load_line: bool = False
    extrude_calibration_test: bool = False
    turn_off_light: bool = False
    final_start: bool = False
    pre_extrude: bool = False
    preheat_offset: int = 20
    
    # End GCode (6 templates)
    end_print_start: bool = False
    timelapse: bool = False
    move_safe_position: bool = False
    auto_eject: bool = False
    end_sound: bool = False
    end_print_final: bool = False
    cooldown_temp: int = 32
    
    use_template_mode: bool = True


class PresetCreate(PresetBase):
    """Fields for creating a preset"""
    is_default: bool = False


class PresetUpdate(BaseModel):
    """Fields for updating a preset (all optional)"""
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_default: Optional[bool] = None
    
    # Start GCode (21 templates)
    start_machine: Optional[bool] = None
    heat_bed_hotend: Optional[bool] = None
    startup_sound: Optional[bool] = None
    avoid_end_stop: Optional[bool] = None
    reset_machine_status: Optional[bool] = None
    cog_noise_reduction: Optional[bool] = None
    ams_slot: Optional[bool] = None
    flow_calibration: Optional[bool] = None
    vibration_test: Optional[bool] = None
    wipe_nozzle: Optional[bool] = None
    clean_nozzle: Optional[bool] = None
    brush_material_wipe: Optional[bool] = None
    final_wipe_nozzle: Optional[bool] = None
    auto_bed_leveling: Optional[bool] = None
    home_after_wipe: Optional[bool] = None
    prepare_print: Optional[bool] = None
    nozzle_load_line: Optional[bool] = None
    extrude_calibration_test: Optional[bool] = None
    turn_off_light: Optional[bool] = None
    final_start: Optional[bool] = None
    pre_extrude: Optional[bool] = None
    preheat_offset: Optional[int] = None
    
    # End GCode (6 templates)
    end_print_start: Optional[bool] = None
    timelapse: Optional[bool] = None
    move_safe_position: Optional[bool] = None
    auto_eject: Optional[bool] = None
    end_sound: Optional[bool] = None
    end_print_final: Optional[bool] = None
    cooldown_temp: Optional[int] = None
    
    use_template_mode: Optional[bool] = None


class PresetResponse(PresetBase):
    """Preset response with all fields"""
    preset_id: int
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== API Endpoints ====================

@router.get("", response_model=List[PresetResponse])
async def get_all_presets(db: Session = Depends(get_db)):
    """Get all print presets"""
    presets = db.query(PrintPreset).order_by(PrintPreset.name).all()
    return presets


@router.get("/default", response_model=Optional[PresetResponse])
async def get_default_preset(db: Session = Depends(get_db)):
    """Get the default preset (if any)"""
    preset = db.query(PrintPreset).filter(PrintPreset.is_default == True).first()
    if not preset:
        return None
    return preset


@router.get("/{preset_id}", response_model=PresetResponse)
async def get_preset(preset_id: int, db: Session = Depends(get_db)):
    """Get a specific preset by ID"""
    preset = db.query(PrintPreset).filter(PrintPreset.preset_id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset


@router.post("", response_model=PresetResponse)
async def create_preset(preset_data: PresetCreate, db: Session = Depends(get_db)):
    """Create a new preset"""
    # If this is set as default, unset other defaults
    if preset_data.is_default:
        db.query(PrintPreset).filter(PrintPreset.is_default == True).update({"is_default": False})
    
    # Populate every preset field so toggles in the UI persist correctly
    preset = PrintPreset(**preset_data.dict())
    
    db.add(preset)
    db.commit()
    db.refresh(preset)
    
    return preset


@router.put("/{preset_id}", response_model=PresetResponse)
async def update_preset(preset_id: int, preset_data: PresetUpdate, db: Session = Depends(get_db)):
    """Update an existing preset"""
    preset = db.query(PrintPreset).filter(PrintPreset.preset_id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # If setting as default, unset other defaults first
    if preset_data.is_default:
        db.query(PrintPreset).filter(
            PrintPreset.preset_id != preset_id,
            PrintPreset.is_default == True
        ).update({"is_default": False})
    
    # Update fields that are provided
    update_data = preset_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(preset, key, value)
    
    preset.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(preset)
    
    return preset


@router.delete("/{preset_id}")
async def delete_preset(preset_id: int, db: Session = Depends(get_db)):
    """Delete a preset"""
    preset = db.query(PrintPreset).filter(PrintPreset.preset_id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    db.delete(preset)
    db.commit()
    
    return {"success": True, "message": f"Preset '{preset.name}' deleted"}


@router.post("/{preset_id}/set-default")
async def set_default_preset(preset_id: int, db: Session = Depends(get_db)):
    """Set a preset as the default"""
    preset = db.query(PrintPreset).filter(PrintPreset.preset_id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    
    # Unset all other defaults
    db.query(PrintPreset).filter(PrintPreset.is_default == True).update({"is_default": False})
    
    # Set this one as default
    preset.is_default = True
    preset.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": f"'{preset.name}' is now the default preset"}


@router.post("/create-defaults")
async def create_default_presets(db: Session = Depends(get_db)):
    """Create default presets if none exist"""
    existing = db.query(PrintPreset).count()
    if existing > 0:
        return {"success": True, "message": f"{existing} presets already exist", "created": 0}
    
    default_presets = [
        {
            "name": "Quick Print",
            "description": "Skip calibrations for faster start. Good for tested models.",
            "icon": "⚡",
            "color": "22c55e",
            "is_default": True,
            "auto_bed_leveling": False,
            "flow_calibration": False,
            "vibration_test": False,
            "clean_nozzle": True,
            "wipe_nozzle": True,
            "nozzle_load_line": True,
            "auto_eject": True,
            "cooldown_temp": 32,
            "startup_sound": True,
            "end_sound": True,
            "timelapse": False,
            "pre_extrude": True,
            "preheat_offset": 20,
            "use_template_mode": True,
        },
        {
            "name": "Full Calibration",
            "description": "All calibrations enabled. Best for new filaments or first prints.",
            "icon": "🔧",
            "color": "3b82f6",
            "is_default": False,
            "auto_bed_leveling": True,
            "flow_calibration": True,
            "vibration_test": True,
            "clean_nozzle": True,
            "wipe_nozzle": True,
            "nozzle_load_line": True,
            "auto_eject": True,
            "cooldown_temp": 32,
            "startup_sound": True,
            "end_sound": True,
            "timelapse": False,
            "pre_extrude": True,
            "preheat_offset": 0,
            "use_template_mode": True,
        },
        {
            "name": "Timelapse Mode",
            "description": "Optimized for timelapse recording with clean nozzle.",
            "icon": "🎬",
            "color": "d946ef",
            "is_default": False,
            "auto_bed_leveling": True,
            "flow_calibration": False,
            "vibration_test": False,
            "clean_nozzle": True,
            "wipe_nozzle": True,
            "nozzle_load_line": True,
            "auto_eject": False,  # Don't auto-eject during timelapse
            "cooldown_temp": 32,
            "startup_sound": False,  # Silent for timelapse
            "end_sound": False,
            "timelapse": True,
            "pre_extrude": True,
            "preheat_offset": 20,
            "use_template_mode": True,
        },
        {
            "name": "Silent Night",
            "description": "Quiet mode - no sounds, no vibration test.",
            "icon": "🌙",
            "color": "6366f1",
            "is_default": False,
            "auto_bed_leveling": True,
            "flow_calibration": False,
            "vibration_test": False,
            "clean_nozzle": True,
            "wipe_nozzle": True,
            "nozzle_load_line": True,
            "auto_eject": True,
            "cooldown_temp": 32,
            "startup_sound": False,
            "end_sound": False,
            "timelapse": False,
            "pre_extrude": True,
            "preheat_offset": 20,
            "use_template_mode": True,
        },
    ]
    
    for preset_data in default_presets:
        preset = PrintPreset(**preset_data)
        db.add(preset)
    
    db.commit()
    
    return {"success": True, "message": "Default presets created", "created": len(default_presets)}
