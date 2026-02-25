"""
Configuration settings for 3D Print Farm Management System
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
GCODE_DIR = DATA_DIR / "gcode"
QUEUE_FILES_DIR = DATA_DIR / "queue_files"  # Modified files for queue items
OUTPUT_DIR = DATA_DIR / "3mf_output"  # Output folder for modified 3MF files
LOG_DIR = BASE_DIR / "logs"
DB_DIR = DATA_DIR

# Ensure directories exist
for dir_path in [DATA_DIR, UPLOAD_DIR, GCODE_DIR, QUEUE_FILES_DIR, OUTPUT_DIR, LOG_DIR, DB_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# FastAPI Settings
API_TITLE = "3D Print Farm Management System"
API_VERSION = "1.0.0"
API_DESCRIPTION = "API for managing Bambu Lab 3D printer farm with automated queue management"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Server Settings
HOST = os.getenv("API_HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", 8000))
RELOAD = os.getenv("RELOAD", "true").lower() == "true"

# Database Settings
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_DIR}/farm.db")
DATABASE_PATH = str(DB_DIR / "farm.db")

# File Upload Settings
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", 500))
ALLOWED_MODEL_EXTENSIONS = [".3mf", ".stl"]
ALLOWED_GCODE_EXTENSIONS = [".gcode", ".g", ".gc"]

# OrcaSlicer Settings
ORCA_SLICER_PATH = os.getenv("ORCA_SLICER_PATH", "orca-slicer")
DEFAULT_PRINTER_PROFILE = "Bambu Lab A1"
DEFAULT_LAYER_HEIGHT = float(os.getenv("DEFAULT_LAYER_HEIGHT", 0.2))
DEFAULT_INFILL_DENSITY = int(os.getenv("DEFAULT_INFILL_DENSITY", 15))
SLICING_TIMEOUT_SECONDS = int(os.getenv("SLICING_TIMEOUT_SECONDS", 300))

# Bambu Lab Settings
BAMBU_USERNAME = os.getenv("BAMBU_USERNAME", "")
BAMBU_PASSWORD = os.getenv("BAMBU_PASSWORD", "")
BAMBU_PRINTER_ID = os.getenv("BAMBU_PRINTER_ID", "")
BAMBU_PRINTER_IP = os.getenv("BAMBU_PRINTER_IP", "")
BAMBU_ACCESS_CODE = os.getenv("BAMBU_ACCESS_CODE", "")
# Serial number for MQTT: prefer BAMBU_SERIAL, fallback to BAMBU_PRINTER_ID
BAMBU_SERIAL = os.getenv("BAMBU_SERIAL", "") or BAMBU_PRINTER_ID
BAMBU_REGION = os.getenv("BAMBU_REGION", "us")

# MQTT Settings - For local LAN mode, use printer IP as broker
# For cloud mode, use mqtt.bambulab.com
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt.bambulab.com")
MQTT_LOCAL_BROKER = BAMBU_PRINTER_IP  # Direct connection to printer
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", 60))

# API Settings
API_TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT_SECONDS", 30))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

# Logging Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Feature Flags
ENABLE_AUTO_EJECT = os.getenv("ENABLE_AUTO_EJECT", "true").lower() == "true"
ENABLE_MQTT = os.getenv("ENABLE_MQTT", "true").lower() == "true"
ENABLE_ORCA_INTEGRATION = os.getenv("ENABLE_ORCA_INTEGRATION", "true").lower() == "true"

# Queue Settings
QUEUE_CHECK_INTERVAL_SECONDS = int(os.getenv("QUEUE_CHECK_INTERVAL_SECONDS", 5))
AUTO_START_NEXT_JOB = os.getenv("AUTO_START_NEXT_JOB", "true").lower() == "true"

# Print Settings Defaults
DEFAULT_PRINT_SETTINGS = {
    "layer_height": DEFAULT_LAYER_HEIGHT,
    "infill_density": DEFAULT_INFILL_DENSITY,
    "print_speed": 100,
    "nozzle_temp": 220,
    "bed_temp": 60,
    "support_enabled": False,
}
