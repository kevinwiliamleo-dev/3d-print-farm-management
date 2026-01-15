"""
Job Service - Manage print jobs and slicing operations
Follows naming conventions from README.md
"""
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.db import Job, PrintSettings
from src.models.schemas import JobCreate, JobResponse
import logging
import os

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing print jobs"""

    def __init__(self, db: Session):
        self.db = db

    def create_job(self, job_create: JobCreate, filename: str) -> JobResponse:
        """
        Create new print job with upload file
        
        Args:
            job_create: Job creation data (loop_count, settings)
            filename: Original uploaded filename
            
        Returns:
            JobResponse with job_id, job_name, status
        """
        # Generate job_name from filename
        job_name = os.path.splitext(filename)[0]
        job_status = "pending"
        
        # Create job_id entry
        job_record = Job(
            job_name=job_name,
            filename=filename,
            upload_timestamp=datetime.utcnow(),
            loop_count=job_create.loop_count,
            current_loop=0,
            status=job_status,
            gcode_size_mb=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(job_record)
        self.db.commit()
        self.db.refresh(job_record)
        
        logger.info(f"Created job: job_id={job_record.job_id}, job_name={job_name}, loop_count={job_create.loop_count}")
        
        return JobResponse(
            job_id=job_record.job_id,
            job_name=job_record.job_name,
            filename=job_record.filename,
            upload_timestamp=job_record.upload_timestamp,
            gcode_size_mb=job_record.gcode_size_mb,
            loop_count=job_record.loop_count,
            current_loop=job_record.current_loop,
            status=job_record.status,
            created_at=job_record.created_at,
            updated_at=job_record.updated_at
        )

    def get_job_by_id(self, job_id: int) -> JobResponse:
        """Get job details by job_id"""
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return None
        
        return JobResponse(
            job_id=job.job_id,
            job_name=job.job_name,
            filename=job.filename,
            upload_timestamp=job.upload_timestamp,
            gcode_size_mb=job.gcode_size_mb,
            loop_count=job.loop_count,
            current_loop=job.current_loop,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at
        )

    def get_all_jobs(self) -> list:
        """Get all jobs from database"""
        jobs = self.db.query(Job).all()
        return [
            JobResponse(
                job_id=job.job_id,
                job_name=job.job_name,
                filename=job.filename,
                upload_timestamp=job.upload_timestamp,
                gcode_size_mb=job.gcode_size_mb,
                loop_count=job.loop_count,
                current_loop=job.current_loop,
                status=job.status,
                created_at=job.created_at,
                updated_at=job.updated_at
            )
            for job in jobs
        ]

    def update_job_status(self, job_id: int, job_status: str) -> bool:
        """
        Update job_status for given job_id
        
        Status values: pending, running, completed, failed
        """
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return False
        
        job.status = job_status
        job.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Updated job_status: job_id={job_id}, status={job_status}")
        return True

    def update_current_loop(self, job_id: int, loop_number: int) -> bool:
        """Update current_loop for job_id"""
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return False
        
        job.current_loop = loop_number
        job.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Updated current_loop: job_id={job_id}, current_loop={loop_number}")
        return True

    def update_gcode_size(self, job_id: int, gcode_size_mb: float) -> bool:
        """Update gcode_size_mb for generated G-code file"""
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return False
        
        job.gcode_size_mb = gcode_size_mb
        job.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Updated gcode_size_mb: job_id={job_id}, size={gcode_size_mb}MB")
        return True

    def delete_job(self, job_id: int) -> bool:
        """Delete job by job_id"""
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return False
        
        self.db.delete(job)
        self.db.commit()
        
        logger.info(f"Deleted job: job_id={job_id}")
        return True

    def is_job_complete(self, job_id: int) -> bool:
        """Check if job completed all loops"""
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return False
        
        # Job complete when current_loop >= loop_count
        return job.current_loop >= job.loop_count

    def should_repeat_job(self, job_id: int) -> bool:
        """Check if job should repeat (current_loop < loop_count)"""
        job = self.db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            return False
        
        return job.current_loop < job.loop_count
