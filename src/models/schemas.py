"""
Pydantic models for API requests and responses
Following naming conventions from README
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


# ==================== Enums ====================

class JobStatusEnum(str, Enum):
    """Job status values"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PrinterStatusEnum(str, Enum):
    """Printer status values"""
    IDLE = "idle"
    PRINTING = "printing"
    OFFLINE = "offline"
    ERROR = "error"


# ==================== Print Settings ====================

class PrintAutomationSettings(BaseModel):
    """
    Simplified automation settings (3 checkboxes only)
    Settings come from slicer - these are MQTT command flags only
    """
    # Calibration options (sent via MQTT command)
    auto_bed_leveling: bool = Field(default=True, description="Enable bed leveling calibration")
    flow_calibration: bool = Field(default=False, description="Enable flow calibration")
    timelapse: bool = Field(default=False, description="Enable timelapse recording")
    
    def validate_settings(self):
        """No validation needed - simple flags"""
        return self


class PrintSettingsCreate(BaseModel):
    """Print settings for slicing configuration"""
    layer_height: float = Field(default=0.2, ge=0.1, le=0.4)
    infill_density: int = Field(default=15, ge=0, le=100)
    print_speed: int = Field(default=100, ge=20, le=200)
    nozzle_temp: int = Field(default=220, ge=150, le=260)
    bed_temp: int = Field(default=60, ge=20, le=100)
    support_enabled: bool = Field(default=False)
    printer_profile: str = Field(default="Bambu Lab A1")


class PrintSettingsResponse(PrintSettingsCreate):
    """Print settings response"""
    setting_id: int
    job_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Job Management ====================

class JobCreate(BaseModel):
    """Create a new print job"""
    job_name: str = Field(..., min_length=1, max_length=255)
    loop_count: int = Field(default=1, ge=1, le=1000)
    print_settings: Optional[PrintSettingsCreate] = None


class JobUpdate(BaseModel):
    """Update job details"""
    job_name: Optional[str] = None
    loop_count: Optional[int] = None
    status: Optional[JobStatusEnum] = None


class JobResponse(BaseModel):
    """Job response"""
    job_id: int
    job_name: str
    filename: str
    upload_timestamp: datetime
    gcode_size_mb: Optional[float] = None
    loop_count: int
    current_loop: int
    status: str
    print_settings: Optional[PrintSettingsResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """List of jobs"""
    total_count: int
    jobs: list[JobResponse]


# ==================== Queue Management ====================

class QueueItemCreate(BaseModel):
    """Add job to queue with automation settings"""
    job_id: int
    printer_id: str = Field(default="bambu-a1-001")
    
    # AMS settings
    ams_slot: int = Field(default=0, ge=0, le=255, description="AMS slot (0-3, or 255 for external)")
    use_ams: bool = Field(default=True, description="Use AMS or external spool")
    
    # Filament profile (optional - for temperature overrides)
    filament_id: Optional[int] = Field(default=None, description="Filament profile ID from inventory")
    
    # Automation settings
    automation: Optional[PrintAutomationSettings] = Field(default=None, description="Print automation settings")


class QueueItemUpdate(BaseModel):
    """Update queue item"""
    position_in_queue: Optional[int] = None
    status: Optional[str] = None
    automation: Optional[PrintAutomationSettings] = None


class QueueItemResponse(BaseModel):
    """Queue item response with automation settings"""
    queue_id: int
    job_id: int
    job_name: Optional[str] = None
    printer_id: str
    position_in_queue: int
    current_loop: int
    status: str
    
    # AMS settings
    ams_slot: int = 0
    use_ams: bool = True
    filament_already_loaded: bool = False
    
    # Simplified automation (3 settings only)
    auto_bed_leveling: bool = True
    flow_calibration: bool = False
    timelapse: bool = False
    
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QueueResponse(BaseModel):
    """Queue status response"""
    total_jobs: int
    current_job_id: Optional[int] = None
    queue_items: list[QueueItemResponse]


# ==================== Print History ====================

class PrintHistoryCreate(BaseModel):
    """Create print history entry"""
    job_id: int
    printer_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    material_used_grams: Optional[float] = None
    completion_status: str


class PrintHistoryResponse(BaseModel):
    """Print history response"""
    history_id: int
    job_id: int
    job_name: Optional[str] = None
    printer_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[float] = None
    material_used_grams: Optional[float] = None
    print_success: bool
    eject_time: Optional[datetime] = None
    completion_status: str
    error_message: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PrintHistoryListResponse(BaseModel):
    """List of print history"""
    total_count: int
    history_items: list[PrintHistoryResponse]


# ==================== Printer Management ====================

class PrinterCreate(BaseModel):
    """Register a new printer"""
    printer_id: str = Field(..., min_length=1, max_length=100)
    printer_name: str = Field(..., min_length=1, max_length=255)
    model: str = Field(default="Bambu Lab A1")


class PrinterUpdate(BaseModel):
    """Update printer details"""
    printer_name: Optional[str] = None
    status: Optional[PrinterStatusEnum] = None
    is_active: Optional[bool] = None


class PrinterResponse(BaseModel):
    """Printer response"""
    printer_id: str
    printer_name: str
    model: str
    status: str
    last_heartbeat: Optional[datetime] = None
    is_active: bool
    mqtt_connected: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PrinterListResponse(BaseModel):
    """List of printers"""
    total_count: int
    printers: list[PrinterResponse]


# ==================== File Slicing ====================

class SlicingSettingsRequest(BaseModel):
    """Slicing request with custom settings"""
    job_name: str = Field(..., min_length=1, max_length=255)
    loop_count: int = Field(default=1, ge=1, le=1000)
    layer_height: float = Field(default=0.2, ge=0.1, le=0.4)
    infill_density: int = Field(default=15, ge=0, le=100)
    print_speed: int = Field(default=100, ge=20, le=200)
    nozzle_temp: int = Field(default=220, ge=150, le=260)
    bed_temp: int = Field(default=60, ge=20, le=100)
    support_enabled: bool = Field(default=False)


class SlicingProgressResponse(BaseModel):
    """Slicing progress response"""
    job_id: int
    status: str
    progress_percent: int
    message: str
    gcode_path: Optional[str] = None
    gcode_size_mb: Optional[float] = None


class SlicingCompleteResponse(BaseModel):
    """Slicing complete response"""
    job_id: int
    job_name: str
    gcode_path: str
    gcode_size_mb: float
    slicing_time_seconds: float
    status: str


# ==================== Error Response ====================

class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None


# ==================== Status Response ====================

class SystemStatusResponse(BaseModel):
    """System status overview"""
    status: str
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_printers: int
    active_printers: int
    queue_length: int
    mqtt_connected: bool
