"""
History API Routes - Handle print history queries
Follows naming conventions from README.md
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database import get_db
from src.database.db import PrintHistory, Job
from typing import Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
async def get_print_history(
    printer_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get print history with optional filters
    
    - **printer_id**: Filter by specific printer
    - **limit**: Maximum number of records (default 50)
    - **days**: History period in days (default 30)
    """
    try:
        # Calculate date range
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query
        query = db.query(PrintHistory).filter(
            PrintHistory.created_at >= start_date
        )
        
        if printer_id:
            query = query.filter(PrintHistory.printer_id == printer_id)
        
        # Order by most recent first
        query = query.order_by(PrintHistory.created_at.desc()).limit(limit)
        
        history_items = query.all()
        
        # Build response with job names
        result = []
        for item in history_items:
            job = db.query(Job).filter(Job.job_id == item.job_id).first()
            job_name = job.job_name if job else f"Job #{item.job_id}"
            
            result.append({
                "history_id": item.history_id,
                "job_id": item.job_id,
                "job_name": job_name,
                "printer_id": item.printer_id,
                "start_time": item.start_time.isoformat() if item.start_time else None,
                "end_time": item.end_time.isoformat() if item.end_time else None,
                "duration_minutes": item.duration_minutes,
                "material_used_grams": item.material_used_grams,
                "print_success": item.print_success,
                "eject_time": item.eject_time.isoformat() if item.eject_time else None,
                "completion_status": item.completion_status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })
        
        return {
            "history": result,
            "total": len(result),
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_history_stats(
    printer_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics from print history
    
    Returns: total_prints, successful_prints, failed_prints,
             total_duration_hours, total_material_kg
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Build base query
        query = db.query(PrintHistory).filter(
            PrintHistory.created_at >= start_date
        )
        
        if printer_id:
            query = query.filter(PrintHistory.printer_id == printer_id)
        
        all_history = query.all()
        
        # Calculate statistics
        total_prints = len(all_history)
        successful_prints = sum(1 for h in all_history if h.print_success)
        failed_prints = total_prints - successful_prints
        total_duration_minutes = sum(h.duration_minutes or 0 for h in all_history)
        total_material_grams = sum(h.material_used_grams or 0 for h in all_history)
        
        # Success rate
        success_rate = (successful_prints / total_prints * 100) if total_prints > 0 else 0
        
        # Average print duration
        avg_duration = (total_duration_minutes / total_prints) if total_prints > 0 else 0
        
        return {
            "period_days": days,
            "total_prints": total_prints,
            "successful_prints": successful_prints,
            "failed_prints": failed_prints,
            "success_rate": round(success_rate, 1),
            "total_duration_hours": round(total_duration_minutes / 60, 1),
            "average_duration_minutes": round(avg_duration, 1),
            "total_material_grams": round(total_material_grams, 1),
            "total_material_kg": round(total_material_grams / 1000, 2),
        }
        
    except Exception as e:
        logger.error(f"Error getting history stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{history_id}")
async def get_history_detail(history_id: int, db: Session = Depends(get_db)):
    """Get detailed information for specific history entry"""
    try:
        history_item = db.query(PrintHistory).filter(
            PrintHistory.history_id == history_id
        ).first()
        
        if not history_item:
            raise HTTPException(status_code=404, detail="History entry not found")
        
        job = db.query(Job).filter(Job.job_id == history_item.job_id).first()
        
        return {
            "history_id": history_item.history_id,
            "job_id": history_item.job_id,
            "job_name": job.job_name if job else None,
            "printer_id": history_item.printer_id,
            "start_time": history_item.start_time,
            "end_time": history_item.end_time,
            "duration_minutes": history_item.duration_minutes,
            "material_used_grams": history_item.material_used_grams,
            "print_success": history_item.print_success,
            "eject_time": history_item.eject_time,
            "completion_status": history_item.completion_status,
            "notes": history_item.notes if hasattr(history_item, 'notes') else None,
            "created_at": history_item.created_at,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
