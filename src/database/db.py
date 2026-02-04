"""
Database initialization and management
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from src.config import DATABASE_URL, DATABASE_PATH
import os

# Create database engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==================== Database Models ====================

class Job(Base):
    """
    Print job definition with file and settings information
    Following naming convention: job_id, job_name, etc
    """
    __tablename__ = "jobs"

    job_id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    gcode_size_mb = Column(Float, nullable=True)
    loop_count = Column(Integer, default=1)
    current_loop = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    print_settings = relationship("PrintSettings", back_populates="job", cascade="all, delete-orphan")
    print_history = relationship("PrintHistory", back_populates="job", cascade="all, delete-orphan")
    queue_items = relationship("Queue", back_populates="job", cascade="all, delete-orphan")


class PrintSettings(Base):
    """
    Print settings for each job
    Stores all slicing and print parameters
    """
    __tablename__ = "print_settings"

    setting_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    layer_height = Column(Float, default=0.2)
    infill_density = Column(Integer, default=15)  # 0-100%
    print_speed = Column(Integer, default=100)  # mm/s
    nozzle_temp = Column(Integer, default=220)  # °C
    bed_temp = Column(Integer, default=60)  # °C
    support_enabled = Column(Boolean, default=False)
    printer_profile = Column(String(100), default="Bambu Lab A1")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="print_settings")


class Queue(Base):
    """
    Print queue tracking
    Manages job ordering and execution status
    """
    __tablename__ = "queue"

    queue_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    printer_id = Column(String(100), default="bambu-a1-001")
    position_in_queue = Column(Integer, index=True)
    current_loop = Column(Integer, default=0)  # Start from 0, increment after each completion
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    
    # AMS (Automatic Material System) settings
    ams_slot = Column(Integer, default=0)  # Which AMS slot to use (0-3)
    ams_mapping = Column(String(100), default="")  # AMS mapping for multi-color
    use_ams = Column(Boolean, default=True)  # Whether to use AMS
    filament_already_loaded = Column(Boolean, default=False)  # Skip AMS load
    
    # Print settings (3 checkboxes only - for display, not processing)
    auto_bed_leveling = Column(Boolean, default=True)   # Enable bed leveling
    flow_calibration = Column(Boolean, default=False)   # Enable flow calibration  
    timelapse = Column(Boolean, default=False)          # Enable timelapse recording
    
    # Skip ALL preprocessing - file from slicer sent as-is
    skip_preprocessing = Column(Boolean, default=True)  # Always True - no G-code modification
    
    # Modified file path - stores the queue-specific modified 3MF file
    # This is the actual file that will be printed (with G-code modifications applied)
    queue_file_path = Column(String(500), nullable=True)  # Path to modified 3MF in queue_files/
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="queue_items")


class BucketList(Base):
    """
    Bucket List - Store jobs for later printing
    Saves all settings so user can print anytime without reconfiguring
    """
    __tablename__ = "bucket_list"

    bucket_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    printer_id = Column(String(100), default="bambu-a1-001")
    
    # AMS (Automatic Material System) settings
    ams_slot = Column(Integer, default=0)
    ams_mapping = Column(String(100), default="")
    use_ams = Column(Boolean, default=True)
    filament_already_loaded = Column(Boolean, default=False)
    
    # Print settings (3 checkboxes only)
    auto_bed_leveling = Column(Boolean, default=True)
    flow_calibration = Column(Boolean, default=False)
    timelapse = Column(Boolean, default=False)
    
    # Loop count for this bucket item
    loop_count = Column(Integer, default=1)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)  # User notes for this saved job
    
    # Relationships
    job = relationship("Job")


class PrintHistory(Base):
    """
    Complete print job history and logs
    Records all printing attempts and results
    """
    __tablename__ = "print_history"

    history_id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.job_id"), nullable=False)
    printer_id = Column(String(100), default="bambu-a1-001")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    material_used_grams = Column(Float, nullable=True)
    print_success = Column(Boolean, default=False)
    eject_time = Column(DateTime, nullable=True)
    completion_status = Column(String(255))  # success, failed, paused, etc
    error_message = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="print_history")


class Printer(Base):
    """
    Printer configuration and status
    Stores information about connected printers
    Enhanced with real-time status from MQTT
    """
    __tablename__ = "printers"

    printer_id = Column(String(100), primary_key=True, index=True)
    printer_name = Column(String(255), nullable=False)
    printer_ip = Column(String(50), nullable=True)  # IP address for LAN mode
    model = Column(String(100), default="Bambu Lab A1")
    status = Column(String(50), default="idle")  # idle, printing, paused, offline, error
    last_heartbeat = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    mqtt_connected = Column(Boolean, default=False)
    
    # Real-time print status (synced from MQTT)
    print_progress = Column(Integer, default=0)  # 0-100%
    remaining_time = Column(Integer, default=0)  # seconds
    current_file = Column(String(255), nullable=True)  # currently printing file
    
    # Temperature data (synced from MQTT)
    nozzle_temp = Column(Float, default=0.0)
    nozzle_target_temp = Column(Float, default=0.0)
    bed_temp = Column(Float, default=0.0)
    bed_target_temp = Column(Float, default=0.0)
    chamber_temp = Column(Float, default=0.0)
    
    # Error tracking (synced from MQTT)
    print_error = Column(Integer, default=0)  # Error code from printer (0 = no error)
    
    # Queue automation settings
    auto_continue = Column(Boolean, default=True)  # Auto start next job after completion
    
    # Print stage tracking (synced from MQTT)
    # stg_cur values: -1=idle, 0=printing, 1=auto bed leveling, 2=heatbed preheating, 
    # 3=sweeping XY mech mode, 4=changing filament, 5=M400 pause, 6=paused due to filament runout,
    # 7=heating hotend, 8=calibrating extrusion, 9=scanning bed surface, 10=inspecting first layer,
    # 11=identifying build plate type, 12=calibrating micro lidar, 13=homing toolhead,
    # 14=cleaning nozzle tip, 15=checking extruder temperature, 16=paused by user
    print_stage = Column(Integer, default=0)  # Current print stage from printer
    
    # A1 Tilt Kit configuration for bed cooling
    kit_enabled = Column(Boolean, default=False)  # Is Kit installed and enabled?
    kit_ip = Column(String(50), nullable=True)  # Kit IP address for control
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AMSSlotAssignment(Base):
    """
    AMS Slot Assignments
    Links filament profiles to AMS slots on each printer
    
    Synced from printer MQTT (like OrcaSlicer):
    - color: Actual color from printer (RRGGBBAA hex)
    - filament_name: Human-readable name from printer
    """
    __tablename__ = "ams_slot_assignments"

    assignment_id = Column(Integer, primary_key=True, index=True)
    printer_id = Column(String(100), nullable=False)
    slot_number = Column(Integer, nullable=False)  # 0-3 for AMS Lite
    filament_id = Column(Integer, ForeignKey("filament_profiles.filament_id"), nullable=False)
    remaining_grams = Column(Float, default=1000)  # Remaining filament in grams
    color = Column(String(10), nullable=True)  # Synced from printer (RRGGBBAA hex)
    filament_name = Column(String(255), nullable=True)  # Synced from printer
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one filament per slot per printer
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
    # Relationships
    filament = relationship("FilamentProfile")


class FilamentProfile(Base):
    """
    Filament profile database
    Stores filament characteristics for easy selection and configuration
    
    Dapat digunakan untuk:
    - Menyimpan profil filament yang dimiliki user
    - Memilih filament untuk di-apply ke slot AMS
    - Reference suhu dan karakteristik saat printing
    """
    __tablename__ = "filament_profiles"

    filament_id = Column(Integer, primary_key=True, index=True)
    
    # Basic Info
    name = Column(String(255), nullable=False)  # Nama filament, e.g., "Bambu PLA Basic - Black"
    brand = Column(String(100), nullable=False)  # Merek, e.g., "Bambu Lab", "eSUN", "Polymaker"
    material_type = Column(String(50), nullable=False)  # Jenis: PLA, PETG, ABS, TPU, ASA, etc.
    color_name = Column(String(100), nullable=True)  # Nama warna, e.g., "Matte Black"
    color_hex = Column(String(8), default="000000FF")  # RRGGBBAA format
    
    # Temperature Settings
    nozzle_temp_min = Column(Integer, default=190)  # °C
    nozzle_temp_max = Column(Integer, default=240)  # °C
    nozzle_temp_default = Column(Integer, default=220)  # Recommended temp
    bed_temp_min = Column(Integer, default=45)  # °C
    bed_temp_max = Column(Integer, default=65)  # °C
    bed_temp_default = Column(Integer, default=55)  # Recommended temp
    
    # Print Settings
    max_volumetric_speed = Column(Float, default=12.0)  # mm³/s - Max flow rate
    k_value = Column(Float, default=0.02)  # Pressure advance / K-factor
    
    # Physical Properties
    density = Column(Float, default=1.24)  # g/cm³
    diameter = Column(Float, default=1.75)  # mm (1.75 or 2.85)
    spool_weight = Column(Float, default=1000)  # grams per spool
    
    # Drying Settings
    drying_temp = Column(Integer, default=50)  # °C
    drying_time = Column(Integer, default=8)  # hours
    
    # Compatibility
    requires_enclosure = Column(Boolean, default=False)  # Butuh enclosure (ABS, ASA)
    requires_hardened_nozzle = Column(Boolean, default=False)  # Butuh nozzle hardened (CF, GF)
    
    # User Notes
    notes = Column(Text, nullable=True)  # Catatan tambahan
    purchase_link = Column(String(500), nullable=True)  # Link pembelian
    
    # Stock Management
    stock_count = Column(Integer, default=0)  # Jumlah spool yang dimiliki
    
    # Metadata
    is_active = Column(Boolean, default=True)  # Aktif/tidak digunakan
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DATABASE_PATH}")


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
