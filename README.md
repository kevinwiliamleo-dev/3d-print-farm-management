# 🖨️ 3D Print Farm Management System

A web-based application to manage and automate 3D printing operations on a Bambu Lab A1 Combo AMS printer farm. This system handles automatic job queuing, multi-printer management, printing history tracking, and automated slicing via OrcaSlicer.

## � Repository

- **GitHub:** https://github.com/kevinwiliamleo-dev/3d-print-farm-management
- **Visibility:** Private 🔒
- **Main Branch:** `main` (production/stable code)
- **Development Branch:** `development` (active development)

### Branches
- `main` - Production-ready stable code
- `development` - Active development and new features

### Development Workflow
All new features and changes are developed in the `development` branch. After testing and validation, changes are merged to `main` for production deployment.

**Branch Creation Date:** January 15, 2026
- Created `development` branch for ongoing feature development
- Established workflow: `development` → testing → `main`

## �📋 Project Overview

**Purpose:** Streamline 3D printing operations by automating file slicing, print job scheduling, queue management, and multi-printer control.

**Target User:** Personal 3D print farm management

**Tech Stack:**
- **Frontend:** React (Web UI with Tailwind CSS)
- **Backend:** Python (FastAPI)
- **Slicer:** OrcaSlicer (CLI-based automated slicing)
- **Database:** SQLite with SQLAlchemy ORM
- **Hardware:** Bambu Lab A1 Combo AMS
- **Deployment:** Local server

---

## ✨ Key Features

### 🔄 Automated Workflow
- **File Upload**: 3MF/STL file support
- **Auto-Slicing**: OrcaSlicer CLI integration with custom presets
- **Smart Queue**: FIFO with loop count support (print jobs multiple times)
- **Auto-Transfer**: FTPS upload to printer SD card
- **MQTT Control**: Start/stop/pause/resume commands

### 📊 Real-Time Monitoring
- **Live Status**: WebSocket-based progress tracking
- **Print Progress**: Time remaining, layer count, percentage
- **Camera Feed**: Auto-reload on tab switch
- **Dual Stop Detection**: Detects stops from both web UI and printer LCD
- **Accurate Time Display**: Proper minute-to-second conversion

### 🎛️ Printer Management
- **Multi-Printer Support**: Independent queue per printer
- **AMS Slot Control**: Assign filaments to AMS slots
- **Filament Inventory**: Track materials, colors, temperatures, stock levels
- **Auto-Eject**: Automatic bed clearing after completion
- **Status Sync**: Database + UI updates on all state changes

### 📈 History & Tracking
- Complete print history with timestamps
- Slicing settings logged per job
- Material usage tracking
- Success/failure rates
- Print duration analytics

## 🆕 Recent Updates (February 2026)

**Critical Bug Fixes (February 3, 2026):**
- ✅ **Fixed Premature Print Completion Bug**
  - **Problem**: Queue showed loop completed in 0.0 minutes (6ms after start)
  - **Root Cause**: Completion callback triggered during "uploading" status phase
  - **Solution**: 
    * Removed "uploading" from active queue status filter
    * Added 30-second minimum runtime validation
    * Track start time per queue_id: `self._last_running_time`
    * Ignore completion if print ran < 30 seconds
  - **Impact**: Accurate loop tracking and print duration logging
  - **File**: `src/services/print_control_service.py` (lines 52, 58-110, 315, 555)

- ✅ **Fixed Calibration Inverse Logic Bug**
  - **Problem**: Calibrations running despite checkboxes OFF (inverse behavior)
  - **Root Cause**: Incorrect `not` operator applied to boolean values
  - **Solution**: 
    * Removed `not` operator from `flow_cali` and `bed_leveling`
    * Changed `vibration_cali=True` → `vibration_cali=False` (always skip)
    * Updated logic: True=RUN calibration, False=SKIP calibration
  - **Impact**: Checkboxes now work correctly (OFF=skip, ON=run)
  - **File**: `src/services/print_control_service.py` (lines 298-300, 514-516)

**Major Simplification (February 2, 2026):**
- ✅ **Removed ALL Preset & Template Systems**
  - Deleted PrintPreset model & database table
  - Deleted GCodeTemplate model & database table
  - Removed /api/presets/* endpoints (323 lines)
  - Removed /api/templates_db/* endpoints (entire file)
  - Eliminated 800+ lines of G-code modification logic
- ✅ **Simplified Queue System**
  - Reduced from 40+ parameters to 7 essential parameters
  - Only 3 print checkboxes: bed_leveling, flow_calibration, timelapse
  - Only 4 AMS settings: slot, mapping, use_ams, filament_already_loaded
  - Files from slicer sent AS-IS without modification
- ✅ **Updated File Processing**
  - Changed from "modify G-code with templates" to "copy file as-is"
  - skip_preprocessing = True (always enabled)
  - Simple shutil.copy() instead of complex preprocessing
- ✅ **Documentation Updated**
  - README reflects new simplified system
  - Marked old template sections as DEPRECATED
  - Added migration notes for February 2026 changes

**Previous Updates (January 2026):**

**UI/UX Enhancements:**
- Print progress always visible (shows idle state)
- Camera auto-reload on tab switch
- Fixed time display (proper minute-to-second conversion)
- Enhanced status cards with conditional styling

**System Improvements:**
- Dual stop detection (web UI + printer LCD)
- Automatic queue status sync
- Callback system for print state transitions
- Cleaned codebase: removed 94 test/utility files (~11,646 lines)

---

## ⚙️ Print Settings (February 2026)

**MAJOR SIMPLIFICATION:** Removed all preset and template systems. Files from slicer (OrcaSlicer/BambuStudio) are sent AS-IS without any G-code modification.

### What Was Removed (February 2, 2026)

**Database Models:**
- ❌ `PrintPreset` - Print preset system (21 start templates + 6 end templates)
- ❌ `GCodeTemplate` - G-code template storage and management

**API Endpoints:**
- ❌ `/api/presets/*` - All preset management endpoints (323 lines removed)
- ❌ `/api/templates_db/*` - All template management endpoints (entire file removed)

**File Processing:**
- ❌ G-code modification engine (400+ lines removed)
- ❌ Template injection system
- ❌ Section toggle system
- ❌ 40+ automation parameters removed:
  - vibration_test, clean_nozzle, wipe_nozzle, nozzle_load_line
  - auto_eject, cooldown_temp, startup_sound, end_sound
  - quick_start, preheat_offset, pre_extrude, pre_extrude_length
  - cog_noise_reduction, brush_material_wipe, final_wipe_nozzle
  - avoid_end_stop, reset_machine_status, home_after_wipe
  - prepare_print, extrude_calibration_test, turn_off_light, final_start

### Current System (Simplified)

**Print Settings (3 Checkboxes - Working Correctly as of Feb 3, 2026):**
- ✅ **Bed Leveling** (`auto_bed_leveling`) - True=RUN, False=SKIP (normal logic)
- ✅ **Flow Calibration** (`flow_calibration`) - True=RUN, False=SKIP (normal logic)
- ✅ **Timelapse** (`timelapse`) - True=ENABLE, False=DISABLE
- ⚠️ **Note**: Vibration calibration always SKIPPED by system design

**AMS Settings (4 Fields):**
- ✅ `ams_slot` - AMS tray slot (0-3)
- ✅ `ams_mapping` - AMS mapping for multi-color
- ✅ `use_ams` - Whether to use AMS
- ✅ `filament_already_loaded` - Skip AMS load sequence

**Other:**
- ✅ `loop_count` - Number of times to print this job
- ✅ **Loop Tracking**: Accurate duration logging (min 30s validation)

### New File Processing Flow

```
1. USER UPLOADS FILE from OrcaSlicer/BambuStudio
   └─> File already has ALL settings configured in slicer

2. SYSTEM COPIES FILE AS-IS
   └─> shutil.copy(source_file, queue_file_path)
   └─> NO G-code modification
   └─> skip_preprocessing = True (always)

3. SYSTEM SENDS FILE TO PRINTER
   └─> FTPS upload to printer SD card
   └─> File printed exactly as exported from slicer

4. PRINT SETTINGS STORED FOR DISPLAY ONLY
   └─> 3 checkboxes shown in queue UI
   └─> No actual processing applied to file
```

**Why This Change:**
- Slicer (OrcaSlicer/BambuStudio) already configures all settings
- No need for system to modify G-code
- Simpler, more predictable behavior
- Eliminates 800+ lines of complex template logic

---

## ⚙️ Print Startup Configuration (January 2026) - DEPRECATED

**⚠️ WARNING:** This section describes the OLD template/preset system that was removed on February 2, 2026. Files are now sent as-is from slicer without any modification.

---

## 🔧 Technical Implementation Highlights

### Dual Stop Detection
**Problem:** Queue didn't update when print stopped from printer LCD.  
**Solution:** MQTT callback system detects `gcode_state` transitions.

```python
# bambu_service.py
def on_print_stopped(self):
    # Detects: printing/paused → idle (progress < 100%)
    
# main.py  
def handle_print_stopped(printer_id):
    # Update queue & job status to "stopped"
    # Broadcast via WebSocket

# Flow:
# Printer LCD Stop → MQTT FAILED → bambu_service → callback → DB update → UI
```

### Camera Auto-Reload
**Problem:** Camera didn't reload without page refresh.  
**Solution:** React key prop change forces component remount.

```typescript
const [cameraKey, setCameraKey] = useState(0);

const handleTabClick = (tab: string) => {
  if (tab === 'status') setCameraKey(prev => prev + 1);
};

<PrinterStatus key={cameraKey} printer={printer} />
```

### Time Display Fix
**Problem:** Remaining time showed minutes as seconds.  
**Root Cause:** MQTT sends `mc_remaining_time` in minutes.  
**Solution:** Convert to seconds in backend.

```python
# Backend: mc_remaining_time * 60 → seconds
# Frontend: formatRemainingTime(seconds) → "3h 9m"
```

---

## 📁 Project Directory Structure

```
cooking-ai-agent/
├── 📂 src/                          # Backend source code (Python/FastAPI)
│   ├── main.py                      # FastAPI application entry point
│   ├── config.py                    # Application configuration
│   │
│   ├── 📂 api/                      # REST API endpoints
│   │   ├── bucket_list.py           # Bucket list management API
│   │   ├── camera.py                # Camera streaming endpoints
│   │   ├── filaments.py             # Filament inventory CRUD
│   │   ├── history.py               # Print history API
│   │   ├── jobs.py                  # Job management (upload, delete)
│   │   ├── presets.py               # Print presets CRUD
│   │   ├── printers.py              # Printer management
│   │   ├── printer_files.py         # SD card file operations
│   │   ├── print_control.py         # Start/Stop/Pause print control
│   │   ├── queue.py                 # Queue management API
│   │   ├── templates.py             # G-code templates (JSON config)
│   │   ├── templates_db.py          # G-code templates (database)
│   │   └── websocket.py             # WebSocket real-time updates
│   │
│   ├── 📂 services/                 # Business logic layer
│   │   ├── bambu_service.py         # MQTT client for Bambu Lab printers
│   │   ├── discovery_service.py     # mDNS printer discovery
│   │   ├── ftps_service.py          # FTPS file upload to printer
│   │   ├── gcode_preprocessor.py    # G-code modification engine
│   │   ├── gcode_templates.py       # Template injection logic
│   │   ├── job_service.py           # Job processing service
│   │   ├── printer_service.py       # Printer state management
│   │   ├── print_control_service.py # Print control orchestration
│   │   └── queue_service.py         # Queue processing & file prep
│   │
│   ├── 📂 database/                 # Database layer
│   │   └── db.py                    # SQLAlchemy models & schema
│   │
│   ├── 📂 models/                   # Pydantic data models
│   │
│   └── 📂 utils/                    # Utility functions
│       ├── gcode_parser.py          # Parse G-code & 3MF metadata
│       └── slicer.py                # OrcaSlicer CLI integration
│
├── 📂 frontend/                     # React frontend
│   ├── package.json                 # NPM dependencies
│   └── 📂 src/
│       ├── App.tsx                  # Main React application
│       ├── 📂 api/
│       │   └── client.ts            # API client (Axios)
│       ├── 📂 components/           # React components
│       │   ├── AmsStatusDisplay.tsx # AMS slot visualization
│       │   ├── Dashboard.tsx        # Main dashboard
│       │   ├── FilamentInventory.tsx# Filament management UI
│       │   ├── GCodeTemplates.tsx   # Template editor
│       │   ├── GCodeViewer.tsx      # G-code preview
│       │   ├── HistoryViewer.tsx    # Print history display
│       │   ├── JobsList.tsx         # Job list management
│       │   ├── JobUploadForm.tsx    # File upload form
│       │   ├── PrinterCard.tsx      # Printer status card
│       │   ├── PrinterFilesTab.tsx  # SD card file browser
│       │   ├── PrinterStatus.tsx    # Real-time printer status
│       │   ├── PrintPreviewModal.tsx# Print preview modal
│       │   ├── QueueDashboard.tsx   # Queue management UI
│       │   └── QueueManager.tsx     # Queue controls
│       ├── 📂 hooks/                # Custom React hooks
│       └── 📂 services/             # Frontend services
│
├── 📂 data/                         # Data storage
│   ├── farm.db                      # SQLite database
│   ├── 📂 uploads/                  # Uploaded 3MF/STL files
│   ├── 📂 queue_files/              # Processed files ready for print
│   ├── 📂 3mf_input/                # 3MF input staging
│   ├── 📂 3mf_output/               # Modified 3MF output
│   └── 📂 gcode/                    # Extracted G-code files
│
├── 📂 docs/                         # Documentation
│   ├── COMPREHENSIVE_DOCUMENTATION.md  # 📖 Complete system reference
│   ├── ARCHITECTURE.md              # Backend architecture details
│   ├── FRONTEND_DOCUMENTATION.md    # Frontend component docs
│   ├── DOCUMENTATION_INDEX.md       # Documentation navigation
│   ├── DEVELOPMENT.md               # Development guide
│   ├── PROJECT_STRUCTURE.md         # Project structure details
│   ├── 3MF_PARSER.md                # 3MF file format guide
│   ├── DIRECT_UPLOAD.md             # FTPS upload guide
│   ├── PRINTER_DISCOVERY_GUIDE.md   # Printer discovery setup
│   └── CAMERA_URLS.md               # Camera streaming URLs
│
├── 📂 tests/                        # Unit & integration tests
│
├── 📂 logs/                         # Application logs
│
└── 📂 venv_clean/                   # Python virtual environment
```

### 🔍 Quick Reference - What to Find Where

| Looking for... | Go to... |
|----------------|----------|
| **API Endpoints** | `src/api/` - Each file handles one domain |
| **Business Logic** | `src/services/` - Core functionality |
| **Database Schema** | `src/database/db.py` - All SQLAlchemy models |
| **G-code Processing** | `src/services/gcode_preprocessor.py` |
| **Template System** | `src/services/gcode_templates.py` + `src/api/templates_db.py` |
| **MQTT Communication** | `src/services/bambu_service.py` |
| **File Upload (FTPS)** | `src/services/ftps_service.py` |
| **Printer Discovery** | `src/services/discovery_service.py` |
| **React Components** | `frontend/src/components/` |
| **API Client (Frontend)** | `frontend/src/api/client.ts` |
| **Full Documentation** | `docs/COMPREHENSIVE_DOCUMENTATION.md` |
| **Database File** | `data/farm.db` |
| **Uploaded Files** | `data/uploads/` |
| **Processed Queue Files** | `data/queue_files/` |

### 📊 Database Tables (in `src/database/db.py`)

| Table | Purpose |
|-------|---------|
| `printers` | Printer configurations (IP, access code, etc) |
| `jobs` | Uploaded files & metadata |
| `queue` | Print queue with simplified settings (3 checkboxes + AMS) |
| `history` | Completed print logs |
| `filament_profiles` | Filament inventory |
| `ams_slot_assignments` | AMS slot → filament mapping |
| `bucket_list` | Saved jobs for later printing |

**Removed Tables (February 2, 2026):**
- ❌ `gcode_templates` - G-code template library (removed)
- ❌ `print_presets` - Saved print setting presets (removed)
- ❌ `automation_settings` - Automation preferences (removed)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────┐
│   User Upload (.3mf / .stl)     │
│   + Custom Slicing Settings     │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│  Web Interface (React)           │
│  - Upload form                  │
│  - Settings (layer, infill)     │
│  - Queue management             │
│  - Dashboard & history          │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│  Backend (Python FastAPI)        │
│  - Slice manager (OrcaSlicer)   │
│  - Queue manager                │
│  - Job scheduler                │
└──────────────┬──────────────────┘
               │
        ┌──────┴────────┐
        │               │
   ┌────▼────┐    ┌────▼────┐
   │ Database │    │ OrcaSlicer
   │ (SQLite) │    │ (CLI)
   │ History  │    │ 
   │ Jobs     │    │ Bambu Lab
   │ Queue    │    │ MQTT API
   └──────────┘    └─────────┘
```

---

## 🔄 Print Flow

```
1. USER UPLOADS FILE
   └─> Select .3mf or .stl from local machine
   └─> Set slicing parameters (layer height, infill, etc)
   └─> Set number of loops (e.g., 5)

2. APPLICATION SLICES FILE
   └─> Call OrcaSlicer CLI with Bambu Lab A1 profile
   └─> Generate optimized G-code
   └─> Save to storage

3. APPLICATION QUEUES JOB
   └─> Add to queue
   └─> Assign job ID
   └─> Store in database with slicing settings

4. PRINTER STARTS PRINTING
   └─> Send G-code to Bambu Lab A1 via MQTT
   └─> Monitor print progress

5. PRINT COMPLETES
   └─> Detect completion (sensor/MQTT status)
   └─> Trigger auto-eject
   └─> Wait for manual removal or proceed

6. NEXT EXECUTION
   └─> If loop count not reached → repeat print (go to step 4)
   └─> Else → load next job from queue (go to step 4)

7. LOGGING
   └─> Record job details in history
   └─> Timestamp, material, duration, slicing settings, status
```

---

## 📡 File Transfer to Printer

### 🎯 Current Implementation (Active)

**System uses FTPS Direct Upload method exclusively** - This is the ONLY method used in production.

| Step | Action | Implementation | Notes |
|------|--------|---------------|-------|
| 1 | Upload to printer | FTPS port 990 → `cache/` folder | `print_control_service.py` |
| 2 | Start print | MQTT `start_print_from_sd()` | `bambu_service.py` |
| 3 | Monitor progress | WebSocket `/ws` | Real-time status |
| 4 | Control print | MQTT pause/resume/stop | Database sync |

### ✅ **FTPS Direct Upload (ACTIVE METHOD)**

**Used By:**
- ✅ `print_control_service.py` - `start_next_job()` (Main Queue System)
- ✅ `queue_service.py` - All queue operations
- ✅ All production workflows

**Why This Method:**
- ✅ No HTTP server dependency
- ✅ Direct file transfer to printer SD card
- ✅ Faster and more reliable
- ✅ Progress callback integrated with WebSocket
- ✅ Based on OctoPrint-BambuPrinter plugin
- ✅ Tested and stable

**How It Works:**
```
1. Upload via FTPS (port 990) → Printer SD card `/cache/`
2. Send MQTT: start_print_from_sd(filename="model.3mf")
3. Printer prints from SD card file
```

**Implementation:**
```python
from src.services.ftps_service import BambuFTPSClient

ftps_client = BambuFTPSClient(
    host="192.168.4.101",
    access_code="34782589"
)

with ftps_client as ftp:
    # Upload with progress callback
    ftp.upload_file("model.3mf", "model.3mf", progress_callback)

# Then start print from SD
bambu_client.start_print_from_sd(filename="model.3mf")
```

**FTPS Technical Details:**
- Protocol: FTPS with implicit SSL/TLS
- Port: 990
- Username: `bblp` (Bambu Printer Linux Printer)
- Password: Access code from printer
- Client: `src/services/ftps_service.py` - `BambuFTPSClient` class
- Target folder: `/cache/` on printer SD card

**FTPS Error Handling:**
| Error | Cause | Solution |
|-------|-------|----------|
| Connection timeout | Printer offline/wrong IP | Check printer is on and IP correct |
| SSL handshake failed | Wrong port | Use port 990 (implicit SSL) |
| Auth failed (530) | Wrong access code | Check access code in printer settings |
| File not found (550) | Wrong path | Files upload to `/cache/` by default |

**Active Endpoints:**
```
POST /api/print-control/{printer_id}/start-next  # Start next job in queue (uses FTPS)
```

---

### ❌ **HTTP Download Method (LEGACY - NOT USED)**

**Status:** ⚠️ Code exists but NOT used in production workflow

**Location:** `bambu_service.py` - `send_print_file()` function (line 1960)

**Why Not Used:**
- ❌ Requires HTTP server running
- ❌ Printer must download from server (double network transfer)
- ❌ More complex error handling
- ❌ Slower than direct upload
- ❌ Not integrated with main queue system

**This method exists as:**
- Legacy code from early development
- Potential fallback if FTPS fails (not implemented)
- Reference implementation for HTTP-based approach

**How it would work (if used):**
```python
# NOT USED IN PRODUCTION
success = mqtt_client.send_print_file(
    "model.3mf",
    local_server_url="http://192.168.4.26:5000"
)

# Would do:
# 1. File hosted at http://server:5000/uploads/model.3mf
# 2. Send MQTT project_file with HTTP URL
# 3. Printer downloads from HTTP server
# 4. Send MQTT start command
```

**Conclusion:** System exclusively uses FTPS Direct Upload for reliability and performance.

---

## 📡 OrcaSlicer Integration

### What is OrcaSlicer?
- **Open Source** fork of Bambu Studio optimized for automation
- **Native Bambu Lab A1 Support** - Best optimization available
- **CLI-Based** - Perfect for headless/server deployments
- **Lightweight** - Fast slicing performance
- **Free** - No licensing costs

### Installation

1. **Windows:**
   ```bash
   # Via WinGet
   winget install orcaslicer
   
   # Or download from GitHub
   # https://github.com/SoftFever/OrcaSlicer/releases
   ```

2. **Linux:**
   ```bash
   sudo apt-get install orca-slicer
   ```

3. **macOS:**
   ```bash
   brew install orcaslicer
   ```

4. **Verify Installation:**
   ```bash
   orca-slicer --version
   ```

### CLI Usage

```bash
# Basic slicing with A1 profile (Windows)
OrcaSlicer.exe --slice model.3mf \
  --load-settings "Bambu Lab A1.json" \
  --export-gcode

# Linux/macOS
orca-slicer --slice model.3mf \
  --load-settings "Bambu Lab A1.json" \
  --export-gcode

# Export to specific output path
orca-slicer --slice model.3mf \
  --export-gcode model.gcode

# Note: Check OrcaSlicer documentation for latest CLI options
# https://github.com/SoftFever/OrcaSlicer/wiki/Command-Line-Interface
```

### Python Integration (Backend)

```python
import subprocess
import os

class OrcaSlicerManager:
    def __init__(self, orca_path="orca-slicer"):
        self.orca_path = orca_path
        self.printer_profile = "Bambu Lab A1"
    
    def slice_model(self, input_file, output_gcode, 
                   layer_height=0.2, infill=15):
        """Slice model using OrcaSlicer CLI"""
        cmd = [
            self.orca_path,
            "--slice",
            input_file,
            "--printer", self.printer_profile,
            "--layer-height", str(layer_height),
            "--infill-density", str(infill),
            "--output", output_gcode
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, timeout=300)
            return {"success": True, "output": output_gcode}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

---

## 📊 Database Schema (SQLite)

### Jobs Table
```
- job_id (PRIMARY KEY)
- filename
- upload_timestamp
- loop_count
- status (pending, running, completed, failed)
- created_at
```

### Print History Table
```
- history_id (PRIMARY KEY)
- job_id (FOREIGN KEY)
- printer_id
- start_time
- end_time
- duration_minutes
- material_used
- status (success, failed)
- eject_time
- notes
```

### Queue Table (Simplified - February 2026)
```
- queue_id (PRIMARY KEY)
- job_id (FOREIGN KEY)
- printer_id
- position_in_queue
- current_loop
- status (pending, running, completed, failed, stopped)
# AMS settings (4 fields)
- ams_slot (0-3)
- ams_mapping ("[0]", "[0,1,2,3]", etc)
- use_ams (boolean)
- filament_already_loaded (boolean)
# Print settings (3 checkboxes - for display only)
- auto_bed_leveling (boolean)
- flow_calibration (boolean)
- timelapse (boolean)
# File processing
- skip_preprocessing (always True)
- queue_file_path (path to copied file)
# Timestamps
- created_at
- started_at
- completed_at
```

---

## 🛠️ Development Roadmap

### Phase 1: Core Functionality ✅ COMPLETED
- [x] Backend API structure (FastAPI with modular routers)
- [x] Database setup (SQLAlchemy with SQLite)
- [x] Bambu Lab MQTT connection (via bambu_service.py)
- [x] Basic file upload endpoint
- [x] Queue management logic
- [x] Job management API
- [x] Printer discovery service

### Phase 2: Printer Integration ✅ COMPLETED
- [x] G-code transmission to printer
- [x] Print progress monitoring
- [x] Print control service (start/pause/stop/resume)
- [x] Auto-eject triggering (tested & working!)
- [x] MQTT LAN mode connection
- [x] Loop counter logic (in progress)
- [x] File loading via Bambu Studio (working with START command)

### Phase 3: Web Interface ✅ COMPLETED
- [x] React frontend setup with Tailwind CSS
- [x] Job upload UI (JobUploadForm component)
- [x] Queue dashboard (QueueDashboard component)
- [x] Real-time status updates (WebSocket)
- [x] History viewer (HistoryViewer component)
- [x] Printer status cards (PrinterCard component)
- [x] Tabbed dashboard interface

### Phase 4: Testing & Refinement ✅ COMPLETED (Jan 2026)
- [x] MQTT connection testing
- [x] Auto-eject command testing
- [x] Print start API testing
- [x] **Direct FTPS Upload Implementation**
  - [x] FTPS client with implicit SSL/TLS (port 990)
  - [x] File upload directly to printer SD card
  - [x] MQTT start command integration
  - [x] Full end-to-end testing - **ALL TESTS PASSING** ✅
- [x] **UI/UX Enhancements** ✨ NEW
  - [x] Print progress container always visible
  - [x] Camera auto-reload on tab switch
  - [x] Remaining time accuracy fix
  - [x] Print stopped detection from printer
  - [x] Status card conditional styling
- [x] **Version Control & Collaboration** ✨ NEW
  - [x] Git repository initialization
  - [x] GitHub private repository setup
  - [x] Development branch workflow
  - [x] Documentation updates
- [x] **Filament Inventory System** ✨ NEW
  - [x] FilamentProfile database model
  - [x] Full CRUD API endpoints
  - [x] Frontend inventory management tab
  - [x] Stock tracking (spool count, remaining grams)
- [x] **AMS Slot Assignment** ✨ NEW
  - [x] ams_slot_assignments database table
  - [x] Slot assignment API with MQTT sync
  - [x] Visual AMS display component
  - [x] Load/Unload filament with progress display
  - [x] Temperature display during heating
- [x] **Print Control Buttons** ✨ FIXED (Jan 3, 2026)
  - [x] Stop button - Database query fix
  - [x] Pause button - Database query fix
  - [x] Resume button sync with printer status
  - [x] Comprehensive logging (frontend & backend)
- [x] **WebSocket Stability** ✨ FIXED (Jan 3, 2026)
  - [x] Heartbeat mechanism (ping/pong)
  - [x] Visibility change handler
  - [x] Window focus reconnection
  - [x] Remaining time display
- [x] **SD Card Print Command** ✨ DOCUMENTED (Jan 3, 2026)
  - [x] Correct URL format: `file:///sdcard/{path}`
  - [x] sequence_id timestamp format
  - [x] AMS mapping configuration
  - [x] 3MF structure requirements
- [ ] Full print cycle testing with real models
- [ ] Performance optimization

### Phase 5: Multi-Printer Support
- [ ] Multi-printer architecture
- [ ] Load balancing
- [ ] Independent queues per printer

---

## 🔧 Current Printer Configuration

### Bambu Lab A1 Combo AMS
```
Printer IP:      192.168.4.101
Printer ID:      03900D5A2402051
MQTT Port:       8883 (TLS)
MQTT Username:   bblp
Access Code:     34782589
FTP Port:        990 (Implicit FTPS)
Mode:            LAN Mode (local network)
```

### Connection Status (Last Tested: January 3, 2026)
- ✅ MQTT Connection: Working
- ✅ Status Push: Receiving printer status (real-time)
- ✅ Auto-Eject: Working (G28 X Y + G1 Y 230)
- ✅ Print Start Command: API working with SD card files
- ✅ Direct FTPS Upload: Working (port 990 implicit SSL)
- ✅ Print Control Buttons: Pause/Resume/Stop all working
- ✅ WebSocket: Stable with heartbeat mechanism
- ✅ SD Card Print: Working (file:///sdcard/ URL format)
- ✅ AMS Status: Receiving tray data via MQTT
- ✅ AMS Filament Settings: ams_filament_setting command working
- ✅ AMS Load/Unload: ams_change_filament & unload_filament working

---

## ❗ Common Issues & Solutions

### Print Command Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "File not found" when starting print | Wrong URL path | Use `file:///sdcard/cache/filename.3mf` for uploaded files |
| Print doesn't start | sequence_id is static | Use `str(int(time.time() * 1000))` for unique ID |
| Wrong plate printed | Wrong `param` value | Check `Metadata/plate_1.gcode` matches your plate |
| AMS doesn't load filament | Wrong ams_mapping | Array indices start at 0: `[0,1,2,3]` for slots 1-4 |

### FTPS Upload Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | Wrong port | Use port 990 (implicit SSL), not 21 |
| SSL error | Using explicit SSL | Bambu uses IMPLICIT SSL (wrap socket before connect) |
| Auth failed | Wrong credentials | Username: `bblp`, Password: printer access code |
| Upload succeeds but print fails | File in wrong folder | Files go to `/cache/` folder |

### WebSocket Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Disconnects when tab inactive | Browser throttling | Heartbeat + visibility handler implemented |
| Status not updating | Connection dropped | Check `useWebSocket.ts` reconnect logic |
| No data received | Backend not sending | Verify `websocket.py` broadcast loop |

### Print Control Button Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Pause/Stop not working | Using instance variable | Query database for running queue item |
| Resume shows wrong state | State not synced | useEffect syncs isPaused with printer.status |
| Button click no response | No logging | Check browser console and backend logs |

### 3MF File Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No thumbnail on LCD | Missing metadata | Ensure file sliced with OrcaSlicer/Bambu Studio |
| No time estimate | Missing slice_info | Check `Metadata/slice_info.config` exists |
| "Invalid gcode" | Wrong structure | Verify `Metadata/plate_1.gcode` exists |

### Diagnostic Tools

```bash
# Check database status
sqlite3 data/farm.db "SELECT * FROM queue WHERE status='running'"

# View logs
tail -f logs/backend.log    # Linux/macOS
Get-Content logs/backend.log -Tail 50 -Wait  # Windows
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- OrcaSlicer (CLI slicing)
- Bambu Lab A1 Combo AMS printer

### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Configure environment
cp .env.example .env
# Edit .env with your Bambu Lab credentials and printer IP/serial

# 3. Run (auto-starts backend + frontend)
start.bat           # Windows
./start.sh          # Linux/macOS
```

**Access:** http://localhost:3051

---

## 📝 Configuration

### .env File (Opsional - Untuk Development)

> **Catatan:** Printer configuration **disimpan di database** (SQLite: `./data/farm.db`).  
> Environment variables di bawah ini hanya sebagai **fallback** untuk testing/development.

```env
# Bambu Lab Credentials (OPSIONAL - gunakan UI untuk add printer)
BAMBU_USERNAME=your_email@example.com
BAMBU_ACCESS_CODE=your_access_code
BAMBU_PRINTER_IP=192.168.1.100
BAMBU_PRINTER_ID=03900D5A2402051
BAMBU_PRINTER_SN=03900D5A2402051

# Server
BACKEND_PORT=5051
FRONTEND_PORT=3051

# Database
DB_PATH=./data/farm.db
```

**Cara Add Printer (Recommended):**
1. Buka frontend: http://localhost:3051
2. Navigate ke Printer Settings
3. Add printer via UI → Data tersimpan di database
4. Database persistent via Docker volume mounting

See [SETUP.md](SETUP.md) for detailed configuration guide.

---

## 📡 API Documentation

### Base URL
```
http://localhost:8000
```

### Available Endpoints

#### Health Check
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root - API health check |
| GET | `/health` | Detailed health status |

#### Jobs Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List all jobs |
| POST | `/api/jobs` | Create new job (upload file) |
| GET | `/api/jobs/{job_id}` | Get job details |
| PUT | `/api/jobs/{job_id}` | Update job |
| DELETE | `/api/jobs/{job_id}` | Delete job |

#### Queue Management (Simplified - February 2026)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/queue/{printer_id}` | Get queue for printer |
| POST | `/api/queue/add` | Add job to queue (7 parameters only) |
| PUT | `/api/queue/{queue_id}/position` | Update queue position |
| DELETE | `/api/queue/{queue_id}` | Remove from queue |

**AddToQueueRequest Schema (Simplified):**
```json
{
  "job_id": 1,
  "printer_id": "03900D5A2402051",
  // AMS settings (4 fields)
  "ams_slot": 0,
  "ams_mapping": "[0]",
  "use_ams": true,
  "filament_already_loaded": false,
  // Print settings (3 checkboxes)
  "auto_bed_leveling": true,
  "flow_calibration": false,
  "timelapse": false
}
```

**What Was Removed:**
- ❌ 40+ automation parameters (vibration_test, clean_nozzle, quick_start, etc.)
- ❌ preset_id parameter
- ❌ use_template_mode parameter
- ❌ All template/preset-related fields

#### Printer Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/printers` | List all printers |
| GET | `/api/printers/{printer_id}` | Get printer status |
| POST | `/api/printers/{printer_id}/start` | Start print |
| POST | `/api/printers/{printer_id}/pause` | Pause print |
| POST | `/api/printers/{printer_id}/resume` | Resume print |
| POST | `/api/printers/{printer_id}/stop` | Stop print |

#### Print Control & Status ✨ ENHANCED
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/print-control/{printer_id}/status` | Get current print status with job info |
| GET | `/api/print-control/{printer_id}/mqtt-status` | Get real-time MQTT status (progress, time, temp) |
| POST | `/api/print-control/{printer_id}/start-next` | Start next job in queue |
| POST | `/api/print-control/{printer_id}/pause` | Pause current print |
| POST | `/api/print-control/{printer_id}/resume` | Resume paused print |
| POST | `/api/print-control/{printer_id}/stop` | Stop current print and update queue |

**MQTT Status Response:**
```json
{
  "printer_id": "03900D5A2402051",
  "printer_status": "printing", // idle | printing | paused | offline
  "mqtt_connected": true,
  "progress": 45,                 // 0-100%
  "remaining_time": 3540,        // seconds (converted from minutes)
  "current_file": "model.3mf",
  "nozzle_temp": 220.5,
  "bed_temp": 60.0,
  "layer_num": 125,
  "total_layers": 280
}
```

#### Filament Inventory ✨ NEW
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/filaments` | List all filament profiles |
| POST | `/api/filaments` | Create new filament profile |
| GET | `/api/filaments/{id}` | Get filament by ID |
| PUT | `/api/filaments/{id}` | Update filament profile |
| DELETE | `/api/filaments/{id}` | Delete filament |
| POST | `/api/filaments/{id}/stock/add` | Add stock (grams) |
| POST | `/api/filaments/{id}/apply/{printer_id}/{slot}` | Apply settings to printer slot |

#### AMS Slot Management ✨ NEW
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/filaments/slots/{printer_id}` | Get all slot assignments with filament details |
| POST | `/api/filaments/slots/{printer_id}/{slot}` | Assign filament from inventory to slot |
| PUT | `/api/filaments/slots/{printer_id}/{slot}/remaining` | Update remaining grams for slot |
| POST | `/api/printers/{printer_id}/ams/load/{slot}` | Load filament from slot |
| POST | `/api/printers/{printer_id}/ams/unload` | Unload current filament |

### API Response Format
```json
{
  "status": "success",
  "data": { ... },
  "message": "Operation completed"
}
```

---

## 🧪 Testing Strategy

### Phase 1: Mock Testing
- Mock Bambu Lab API responses
- Test queue logic without real printer
- Validate database operations

### Phase 2: Integration Testing
- Connect to real Bambu Lab A1
- Test actual G-code transmission
- Verify print completion detection
- Test auto-eject trigger

### Phase 3: Load Testing
- Multiple jobs in queue
- Long print sessions
- Loop counter accuracy

---

## 📚 Useful Resources

- **Bambu Lab Cloud API:** https://github.com/coelacant1/Bambu-Lab-Cloud-API
- **FDM Monster Reference:** https://github.com/fdm-monster/fdm-monster
- **Home Assistant Bambu Integration:** https://github.com/nberktumer/ha-bambu-lab-p1-spaghetti-detection
- **Bambu Lab Documentation:** https://wiki.bambulab.com/

---

## 🎯 Success Criteria

✅ Minimal, simple, and easy-to-use interface
✅ Reliable print queue management
✅ Accurate loop counting
✅ Auto-eject functionality
✅ Complete printing history
✅ Scalable for additional printers
✅ Stable connection to Bambu Lab A1

---

## 🧹 Maintenance

### Cleanup Temporary Files
```bash
# Windows PowerShell
Get-ChildItem -Path "data/uploads" -Filter "tmp*" | Remove-Item -Force

# Linux/macOS
rm -f data/uploads/tmp*
```

### Database Backup
```bash
# Backup database
cp data/farm.db data/farm_backup_$(date +%Y%m%d).db
```

### Log Rotation
- Logs are stored in `logs/` directory
- Consider setting up log rotation for production use

---

---

## 🏷️ Naming Conventions & Code Standards

**IMPORTANT:** Use these conventions consistently throughout the project to avoid confusion and duplicate variable names.

### Python Backend Naming

#### **Variables**
```python
# Jobs & Queue Management
job_id              # Primary key for job (int)
job_name            # User-given name for job (str)
job_status          # Status: "pending" | "running" | "completed" | "failed" (str)
job_loop_count      # How many times to print this job (int)
job_current_loop    # Current loop iteration (int)
queue_position      # Position in queue (int)
queue_id            # Primary key for queue entry (int)

# File & Slicing
input_file          # Path to uploaded .3mf/.stl file (str)
output_gcode        # Path to generated G-code file (str)
gcode_size_mb       # Size of G-code in megabytes (float)
layer_height        # Layer height setting in mm (float) - e.g., 0.2
infill_density      # Infill percentage (int) - e.g., 15
print_settings      # Dictionary of all print settings (dict)

# Printer & Hardware
printer_id          # Unique identifier for printer (str/int)
printer_name        # Display name for printer (str) - e.g., "Bambu A1 #1"
printer_status      # Status: "idle" | "printing" | "offline" (str)
mqtt_broker         # MQTT server address (str)
mqtt_port           # MQTT server port (int) - default 8883
mqtt_topic          # MQTT topic for communication (str)

# Print History & Logging
history_id          # Primary key for history entry (int)
start_time          # Print start timestamp (datetime)
end_time            # Print end timestamp (datetime)
duration_minutes    # Print duration in minutes (float)
material_used_grams # Material used in grams (float)
eject_time          # Time when auto-eject triggered (datetime)
print_success       # Whether print succeeded (bool)
completion_status   # Status message (str)

# API & Requests
api_key             # Authentication token (str)
api_endpoint        # URL endpoint (str)
request_timeout     # Timeout in seconds (int) - default 30
response_data       # JSON response from API (dict)
```

#### **Functions**
```python
# Slicing Operations
def slice_model(input_file, output_gcode, **settings):
    """Slice .3mf/.stl to G-code"""
    
def get_slice_status(job_id):
    """Get current slicing status"""

# Queue Management
def add_job_to_queue(job_id, loop_count):
    """Add job to print queue"""
    
def get_next_job():
    """Get next job from queue"""
    
def update_queue_position(job_id, new_position):
    """Update job position in queue"""

# Printer Control
def send_gcode_to_printer(printer_id, gcode_path):
    """Send G-code to printer via MQTT"""
    
def trigger_auto_eject(printer_id):
    """Trigger auto-eject mechanism"""
    
def get_printer_status(printer_id):
    """Get current printer status"""

# History & Logging
def log_print_completion(job_id, duration, success, notes=""):
    """Log completed print job"""
    
def get_print_history(printer_id, days=30):
    """Get print history for specified period"""
```

#### **Database Tables & Fields**
```python
# Table: jobs
job_id (PK)         # INTEGER PRIMARY KEY
job_name            # TEXT - User-given name
filename            # TEXT - Original filename
upload_timestamp    # DATETIME - When uploaded
gcode_size_mb       # REAL - Size of generated G-code
loop_count          # INTEGER - Total loops requested
current_loop        # INTEGER - Current loop (0-indexed)
status              # TEXT - pending|running|completed|failed
created_at          # DATETIME - Creation timestamp
updated_at          # DATETIME - Last update timestamp

# Table: print_history
history_id (PK)     # INTEGER PRIMARY KEY
job_id (FK)         # INTEGER - Reference to jobs table
printer_id          # TEXT - Which printer
start_time          # DATETIME - Print start
end_time            # DATETIME - Print end
duration_minutes    # REAL - Total duration
material_used_grams # REAL - Material consumed
print_success       # BOOLEAN - Success indicator
eject_time          # DATETIME - When ejected
completion_status   # TEXT - Success/error message
notes               # TEXT - Additional notes
created_at          # DATETIME - Record creation

# Table: queue
queue_id (PK)       # INTEGER PRIMARY KEY
job_id (FK)         # INTEGER - Reference to job
printer_id          # TEXT - Target printer
position_in_queue   # INTEGER - Queue order
current_loop        # INTEGER - Current loop number
status              # TEXT - pending|running|completed
created_at          # DATETIME - Added to queue
started_at          # DATETIME - Started printing
completed_at        # DATETIME - Completed

# Table: print_settings
setting_id (PK)     # INTEGER PRIMARY KEY
job_id (FK)         # INTEGER - Reference to job
layer_height        # REAL - mm
infill_density      # INTEGER - 0-100%
print_speed         # INTEGER - mm/s (optional)
nozzle_temp         # INTEGER - °C (optional)
bed_temp            # INTEGER - °C (optional)
support_enabled     # BOOLEAN
created_at          # DATETIME
```

#### **Constants & Enums**
```python
# Status Values
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

PRINTER_STATUS_IDLE = "idle"
PRINTER_STATUS_PRINTING = "printing"
PRINTER_STATUS_OFFLINE = "offline"

# Default Settings
DEFAULT_LAYER_HEIGHT = 0.2
DEFAULT_INFILL_DENSITY = 15
DEFAULT_PRINT_SPEED = 100
DEFAULT_MQTT_PORT = 8883
DEFAULT_API_TIMEOUT = 30

# File Configuration
ALLOWED_MODEL_EXTENSIONS = [".3mf", ".stl"]
ALLOWED_GCODE_EXTENSIONS = [".gcode", ".g", ".gc"]
MAX_FILE_SIZE_MB = 500
GCODE_OUTPUT_DIR = "./data/gcode"
UPLOAD_TEMP_DIR = "./data/uploads"
```

### Frontend (React) Naming

#### **Variables**
```javascript
// Job & Queue State
jobId, setJobId         // Currently selected job
jobName, setJobName     // Job display name
jobList, setJobList     // Array of all jobs
queueItems, setQueueItems   // Current queue items
currentLoops, setCurrentLoops   // Loop count input

// File Upload
selectedFile, setSelectedFile   // Uploaded file
uploadProgress, setUploadProgress   // Upload percentage
fileSize, setFileSize   // Size of uploaded file

// Print Settings
layerHeight, setLayerHeight     // Layer height input
infillDensity, setInfillDensity // Infill percentage
printSettings, setPrintSettings // All settings object

// UI State
isLoading, setIsLoading         // Loading indicator
errorMessage, setErrorMessage   // Error display
successMessage, setSuccessMessage   // Success notification
```

#### **Component Names**
```javascript
// Main Components
<JobUploadForm />
<QueueManager />
<PrinterStatus />
<PrintHistory />
<Dashboard />

// Sub-Components
<FileUploadInput />
<PrintSettingsForm />
<QueueItemCard />
<HistoryTable />
<StatusIndicator />
```

### Consistency Rules

**✅ DO:**
- Use **snake_case** for Python variables and functions
- Use **camelCase** for JavaScript variables and functions
- Use **UPPER_SNAKE_CASE** for constants
- Use descriptive, explicit names (not abbreviated)
- Prefix boolean variables with `is_`, `has_`, `should_`
- Suffix IDs with `_id`

**❌ DON'T:**
- Use single letter variables (except in loops)
- Mix naming styles in same file
- Create duplicate variable names
- Use abbreviations unless commonly understood (e.g., `mqtt_`, `gcode_`)
- Use vague names like `data`, `temp`, `var1`, `result`

### Example Usage

```python
# ❌ BAD
def process(f, l, i):
    g = orca_slice(f)
    q_add(g, l)
    return p_send(g, i)

# ✅ GOOD
def queue_and_send_job(input_file, loop_count, printer_id):
    output_gcode = slice_model_with_orca(input_file)
    queue_id = add_job_to_queue(output_gcode, loop_count)
    send_gcode_to_printer(printer_id, output_gcode)
    return queue_id
```

---

## � Additional Documentation

For detailed information, see:
- [SETUP.md](SETUP.md) - Detailed setup guide
- [QUICKSTART.md](QUICKSTART.md) - Quick start tutorial  
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [docs/COMPREHENSIVE_DOCUMENTATION.md](docs/COMPREHENSIVE_DOCUMENTATION.md) - Complete reference
- [docs/FRONTEND_DOCUMENTATION.md](docs/FRONTEND_DOCUMENTATION.md) - Frontend components
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) - Development guide

---

## 📞 Support & Contributing

This is a personal project for 3D print farm automation. For questions or suggestions, please open an issue on GitHub.

**Project Status:** ✅ Production Ready (with Feb 3, 2026 bug fixes)  
**Last Updated:** February 3, 2026

**Recent Fixes:**
- ✅ Print completion timing validation (30s minimum)
- ✅ Calibration logic corrected (checkboxes work as expected)

---

**Made with ❤️ for Bambu Lab A1 Combo AMS**
xZ