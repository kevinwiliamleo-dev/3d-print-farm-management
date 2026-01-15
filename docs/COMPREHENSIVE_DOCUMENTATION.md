# 3D Print Farm Management System - Comprehensive Documentation

**Last Updated**: January 7, 2026
**Version**: 1.0.0
**Author**: Development Team

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Quick Start](#2-quick-start)
3. [Architecture](#3-architecture)
4. [Database Schema](#4-database-schema)
5. [API Reference](#5-api-reference)
6. [Frontend Components](#6-frontend-components)
7. [Services & Business Logic](#7-services--business-logic)
8. [G-Code Template System](#8-g-code-template-system)
9. [Preset System](#9-preset-system)
10. [Print Flow](#10-print-flow)
11. [MQTT Communication](#11-mqtt-communication)
12. [Known Issues & Solutions](#12-known-issues--solutions)
13. [Development Guide](#13-development-guide)

---

## 1. System Overview

### 1.1 Purpose
A comprehensive 3D Print Farm Management System for Bambu Lab printers (A1 series). Enables:
- Multi-printer management
- Print queue with FIFO ordering
- Real-time monitoring via MQTT
- G-code preprocessing with templates
- AMS (Automatic Material System) integration
- Auto-eject with cooldown
- Camera streaming

### 1.2 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, Paho-MQTT |
| **Frontend** | React 19, TypeScript, TailwindCSS, Axios |
| **Database** | SQLite (farm.db) |
| **Communication** | MQTT (printer), WebSocket (frontend), FTPS (file upload) |

### 1.3 Ports
- **Backend**: http://localhost:5000
- **Frontend**: http://localhost:3000
- **Printer MQTT**: Port 8883 (TLS)
- **Printer FTPS**: Port 990

---

## 2. Quick Start

### 2.1 Prerequisites
```bash
# Python 3.11+
python --version

# Node.js 18+
node --version
```

### 2.2 Installation
```bash
cd cooking-ai-agent

# Backend dependencies
pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 2.3 Configuration
Create `.env` file:
```env
BAMBU_PRINTER_IP=192.168.4.101
BAMBU_ACCESS_CODE=your_access_code
BAMBU_SERIAL=your_serial_number
```

### 2.4 Running
```bash
# Option 1: Use start-all.bat (Windows)
.\start-all.bat

# Option 2: Manual start
# Terminal 1 - Backend
python -m uvicorn src.main:app --host 0.0.0.0 --port 5000

# Terminal 2 - Frontend
cd frontend && npm start
```

### 2.5 First Time Setup
1. Open http://localhost:3000
2. System auto-registers printer from .env
3. Upload a .3mf file
4. Select preset and add to queue
5. Start print

---

## 3. Architecture

### 3.1 Directory Structure
```
cooking-ai-agent/
├── src/                          # Backend source
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Configuration
│   ├── api/                      # REST API endpoints
│   │   ├── jobs.py               # File upload, job management
│   │   ├── queue.py              # Queue operations
│   │   ├── printers.py           # Printer registration
│   │   ├── print_control.py      # Start/pause/stop
│   │   ├── websocket.py          # Real-time updates
│   │   ├── camera.py             # Camera streaming
│   │   ├── templates.py          # G-code templates CRUD
│   │   ├── presets.py            # Print presets CRUD
│   │   ├── filaments.py          # Filament inventory
│   │   ├── ams.py                # AMS slot management
│   │   ├── printer_files.py      # SD card files
│   │   └── history.py            # Print history
│   ├── services/                 # Business logic
│   │   ├── bambu_service.py      # MQTT communication (1800+ lines)
│   │   ├── queue_service.py      # Queue logic
│   │   ├── job_service.py        # Job management
│   │   ├── printer_service.py    # Printer status
│   │   ├── print_service.py      # Print workflow
│   │   ├── ftps_service.py       # FTPS uploads
│   │   ├── gcode_preprocessor.py # G-code modification
│   │   ├── gcode_templates.py    # Template generation
│   │   └── discovery_service.py  # Printer discovery
│   ├── database/
│   │   ├── db.py                 # SQLAlchemy models
│   │   └── __init__.py           # DB exports
│   ├── models/
│   │   └── schemas.py            # Pydantic schemas
│   └── utils/
│       ├── gcode_parser.py       # 3MF/G-code parsing
│       ├── gcode_section_parser.py # Section detection
│       └── 3mf_utils.py          # 3MF manipulation
├── frontend/                     # React frontend
│   └── src/
│       ├── App.tsx               # Entry point
│       ├── api/client.ts         # API client (50+ methods)
│       └── components/
│           ├── Dashboard.tsx     # Main layout
│           ├── QueueDashboard.tsx # Upload & queue (2900+ lines)
│           ├── GCodeTemplates.tsx # Template editor
│           ├── FilamentInventory.tsx # Filament CRUD
│           ├── AmsStatusDisplay.tsx # AMS management
│           └── ...
├── data/                         # Runtime data
│   ├── farm.db                   # SQLite database
│   ├── uploads/                  # Uploaded files
│   ├── queue_files/              # Modified queue files
│   └── 3mf_output/               # Processed outputs
└── docs/                         # Documentation
```

### 3.2 Data Flow Diagram
```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │◄────►│   Backend   │◄────►│   Printer   │
│  (React)    │ HTTP │  (FastAPI)  │ MQTT │ (Bambu A1)  │
│  port:3000  │ WS   │  port:5000  │ FTPS │             │
└─────────────┘      └──────┬──────┘      └─────────────┘
                           │
                     ┌─────▼─────┐
                     │  SQLite   │
                     │ (farm.db) │
                     └───────────┘
```

---

## 4. Database Schema

### 4.1 Tables Overview

| Table | Purpose | Records |
|-------|---------|---------|
| `jobs` | Uploaded print files | Dynamic |
| `queue` | Print queue entries | Dynamic |
| `printers` | Registered printers | 1+ |
| `print_history` | Print logs | Dynamic |
| `gcode_templates` | G-code templates | 27 |
| `filament_profiles` | Filament inventory | Dynamic |
| `ams_slot_assignments` | AMS slot config | 4 per printer |
| `print_presets` | Preset profiles | 4 default |
| `bucket_list` | Saved jobs | Dynamic |

### 4.2 Table: `jobs`
```sql
CREATE TABLE jobs (
    job_id INTEGER PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    gcode_size_mb FLOAT,
    loop_count INTEGER DEFAULT 1,
    current_loop INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed
    created_at DATETIME,
    updated_at DATETIME
);
```

### 4.3 Table: `queue`
```sql
CREATE TABLE queue (
    queue_id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(job_id),
    printer_id VARCHAR(100) DEFAULT 'bambu-a1-001',
    position_in_queue INTEGER,
    current_loop INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, uploading, running, completed, failed
    
    -- AMS Settings
    ams_slot INTEGER DEFAULT 0,            -- 0-3 for AMS, 254/255 for external
    ams_mapping VARCHAR(100) DEFAULT '',   -- "[0,1,2,3]" for multi-color
    use_ams BOOLEAN DEFAULT TRUE,
    filament_already_loaded BOOLEAN DEFAULT FALSE,
    
    -- Template Mode
    use_template_mode BOOLEAN DEFAULT TRUE,  -- Replace all start/end with templates
    
    -- Filament Reference
    filament_id INTEGER REFERENCES filament_profiles(filament_id),
    
    -- Automation Settings
    auto_bed_leveling BOOLEAN DEFAULT TRUE,
    flow_calibration BOOLEAN DEFAULT TRUE,
    vibration_test BOOLEAN DEFAULT FALSE,
    clean_nozzle BOOLEAN DEFAULT TRUE,
    wipe_nozzle BOOLEAN DEFAULT TRUE,
    nozzle_load_line BOOLEAN DEFAULT TRUE,
    auto_eject BOOLEAN DEFAULT FALSE,
    cooldown_temp INTEGER DEFAULT 32,
    startup_sound BOOLEAN DEFAULT TRUE,
    end_sound BOOLEAN DEFAULT TRUE,
    timelapse BOOLEAN DEFAULT TRUE,
    
    -- Quick Start
    quick_start BOOLEAN DEFAULT TRUE,
    preheat_offset INTEGER DEFAULT 20,
    pre_extrude BOOLEAN DEFAULT TRUE,
    pre_extrude_length FLOAT DEFAULT 2.2,
    
    -- File Path
    queue_file_path VARCHAR(500),  -- Modified 3MF path
    
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME
);
```

### 4.4 Table: `printers`
```sql
CREATE TABLE printers (
    printer_id VARCHAR(100) PRIMARY KEY,
    printer_name VARCHAR(255) NOT NULL,
    printer_ip VARCHAR(50),
    model VARCHAR(100) DEFAULT 'Bambu Lab A1',
    status VARCHAR(50) DEFAULT 'idle',  -- idle, printing, paused, offline, error
    last_heartbeat DATETIME,
    is_active BOOLEAN DEFAULT TRUE,
    mqtt_connected BOOLEAN DEFAULT FALSE,
    
    -- Real-time Print Status
    print_progress INTEGER DEFAULT 0,      -- 0-100%
    remaining_time INTEGER DEFAULT 0,      -- seconds
    current_file VARCHAR(255),
    
    -- Temperature
    nozzle_temp FLOAT DEFAULT 0.0,
    nozzle_target_temp FLOAT DEFAULT 0.0,
    bed_temp FLOAT DEFAULT 0.0,
    bed_target_temp FLOAT DEFAULT 0.0,
    chamber_temp FLOAT DEFAULT 0.0,
    
    created_at DATETIME,
    updated_at DATETIME
);
```

### 4.5 Table: `gcode_templates`
```sql
CREATE TABLE gcode_templates (
    template_id INTEGER PRIMARY KEY,
    template_key VARCHAR(100) NOT NULL,    -- "machine_init", "ams_loading"
    printer_model VARCHAR(100),            -- NULL = default for all
    name VARCHAR(255) NOT NULL,            -- Display name
    description TEXT,
    category VARCHAR(20) NOT NULL,         -- 'start' or 'end'
    order INTEGER DEFAULT 1,               -- Execution order
    enabled BOOLEAN DEFAULT TRUE,
    controllable BOOLEAN DEFAULT FALSE,    -- Can be toggled in UI
    setting_key VARCHAR(100),              -- Maps to: "vibration_test", "auto_eject"
    gcode TEXT NOT NULL,                   -- Actual G-code with {variables}
    created_at DATETIME,
    updated_at DATETIME
);
```

**Template Keys (27 templates)**:
| Order | Key | Category | Controllable | Description |
|-------|-----|----------|--------------|-------------|
| 1 | `start_machine` | start | No | Machine initialization |
| 2 | `heat_bed_hotend` | start | No | Heat bed and nozzle |
| 3 | `startup_sound` | start | Yes | Play startup melody |
| 4 | `avoid_end_stop` | start | Yes | Move away from end stops |
| 5 | `reset_machine_status` | start | Yes | Reset machine state |
| 6 | `cog_noise_reduction` | start | Yes | Reduce gear noise |
| 7 | `ams_slot` | start | No | AMS slot selection |
| 8 | `flow_calibration` | start | Yes | Flow test (M983/M984) |
| 9 | `vibration_test` | start | Yes | Resonance test (M970) |
| 10 | `wipe_nozzle` | start | Yes | Wipe nozzle M109 S140 |
| 11 | `clean_nozzle` | start | Yes | Clean nozzle sequence |
| 12 | `brush_material_wipe` | start | Yes | Brush wipe |
| 13 | `final_wipe_nozzle` | start | Yes | Final nozzle wipe |
| 14 | `auto_bed_leveling` | start | Yes | G29 bed leveling |
| 15 | `home_after_wipe` | start | Yes | Home after cleaning |
| 16 | `prepare_print` | start | Yes | Prepare for print |
| 17 | `nozzle_load_line` | start | Yes | Purge line at front |
| 18 | `extrude_calibration_test` | start | Yes | Extrude test |
| 19 | `turn_off_light` | start | Yes | Turn off LED |
| 20 | `final_start` | start | Yes | Final start commands |
| 21 | `pre_extrude` | start | Yes | Quick Start pre-extrude |
| 22 | `end_print_start` | end | No | End print init |
| 23 | `timelapse` | end | Yes | Timelapse end sequence |
| 24 | `move_safe_position` | end | Yes | Move to safe Z |
| 25 | `auto_eject` | end | Yes | Auto push-off |
| 26 | `end_sound` | end | Yes | End melody |
| 27 | `end_print_final` | end | No | Final end commands |

### 4.6 Table: `print_presets`
```sql
CREATE TABLE print_presets (
    preset_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10) DEFAULT '⚡',
    color VARCHAR(8) DEFAULT '3b82f6',
    is_default BOOLEAN DEFAULT FALSE,
    
    -- Start G-code (21 settings)
    start_machine BOOLEAN DEFAULT FALSE,
    heat_bed_hotend BOOLEAN DEFAULT FALSE,
    startup_sound BOOLEAN DEFAULT FALSE,
    avoid_end_stop BOOLEAN DEFAULT FALSE,
    reset_machine_status BOOLEAN DEFAULT FALSE,
    cog_noise_reduction BOOLEAN DEFAULT FALSE,
    ams_slot BOOLEAN DEFAULT FALSE,
    flow_calibration BOOLEAN DEFAULT FALSE,
    vibration_test BOOLEAN DEFAULT FALSE,
    wipe_nozzle BOOLEAN DEFAULT FALSE,
    clean_nozzle BOOLEAN DEFAULT FALSE,
    brush_material_wipe BOOLEAN DEFAULT FALSE,
    final_wipe_nozzle BOOLEAN DEFAULT FALSE,
    auto_bed_leveling BOOLEAN DEFAULT FALSE,
    home_after_wipe BOOLEAN DEFAULT FALSE,
    prepare_print BOOLEAN DEFAULT FALSE,
    nozzle_load_line BOOLEAN DEFAULT FALSE,
    extrude_calibration_test BOOLEAN DEFAULT FALSE,
    turn_off_light BOOLEAN DEFAULT FALSE,
    final_start BOOLEAN DEFAULT FALSE,
    pre_extrude BOOLEAN DEFAULT FALSE,
    preheat_offset INTEGER DEFAULT 20,
    quick_start BOOLEAN DEFAULT FALSE,
    
    -- End G-code (6 settings)
    end_print_start BOOLEAN DEFAULT FALSE,
    timelapse BOOLEAN DEFAULT FALSE,
    move_safe_position BOOLEAN DEFAULT FALSE,
    auto_eject BOOLEAN DEFAULT FALSE,
    end_sound BOOLEAN DEFAULT FALSE,
    end_print_final BOOLEAN DEFAULT FALSE,
    cooldown_temp INTEGER DEFAULT 32,
    
    use_template_mode BOOLEAN DEFAULT TRUE,
    created_at DATETIME,
    updated_at DATETIME
);
```

**Default Presets**:
| ID | Name | Description |
|----|------|-------------|
| 1 | Quick Print | Skip calibration for fast start |
| 2 | Full Calibration | All tests enabled |
| 3 | Timelapse Mode | Optimized for timelapse |
| 4 | Silent Night | Minimal sounds, reduced noise |

### 4.7 Table: `filament_profiles`
```sql
CREATE TABLE filament_profiles (
    filament_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    material_type VARCHAR(50) NOT NULL,    -- PLA, PETG, ABS, TPU
    color_name VARCHAR(100),
    color_hex VARCHAR(8) DEFAULT '000000FF',
    
    -- Temperature
    nozzle_temp_min INTEGER DEFAULT 190,
    nozzle_temp_max INTEGER DEFAULT 240,
    nozzle_temp_default INTEGER DEFAULT 220,
    bed_temp_min INTEGER DEFAULT 45,
    bed_temp_max INTEGER DEFAULT 65,
    bed_temp_default INTEGER DEFAULT 55,
    
    -- Print Settings
    max_volumetric_speed FLOAT DEFAULT 12.0,
    k_value FLOAT DEFAULT 0.02,
    
    -- Physical
    density FLOAT DEFAULT 1.24,
    diameter FLOAT DEFAULT 1.75,
    spool_weight FLOAT DEFAULT 1000,
    
    -- Drying
    drying_temp INTEGER DEFAULT 50,
    drying_time INTEGER DEFAULT 8,
    
    -- Compatibility
    requires_enclosure BOOLEAN DEFAULT FALSE,
    requires_hardened_nozzle BOOLEAN DEFAULT FALSE,
    
    notes TEXT,
    purchase_link VARCHAR(500),
    stock_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME,
    updated_at DATETIME
);
```

### 4.8 Table: `ams_slot_assignments`
```sql
CREATE TABLE ams_slot_assignments (
    assignment_id INTEGER PRIMARY KEY,
    printer_id VARCHAR(100) NOT NULL,
    slot_number INTEGER NOT NULL,          -- 0-3 for AMS Lite
    filament_id INTEGER REFERENCES filament_profiles(filament_id),
    remaining_grams FLOAT DEFAULT 1000,
    updated_at DATETIME
);
```

---

## 5. API Reference

### 5.1 Job Endpoints (`/api/jobs`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/jobs/upload` | Upload 3MF/G-code file |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{job_id}` | Get job details |
| GET | `/api/jobs/{job_id}/metadata` | Get parsed metadata |
| GET | `/api/jobs/{job_id}/gcode` | Get G-code content |
| GET | `/api/jobs/{job_id}/print-preview` | Get print steps preview |
| GET | `/api/jobs/{job_id}/thumbnail` | Get thumbnail image |
| DELETE | `/api/jobs/{job_id}` | Delete job |

**Upload Example**:
```bash
curl -X POST http://localhost:5000/api/jobs/upload \
  -F "file=@model.3mf"
```

### 5.2 Queue Endpoints (`/api/queue`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/queue/add` | Add job to queue with settings |
| GET | `/api/queue/{printer_id}` | Get printer's queue |
| GET | `/api/queue/{printer_id}/status` | Get queue statistics |
| POST | `/api/queue/{queue_id}/start` | Start printing (async) |
| POST | `/api/queue/{queue_id}/remove` | Remove from queue |
| PUT | `/api/queue/{queue_id}/settings` | Update queue settings |
| GET | `/api/queue/{queue_id}/details` | Get full queue details |
| GET | `/api/queue/{queue_id}/download` | Download modified file |

**Add to Queue Request**:
```json
{
  "job_id": 1,
  "printer_id": "03900D5A2402051",
  "preset_id": 1,                    // NEW: Load all settings from preset
  "ams_slot": 0,
  "ams_mapping": "[0]",
  "use_ams": true,
  "filament_already_loaded": false,
  "use_template_mode": true
}
```

### 5.3 Printer Endpoints (`/api/printers`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/printers/register` | Register new printer |
| GET | `/api/printers` | List all printers |
| GET | `/api/printers/{printer_id}` | Get printer status |
| GET | `/api/printers/{printer_id}/refresh` | Force MQTT refresh |
| DELETE | `/api/printers/{printer_id}` | Remove printer |
| POST | `/api/printers/discover` | Network discovery |
| POST | `/api/printers/discover/ip` | Find by IP |

### 5.4 Print Control (`/api/print`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/print/{queue_id}/start` | Start queue job |
| POST | `/api/print/{printer_id}/pause` | Pause print |
| POST | `/api/print/{printer_id}/resume` | Resume print |
| POST | `/api/print/{printer_id}/cancel` | Cancel print |
| POST | `/api/print/{printer_id}/stop` | Stop with end sequence |

### 5.5 Template Endpoints (`/api/templates`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/templates` | List all templates |
| GET | `/api/templates/{template_id}` | Get template |
| PUT | `/api/templates/{template_id}` | Update template |
| POST | `/api/templates` | Create template |
| DELETE | `/api/templates/{template_id}` | Delete template |
| POST | `/api/templates/reset-defaults` | Reset to defaults |

### 5.6 Preset Endpoints (`/api/presets`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/presets` | List all presets |
| GET | `/api/presets/{preset_id}` | Get preset |
| POST | `/api/presets` | Create preset |
| PUT | `/api/presets/{preset_id}` | Update preset |
| DELETE | `/api/presets/{preset_id}` | Delete preset |
| POST | `/api/presets/{preset_id}/set-default` | Set as default |

### 5.7 WebSocket (`/ws/status`)

```javascript
const ws = new WebSocket('ws://localhost:5000/ws/status');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type: 'status', 'print_progress', 'temperature', etc.
  // data.printer_id: printer identifier
  // data.payload: status data
};
```

---

## 6. Frontend Components

### 6.1 Main Components

| Component | Lines | Purpose |
|-----------|-------|---------|
| `Dashboard.tsx` | ~1200 | Main layout, tab navigation |
| `QueueDashboard.tsx` | ~2930 | Upload, preview, queue, settings |
| `GCodeTemplates.tsx` | ~1744 | Template editor, preset manager |
| `FilamentInventory.tsx` | ~1353 | Filament CRUD with brand presets |
| `AmsStatusDisplay.tsx` | ~1183 | AMS slot management |
| `PrinterStatus.tsx` | ~500 | Camera, print controls |
| `PrinterCard.tsx` | ~407 | Sidebar printer display |

### 6.2 State Management

**QueueDashboard Key States**:
```typescript
// Upload workflow
const [selectedFile, setSelectedFile] = useState<File | null>(null);
const [uploadedJobId, setUploadedJobId] = useState<number | null>(null);
const [showPreview, setShowPreview] = useState(false);

// Printer & AMS
const [selectedUploadPrinter, setSelectedUploadPrinter] = useState<string>('');
const [selectedAmsSlot, setSelectedAmsSlot] = useState<number>(0);
const [amsTrays, setAmsTrays] = useState<AmsTray[]>([]);

// Preset Selection
const [selectedPresetId, setSelectedPresetId] = useState<number | null>(null);
const selectedPreset = presets.find(p => p.preset_id === selectedPresetId);

// Settings derived from preset
const useTemplateMode = selectedPreset?.use_template_mode ?? true;
const autoBedLeveling = selectedPreset?.auto_bed_leveling ?? true;
const flowCalibration = selectedPreset?.flow_calibration ?? false;
// ... all other settings from preset
```

### 6.3 API Client Methods

Located in `frontend/src/api/client.ts`:

```typescript
class PrintFarmClient {
  // Jobs
  uploadJob(file, loopCount, onProgress?): Promise<JobResponse>
  getJobMetadata(jobId): Promise<JobMetadata>
  getJobThumbnailUrl(jobId): string
  
  // Queue
  addJobToQueue(jobId, printerId, settings): Promise<QueueItemResponse>
  getQueueForPrinter(printerId): Promise<QueueItemResponse[]>
  
  // Printers
  getAllPrinters(): Promise<PrinterResponse[]>
  getPrinterById(printerId): Promise<PrinterResponse>
  
  // AMS
  getAmsTrays(printerId): Promise<AmsTrayData>
  amsLoadFilament(printerId, slot, temp?): Promise<any>
  
  // Print Control
  startQueueJob(queueId): Promise<any>
  pausePrint(printerId): Promise<any>
  
  // Presets
  getAllPresets(): Promise<PrintPreset[]>
  setDefaultPreset(presetId): Promise<void>
  
  // Templates
  getAllTemplates(): Promise<GCodeTemplate[]>
  updateTemplate(templateId, data): Promise<GCodeTemplate>
}

export const printFarmClient = new PrintFarmClient();
```

---

## 7. Services & Business Logic

### 7.1 BambuService (`bambu_service.py`)

**Purpose**: MQTT communication with Bambu Lab printers

**Key Features**:
- TLS connection to printer on port 8883
- Real-time status updates (temperature, progress, AMS)
- Command sending (start, pause, stop, AMS load)
- Auto-reconnection with exponential backoff
- Stop button with end sequence

**Important Methods**:
```python
class BambuLabMQTTClient:
    def connect() -> bool
    def disconnect()
    def send_command(command: dict) -> bool
    def start_print(filename: str, ams_mapping: list) -> bool
    def pause_print() -> bool
    def resume_print() -> bool
    def stop_print() -> bool              # Immediate stop
    def stop_print_with_end_sequence() -> bool  # Safe stop with cleanup
    def ams_load_filament(slot: int, temp: int) -> bool
    def ams_unload_filament() -> bool
    
    # Callbacks
    def on_message(client, userdata, msg)  # Handle printer responses
    def on_connect(client, userdata, flags, rc)
    def on_disconnect(client, userdata, rc)
```

**Stop with End Sequence** (NEW):
```python
async def _run_stop_end_sequence(self):
    """Run end sequence after stop"""
    # Load templates from database
    from src.api.templates_db import get_template_by_key
    
    end_print_template = get_template_by_key('end_print_start', 'Bambu Lab A1')
    move_safe_template = get_template_by_key('move_to_safe', 'Bambu Lab A1')
    
    # Send G-code commands
    self.send_gcode(end_print_template['gcode'])
    self.send_gcode(move_safe_template['gcode'])
```

### 7.2 QueueService (`queue_service.py`)

**Purpose**: Queue management and file preprocessing

**Key Methods**:
```python
class QueueService:
    def add_job_to_queue(
        job_id, printer_id, loop_count,
        ams_slot, use_ams, filament_already_loaded,
        use_template_mode,
        auto_bed_leveling, flow_calibration, vibration_test,
        clean_nozzle, wipe_nozzle, nozzle_load_line,
        startup_sound, end_sound, timelapse,
        auto_eject, cooldown_temp,
        quick_start, preheat_offset, pre_extrude,
        # NEW controllable templates
        cog_noise_reduction, brush_material_wipe, final_wipe_nozzle,
        avoid_end_stop, reset_machine_status, home_after_wipe,
        prepare_print, extrude_calibration_test, turn_off_light, final_start
    ) -> dict
    
    def _create_modified_queue_file(
        source_file, dest_file, 
        # All settings...
    ) -> str
    
    def get_printer_queue(printer_id) -> list
    def get_queue_status(printer_id) -> dict
    def remove_from_queue(queue_id) -> bool
```

### 7.3 GCodePreprocessor (`gcode_preprocessor.py`)

**Purpose**: Modify G-code based on settings

**Key Classes**:
```python
@dataclass
class PrintSettings:
    use_template_mode: bool = True
    auto_bed_leveling: bool = True
    flow_calibration: bool = False
    vibration_test: bool = False
    clean_nozzle: bool = True
    wipe_nozzle: bool = True
    nozzle_load_line: bool = True
    startup_sound: bool = True
    end_sound: bool = True
    ams_slot: int = 0
    use_ams: bool = True
    filament_already_loaded: bool = False
    auto_eject: bool = False
    cooldown_temp: int = 32
    quick_start: bool = True
    preheat_offset: int = 20
    pre_extrude: bool = True
    pre_extrude_length: float = 2.2
    # NEW controllable templates
    cog_noise_reduction: bool = True
    brush_material_wipe: bool = True
    final_wipe_nozzle: bool = True
    # ... more

class GCodePreprocessor:
    def process_gcode(gcode: str, settings: PrintSettings, filament: FilamentSettings) -> str
```

### 7.4 GCodeTemplates (`gcode_templates.py`)

**Purpose**: Generate G-code from templates

**Key Classes**:
```python
@dataclass
class TemplateSettings:
    # Maps to controllable templates
    vibration_test: bool = False
    flow_calibration: bool = True
    auto_bed_leveling: bool = True
    clean_nozzle: bool = True
    wipe_nozzle: bool = True
    nozzle_load_line: bool = True
    startup_sound: bool = True
    end_sound: bool = True
    auto_eject: bool = False
    timelapse: bool = False
    # NEW
    cog_noise_reduction: bool = True
    brush_material_wipe: bool = True
    # ... more

class GCodeTemplateGenerator:
    def generate_start_gcode(settings, variables) -> str
    def generate_end_gcode(settings, variables) -> str
    def _is_template_enabled(template, settings) -> bool
```

---

## 8. G-Code Template System

### 8.1 How Templates Work

1. Templates stored in `gcode_templates` table
2. Each template has `order` for execution sequence
3. Templates can have `controllable=True` with `setting_key`
4. When `controllable`, template is skipped if setting is False
5. Templates support variables like `{nozzle_temp}`, `{bed_temp}`

### 8.2 Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{nozzle_temp}` | Target nozzle temperature | 220 |
| `{bed_temp}` | Target bed temperature | 60 |
| `{ams_slot}` | Selected AMS slot | 0 |
| `{cooldown_temp}` | Bed temp before eject | 32 |
| `{preheat_temp}` | Preheat temperature | 200 |
| `{pre_extrude_length}` | Pre-extrude mm | 2.2 |

### 8.3 Template Mode vs Section Toggle

**Template Mode** (Recommended):
- Replace ALL start/end G-code with generated templates
- Clean, predictable output
- Full control over what's included

**Section Toggle** (Legacy):
- Comment out specific sections in original G-code
- Preserves original slicer output
- Less reliable due to marker parsing

### 8.4 Adding Custom Template

```python
# Via API
POST /api/templates
{
    "template_key": "custom_warm_up",
    "printer_model": "Bambu Lab A1",
    "name": "Custom Warm Up",
    "category": "start",
    "order": 5,
    "enabled": true,
    "controllable": true,
    "setting_key": "custom_warm_up",
    "gcode": "G28 ; Home\nG1 Z50 F3000 ; Raise"
}
```

---

## 9. Preset System

### 9.1 How Presets Work

1. User selects preset in UI
2. Frontend sends `preset_id` to backend
3. Backend loads ALL settings from preset
4. Settings passed to QueueService
5. QueueService creates modified file with those settings

### 9.2 Preset Flow (NEW Implementation)

```
Frontend                           Backend
   │                                  │
   │ Select Preset ──────────────────►│
   │                                  │
   │ Add to Queue {preset_id: 1} ────►│
   │                                  │
   │                    Load preset from DB
   │                    Get all 27+ settings
   │                                  │
   │                    Call queue_service.add_job_to_queue(
   │                        preset settings...
   │                    )
   │                                  │
   │                    Create modified 3MF
   │                    with template-based G-code
   │                                  │
   │◄──────────────── {queue_id: 1} ──│
```

### 9.3 Quick Print Preset Settings

```python
# Quick Print - Skip slow calibration
{
    "name": "Quick Print",
    "quick_start": True,          # Skip vibration + flow
    "vibration_test": False,
    "flow_calibration": False,
    "cog_noise_reduction": False,  # Skip cog noise reduction
    "brush_material_wipe": False,  # Skip brush wipe
    "final_wipe_nozzle": False,    # Skip final wipe
    "extrude_calibration_test": False,
    "home_after_wipe": False,
    "auto_bed_leveling": True,     # Keep bed leveling
    "startup_sound": True,
    "auto_eject": True,
    "cooldown_temp": 32
}
```

---

## 10. Print Flow

### 10.1 Complete Print Flow

```
1. UPLOAD FILE
   └── POST /api/jobs/upload
       └── Save to data/uploads/
       └── Create jobs record
       └── Return job_id

2. ADD TO QUEUE
   └── POST /api/queue/add {job_id, printer_id, preset_id}
       └── Load preset settings from DB
       └── Call queue_service.add_job_to_queue()
           └── Create modified 3MF file
               └── Extract original G-code
               └── Apply template mode
               └── Generate start G-code from templates
               └── Generate end G-code from templates
               └── Re-pack 3MF with new G-code
           └── Save to data/queue_files/
           └── Create queue record
       └── Return queue_id

3. START PRINT
   └── POST /api/queue/{queue_id}/start
       └── Set status = "uploading"
       └── Background task:
           └── Upload file via FTPS to printer
           └── Send MQTT print command
           └── Set status = "running"

4. MONITOR PRINT
   └── MQTT receives progress updates
       └── Update printer record (progress, temps)
       └── Broadcast via WebSocket

5. PRINT COMPLETE
   └── MQTT receives finish status
       └── Update queue status = "completed"
       └── Create print_history record
       └── If auto_eject: wait for cooldown, send eject command
```

### 10.2 Stop with End Sequence Flow

```
1. User clicks STOP button
2. Frontend: POST /api/print/{printer_id}/stop

3. Backend (bambu_service.py):
   └── stop_print_with_end_sequence()
       └── Send M400 (wait for moves)
       └── Send M981 S0 (disable camera)
       └── Load end_print_start template from DB
       └── Send template G-code
       └── Load move_to_safe template from DB
       └── Send template G-code
       └── Send MQTT stop command

4. Printer:
   └── Execute end G-code (turn off heaters, move to safe)
   └── Stop print
```

---

## 11. MQTT Communication

### 11.1 Connection

```python
MQTT_BROKER = printer_ip  # e.g., "192.168.4.101"
MQTT_PORT = 8883          # TLS
MQTT_TOPIC = f"device/{serial}/report"
```

### 11.2 Message Types

**Status Update**:
```json
{
    "print": {
        "gcode_state": "RUNNING",
        "mc_percent": 45,
        "mc_remaining_time": 3600,
        "stg_cur": 2,
        "subtask_name": "model.3mf"
    }
}
```

**Temperature Update**:
```json
{
    "print": {
        "nozzle_temper": 220.5,
        "nozzle_target_temper": 220,
        "bed_temper": 60.2,
        "bed_target_temper": 60
    }
}
```

**AMS Status**:
```json
{
    "print": {
        "ams": {
            "tray_now": 0,
            "ams_exist_bits": "1",
            "tray": [
                {"id": "0", "tray_type": "PLA", "tray_color": "FF0000FF"},
                {"id": "1", "tray_type": "PETG", "tray_color": "00FF00FF"}
            ]
        }
    }
}
```

### 11.3 Commands

**Start Print**:
```json
{
    "print": {
        "sequence_id": "123",
        "command": "project_file",
        "param": "Metadata/plate_1.gcode",
        "subtask_name": "model.3mf",
        "url": "ftp://model.3mf",
        "use_ams": true,
        "ams_mapping": [0]
    }
}
```

**Pause/Resume/Stop**:
```json
{"print": {"sequence_id": "124", "command": "pause"}}
{"print": {"sequence_id": "125", "command": "resume"}}
{"print": {"sequence_id": "126", "command": "stop"}}
```

**Send G-code**:
```json
{
    "print": {
        "sequence_id": "127",
        "command": "gcode_line",
        "param": "G28 ; Home all axes"
    }
}
```

---

## 12. Known Issues & Solutions

### 12.1 Issue: Template Save Not Working

**Symptom**: Template changes don't persist after page refresh

**Root Cause**: Frontend state caching, not reloading from database

**Solution**:
```typescript
// After save, force reload templates
const handleSaveTemplate = async () => {
    await printFarmClient.updateTemplate(templateId, data);
    await loadTemplates();  // Force reload
    setMessage({ type: 'success', text: 'Template saved!' });
};
```

### 12.2 Issue: Quick Print Still Includes Slow Templates

**Symptom**: Using Quick Print preset but G-code still has cog_noise_reduction, brush_wipe

**Root Cause**: 
1. Templates not marked as `controllable`
2. Frontend sending individual settings, not `preset_id`

**Solution**:
1. Update templates in database:
```sql
UPDATE gcode_templates SET controllable=1, setting_key='cog_noise_reduction' 
WHERE template_key='cog_noise_reduction';
```

2. Frontend sends `preset_id`:
```typescript
await printFarmClient.addJobToQueue(jobId, printerId, {
    presetId: selectedPresetId,  // Backend loads all settings from preset
    amsSlot: selectedAmsSlot,
    useAms: useAms
});
```

3. Backend loads preset settings:
```python
if request.preset_id:
    preset = db.query(PrintPreset).filter(PrintPreset.preset_id == request.preset_id).first()
    cog_noise_reduction = preset.cog_noise_reduction
    brush_material_wipe = preset.brush_material_wipe
    # ... load all settings
```

### 12.3 Issue: Stop Button Leaves Heaters On

**Symptom**: Pressing stop doesn't turn off nozzle/bed heaters

**Root Cause**: MQTT stop command is immediate, no cleanup G-code

**Solution**: Implement `stop_print_with_end_sequence()`:
```python
async def stop_print_with_end_sequence(self):
    # Run end sequence
    await self._run_stop_end_sequence()
    # Then send stop command
    self.stop_print()
    
async def _run_stop_end_sequence(self):
    # Load templates from database
    end_template = get_template_by_key('end_print_start', 'Bambu Lab A1')
    safe_template = get_template_by_key('move_to_safe', 'Bambu Lab A1')
    
    # Send G-code
    self.send_gcode(end_template['gcode'])
    self.send_gcode(safe_template['gcode'])
```

### 12.4 Issue: AMS Load Gets Stuck

**Symptom**: Filament loading hangs at 0%

**Root Cause**: Incorrect AMS slot number or MQTT command format

**Solution**:
```python
def ams_load_filament(self, slot: int, temp: int = 220):
    # Slot 0-3 for AMS Lite
    # Slot 254 = external spool
    command = {
        "print": {
            "sequence_id": str(int(time.time())),
            "command": "ams_filament_setting",
            "ams_id": 0,
            "tray_id": slot,  # Must match AMS slot
            "tray_type": "PLA",
            "nozzle_temp_min": temp,
            "nozzle_temp_max": temp
        }
    }
    self.send_command(command)
```

### 12.5 Issue: WebSocket Disconnects Frequently

**Symptom**: Real-time updates stop working

**Root Cause**: No heartbeat, connection timeout

**Solution**: Add WebSocket ping/pong:
```typescript
// WebSocketManager.ts
private setupHeartbeat() {
    setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
}
```

### 12.6 Issue: 3MF Parsing Fails

**Symptom**: "Failed to extract G-code" error

**Root Cause**: 3MF file structure different than expected

**Solution**: Handle multiple plate formats:
```python
def extract_gcode_from_3mf(file_path, plate_num=1):
    with zipfile.ZipFile(file_path, 'r') as zf:
        # Try multiple possible paths
        possible_paths = [
            f'Metadata/plate_{plate_num}.gcode',
            f'plate_{plate_num}.gcode',
            'Metadata/model.gcode',
            '3D/model.gcode'
        ]
        
        for path in possible_paths:
            if path in zf.namelist():
                return zf.read(path).decode('utf-8')
        
        raise ValueError("G-code not found in 3MF")
```

---

## 13. Development Guide

### 13.1 Adding New Template Setting

1. **Database**: Add column to `print_presets` and `queue`
```sql
ALTER TABLE print_presets ADD COLUMN new_feature BOOLEAN DEFAULT TRUE;
ALTER TABLE queue ADD COLUMN new_feature BOOLEAN DEFAULT TRUE;
```

2. **Backend Models**: Update `src/database/db.py`
```python
class PrintPreset(Base):
    new_feature = Column(Boolean, default=True)

class Queue(Base):
    new_feature = Column(Boolean, default=True)
```

3. **API Request**: Update `src/api/queue.py`
```python
class AddToQueueRequest(BaseModel):
    new_feature: bool = Field(default=True)
```

4. **Service**: Update `src/services/queue_service.py`
```python
def add_job_to_queue(self, ..., new_feature: bool = True):
    # Pass to _create_modified_queue_file
```

5. **Preprocessor**: Update `src/services/gcode_preprocessor.py`
```python
@dataclass
class PrintSettings:
    new_feature: bool = True
```

6. **Templates**: Update `src/services/gcode_templates.py`
```python
@dataclass
class TemplateSettings:
    new_feature: bool = True

def _is_template_enabled(self, template, settings):
    setting_map = {
        'new_feature': settings.new_feature,
    }
```

7. **Frontend API**: Update `frontend/src/api/client.ts`
```typescript
interface QueueSettings {
    newFeature?: boolean;
}
```

8. **Frontend UI**: Update `frontend/src/components/QueueDashboard.tsx`
```typescript
const newFeature = selectedPreset?.new_feature ?? true;
```

### 13.2 Database Migrations

```bash
# Add column
python -c "
import sqlite3
conn = sqlite3.connect('data/farm.db')
cursor = conn.cursor()
cursor.execute('ALTER TABLE print_presets ADD COLUMN new_feature BOOLEAN DEFAULT 1')
conn.commit()
conn.close()
"
```

### 13.3 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_queue_service.py -v

# Test API manually
curl http://localhost:5000/api/presets
curl http://localhost:5000/api/templates
```

### 13.4 Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check database
python -c "
import sqlite3
conn = sqlite3.connect('data/farm.db')
c = conn.cursor()
c.execute('SELECT * FROM print_presets')
for row in c.fetchall():
    print(row)
conn.close()
"
```

### 13.5 Common Commands

```bash
# Kill all processes
taskkill /IM python.exe /F
taskkill /IM node.exe /F

# Clear queue and jobs
python -c "
import sqlite3
conn = sqlite3.connect('data/farm.db')
c = conn.cursor()
c.execute('DELETE FROM queue')
c.execute('DELETE FROM jobs')
conn.commit()
"

# Delete queue files
Remove-Item -Path "data\queue_files\*" -Force

# Restart servers
.\start-all.bat
```

---

## Appendix A: File Reference

| File | Lines | Description |
|------|-------|-------------|
| `src/main.py` | ~100 | FastAPI entry |
| `src/config.py` | ~60 | Configuration |
| `src/database/db.py` | ~454 | Database models |
| `src/api/queue.py` | ~600 | Queue API |
| `src/api/jobs.py` | ~400 | Jobs API |
| `src/services/bambu_service.py` | ~1800 | MQTT client |
| `src/services/queue_service.py` | ~800 | Queue logic |
| `src/services/gcode_preprocessor.py` | ~1200 | G-code processing |
| `src/services/gcode_templates.py` | ~600 | Template generation |
| `frontend/src/components/QueueDashboard.tsx` | ~2930 | Main queue UI |
| `frontend/src/components/GCodeTemplates.tsx` | ~1744 | Template editor |
| `frontend/src/api/client.ts` | ~1100 | API client |

---

## Appendix B: Environment Variables

```env
# Printer Configuration
BAMBU_PRINTER_IP=192.168.4.101
BAMBU_ACCESS_CODE=your_access_code
BAMBU_SERIAL=03900D5A2402051

# Server Configuration
HOST=0.0.0.0
PORT=5000

# Database
DATABASE_URL=sqlite:///./data/farm.db

# Features
ENABLE_AUTO_EJECT=true
ENABLE_MQTT=true
```

---

## Appendix C: Glossary

| Term | Description |
|------|-------------|
| **AMS** | Automatic Material System - Bambu's filament changer |
| **3MF** | 3D Manufacturing Format - Contains model + G-code |
| **G-code** | Machine instructions for 3D printer |
| **MQTT** | Message protocol for printer communication |
| **FTPS** | FTP over TLS for file uploads |
| **Preset** | Saved automation settings profile |
| **Template** | G-code snippet with variables |
| **Queue** | FIFO list of pending print jobs |
| **Quick Start** | Skip calibration for faster print start |
| **Auto Eject** | Push off completed print automatically |

---

*End of Documentation*
