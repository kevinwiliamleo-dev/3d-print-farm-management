"""
Filament Profile API Routes
CRUD operations for filament profiles and AMS slot assignment
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field
from typing import List, Optional
from src.database import get_db
from src.database.db import FilamentProfile
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/filaments", tags=["filaments"])


# ==================== Pydantic Models ====================

class FilamentProfileCreate(BaseModel):
    """Create new filament profile"""
    name: str = Field(..., description="Nama filament, e.g., 'Bambu PLA Basic - Black'")
    brand: str = Field(..., description="Merek, e.g., 'Bambu Lab', 'eSUN'")
    material_type: str = Field(..., description="Jenis: PLA, PETG, ABS, TPU, ASA, etc.")
    color_name: Optional[str] = Field(None, description="Nama warna, e.g., 'Matte Black'")
    color_hex: str = Field(default="000000FF", description="RRGGBBAA format")
    
    # Temperature Settings
    nozzle_temp_min: int = Field(default=190, ge=150, le=350)
    nozzle_temp_max: int = Field(default=240, ge=150, le=350)
    nozzle_temp_default: int = Field(default=220, ge=150, le=350)
    bed_temp_min: int = Field(default=45, ge=0, le=150)
    bed_temp_max: int = Field(default=65, ge=0, le=150)
    bed_temp_default: int = Field(default=55, ge=0, le=150)
    
    # Print Settings
    max_volumetric_speed: float = Field(default=12.0, ge=1.0, le=50.0)
    k_value: float = Field(default=0.02, ge=0.0, le=1.0)
    
    # Physical Properties
    density: float = Field(default=1.24, ge=0.5, le=3.0)
    diameter: float = Field(default=1.75, ge=1.0, le=3.0)
    spool_weight: float = Field(default=1000, ge=100, le=5000)
    
    # Drying Settings
    drying_temp: int = Field(default=50, ge=30, le=120)
    drying_time: int = Field(default=8, ge=1, le=48)
    
    # Compatibility
    requires_enclosure: bool = Field(default=False)
    requires_hardened_nozzle: bool = Field(default=False)
    
    # User Notes
    notes: Optional[str] = None
    purchase_link: Optional[str] = None
    stock_count: int = Field(default=0, ge=0)


class FilamentProfileUpdate(BaseModel):
    """Update filament profile (all fields optional)"""
    name: Optional[str] = None
    brand: Optional[str] = None
    material_type: Optional[str] = None
    color_name: Optional[str] = None
    color_hex: Optional[str] = None
    nozzle_temp_min: Optional[int] = None
    nozzle_temp_max: Optional[int] = None
    nozzle_temp_default: Optional[int] = None
    bed_temp_min: Optional[int] = None
    bed_temp_max: Optional[int] = None
    bed_temp_default: Optional[int] = None
    max_volumetric_speed: Optional[float] = None
    k_value: Optional[float] = None
    density: Optional[float] = None
    diameter: Optional[float] = None
    spool_weight: Optional[float] = None
    drying_temp: Optional[int] = None
    drying_time: Optional[int] = None
    requires_enclosure: Optional[bool] = None
    requires_hardened_nozzle: Optional[bool] = None
    notes: Optional[str] = None
    purchase_link: Optional[str] = None
    stock_count: Optional[int] = None
    is_active: Optional[bool] = None


class FilamentProfileResponse(BaseModel):
    """Filament profile response"""
    filament_id: int
    name: str
    brand: str
    material_type: str
    color_name: Optional[str]
    color_hex: str
    nozzle_temp_min: int
    nozzle_temp_max: int
    nozzle_temp_default: int
    bed_temp_min: int
    bed_temp_max: int
    bed_temp_default: int
    max_volumetric_speed: float
    k_value: float
    density: float
    diameter: float
    spool_weight: float
    drying_temp: int
    drying_time: int
    requires_enclosure: bool
    requires_hardened_nozzle: bool
    notes: Optional[str]
    purchase_link: Optional[str]
    stock_count: int
    is_active: bool
    
    class Config:
        from_attributes = True


class ApplyFilamentToSlotRequest(BaseModel):
    """Request to apply filament to AMS slot"""
    filament_id: int = Field(..., description="Filament profile ID to apply")
    slot: int = Field(..., ge=0, le=254, description="AMS slot number (0-3 or 254 for external)")


# ==================== API Endpoints ====================

@router.get("", response_model=List[FilamentProfileResponse])
async def get_all_filaments(
    material_type: Optional[str] = None,
    brand: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get all filament profiles with optional filtering
    
    - **material_type**: Filter by material (PLA, PETG, ABS, etc.)
    - **brand**: Filter by brand
    - **active_only**: Only show active filaments (default: True)
    """
    query = db.query(FilamentProfile)
    
    if active_only:
        query = query.filter(FilamentProfile.is_active == True)
    
    if material_type:
        query = query.filter(FilamentProfile.material_type == material_type.upper())
    
    if brand:
        query = query.filter(FilamentProfile.brand.ilike(f"%{brand}%"))
    
    return query.order_by(FilamentProfile.brand, FilamentProfile.name).all()


@router.get("/materials")
async def get_material_types(db: Session = Depends(get_db)):
    """Get list of unique material types in database"""
    materials = db.query(FilamentProfile.material_type).distinct().all()
    return {"materials": sorted([m[0] for m in materials if m[0]])}


@router.get("/brands")
async def get_brands(db: Session = Depends(get_db)):
    """Get list of unique brands in database"""
    brands = db.query(FilamentProfile.brand).distinct().all()
    return {"brands": sorted([b[0] for b in brands if b[0]])}


@router.get("/{filament_id}", response_model=FilamentProfileResponse)
async def get_filament(filament_id: int, db: Session = Depends(get_db)):
    """Get single filament profile by ID"""
    filament = db.query(FilamentProfile).filter(FilamentProfile.filament_id == filament_id).first()
    if not filament:
        raise HTTPException(status_code=404, detail="Filament profile not found")
    return filament


@router.post("", response_model=FilamentProfileResponse, status_code=201)
async def create_filament(filament: FilamentProfileCreate, db: Session = Depends(get_db)):
    """
    Create new filament profile
    
    Store filament characteristics for easy selection when printing.
    """
    try:
        db_filament = FilamentProfile(**filament.model_dump())
        db.add(db_filament)
        db.commit()
        db.refresh(db_filament)
        logger.info(f"Created filament profile: {db_filament.name}")
        return db_filament
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating filament: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{filament_id}", response_model=FilamentProfileResponse)
async def update_filament(
    filament_id: int,
    filament: FilamentProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update filament profile"""
    db_filament = db.query(FilamentProfile).filter(FilamentProfile.filament_id == filament_id).first()
    if not db_filament:
        raise HTTPException(status_code=404, detail="Filament profile not found")
    
    try:
        update_data = filament.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_filament, key, value)
        
        db.commit()
        db.refresh(db_filament)
        logger.info(f"Updated filament profile: {db_filament.name}")
        return db_filament
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating filament: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filament_id}")
async def delete_filament(filament_id: int, db: Session = Depends(get_db)):
    """Delete filament profile (soft delete - sets is_active to False)"""
    db_filament = db.query(FilamentProfile).filter(FilamentProfile.filament_id == filament_id).first()
    if not db_filament:
        raise HTTPException(status_code=404, detail="Filament profile not found")
    
    try:
        # Soft delete - just deactivate
        db_filament.is_active = False
        db.commit()
        logger.info(f"Deactivated filament profile: {db_filament.name}")
        return {"message": f"Filament '{db_filament.name}' deactivated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filament_id}/permanent")
async def delete_filament_permanent(filament_id: int, db: Session = Depends(get_db)):
    """Permanently delete filament profile"""
    db_filament = db.query(FilamentProfile).filter(FilamentProfile.filament_id == filament_id).first()
    if not db_filament:
        raise HTTPException(status_code=404, detail="Filament profile not found")
    
    try:
        name = db_filament.name
        db.delete(db_filament)
        db.commit()
        logger.info(f"Permanently deleted filament profile: {name}")
        return {"message": f"Filament '{name}' permanently deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{filament_id}/apply-to-slot")
async def apply_filament_to_ams_slot(
    filament_id: int,
    slot: int,
    printer_id: str = "03900D5A2402051",
    db: Session = Depends(get_db)
):
    """
    Apply filament profile settings to an AMS slot on the printer.
    Also saves the assignment to database for display purposes.
    
    - **filament_id**: Filament profile ID from database
    - **slot**: AMS slot number (0-3 for AMS Lite, 254 for external)
    - **printer_id**: Target printer ID
    """
    # Get filament profile
    db_filament = db.query(FilamentProfile).filter(FilamentProfile.filament_id == filament_id).first()
    if not db_filament:
        raise HTTPException(status_code=404, detail="Filament profile not found")
    
    try:
        # Get Bambu service (singleton - no arguments)
        from src.services.bambu_service import get_bambu_client
        
        bambu_client = get_bambu_client()
        if not bambu_client or not bambu_client.mqtt_connected:
            raise HTTPException(status_code=503, detail="Printer not connected")
        
        # Apply filament settings to slot
        success = bambu_client.ams_filament_setting(
            slot=slot,
            tray_color=db_filament.color_hex,
            tray_type=db_filament.material_type
        )
        
        if success:
            # Save assignment to database
            db.execute(
                text("""
                INSERT INTO ams_slot_assignments (printer_id, slot_number, filament_id, remaining_grams, updated_at)
                VALUES (:printer_id, :slot, :filament_id, :remaining_grams, CURRENT_TIMESTAMP)
                ON CONFLICT(printer_id, slot_number) 
                DO UPDATE SET filament_id = :filament_id2, remaining_grams = :remaining_grams2, updated_at = CURRENT_TIMESTAMP
                """),
                {
                    "printer_id": printer_id, 
                    "slot": slot, 
                    "filament_id": filament_id, 
                    "remaining_grams": db_filament.spool_weight or 0,
                    "filament_id2": filament_id, 
                    "remaining_grams2": db_filament.spool_weight or 0
                }
            )
            db.commit()
            
            return {
                "success": True,
                "message": f"Applied '{db_filament.name}' to slot {slot}",
                "printer_id": printer_id,
                "slot": slot,
                "filament": {
                    "id": db_filament.filament_id,
                    "name": db_filament.name,
                    "brand": db_filament.brand,
                    "type": db_filament.material_type,
                    "color": db_filament.color_hex,
                    "spool_weight": db_filament.spool_weight
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to apply filament settings to printer")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying filament to slot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class StockUpdate(BaseModel):
    """Stock update request"""
    grams: int = Field(default=1000, ge=0)


@router.post("/{filament_id}/stock/add")
async def add_stock(filament_id: int, stock: StockUpdate, db: Session = Depends(get_db)):
    """Add grams to filament (adding a new spool = +1000g, also increases stock_count)"""
    db_filament = db.query(FilamentProfile).filter(FilamentProfile.filament_id == filament_id).first()
    if not db_filament:
        raise HTTPException(status_code=404, detail="Filament profile not found")
    
    grams = stock.grams
    db_filament.spool_weight = (db_filament.spool_weight or 0) + grams
    # Also update stock count based on grams added (1 spool = 1000g)
    spools_added = grams // 1000
    if spools_added > 0:
        db_filament.stock_count = (db_filament.stock_count or 0) + spools_added
    db.commit()
    db.refresh(db_filament)
    
    return db_filament


# ==================== AMS Slot Assignment Endpoints ====================

@router.get("/slots/{printer_id}")
async def get_slot_assignments(printer_id: str, db: Session = Depends(get_db)):
    """
    Get all AMS slot assignments for a printer with filament details.
    
    Returns merged data from printer and our filament inventory.
    """
    try:
        # Get slot assignments from database with filament details
        result = db.execute(
            text("""
            SELECT 
                sa.slot_number,
                sa.filament_id,
                sa.remaining_grams,
                sa.updated_at,
                fp.name,
                fp.brand,
                fp.material_type,
                fp.color_hex,
                fp.color_name,
                fp.nozzle_temp_default,
                fp.bed_temp_default,
                fp.spool_weight
            FROM ams_slot_assignments sa
            LEFT JOIN filament_profiles fp ON sa.filament_id = fp.filament_id
            WHERE sa.printer_id = :printer_id
            ORDER BY sa.slot_number
            """),
            {"printer_id": printer_id}
        ).fetchall()
        
        slots = {}
        for row in result:
            slots[row[0]] = {
                "slot": row[0],
                "filament_id": row[1],
                "remaining_grams": row[2],
                "updated_at": row[3],
                "name": row[4],
                "brand": row[5],
                "material_type": row[6],
                "color_hex": row[7],
                "color_name": row[8],
                "nozzle_temp_default": row[9],
                "bed_temp_default": row[10],
                "spool_weight": row[11]
            }
        
        return {
            "printer_id": printer_id,
            "slots": slots
        }
        
    except Exception as e:
        logger.error(f"Error getting slot assignments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/slots/{printer_id}/{slot_number}")
async def assign_filament_to_slot(
    printer_id: str,
    slot_number: int,
    filament_id: int,
    remaining_grams: float = None,
    db: Session = Depends(get_db)
):
    """
    Assign a filament from inventory to an AMS slot.
    Also sends the settings to the printer.
    """
    # Get filament profile
    db_filament = db.query(FilamentProfile).filter(FilamentProfile.filament_id == filament_id).first()
    if not db_filament:
        raise HTTPException(status_code=404, detail="Filament profile not found")
    
    try:
        # Send to printer
        from src.services.bambu_service import get_bambu_client
        
        bambu_client = get_bambu_client()
        if bambu_client and bambu_client.mqtt_connected:
            bambu_client.ams_filament_setting(
                slot=slot_number,
                tray_color=db_filament.color_hex,
                tray_type=db_filament.material_type
            )
        
        # Default remaining to spool weight if not specified
        if remaining_grams is None:
            remaining_grams = db_filament.spool_weight or 1000
        
        # Save assignment to database
        db.execute(
            text("""
            INSERT INTO ams_slot_assignments (printer_id, slot_number, filament_id, remaining_grams, updated_at)
            VALUES (:printer_id, :slot_number, :filament_id, :remaining_grams, CURRENT_TIMESTAMP)
            ON CONFLICT(printer_id, slot_number) 
            DO UPDATE SET filament_id = :filament_id2, remaining_grams = :remaining_grams2, updated_at = CURRENT_TIMESTAMP
            """),
            {
                "printer_id": printer_id,
                "slot_number": slot_number,
                "filament_id": filament_id,
                "remaining_grams": remaining_grams,
                "filament_id2": filament_id,
                "remaining_grams2": remaining_grams
            }
        )
        db.commit()
        
        return {
            "success": True,
            "message": f"Assigned '{db_filament.name}' to slot {slot_number}",
            "printer_id": printer_id,
            "slot": slot_number,
            "filament": {
                "id": db_filament.filament_id,
                "name": db_filament.name,
                "brand": db_filament.brand,
                "material_type": db_filament.material_type,
                "color_hex": db_filament.color_hex,
                "remaining_grams": remaining_grams
            }
        }
        
    except Exception as e:
        logger.error(f"Error assigning filament to slot: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/slots/{printer_id}/{slot_number}/remaining")
async def update_slot_remaining(
    printer_id: str,
    slot_number: int,
    remaining_grams: float,
    db: Session = Depends(get_db)
):
    """Update remaining grams for a slot"""
    try:
        db.execute(
            text("""
            UPDATE ams_slot_assignments 
            SET remaining_grams = :remaining_grams, updated_at = CURRENT_TIMESTAMP
            WHERE printer_id = :printer_id AND slot_number = :slot_number
            """),
            {
                "remaining_grams": remaining_grams,
                "printer_id": printer_id,
                "slot_number": slot_number
            }
        )
        db.commit()
        
        return {
            "success": True,
            "printer_id": printer_id,
            "slot": slot_number,
            "remaining_grams": remaining_grams
        }
        
    except Exception as e:
        logger.error(f"Error updating slot remaining: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{filament_id}/stock/use")
async def use_stock(filament_id: int, grams: int = 0, db: Session = Depends(get_db)):
    """Use grams from filament (subtract from remaining weight)"""
    db_filament = db.query(FilamentProfile).filter(FilamentProfile.filament_id == filament_id).first()
    if not db_filament:
        raise HTTPException(status_code=404, detail="Filament profile not found")
    
    db_filament.spool_weight = max(0, (db_filament.spool_weight or 0) - grams)
    db.commit()
    db.refresh(db_filament)
    
    return db_filament
