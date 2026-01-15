# 3D Print Farm Management System - Architecture Documentation

## Project Overview

A comprehensive 3D Print Farm Management System designed for Bambu Lab printers (primarily A1 series). The system provides:
- File upload and job management
- Print queue with FIFO ordering
- Real-time printer monitoring via MQTT
- G-code preprocessing with customizable templates
- AMS (Automatic Material System) integration
- FTPS direct file uploads to printers
- WebSocket-based live status updates
- Camera streaming support
- Print history and statistics

---

## Project Structure

```
cooking-ai-agent/
├── src/                    # Main source code
│   ├── main.py             # FastAPI application entry point
│   ├── config.py           # Configuration settings
│   ├── api/                # REST API endpoints
│   ├── services/           # Business logic services
│   ├── database/           # Database models and schema
│   ├── models/             # Pydantic schemas
│   └── utils/              # Utility functions
├── frontend/               # React frontend (separate package)
├── data/                   # Runtime data storage
│   ├── uploads/            # Uploaded 3MF/STL files
│   ├── queue_files/        # Modified files for queue items
│   ├── 3mf_output/         # Output folder for processed files
│   ├── gcode/              # G-code files
│   └── farm.db             # SQLite database
├── logs/                   # Application logs
├── scripts/                # Utility scripts
├── tests/                  # Test files
└── docs/                   # Documentation
```

---

## Core Files

### Entry Point

#### `src/main.py`
**Purpose**: FastAPI application entry point and server configuration

**Key Components**:
- `lifespan()` - Async context manager for startup/shutdown
- FastAPI app creation with CORS middleware
- Router registration for all API endpoints
- Static file serving for uploads

**Dependencies**:
- FastAPI, CORSMiddleware
- `src.config` - Configuration settings
- `src.database` - Database initialization
- `src.services.bambu_service` - MQTT client initialization
- All API routers

**Startup Flow**:
1. Configure logging
2. Set main event loop for WebSocket broadcasts
3. Initialize database (`init_db()`)
4. Initialize Bambu MQTT client for real-time communication
5. Register all API routers

### Configuration

#### `src/config.py`
**Purpose**: Centralized configuration management

**Key Settings**:
| Category | Settings |
|----------|----------|
| **Paths** | `BASE_DIR`, `DATA_DIR`, `UPLOAD_DIR`, `GCODE_DIR`, `QUEUE_FILES_DIR`, `OUTPUT_DIR` |
| **API** | `API_TITLE`, `API_VERSION`, `HOST`, `PORT` |
| **Database** | `DATABASE_URL`, `DATABASE_PATH` |
| **Bambu Lab** | `BAMBU_PRINTER_IP`, `BAMBU_ACCESS_CODE`, `BAMBU_SERIAL` |
| **MQTT** | `MQTT_BROKER`, `MQTT_PORT`, `MQTT_KEEPALIVE` |
| **Features** | `ENABLE_AUTO_EJECT`, `ENABLE_MQTT` |

**Dependencies**:
- `pathlib.Path`
- `python-dotenv` for `.env` file support

---

## API Layer (`src/api/`)

### Job Management

#### `src/api/jobs.py`
**Purpose**: Handle file upload and job CRUD operations

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/jobs/upload` | Upload 3MF/STL file and create job |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/jobs/{job_id}` | Get job details |
| `GET` | `/api/jobs/{job_id}/metadata` | Get print metadata (time, filament, etc.) |
| `GET` | `/api/jobs/{job_id}/thumbnail` | Get model thumbnail image |
| `GET` | `/api/jobs/{job_id}/structure` | Get 3MF internal file structure |
| `GET` | `/api/jobs/{job_id}/gcode` | Get G-code content with sections |
| `DELETE` | `/api/jobs/{job_id}` | Delete job |
| `POST` | `/api/jobs/upload-direct/{job_id}/print` | Direct FTPS upload and print |

**Dependencies**:
- `src.services.job_service.JobService`
- `src.utils.gcode_parser` - Metadata extraction
- `src.models.schemas` - Response models

---

### Queue Management

#### `src/api/queue.py`
**Purpose**: Print queue management with automation settings

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/queue/add` | Add job to queue with settings |
| `GET` | `/api/queue/{printer_id}` | Get queue for printer |
| `GET` | `/api/queue/{printer_id}/status` | Get queue statistics |
| `POST` | `/api/queue/{queue_id}/start` | Start printing queue item |
| `POST` | `/api/queue/{queue_id}/complete` | Mark as completed |
| `POST` | `/api/queue/{queue_id}/remove` | Remove from queue |
| `PUT` | `/api/queue/{queue_id}/position` | Update queue position |
| `GET` | `/api/queue/{queue_id}/details` | Get detailed settings |

**Key Request Models**:
```python
class AddToQueueRequest:
    job_id: int
    printer_id: str
    preset_id: Optional[int]          # Load settings from preset
    ams_slot: int = 0
    use_ams: bool = True
    filament_already_loaded: bool = False
    use_template_mode: bool = True    # Use optimized templates
    
    # Calibration toggles
    auto_bed_leveling: bool = True
    flow_calibration: bool = True
    vibration_test: bool = False
    clean_nozzle: bool = True
    wipe_nozzle: bool = True
    nozzle_load_line: bool = True
    
    # Automation
    auto_eject: bool = False
    cooldown_temp: int = 32
    timelapse: bool = False
    
    # Quick Start (FactorianDesigns optimization)
    quick_start: bool = True
    preheat_offset: int = 20
    pre_extrude: bool = True
```

**Dependencies**:
- `src.services.queue_service.QueueService`
- `src.database.db.PrintPreset`

---

### Printer Management

#### `src/api/printers.py`
**Purpose**: Printer registration and status management

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/printers` | Register new printer |
| `GET` | `/api/printers` | List all printers |
| `GET` | `/api/printers/{printer_id}` | Get printer details |
| `PATCH` | `/api/printers/{printer_id}/status` | Update printer status |
| `PATCH` | `/api/printers/{printer_id}/mqtt` | Update MQTT status |
| `POST` | `/api/printers/{printer_id}/reconnect` | Force MQTT reconnection |
| `POST` | `/api/printers/{printer_id}/refresh` | Refresh status via MQTT |
| `GET` | `/api/printers/{printer_id}/online` | Check online status |
| `GET` | `/api/printers/{printer_id}/idle` | Check idle status |

**Dependencies**:
- `src.services.printer_service.PrinterService`
- `src.services.discovery_service` - Network discovery

---

### Print Control

#### `src/api/print_control.py`
**Purpose**: Printing workflow control (start, pause, resume, cancel)

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/print-control/{printer_id}/start-print` | Start next job in queue |
| `POST` | `/api/print-control/{printer_id}/complete-print` | Handle print completion |
| `POST` | `/api/print-control/{printer_id}/pause` | Pause current print |
| `POST` | `/api/print-control/{printer_id}/resume` | Resume paused print |
| `POST` | `/api/print-control/{printer_id}/cancel` | Cancel current print |
| `GET` | `/api/print-control/{printer_id}/status` | Get current print status |

**Dependencies**:
- `src.services.print_control_service.PrintControlService`
- `src.services.bambu_service.BambuLabMQTTClient`

---

### WebSocket

#### `src/api/websocket.py`
**Purpose**: Real-time status updates via WebSocket

**Endpoints**:
| Type | Path | Description |
|------|------|-------------|
| `WebSocket` | `/ws/status` | All printer status updates |
| `WebSocket` | `/ws/printer/{printer_id}` | Single printer updates |

**Key Features**:
- `ConnectionManager` - Manages active WebSocket connections
- Periodic status broadcasts (every 5 seconds)
- Live MQTT data integration
- Upload progress notifications

**Message Types**:
```python
{
    "type": "status_update",
    "printers": [...],
    "timestamp": 1234567890
}

{
    "type": "upload_progress",
    "progress": {"percent": 50, "bytes_sent": 1000, "total_bytes": 2000}
}
```

---

### Camera

#### `src/api/camera.py`
**Purpose**: Camera streaming from Bambu Lab printers

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/camera/snapshot` | Get single JPEG snapshot |
| `GET` | `/api/camera/snapshot/{printer_id}` | Get snapshot for specific printer |
| `GET` | `/api/camera/stream` | MJPEG video stream |

**Dependencies**:
- `bambulab.JPEGFrameStream` - Bambu camera library

---

### Templates

#### `src/api/templates_db.py`
**Purpose**: G-code template management (database-backed)

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/templates` | Get all templates by category |
| `PUT` | `/api/templates/{template_key}` | Update template |
| `POST` | `/api/templates/{template_key}/toggle` | Toggle enabled state |
| `POST` | `/api/templates/reorder` | Reorder templates |
| `POST` | `/api/templates/reset` | Reset to defaults |
| `POST` | `/api/templates/preview` | Preview generated G-code |

**Template Variables**:
| Variable | Description |
|----------|-------------|
| `{nozzle_temp}` | Nozzle temperature |
| `{bed_temp}` | Bed temperature |
| `{filament_type}` | Filament type (PLA, PETG, etc.) |
| `{ams_slot}` | AMS slot number |
| `{preheat_offset}` | Preheat offset value |
| `{cooldown_temp}` | Cooldown temperature for auto-eject |

---

### Presets

#### `src/api/presets.py`
**Purpose**: Print preset management (saved automation configurations)

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/presets` | Get all presets |
| `GET` | `/api/presets/default` | Get default preset |
| `GET` | `/api/presets/{preset_id}` | Get specific preset |
| `POST` | `/api/presets` | Create new preset |
| `PUT` | `/api/presets/{preset_id}` | Update preset |
| `DELETE` | `/api/presets/{preset_id}` | Delete preset |
| `POST` | `/api/presets/{preset_id}/set-default` | Set as default |
| `POST` | `/api/presets/create-defaults` | Create default presets |

---

### Filaments

#### `src/api/filaments.py`
**Purpose**: Filament profile management and AMS slot assignment

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/filaments` | Get all filament profiles |
| `GET` | `/api/filaments/materials` | Get unique material types |
| `GET` | `/api/filaments/brands` | Get unique brands |
| `GET` | `/api/filaments/{filament_id}` | Get filament details |
| `POST` | `/api/filaments` | Create filament profile |
| `PUT` | `/api/filaments/{filament_id}` | Update filament |
| `DELETE` | `/api/filaments/{filament_id}` | Soft delete filament |
| `POST` | `/api/filaments/{filament_id}/apply-to-slot` | Apply to AMS slot |

---

### Printer Files

#### `src/api/printer_files.py`
**Purpose**: SD card file management via FTPS

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/printer-files/list` | List files on SD card |
| `POST` | `/api/printer-files/print/{filename}` | Print from SD card |
| `DELETE` | `/api/printer-files/{filename}` | Delete file from SD card |

---

### Other API Files

#### `src/api/history.py`
- Print history queries and statistics

#### `src/api/bucket_list.py`
- "Bucket List" - Save jobs for later printing with settings preserved

---

## Service Layer (`src/services/`)

### Bambu MQTT Service

#### `src/services/bambu_service.py`
**Purpose**: Core MQTT communication with Bambu Lab printers

**Key Classes**:

```python
class BambuLabMQTTClient:
    """MQTT client for Bambu Lab printer communication"""
    
    # Connection modes
    - LAN Mode: Direct connection to printer IP
    - Cloud Mode: Via mqtt.bambulab.com
    
    # Topics
    TOPIC_STATUS = "device/{printer_id}/report"
    TOPIC_COMMAND = "device/{printer_id}/request"
    
    # Key methods
    def connect() -> bool
    def disconnect() -> bool
    def start_print_from_sd(filename, ams_slot, ...)
    def pause_print()
    def resume_print()
    def cancel_print()
    def send_print_file_direct(file_path)
```

**Features**:
- Auto-reconnection with exponential backoff
- Connection state management (SocketState, ApiState)
- Real-time temperature and progress tracking
- AMS status monitoring
- Database sync for frontend updates
- Heartbeat for connection health

**Global Functions**:
```python
def get_bambu_client() -> BambuLabMQTTClient
def get_bambu_mqtt_client() -> BambuLabMQTTClient
def initialize_bambu_client(printer_id, printer_ip, access_code, use_lan_mode)
def shutdown_bambu_client()
```

---

### Queue Service

#### `src/services/queue_service.py`
**Purpose**: Print queue business logic

**Key Methods**:
```python
class QueueService:
    def add_job_to_queue(job_id, printer_id, loop_count, **settings)
    def get_printer_queue(printer_id) -> list
    def get_queue_status(printer_id) -> dict
    def start_queue_job(queue_id) -> bool
    def complete_queue_job(queue_id) -> bool
    def remove_from_queue(queue_id, delete_file) -> dict
    def update_queue_position(queue_id, new_position) -> bool
```

**Queue File Creation Flow**:
1. Copy source 3MF from uploads to queue_files
2. Apply G-code modifications based on settings
3. Store modified file path in database

---

### Job Service

#### `src/services/job_service.py`
**Purpose**: Job CRUD operations

**Key Methods**:
```python
class JobService:
    def create_job(job_create, filename) -> JobResponse
    def get_job_by_id(job_id) -> JobResponse
    def get_all_jobs() -> list
    def update_job_status(job_id, status) -> bool
    def delete_job(job_id) -> bool
```

---

### Printer Service

#### `src/services/printer_service.py`
**Purpose**: Printer registration and status management

**Key Methods**:
```python
class PrinterService:
    def create_printer(printer_id, printer_name) -> dict
    def get_printer_by_id(printer_id) -> dict
    def get_all_printers() -> list
    def update_printer_status(printer_id, status) -> bool
    def update_mqtt_connection(printer_id, connected) -> bool
    def is_printer_online(printer_id) -> bool
    def is_printer_idle(printer_id) -> bool
```

---

### Print Control Service

#### `src/services/print_control_service.py`
**Purpose**: Orchestrate printing workflow

**Key Methods**:
```python
class PrintControlService:
    def start_next_job(printer_id) -> bool
    def handle_print_completion(printer_id) -> bool
    def pause_current_print() -> bool
    def resume_current_print() -> bool
    def cancel_current_print() -> bool
    def get_current_print_status() -> dict
```

**Dependencies**:
- `BambuLabMQTTClient` - For printer commands
- `GCodePreprocessor` - For file processing

---

### FTPS Service

#### `src/services/ftps_service.py`
**Purpose**: Direct file upload via FTPS (port 990)

**Key Classes**:
```python
class ImplicitTLS(ftplib.FTP_TLS):
    """FTP_TLS subclass for implicit SSL (Bambu printers)"""

class SimpleFTPSClient:
    """Simple FTPS client for Bambu printers"""
    def connect() -> bool
    def upload_file(local_path, remote_filename, progress_callback) -> bool
    def list_files(path) -> list
    def delete_file(remote_filename) -> bool

class BambuFTPSClient:
    """Wrapper with additional features"""
```

---

### G-code Preprocessor

#### `src/services/gcode_preprocessor.py`
**Purpose**: Modify G-code based on automation settings

**Two Modes**:
1. **Template Mode** (Recommended): Replace ALL start/end G-code with templates
2. **Section Toggle Mode** (Legacy): Comment out specific sections

**Key Classes**:
```python
@dataclass
class PrintSettings:
    use_template_mode: bool = True
    auto_bed_leveling: bool = True
    flow_calibration: bool = True
    vibration_test: bool = False
    clean_nozzle: bool = True
    auto_eject: bool = False
    quick_start: bool = True
    preheat_offset: int = 20
    pre_extrude: bool = True

@dataclass
class FilamentSettings:
    filament_type: str = "PLA"
    nozzle_temp: int = 220
    bed_temp: int = 55

class GCodePreprocessor:
    def process_gcode(gcode_content, print_settings, filament_settings) -> str
```

---

### Discovery Service

#### `src/services/discovery_service.py`
**Purpose**: Auto-discover printers on local network

**Key Functions**:
```python
def check_mqtt_status(ip_address, access_code, printer_id, timeout) -> dict
```

---

## Database Layer (`src/database/`)

### Database Schema

#### `src/database/db.py`
**Purpose**: SQLAlchemy ORM models

### Tables Overview

#### `jobs` - Print Job Definitions
| Column | Type | Description |
|--------|------|-------------|
| `job_id` | INTEGER PK | Primary key |
| `job_name` | VARCHAR(255) | Display name |
| `filename` | VARCHAR(255) | Original filename |
| `upload_timestamp` | DATETIME | Upload time |
| `gcode_size_mb` | FLOAT | G-code file size |
| `loop_count` | INTEGER | Times to print |
| `current_loop` | INTEGER | Current loop number |
| `status` | VARCHAR(50) | pending/running/completed/failed |

#### `queue` - Print Queue
| Column | Type | Description |
|--------|------|-------------|
| `queue_id` | INTEGER PK | Primary key |
| `job_id` | INTEGER FK | Reference to jobs |
| `printer_id` | VARCHAR(100) | Target printer |
| `position_in_queue` | INTEGER | FIFO position |
| `current_loop` | INTEGER | Current loop |
| `status` | VARCHAR(50) | pending/running/completed/failed |
| `ams_slot` | INTEGER | AMS slot (0-3, 254=external) |
| `ams_mapping` | VARCHAR(100) | Multi-color mapping |
| `use_ams` | BOOLEAN | Use AMS or external |
| `filament_already_loaded` | BOOLEAN | Skip AMS load |
| `use_template_mode` | BOOLEAN | Use template mode |
| `filament_id` | INTEGER FK | Filament profile reference |
| `auto_bed_leveling` | BOOLEAN | Enable bed leveling |
| `flow_calibration` | BOOLEAN | Enable flow test |
| `vibration_test` | BOOLEAN | Enable vibration test |
| `clean_nozzle` | BOOLEAN | Enable nozzle cleaning |
| `wipe_nozzle` | BOOLEAN | Enable wipe nozzle |
| `nozzle_load_line` | BOOLEAN | Enable purge line |
| `auto_eject` | BOOLEAN | Auto push-off |
| `cooldown_temp` | INTEGER | Bed temp for eject |
| `startup_sound` | BOOLEAN | Play startup sound |
| `end_sound` | BOOLEAN | Play end sound |
| `timelapse` | BOOLEAN | Enable timelapse |
| `quick_start` | BOOLEAN | Skip calibrations |
| `preheat_offset` | INTEGER | Preheat offset |
| `pre_extrude` | BOOLEAN | Pre-extrude command |
| `pre_extrude_length` | FLOAT | Extrude length (mm) |
| `queue_file_path` | VARCHAR(500) | Modified file path |

#### `printers` - Printer Registration
| Column | Type | Description |
|--------|------|-------------|
| `printer_id` | VARCHAR(100) PK | Serial number |
| `printer_name` | VARCHAR(255) | Display name |
| `printer_ip` | VARCHAR(50) | IP address |
| `model` | VARCHAR(100) | Printer model |
| `status` | VARCHAR(50) | idle/printing/paused/offline |
| `mqtt_connected` | BOOLEAN | MQTT connection state |
| `print_progress` | INTEGER | Current progress (0-100) |
| `remaining_time` | INTEGER | Seconds remaining |
| `nozzle_temp` | FLOAT | Current nozzle temp |
| `nozzle_target_temp` | FLOAT | Target nozzle temp |
| `bed_temp` | FLOAT | Current bed temp |
| `bed_target_temp` | FLOAT | Target bed temp |
| `chamber_temp` | FLOAT | Chamber temperature |

#### `print_history` - Print Logs
| Column | Type | Description |
|--------|------|-------------|
| `history_id` | INTEGER PK | Primary key |
| `job_id` | INTEGER FK | Reference to jobs |
| `printer_id` | VARCHAR(100) | Printer used |
| `start_time` | DATETIME | Print start |
| `end_time` | DATETIME | Print end |
| `duration_minutes` | FLOAT | Print duration |
| `material_used_grams` | FLOAT | Filament used |
| `print_success` | BOOLEAN | Success status |
| `completion_status` | VARCHAR(255) | Detailed status |

#### `gcode_templates` - G-code Templates
| Column | Type | Description |
|--------|------|-------------|
| `template_id` | INTEGER PK | Primary key |
| `template_key` | VARCHAR(100) | Unique key |
| `printer_model` | VARCHAR(100) | Printer-specific or NULL |
| `name` | VARCHAR(255) | Display name |
| `description` | TEXT | Description |
| `category` | VARCHAR(20) | 'start' or 'end' |
| `order` | INTEGER | Execution order |
| `enabled` | BOOLEAN | Enabled by default |
| `controllable` | BOOLEAN | User can toggle |
| `setting_key` | VARCHAR(100) | Maps to queue setting |
| `gcode` | TEXT | G-code content |

#### `filament_profiles` - Filament Database
| Column | Type | Description |
|--------|------|-------------|
| `filament_id` | INTEGER PK | Primary key |
| `name` | VARCHAR(255) | Filament name |
| `brand` | VARCHAR(100) | Brand name |
| `material_type` | VARCHAR(50) | PLA/PETG/ABS/TPU |
| `color_name` | VARCHAR(100) | Color name |
| `color_hex` | VARCHAR(8) | RRGGBBAA format |
| `nozzle_temp_min/max/default` | INTEGER | Temperature range |
| `bed_temp_min/max/default` | INTEGER | Temperature range |
| `max_volumetric_speed` | FLOAT | Max flow rate |
| `k_value` | FLOAT | Pressure advance |
| `density` | FLOAT | g/cm³ |
| `stock_count` | INTEGER | Spools owned |

#### `ams_slot_assignments` - AMS Configuration
| Column | Type | Description |
|--------|------|-------------|
| `assignment_id` | INTEGER PK | Primary key |
| `printer_id` | VARCHAR(100) | Printer reference |
| `slot_number` | INTEGER | Slot 0-3 |
| `filament_id` | INTEGER FK | Filament in slot |
| `remaining_grams` | FLOAT | Filament remaining |

#### `print_presets` - Automation Presets
| Column | Type | Description |
|--------|------|-------------|
| `preset_id` | INTEGER PK | Primary key |
| `name` | VARCHAR(100) | Preset name |
| `description` | TEXT | Description |
| `icon` | VARCHAR(10) | Emoji icon |
| `color` | VARCHAR(8) | Hex color |
| `is_default` | BOOLEAN | Default preset |
| (All automation settings) | BOOLEAN/INTEGER | Template toggles |

#### `bucket_list` - Saved Jobs
Similar to `queue` table, stores jobs for later printing with all settings preserved.

---

## Models Layer (`src/models/`)

### Pydantic Schemas

#### `src/models/schemas.py`
**Purpose**: API request/response validation

**Key Models**:
```python
class JobCreate(BaseModel):
    job_name: str
    loop_count: int = 1
    print_settings: Optional[PrintSettingsCreate]

class JobResponse(BaseModel):
    job_id: int
    job_name: str
    filename: str
    status: str
    loop_count: int
    current_loop: int

class QueueItemCreate(BaseModel):
    job_id: int
    printer_id: str
    ams_slot: int = 0
    use_ams: bool = True
    automation: Optional[PrintAutomationSettings]

class PrintAutomationSettings(BaseModel):
    auto_bed_leveling: bool = True
    flow_calibration: bool = True
    vibration_test: bool = False
    clean_nozzle: bool = True
    auto_eject: bool = False
    cooldown_temp: int = 32
```

---

## Utilities Layer (`src/utils/`)

### G-code Parser

#### `src/utils/gcode_parser.py`
**Purpose**: Parse 3MF and G-code files for metadata

**Key Functions**:
```python
def parse_gcode_metadata(gcode_content) -> Dict[str, Any]
def parse_file_metadata(file_path) -> Dict[str, Any]
def parse_3mf_metadata(file_path) -> Dict[str, Any]
def extract_3mf_thumbnail(file_path) -> Optional[bytes]
def extract_gcode_thumbnail_from_file(file_path) -> Optional[bytes]
def get_3mf_structure(file_path) -> Dict[str, Any]
def extract_gcode_from_3mf(file_path, plate_number) -> str
def parse_gcode_sections(gcode_content) -> List[Dict]
def apply_section_modifications(gcode, sections, modifications) -> str
```

**Detected Metadata**:
- Estimated print time
- Filament used (mm and grams)
- Filament type and color
- Nozzle/bed temperatures
- Layer count and height
- Slicer name and version
- Automation features (bed leveling, flow calibration, etc.)

---

## Complete Flow Documentation

### File Upload Flow

```
1. User uploads 3MF file via POST /api/jobs/upload
   ↓
2. jobs.py: upload_and_create_job()
   - Validate file extension (.3mf, .stl)
   - Save to data/uploads/
   - Create Job record in database
   ↓
3. Return JobResponse with job_id
```

### Add to Queue Flow

```
1. User adds job to queue via POST /api/queue/add
   ↓
2. queue.py: add_job_to_queue()
   - Load preset if preset_id provided
   - Validate printer exists
   ↓
3. queue_service.py: add_job_to_queue()
   - Determine queue position
   - Create modified 3MF file:
     a. Copy source file to queue_files/
     b. Apply G-code modifications based on settings
     c. Store path in queue_file_path
   - Create Queue record with all settings
   ↓
4. Return queue item with queue_id
```

### Start Print Flow

```
1. User starts print via POST /api/queue/{queue_id}/start
   ↓
2. queue.py: start_queue_job()
   - Set status to "uploading"
   - Start background task
   ↓
3. Background: run_queue_job_background()
   ↓
4. queue_service.py: start_queue_job()
   - Get queue item and job info
   - Get modified file from queue_file_path
   ↓
5. FTPS Upload (ftps_service.py)
   - Connect to printer on port 990
   - Upload file with progress tracking
   - WebSocket broadcast progress
   ↓
6. Start Print via MQTT (bambu_service.py)
   - Send project_file command with settings:
     - AMS mapping
     - Calibration flags
     - Timelapse setting
   ↓
7. Update queue status to "running"
   - Update printer status to "printing"
```

### MQTT Communication Flow

```
1. On startup: initialize_bambu_client()
   ↓
2. BambuLabMQTTClient.connect()
   - Connect to printer IP on port 8883
   - Use LAN mode credentials (bblp/access_code)
   - Enable TLS (insecure for self-signed cert)
   ↓
3. Subscribe to device/{printer_id}/report
   ↓
4. Receive status updates:
   - Parse JSON payload
   - Extract print status, progress, temperatures
   - Sync to database
   - Broadcast via WebSocket
   ↓
5. Send commands to device/{printer_id}/request:
   - pushall: Request full status
   - project_file: Start print
   - pause: Pause print
   - resume: Resume print
   - stop: Cancel print
```

### Template Application Flow

```
1. queue_service._create_modified_queue_file()
   ↓
2. Choose mode based on use_template_mode
   ↓
3a. Template Mode (Recommended):
    - Extract print layers from original G-code
    - Generate start G-code from templates (ordered)
    - Generate end G-code from templates (ordered)
    - Apply Quick Start optimizations if enabled
    - Substitute variables ({nozzle_temp}, etc.)
   ↓
3b. Section Toggle Mode (Legacy):
    - Parse section markers in G-code
    - Comment out disabled sections
    - Keep original structure
   ↓
4. Repack 3MF with modified G-code
```

---

## Dependencies Between Files

### Core Dependencies
```
main.py
├── config.py
├── database/__init__.py → db.py
└── services/bambu_service.py

All API files
├── database/__init__.py
├── models/schemas.py
└── services/*_service.py

queue_service.py
├── database/db.py (Queue, Job models)
├── utils/gcode_parser.py
├── services/gcode_preprocessor.py
└── services/bambu_service.py

bambu_service.py
├── database/db.py (for sync)
├── services/ftps_service.py
└── External: paho-mqtt

print_control_service.py
├── database/db.py
├── services/bambu_service.py
└── services/gcode_preprocessor.py
```

### Import Graph (simplified)
```
config.py → (no internal deps)
    ↓
database/db.py → config.py
    ↓
models/schemas.py → (no internal deps)
    ↓
utils/gcode_parser.py → (no internal deps)
    ↓
services/ftps_service.py → (no internal deps)
    ↓
services/gcode_preprocessor.py → database/db.py
    ↓
services/bambu_service.py → database/db.py, ftps_service.py
    ↓
services/queue_service.py → database/db.py, gcode_parser, bambu_service
    ↓
services/print_control_service.py → database/db.py, bambu_service, gcode_preprocessor
    ↓
api/*.py → services/*.py, database/db.py, models/schemas.py
    ↓
main.py → all api routers, database, bambu_service, config
```

---

## External Dependencies

### Python Packages
| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `sqlalchemy` | ORM and database |
| `pydantic` | Data validation |
| `paho-mqtt` | MQTT client |
| `python-dotenv` | Environment variables |
| `bambulab` | Bambu camera library |

### Bambu Lab Specific
- MQTT on port 8883 (TLS)
- FTPS on port 990 (Implicit TLS)
- Camera streaming (JPEG frames)

---

## Configuration Notes

### Environment Variables (.env)
```env
# Server
API_HOST=0.0.0.0
API_PORT=5000

# Bambu Lab Printer
BAMBU_PRINTER_IP=192.168.x.x
BAMBU_ACCESS_CODE=xxxxxxxx
BAMBU_SERIAL=xxxxxxxxxxx

# Features
ENABLE_AUTO_EJECT=true
ENABLE_MQTT=true
```

### Running the System
```bash
# Backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 5000

# Frontend
cd frontend && npm start
```

---

*Generated: January 2026*
*Author: 3D Print Farm Management System*
