"""
API endpoints for managing gcode templates
Uses database instead of JSON file for multi-printer support
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal

router = APIRouter(prefix="/api/templates", tags=["templates"])


# =======================
# Pydantic Models
# =======================
class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    order: Optional[int] = None
    gcode: Optional[str] = None


class TemplateCreate(BaseModel):
    template_key: str
    name: str
    description: Optional[str] = ""
    category: str  # 'start' or 'end'
    order: int
    enabled: bool = True
    controllable: bool = False
    setting_key: Optional[str] = None
    gcode: str
    printer_model: Optional[str] = None  # NULL = default for all printers


# =======================
# Database Helper Functions
# =======================
def get_templates_from_db(printer_model: Optional[str] = None) -> Dict[str, Any]:
    """Load templates from database"""
    db = SessionLocal()
    try:
        # Get templates (NULL printer_model = default, or specific printer)
        if printer_model:
            # Get specific printer templates OR defaults (NULL)
            query = text("""
                SELECT * FROM gcode_templates 
                WHERE printer_model IS NULL OR printer_model = :model
                ORDER BY category, "order"
            """)
            result = db.execute(query, {"model": printer_model})
        else:
            # Get all default templates
            query = text("""
                SELECT * FROM gcode_templates 
                WHERE printer_model IS NULL
                ORDER BY category, "order"
            """)
            result = db.execute(query)
        
        templates = {}
        for row in result:
            templates[row.template_key] = {
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
        
        return templates
    finally:
        db.close()


def get_template_by_key(template_key: str, printer_model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a single template by its key"""
    db = SessionLocal()
    try:
        if printer_model:
            query = text("""
                SELECT * FROM gcode_templates 
                WHERE template_key = :key AND (printer_model IS NULL OR printer_model = :model)
                LIMIT 1
            """)
            result = db.execute(query, {"key": template_key, "model": printer_model})
        else:
            query = text("""
                SELECT * FROM gcode_templates 
                WHERE template_key = :key AND printer_model IS NULL
                LIMIT 1
            """)
            result = db.execute(query, {"key": template_key})
        
        row = result.fetchone()
        if row:
            return {
                "template_id": row.template_id,
                "template_key": row.template_key,
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
        return None
    finally:
        db.close()


def update_template_in_db(template_key: str, updates: Dict[str, Any], printer_model: Optional[str] = None) -> bool:
    """Update a template in database"""
    db = SessionLocal()
    try:
        # Build update query
        set_clauses = []
        params = {"key": template_key}
        
        if "name" in updates and updates["name"] is not None:
            set_clauses.append("name = :name")
            params["name"] = updates["name"]
        
        if "description" in updates and updates["description"] is not None:
            set_clauses.append("description = :description")
            params["description"] = updates["description"]
        
        if "enabled" in updates and updates["enabled"] is not None:
            set_clauses.append("enabled = :enabled")
            params["enabled"] = 1 if updates["enabled"] else 0
        
        if "order" in updates and updates["order"] is not None:
            set_clauses.append('"order" = :order')
            params["order"] = updates["order"]
        
        if "gcode" in updates and updates["gcode"] is not None:
            set_clauses.append("gcode = :gcode")
            params["gcode"] = updates["gcode"]
        
        set_clauses.append("updated_at = :updated_at")
        params["updated_at"] = datetime.utcnow().isoformat()
        
        if not set_clauses:
            return False
        
        query = f"UPDATE gcode_templates SET {', '.join(set_clauses)} WHERE template_key = :key"
        if printer_model:
            query += " AND (printer_model = :model OR printer_model IS NULL)"
            params["model"] = printer_model
        else:
            query += " AND printer_model IS NULL"
        
        db.execute(text(query), params)
        db.commit()
        return True
    except Exception as e:
        print(f"Error updating template: {e}")
        db.rollback()
        return False
    finally:
        db.close()


# =======================
# API Endpoints
# =======================
@router.get("")
async def get_templates(printer_model: Optional[str] = None):
    """Get all templates, optionally filtered by printer model"""
    templates = get_templates_from_db(printer_model)
    
    # Separate by category
    start_templates = []
    end_templates = []
    
    for key, template in templates.items():
        template_with_key = {**template, "template_key": key}
        if template["category"] == "start":
            start_templates.append(template_with_key)
        elif template["category"] == "end":
            end_templates.append(template_with_key)
    
    # Sort by order
    start_templates.sort(key=lambda x: x.get("order", 999))
    end_templates.sort(key=lambda x: x.get("order", 999))
    
    # Available variables
    variables = [
        {"name": "{nozzle_temp}", "description": "Nozzle temperature in Celsius"},
        {"name": "{bed_temp}", "description": "Bed temperature in Celsius"},
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
    
    return {
        "start_templates": start_templates,
        "end_templates": end_templates,
        "variables": variables
    }


@router.put("/{template_key}")
async def update_template(template_key: str, update: TemplateUpdate, printer_model: Optional[str] = None):
    """Update a specific template"""
    templates = get_templates_from_db(printer_model)
    
    if template_key not in templates:
        raise HTTPException(status_code=404, detail=f"Template '{template_key}' not found")
    
    # Update in database
    success = update_template_in_db(template_key, update.dict(exclude_unset=True), printer_model)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update template")
    
    return {"message": f"Template '{template_key}' updated", "template_key": template_key}


@router.post("/{template_key}/toggle")
async def toggle_template(template_key: str, printer_model: Optional[str] = None):
    """Toggle template enabled/disabled"""
    templates = get_templates_from_db(printer_model)
    
    if template_key not in templates:
        raise HTTPException(status_code=404, detail=f"Template '{template_key}' not found")
    
    current_enabled = templates[template_key]["enabled"]
    success = update_template_in_db(template_key, {"enabled": not current_enabled}, printer_model)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to toggle template")
    
    return {
        "message": f"Template '{template_key}' {'disabled' if current_enabled else 'enabled'}",
        "enabled": not current_enabled
    }


@router.post("/reorder")
async def reorder_templates(category: str, template_keys: List[str], printer_model: Optional[str] = None):
    """Reorder templates in a category"""
    db = SessionLocal()
    try:
        for idx, key in enumerate(template_keys, start=1):
            query = text("""
                UPDATE gcode_templates 
                SET "order" = :order, updated_at = :updated_at
                WHERE template_key = :key AND category = :category
            """)
            params = {
                "order": idx,
                "updated_at": datetime.utcnow().isoformat(),
                "key": key,
                "category": category
            }
            if printer_model:
                query = text("""
                    UPDATE gcode_templates 
                    SET "order" = :order, updated_at = :updated_at
                    WHERE template_key = :key AND category = :category
                    AND (printer_model = :model OR printer_model IS NULL)
                """)
                params["model"] = printer_model
            
            db.execute(query, params)
        
        db.commit()
        return {"message": f"Reordered {len(template_keys)} templates in {category}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/reset")
async def reset_templates():
    """Reset templates to default by re-running migration"""
    import subprocess
    result = subprocess.run(
        ["python", "migrate_templates_db.py"],
        capture_output=True,
        text=True,
        cwd="."
    )
    
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Reset failed: {result.stderr}")
    
    return {"message": "Templates reset to defaults", "output": result.stdout}


@router.post("/preview")
async def preview_gcode(settings: Dict[str, Any]):
    """Generate preview of gcode with current templates and settings"""
    printer_model = settings.get("printer_model")
    templates = get_templates_from_db(printer_model)
    
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
        
        if current == 254:
            return False, "External spool, need to load from AMS"
        if current == 255:
            return False, "No filament loaded, need to load from AMS"
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


@router.get("/printer-models")
async def get_printer_models():
    """Get list of printer models that have custom templates"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT DISTINCT printer_model 
            FROM gcode_templates 
            WHERE printer_model IS NOT NULL
        """)
        result = db.execute(query)
        models = [row[0] for row in result]
        
        return {
            "default": None,  # NULL = default templates
            "models": models
        }
    finally:
        db.close()
