"""
Job API Routes - Handle job upload, listing, and management
Follows naming conventions from README.md
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from src.database import get_db
from src.services.job_service import JobService
from src.models.schemas import JobResponse, JobListResponse
from src.utils.gcode_parser import (
    parse_file_metadata, 
    extract_3mf_thumbnail, 
    get_3mf_structure,
    extract_gcode_thumbnail_from_file,
    extract_gcode_from_3mf,
    parse_gcode_sections,
    apply_section_modifications
)
import logging
import os
import zipfile
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Upload directory - use absolute path to avoid permission issues
UPLOAD_DIR = Path(__file__).parent.parent.parent / "data" / "uploads"
UPLOAD_DIR = UPLOAD_DIR.resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".3mf", ".stl"}


@router.post("/upload", response_model=JobResponse)
async def upload_and_create_job(
    file: UploadFile = File(...),
    loop_count: int = Form(1),
    db: Session = Depends(get_db)
):
    """
    Upload model file and create print job
    
    - **file**: .3mf or .stl model file
    - **loop_count**: How many times to print this job
    
    Returns: job_id, job_name, status
    """
    try:
        # Validate file extension
        filename = file.filename
        file_extension = Path(filename).suffix.lower()
        
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}"
            )
        
        # Validate loop_count
        if loop_count < 1:
            raise HTTPException(status_code=400, detail="loop_count must be >= 1")
        
        # Save uploaded file
        input_file_path = UPLOAD_DIR / filename
        input_file_path = input_file_path.resolve()
        content = await file.read()
        
        # Write file with explicit permissions handling
        try:
            with open(str(input_file_path), "wb") as f:
                f.write(content)
        except PermissionError:
            # If permission denied, try creating in temp location and move
            import tempfile
            import shutil
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            shutil.move(tmp_path, str(input_file_path))
        
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"📤 Uploaded file: {filename}, size: {file_size_mb:.2f} MB")
        
        # Create job in database
        job_service = JobService(db)
        job_create_data = type('JobCreate', (), {
            'loop_count': loop_count,
            'layer_height': 0.2,
            'infill_density': 15
        })()
        
        job_response = job_service.create_job(job_create_data, filename)
        
        logger.info(f"✅ Job created successfully: job_id={job_response.job_id}, name={job_response.job_name}, loops={loop_count}, size={file_size_mb:.2f}MB")
        
        # Return full job response object
        return job_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/metadata")
async def get_job_metadata(job_id: int, db: Session = Depends(get_db)):
    """
    Get metadata from uploaded file (estimated time, filament used, etc.)
    
    Parses 3MF/G-code file to extract:
    - Estimated print time
    - Filament used (grams, mm)
    - Layer count
    - Nozzle/Bed temperatures
    - Filament type and color
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={job_id}")
        
        # Get file path - use filename (original upload name with extension)
        file_path = UPLOAD_DIR / job.filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {job.filename}")
        
        # Parse metadata
        metadata = parse_file_metadata(file_path)
        
        return {
            "job_id": job_id,
            "job_name": job.job_name,
            **metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/thumbnail")
async def get_job_thumbnail(job_id: int, db: Session = Depends(get_db)):
    """
    Get thumbnail image from uploaded file
    
    Supports:
    - 3MF files: Extracts embedded PNG from Metadata/plate_1.png or Metadata/thumbnail.png
    - GCode files: Extracts base64-encoded PNG from ; thumbnail begin/end blocks
    
    Returns: PNG/JPEG image of the model preview
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={job_id}")
        
        # Use filename (original upload name with extension)
        file_path = UPLOAD_DIR / job.filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {job.filename}")
        
        suffix = file_path.suffix.lower()
        thumbnail_data = None
        media_type = "image/png"
        
        # Extract thumbnail based on file type
        if suffix == '.3mf':
            thumbnail_data = extract_3mf_thumbnail(file_path)
        elif suffix in ['.gcode', '.g']:
            thumbnail_data = extract_gcode_thumbnail_from_file(file_path)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Thumbnails only available for 3MF and GCode files"
            )
        
        if not thumbnail_data:
            raise HTTPException(status_code=404, detail="No thumbnail found in file")
        
        # Detect image type from magic bytes
        if thumbnail_data[:3] == b'\xff\xd8\xff':
            media_type = "image/jpeg"
        elif thumbnail_data[:8] == b'\x89PNG\r\n\x1a\n':
            media_type = "image/png"
        
        # Return as image
        return Response(
            content=thumbnail_data,
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename={job.job_name}_thumbnail.png"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job thumbnail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/structure")
async def get_job_file_structure(job_id: int, db: Session = Depends(get_db)):
    """
    Get internal file structure of uploaded 3MF file (for debugging)
    
    Returns: List of files inside the 3MF archive with sizes
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={job_id}")
        
        # Use filename (original upload name with extension)
        file_path = UPLOAD_DIR / job.filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {job.filename}")
        
        if not file_path.suffix.lower() == '.3mf':
            raise HTTPException(status_code=400, detail="Structure only available for 3MF files")
        
        structure = get_3mf_structure(file_path)
        
        return {
            "job_id": job_id,
            "job_name": job.job_name,
            **structure
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job structure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=JobListResponse)
async def list_all_jobs(db: Session = Depends(get_db)):
    """
    Get all print jobs
    
    Returns: List of all jobs with job_id, job_name, status, loop_count
    """
    try:
        job_service = JobService(db)
        jobs = job_service.get_all_jobs()
        
        return JobListResponse(
            total_count=len(jobs),
            jobs=jobs
        )
    except Exception as e:
        logger.error(f"Error fetching jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_details(job_id: int, db: Session = Depends(get_db)):
    """
    Get specific job details by job_id
    
    Returns: job_id, job_name, status, loop_count, current_loop
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={job_id}")
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{job_id}")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Delete job by job_id"""
    try:
        job_service = JobService(db)
        success = job_service.delete_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={job_id}")
        
        return {"message": f"Job deleted: job_id={job_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/gcode")
async def get_job_gcode(
    job_id: int, 
    plate: int = 1, 
    max_lines: int = 5000,
    structured: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get G-code content from uploaded 3MF file.
    
    Args:
        job_id: Job ID
        plate: Build plate number (default: 1)
        max_lines: Maximum lines to return (default: 5000, max: 50000)
        structured: If true, return parsed sections with enable/disable support
        
    Returns:
        - gcode: Array of gcode lines
        - sections: Parsed sections with subSections (if structured=true)
        - total_lines: Total lines in file
        - plates: Available plate files
        - selected_plate: The plate that was extracted
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={job_id}")
        
        file_path = UPLOAD_DIR / job.filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {job.filename}")
        
        suffix = file_path.suffix.lower()
        
        if suffix != '.3mf':
            raise HTTPException(
                status_code=400, 
                detail="G-code extraction only available for 3MF files"
            )
        
        # Limit max_lines to prevent memory issues
        max_lines = min(max_lines, 50000)
        
        result = extract_gcode_from_3mf(file_path, plate_num=plate, max_lines=max_lines)
        
        if result.get('error'):
            raise HTTPException(status_code=500, detail=result['error'])
        
        response = {
            "job_id": job_id,
            "job_name": job.job_name,
            **result
        }
        
        # Add structured sections if requested
        if structured and result.get('gcode'):
            sections_data = parse_gcode_sections(result['gcode'])
            response['sections'] = sections_data['sections']
            response['printBodyStart'] = sections_data['printBodyStart']
            response['endGcodeStart'] = sections_data['endGcodeStart']
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job gcode: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Pydantic models for section modification
class SectionModification(BaseModel):
    sectionId: str
    enabled: bool
    startLine: int
    endLine: int


class ModifyGcodeRequest(BaseModel):
    modifications: List[SectionModification]
    plate: int = 1


@router.patch("/{job_id}/gcode/sections")
async def modify_gcode_sections(
    job_id: int,
    request: ModifyGcodeRequest,
    db: Session = Depends(get_db)
):
    """
    Apply section modifications (enable/disable) to G-code.
    Disabled sections are commented out with ;[DISABLED] prefix.
    
    This creates a modified copy of the 3MF file with the changes applied.
    
    Args:
        job_id: Job ID
        request: Modifications to apply
        
    Returns:
        - success: Boolean
        - modified_file: Path to modified file
        - changes_applied: Number of sections modified
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={job_id}")
        
        file_path = UPLOAD_DIR / job.filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {job.filename}")
        
        suffix = file_path.suffix.lower()
        
        if suffix != '.3mf':
            raise HTTPException(
                status_code=400, 
                detail="G-code modification only available for 3MF files"
            )
        
        # Extract current gcode
        result = extract_gcode_from_3mf(file_path, plate_num=request.plate, max_lines=999999)
        
        if result.get('error'):
            raise HTTPException(status_code=500, detail=result['error'])
        
        lines = result['gcode']
        selected_plate = result['selected_plate']
        
        # Count disabled sections
        disabled_count = sum(1 for m in request.modifications if not m.enabled)
        
        if disabled_count == 0:
            return {
                "success": True,
                "message": "No modifications needed - all sections enabled",
                "changes_applied": 0
            }
        
        # Apply modifications
        modifications = [m.dict() for m in request.modifications]
        modified_lines = apply_section_modifications(lines, modifications)
        
        # Create modified 3MF file
        modified_content = '\n'.join(modified_lines)
        
        # Create new filename with _modified suffix
        original_name = file_path.stem
        modified_filename = f"{original_name}_modified.3mf"
        modified_path = UPLOAD_DIR / modified_filename
        
        # Copy original 3MF and replace the gcode file
        import shutil
        shutil.copy(file_path, modified_path)
        
        # Update the gcode inside the 3MF (which is a ZIP)
        with zipfile.ZipFile(modified_path, 'a') as zf:
            # Remove old gcode file
            # Note: ZipFile doesn't support deletion, so we need to recreate
            pass
        
        # Recreate the 3MF with modified gcode
        temp_path = UPLOAD_DIR / f"{original_name}_temp.3mf"
        
        with zipfile.ZipFile(file_path, 'r') as zf_in:
            with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zf_out:
                for item in zf_in.namelist():
                    if item == selected_plate:
                        # Write modified gcode
                        zf_out.writestr(item, modified_content.encode('utf-8'))
                    else:
                        # Copy other files as-is
                        zf_out.writestr(item, zf_in.read(item))
        
        # Replace the modified file
        if modified_path.exists():
            modified_path.unlink()
        temp_path.rename(modified_path)
        
        logger.info(f"✅ Modified G-code saved: {modified_filename} ({disabled_count} sections disabled)")
        
        return {
            "success": True,
            "message": f"G-code modified successfully - {disabled_count} section(s) disabled",
            "modified_file": modified_filename,
            "changes_applied": disabled_count,
            "original_file": job.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error modifying gcode sections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/print-preview")
async def get_print_preview(job_id: int, db: Session = Depends(get_db)):
    """
    Get step-by-step preview of what the printer will do when printing this job.
    
    Parses the 3MF file to extract:
    - Print settings (temps, speeds, etc)
    - Automation actions (bed leveling, flow calibration, etc)
    - Estimated time and filament usage
    
    Returns a structured list of steps the printer will perform.
    """
    try:
        from src.utils.gcode_parser import parse_file_metadata
        
        job_service = JobService(db)
        job = job_service.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: job_id={job_id}")
        
        file_path = UPLOAD_DIR / job.filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {job.filename}")
        
        # Parse file metadata
        metadata = parse_file_metadata(file_path)
        
        # Build step-by-step preview
        steps = []
        step_num = 1
        
        # Step 1: Machine Start
        steps.append({
            "step": step_num,
            "phase": "preparation",
            "action": "Machine Start",
            "description": "Printer initializes, resets settings, turns on logo lamp",
            "gcode_refs": ["M17", "M960 S5 P1", "G90"],
            "icon": "🔧"
        })
        step_num += 1
        
        # Step 2: Heating
        if metadata.get('bed_temp') or metadata.get('nozzle_temp'):
            heat_desc = []
            if metadata.get('bed_temp'):
                heat_desc.append(f"Bed: {metadata['bed_temp']}°C")
            if metadata.get('nozzle_temp'):
                heat_desc.append(f"Nozzle: {metadata['nozzle_temp']}°C")
            
            steps.append({
                "step": step_num,
                "phase": "preparation", 
                "action": "Heat Bed & Nozzle",
                "description": f"Heating to target temperatures: {', '.join(heat_desc)}",
                "gcode_refs": ["M140", "M104", "M190", "M109"],
                "icon": "🔥",
                "details": {
                    "bed_temp": metadata.get('bed_temp'),
                    "nozzle_temp": metadata.get('nozzle_temp')
                }
            })
            step_num += 1
        
        # Step 3: Startup Sound (if enabled)
        steps.append({
            "step": step_num,
            "phase": "preparation",
            "action": "Startup Sound",
            "description": "Plays startup melody (M1006 commands)",
            "gcode_refs": ["M1006"],
            "icon": "🔊",
            "optional": True
        })
        step_num += 1
        
        # Step 4: Home Axes
        steps.append({
            "step": step_num,
            "phase": "calibration",
            "action": "Home All Axes",
            "description": "Moves to home position (X, Y, Z endstops)",
            "gcode_refs": ["G28"],
            "icon": "🏠"
        })
        step_num += 1
        
        # Step 5: Bed Leveling (if detected)
        if metadata.get('has_bed_leveling'):
            steps.append({
                "step": step_num,
                "phase": "calibration",
                "action": "Auto Bed Leveling",
                "description": "Probes bed at multiple points to create mesh for compensation",
                "gcode_refs": ["G29", "M420"],
                "icon": "📐",
                "estimated_time": "2-5 min"
            })
            step_num += 1
        
        # Step 6: Vibration Calibration (if detected)
        if metadata.get('has_vibration_test'):
            steps.append({
                "step": step_num,
                "phase": "calibration",
                "action": "Vibration Calibration (Input Shaper)",
                "description": "Runs resonance test to reduce ringing/ghosting at high speeds",
                "gcode_refs": ["M970", "M974"],
                "icon": "📳",
                "estimated_time": "1-2 min"
            })
            step_num += 1
        
        # Step 7: Flow Calibration (if detected)
        if metadata.get('has_flow_calibration'):
            steps.append({
                "step": step_num,
                "phase": "calibration",
                "action": "Flow Calibration",
                "description": "Calibrates dynamic extrusion compensation for accurate flow",
                "gcode_refs": ["M983", "M984"],
                "icon": "💧",
                "estimated_time": "30 sec"
            })
            step_num += 1
        
        # Step 8: Nozzle Clean (if detected)
        if metadata.get('has_clean_nozzle'):
            steps.append({
                "step": step_num,
                "phase": "preparation",
                "action": "Nozzle Wipe/Clean",
                "description": "Wipes nozzle on brush/pad to remove debris",
                "gcode_refs": ["G12", "custom wipe sequence"],
                "icon": "🧹"
            })
            step_num += 1
        
        # Step 9: Prime Line
        steps.append({
            "step": step_num,
            "phase": "preparation",
            "action": "Extrude Prime Line",
            "description": "Extrudes filament line along bed edge to prime nozzle",
            "gcode_refs": ["G1 E", "nozzle load line"],
            "icon": "📏"
        })
        step_num += 1
        
        # Step 10: Print Layers
        layer_count = metadata.get('layer_count', 'Unknown')
        est_time = metadata.get('estimated_time', 'Unknown')
        filament_g = metadata.get('filament_used_g')
        
        print_details = {
            "layer_count": layer_count,
            "layer_height": metadata.get('layer_height'),
            "filament_type": metadata.get('filament_type'),
        }
        if filament_g:
            print_details["filament_used_g"] = round(filament_g, 1)
        
        steps.append({
            "step": step_num,
            "phase": "printing",
            "action": "Print Object",
            "description": f"Printing {layer_count} layers - Estimated: {est_time}",
            "gcode_refs": ["G0/G1 moves", "M73 progress"],
            "icon": "🖨️",
            "estimated_time": est_time,
            "details": print_details
        })
        step_num += 1
        
        # Step 11: Finish Sound
        steps.append({
            "step": step_num,
            "phase": "completion",
            "action": "Finish Sound",
            "description": "Plays completion melody",
            "gcode_refs": ["M1006"],
            "icon": "🎵",
            "optional": True
        })
        step_num += 1
        
        # Step 12: Cooldown
        steps.append({
            "step": step_num,
            "phase": "completion",
            "action": "Cooldown",
            "description": "Turns off heaters, cools down bed and nozzle",
            "gcode_refs": ["M140 S0", "M104 S0", "M106 S0"],
            "icon": "❄️"
        })
        step_num += 1
        
        # Step 13: Auto Eject (if detected)
        if metadata.get('has_auto_eject'):
            steps.append({
                "step": step_num,
                "phase": "completion",
                "action": "Auto Eject Print",
                "description": "Moves bed forward to push print off for easy removal",
                "gcode_refs": ["M991 S0 P-1", "G1 Y230"],
                "icon": "📤"
            })
            step_num += 1
        
        # Step 14: Park & Disable
        steps.append({
            "step": step_num,
            "phase": "completion",
            "action": "Park & Disable Motors",
            "description": "Moves to park position, disables stepper motors",
            "gcode_refs": ["G1 X-48 Y180", "M18"],
            "icon": "🅿️"
        })
        
        return {
            "job_id": job_id,
            "job_name": job.job_name,
            "filename": job.filename,
            "metadata": {
                "estimated_time": metadata.get('estimated_time'),
                "estimated_time_seconds": metadata.get('estimated_time_seconds'),
                "layer_count": metadata.get('layer_count'),
                "layer_height": metadata.get('layer_height'),
                "filament_used_g": metadata.get('filament_used_g'),
                "filament_type": metadata.get('filament_type'),
                "bed_temp": metadata.get('bed_temp'),
                "nozzle_temp": metadata.get('nozzle_temp'),
                "slicer_name": metadata.get('slicer_name'),
                "printer_model": metadata.get('printer_model'),
            },
            "automation_detected": {
                "bed_leveling": metadata.get('has_bed_leveling', False),
                "vibration_calibration": metadata.get('has_vibration_test', False),
                "flow_calibration": metadata.get('has_flow_calibration', False),
                "nozzle_clean": metadata.get('has_clean_nozzle', False),
                "auto_eject": metadata.get('has_auto_eject', False),
            },
            "steps": steps,
            "total_steps": len(steps)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting print preview: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
