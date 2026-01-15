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

## 🎯 Core Features

### 1. **File Upload & Automated Slicing**
- Upload .3mf or .stl files
- Automatic slicing using OrcaSlicer CLI
- Customizable print settings (layer height, infill, etc)
- Generate optimized G-code for Bambu Lab A1

### 2. **Print Job Management**
- Queue multiple jobs
- Set loop count per job (how many times to print each job)
- Sequential job execution (Job A with 5 loops → Job B with 3 loops)

### 3. **Queue Management**
- FIFO (First In, First Out) execution
- Pause/Resume queue capability
- Job priority and ordering
- Real-time queue status

### 4. **Printer Control**
- Integrate with Bambu Lab MQTT API
- Send G-code to printer
- Auto-eject after print completion
- Automatic transition to next job

### 5. **Monitoring & History**
- Print job history with timestamps
- Slicing settings logged
- Material tracking
- Print duration logging
- Success/failure status
- Auto-eject time tracking

### 6. **Multi-Printer Support**
- Scalable for additional Bambu Lab printers
- Independent queue management per printer
- Centralized dashboard

### 7. **Filament Inventory Management** ✨ NEW
- Complete filament profile database (brand, material, color, temps, settings)
- Stock tracking (spool count, remaining grams)
- Temperature presets (nozzle & bed min/max/default)
- Physical properties (density, diameter, K-factor)
- Drying requirements
- Purchase links and notes

### 8. **AMS Slot Assignment** ✨ NEW
- Visual AMS slot display matching printer
- Assign filaments from inventory to AMS slots
- Real-time slot status from MQTT
- Load/Unload filament with progress display
- Remaining filament tracking per slot
- MQTT sync with printer settings

### 9. **Real-Time Status Monitoring** ✨ ENHANCED (Jan 2026)
- **Print Progress Container**: Always visible with idle state support
- **Accurate Time Tracking**: Fixed remaining time conversion (minutes → seconds)
- **Smart Camera Reload**: Auto-reload on Status tab click
- **Print Stopped Detection**: Detects stop from both web system and printer
- **Live Status Updates**: WebSocket-based real-time updates
- **Progress Bar**: Visual indicator with percentage and layer count
- **Status Cards**: Time remaining, current layer, progress percentage

### 10. **Enhanced Print Control**
- Pause/Resume/Stop with database sync
- Automatic queue status updates
- Print stopped callback system
- Comprehensive error logging
- Status synchronization across UI components

---

## 🆕 Recent Updates (January 2026)

### UI/UX Improvements
- ✅ **Print Progress Always Visible**: Container shows status even when idle (displays "-" for inactive)
- ✅ **Camera Auto-Reload**: Camera feed reloads when switching to Status tab
- ✅ **Fixed Time Display**: Remaining time now correctly converted from minutes to seconds
- ✅ **Enhanced Status Cards**: Conditional styling for active/idle states

### Print Status Detection
- ✅ **Dual Stop Detection**: System now detects print stopped from:
  - Web interface (Stop button)
  - Printer LCD interface (manual stop)
- ✅ **Queue Status Sync**: Queue automatically updates to "stopped" when print cancelled from printer
- ✅ **Callback System**: `on_print_stopped` callback detects gcode_state transitions

### Code Quality
- ✅ **Git Repository**: Initialized with proper .gitignore
- ✅ **GitHub Integration**: Private repository with development branch
- ✅ **Branch Workflow**: `development` → testing → `main`

---

## ⚠️ IMPORTANT: Print Startup Behavior Fix (January 2026)

### Masalah yang Diperbaiki
Saat print dimulai via sistem (queue/API), printer menunggu di **depan bed** dengan purge line, bukan di posisi **cut filament** (samping) seperti saat kirim manual via CMD.

### Root Cause
1. **MQTT Calibration Parameters**: Parameter `flow_cali`, `vibration_cali`, `bed_leveling` dikirim sebagai `False`, yang membuat printer menjalankan kalibrasi built-in sendiri.
2. **Template `prepare_print`**: Template G-code yang memindahkan nozzle ke `G1 X108.000 Y-0.500` (depan bed) diaktifkan secara default.
3. **Setting default `prepare_print=True`**: Ada di DUA file yang harus di-set `False`.

### Solusi yang Diterapkan

#### 1. MQTT Parameters (Always TRUE = Skip Built-in Calibration)
**File:** `src/services/bambu_service.py`, `src/services/print_control_service.py`, `src/services/queue_service.py`
```python
# TRUE = skip printer's built-in calibration (use G-code calibration instead)
"flow_cali": True,
"vibration_cali": True,
"bed_leveling": True
```

#### 2. Template `prepare_print` Default = False
**File 1:** `src/services/gcode_templates.py` (line ~86)
```python
prepare_print: bool = False  # DEFAULT OFF - avoid moving to front of bed
```

**File 2:** `src/services/gcode_preprocessor.py` (line ~72)
```python
prepare_print: bool = False  # DEFAULT OFF - avoid moving to front of bed
```

#### 3. Template `nozzle_load_line` Default = False
**File 1:** `src/services/gcode_templates.py` (line ~76)
```python
nozzle_load_line: bool = False  # DEFAULT OFF to avoid purge line at front of bed
```

**File 2:** `src/services/gcode_preprocessor.py` (line ~43)
```python
nozzle_load_line: bool = False  # DEFAULT OFF to avoid unwanted purge
```

#### 4. Database Template Disabled
```sql
UPDATE gcode_templates SET enabled=0 WHERE template_id=43;  -- Prepare Print
```

### Hasil
- ✅ Printer sekarang menunggu di posisi **cut filament** (samping/X-48.2)
- ✅ Tidak ada purge line di depan bed
- ✅ Perilaku sama seperti kirim manual via CMD

### File yang Terlibat
| File | Perubahan |
|------|-----------|
| `src/services/gcode_templates.py` | `prepare_print=False`, `nozzle_load_line=False` |
| `src/services/gcode_preprocessor.py` | `prepare_print=False`, `nozzle_load_line=False` |
| `src/services/bambu_service.py` | MQTT params selalu `True` |
| `src/services/print_control_service.py` | MQTT params selalu `True` |
| `src/services/queue_service.py` | MQTT params selalu `True`, preprocessing aktif |
| `data/farm.db` | Template ID 43 disabled |

---

## 🔧 Technical Implementation Details

### Print Stopped Detection System

**Problem Solved:** Queue status didn't update when print was stopped from printer LCD (only worked from web interface).

**Solution:** Callback system to detect gcode_state transitions from MQTT.

**Implementation:**

1. **bambu_service.py** - State Detection
```python
def on_print_stopped(self):
    """Callback when print is stopped (from printer or system)"""
    # Detects: gcode_state transitions from printing/paused to idle
    # Condition: progress < 100% (incomplete print)
```

2. **main.py** - Queue Update Handler
```python
def handle_print_stopped(printer_id: str):
    """Update queue status when print stopped from printer"""
    # Find active queue item (status: running/paused)
    # Update queue status to "stopped"
    # Update job status to "stopped"
    # Log the event
```

3. **Callback Registration**
```python
bambu_client.on_print_stopped = handle_print_stopped
```

**Flow:**
```
Printer LCD Stop → MQTT gcode_state: FAILED → bambu_service detects change
→ on_print_stopped callback → handle_print_stopped() → Update database
→ WebSocket broadcast → Frontend updates UI
```

### Camera Auto-Reload System

**Problem Solved:** Camera didn't reload without full page refresh.

**Solution:** Component remount via key prop change on tab click.

**Implementation:**

1. **Dashboard.tsx** - Tab Click Handler
```typescript
const [cameraKey, setCameraKey] = useState(0);

const handleTabClick = (tab: string) => {
  if (tab === 'status') {
    setCameraKey(prev => prev + 1); // Increment key to force remount
  }
  setActiveTab(tab);
};

// Pass key to PrinterStatus component
<PrinterStatus key={cameraKey} printer={printer} />
```

**Effect:** New key causes React to unmount and remount component, triggering fresh camera connection.

### Remaining Time Accuracy Fix

**Problem Solved:** Remaining time displayed incorrectly (showed minutes as seconds).

**Root Cause:** Bambu Lab MQTT sends `mc_remaining_time` in **minutes**, but system treated it as seconds.

**Solution:**

1. **bambu_service.py** - Conversion
```python
self.remaining_time: int = 0  # Store in SECONDS

# On MQTT message
if "mc_remaining_time" in print_data:
    mc_remaining_time = int(print_data["mc_remaining_time"])
    self.remaining_time = mc_remaining_time * 60  # Convert to seconds
```

2. **print_control.py** - API Response
```python
@router.get("/{printer_id}/mqtt-status")
async def get_mqtt_status(printer_id: str):
    return {
        "remaining_time": status.get("mc_remaining_time", 0)  # Already in seconds
    }
```

3. **Frontend** - Display
```typescript
const formatRemainingTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
};
```

**Example:** 189 minutes → 11,340 seconds → "3h 9m" ✅ (not "3m" ❌)

### Print Progress Always Visible

**Problem Solved:** Progress container disappeared when printer was idle.

**Solution:** Conditional rendering within container, not of the container itself.

**Implementation:**

**PrinterStatus.tsx**
```typescript
{/* Container ALWAYS renders */}
<div style={{ backgroundColor: '#ffffff', padding: '20px' }}>
  
  {/* Progress bar ONLY when printing/paused */}
  {(status === 'printing' || status === 'paused') && (
    <div className="progress-bar">...</div>
  )}
  
  {/* Status cards ALWAYS show */}
  <div className="status-cards">
    {/* Remaining Time - shows "-" when idle */}
    <div>
      {(status === 'printing' || status === 'paused') 
        ? formatRemainingTime(remainingTime)
        : '-'  // Gray dash when idle
      }
    </div>
    
    {/* Layer - shows "-" when idle */}
    <div>
      {(status === 'printing' || status === 'paused')
        ? `${currentLayer} / ${totalLayers}`
        : '-'  // Gray dash when idle
      }
    </div>
  </div>
  
  {/* Control buttons ONLY when printing/paused */}
  {(status === 'printing' || status === 'paused') && (
    <div className="control-buttons">...</div>
  )}
</div>
```

**Result:** 
- Idle: Shows gray "-" in cards, no progress bar, no buttons
- Printing: Shows data, progress bar, and control buttons
- Layout remains stable (no jumping)

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
| `queue` | Print queue with settings |
| `history` | Completed print logs |
| `filament_profiles` | Filament inventory |
| `ams_slot_assignments` | AMS slot → filament mapping |
| `gcode_templates` | G-code template library |
| `print_presets` | Saved print setting presets |
| `automation_settings` | Automation preferences |

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

### Queue Table
```
- queue_id (PRIMARY KEY)
- job_id (FOREIGN KEY)
- printer_id (FOREIGN KEY)
- position_in_queue
- current_loop
- created_at
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

### Quick Diagnostic Commands

```bash
# Check 3MF structure
python check_3mf_structure.py

# List files on SD card
python explore_sd_card.py

# Test MQTT connection
python test_mqtt.py

# Test FTPS connection
python test_direct_upload.py

# Check database queue
python -c "import sqlite3; c=sqlite3.connect('data/farm.db').cursor(); c.execute('SELECT * FROM queue'); print(c.fetchall())"
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ (for modern async features)
- Node.js 18+ (for React frontend)
- OrcaSlicer installed (for automated slicing)
- Bambu Lab A1 Combo AMS printer
- Bambu Lab account (for Cloud API access)
- Local server/machine to host the application

### Installation Steps

1. **Clone/Create Project Structure**
   ```bash
   cd cooking-ai-agent
   ```

2. **Backend Setup**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Configure environment
   cp .env.example .env
   # Add your Bambu Lab credentials and printer details
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. **Run Application**
   ```bash
   python src/main.py
   ```

---

## 📝 Configuration

### .env File
```
# Bambu Lab Credentials
BAMBU_USERNAME=your_email@example.com
BAMBU_PASSWORD=your_password
BAMBU_PRINTER_ID=printer_serial_number

# Server Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Database
DB_PATH=./data/farm.db

# MQTT Settings
MQTT_BROKER=mqtt.bambulab.com
MQTT_PORT=8883
```

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

#### Queue Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/queue` | Get current queue |
| POST | `/api/queue` | Add job to queue |
| PUT | `/api/queue/{queue_id}` | Update queue item position |
| DELETE | `/api/queue/{queue_id}` | Remove from queue |

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

## 📞 Notes

- This is a personal project for 3D print farm automation
- Initial focus on single Bambu Lab A1 Combo AMS
- Design allows easy expansion to multiple printers
- OrcaSlicer handles all file slicing and optimization
- Follow naming conventions to minimize confusion during development

---

**Project Status:** 🚧 In Development - Phase 4 (Testing & Refinement)
**Last Updated:** January 3, 2026

---

## 📝 Development Log

### January 3, 2026 - Print Control & WebSocket Stability Fixes 🔧
**Session Focus:** Fix 7 critical issues with print control buttons and real-time updates

#### ✅ Issues Fixed:

1. **Stop Button Not Working** (Issue #1)
   - **Problem:** Stop button didn't cancel running print
   - **Root Cause:** `stop_print()` used instance variable instead of database query
   - **Solution:** Query database for running queue item:
   ```python
   # OLD (broken)
   queue_item = self.current_print_queue_item
   
   # NEW (working)
   queue_item = db.execute(
       text("SELECT * FROM queue WHERE printer_id = :printer_id AND status = 'running' LIMIT 1"),
       {"printer_id": printer_id}
   ).fetchone()
   ```

2. **Pause Button Not Working** (Issue #2)
   - **Problem:** Pause button didn't pause print
   - **Solution:** Same fix as stop - query database for running item

3. **Process Logs Missing** (Issue #3)
   - **Problem:** No console logs for debugging
   - **Solution:** Added comprehensive logging:
   ```typescript
   // Frontend: PrinterStatus.tsx
   console.log('[PrinterStatus] handlePause clicked, printer:', printer.printerId);
   console.log('[PrinterStatus] Pause API response:', response);
   
   // Backend: print_control.py
   logger.info(f"🔴 [STOP] Button pressed for printer: {printer_id}")
   logger.info(f"⏸️ [PAUSE] Button pressed for printer: {printer_id}")
   ```

4. **Time Display Inaccurate** (Issue #4)
   - **Problem:** Remaining time not showing correctly
   - **Solution:** Added `remaining_time` and `current_file` to WebSocket and API:
   ```python
   # websocket.py
   "remaining_time": status.get("mc_remaining_time", 0),
   "current_file": status.get("subtask_name", ""),
   ```

5. **Resume Button Not Syncing** (Issue #5)
   - **Problem:** Resume button state not matching printer status
   - **Solution:** Added useEffect to sync `isPaused` with printer status:
   ```typescript
   useEffect(() => {
       if (printer.status === 'PAUSED' && !isPaused) {
           setIsPaused(true);
       } else if (printer.status !== 'PAUSED' && isPaused) {
           setIsPaused(false);
       }
   }, [printer.status, isPaused]);
   ```

6. **Button Action Logs Missing** (Issue #6)
   - **Problem:** No logs showing button clicks
   - **Solution:** Added logging to all button handlers and API calls

7. **WebSocket Disconnects Randomly** (Issue #7)
   - **Problem:** WebSocket would disconnect when tab inactive
   - **Solution:** Added heartbeat, visibility change, and focus handlers:
   ```typescript
   // useWebSocket.ts
   
   // Heartbeat response
   if (data.type === 'ping') {
       ws.send(JSON.stringify({ type: 'pong' }));
   }
   
   // Visibility change handler
   document.addEventListener('visibilitychange', () => {
       if (document.visibilityState === 'visible' && !ws?.readyState) {
           connectWebSocket();
       }
   });
   
   // Window focus handler
   window.addEventListener('focus', checkConnection);
   ```

#### 📝 Files Modified:

| File | Changes |
|------|---------|
| `src/services/print_control_service.py` | Database queries for pause/stop/cancel |
| `src/api/print_control.py` | Added logging for all endpoints |
| `src/api/websocket.py` | Added remaining_time, current_file, ping handler |
| `frontend/src/api/client.ts` | Added remainingTime, currentFile to PrinterResponse |
| `frontend/src/components/PrinterStatus.tsx` | Time display, isPaused sync, logging |
| `frontend/src/components/Dashboard.tsx` | Handle new fields in state |
| `frontend/src/hooks/useWebSocket.ts` | Heartbeat, visibility, focus handlers |

#### 🔧 Technical Details:

**Print Control Service Refactor:**
```python
# src/services/print_control_service.py

def pause_print(self, printer_id: str) -> dict:
    """Pause using database query instead of instance variable"""
    with get_db() as db:
        result = db.execute(
            text("""SELECT * FROM queue 
                    WHERE printer_id = :printer_id 
                    AND status IN ('running', 'paused') 
                    LIMIT 1"""),
            {"printer_id": printer_id}
        )
        queue_item = result.fetchone()
        
        if queue_item:
            # Send MQTT pause command
            mqtt_client.pause_print()
            
            # Update database
            db.execute(
                text("UPDATE queue SET status = 'paused' WHERE queue_id = :id"),
                {"id": queue_item.queue_id}
            )
            db.commit()
```

**WebSocket Heartbeat:**
```python
# src/api/websocket.py

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    while True:
        try:
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=1.0
            )
            message = json.loads(data)
            if message.get("type") == "pong":
                # Client responded to ping
                pass
        except asyncio.TimeoutError:
            # Send ping to check connection
            await websocket.send_json({"type": "ping"})
```

---

### January 1, 2026 - Filament Inventory & AMS Slot Management System 📦
**Session Focus:** Complete filament inventory management with AMS slot assignment

#### ✅ Completed Features:

1. **Filament Profile Database** (`src/database/db.py`)
   - New table: `filament_profiles` for storing complete filament specifications
   - Comprehensive filament properties stored:
     - Basic: name, brand, material_type, color_name, color_hex (RRGGBBAA)
     - Temperature: nozzle_temp_min/max/default, bed_temp_min/max/default
     - Print settings: max_volumetric_speed, k_value (pressure advance)
     - Physical: density, diameter (1.75/2.85mm), spool_weight
     - Drying: drying_temp, drying_time
     - Compatibility: requires_enclosure, requires_hardened_nozzle
     - Stock: stock_count, notes, purchase_link

2. **AMS Slot Assignment Database** (`migrate_ams_slots.py`)
   - New table: `ams_slot_assignments` linking slots to filament inventory
   - Schema:
     ```sql
     CREATE TABLE ams_slot_assignments (
         id INTEGER PRIMARY KEY,
         printer_id TEXT NOT NULL,
         slot_number INTEGER NOT NULL,
         filament_id INTEGER,  -- FK to filament_profiles
         remaining_grams REAL DEFAULT 0,
         assigned_at TIMESTAMP,
         updated_at TIMESTAMP,
         UNIQUE(printer_id, slot_number)
     )
     ```

3. **Filament API Endpoints** (`src/api/filaments.py`)

   | Method | Endpoint | Description |
   |--------|----------|-------------|
   | GET | `/api/filaments` | List all filament profiles |
   | POST | `/api/filaments` | Create new filament profile |
   | GET | `/api/filaments/{id}` | Get filament by ID |
   | PUT | `/api/filaments/{id}` | Update filament profile |
   | DELETE | `/api/filaments/{id}` | Delete filament |
   | GET | `/api/filaments/slots/{printer_id}` | Get slot assignments with filament details |
   | POST | `/api/filaments/slots/{printer_id}/{slot}` | Assign filament to slot |
   | PUT | `/api/filaments/slots/{printer_id}/{slot}/remaining` | Update remaining grams |
   | POST | `/api/filaments/{id}/apply/{printer_id}/{slot}` | Apply filament settings to printer |
   | POST | `/api/filaments/{id}/stock/add` | Add stock to filament |

4. **Frontend Filament Inventory Tab** (`frontend/src/components/FilamentInventoryTab.tsx`)
   - Grid display of all filaments with color swatches
   - Add new filament form with all properties
   - Edit existing filament
   - Delete filament
   - Stock management (add/remove spools)
   - Search and filter by material type

5. **AMS Status Display Component** (`frontend/src/components/AmsStatusDisplay.tsx`)
   - Visual 4-slot AMS representation
   - Click slot to edit assignment
   - Shows: filament name, brand, material type, color, remaining grams
   - Connection status indicator
   - Current active slot highlight

6. **Slot Assignment Modal Flow**
   ```
   User clicks "Edit" on slot
       ↓
   Modal opens with filament selection grid
       ↓
   User selects filament from inventory
       ↓
   API: POST /api/filaments/slots/{printer_id}/{slot}
       ↓
   MQTT: ams_filament_setting() sent to printer
       ↓
   UI updates with new filament info
       ↓
   Load/Unload buttons available
   ```

7. **AMS MQTT Commands** (`src/services/bambu_service.py`)
   ```python
   # Set filament settings on AMS slot
   def ams_filament_setting(slot, tray_color, tray_type):
       command = {
           "print": {
               "sequence_id": "0",
               "command": "ams_filament_setting",
               "ams_id": 0,
               "tray_id": slot,
               "tray_color": tray_color,  # "FF0000FF" format
               "nozzle_temp_min": 190,
               "nozzle_temp_max": 240,
               "tray_type": tray_type  # "PLA", "PETG", etc.
           }
       }
   
   # Load filament from slot
   def ams_load_filament(slot):
       command = {"print": {"command": "ams_change_filament", "target": slot}}
   
   # Unload current filament
   def ams_unload_filament():
       command = {"print": {"command": "unload_filament"}}
   ```

#### 📊 Database Schema:

**Table: filament_profiles**
```
filament_id       INTEGER PRIMARY KEY
name              TEXT NOT NULL        -- "Bambu PLA Basic - Black"
brand             TEXT NOT NULL        -- "Bambu Lab"
material_type     TEXT NOT NULL        -- "PLA", "PETG", "ABS"
color_name        TEXT                 -- "Matte Black"
color_hex         TEXT DEFAULT "000000FF"  -- RRGGBBAA
nozzle_temp_min   INTEGER DEFAULT 190
nozzle_temp_max   INTEGER DEFAULT 240
nozzle_temp_default INTEGER DEFAULT 220
bed_temp_min      INTEGER DEFAULT 45
bed_temp_max      INTEGER DEFAULT 65
bed_temp_default  INTEGER DEFAULT 55
max_volumetric_speed REAL DEFAULT 12.0
k_value           REAL DEFAULT 0.02
density           REAL DEFAULT 1.24
diameter          REAL DEFAULT 1.75
spool_weight      REAL DEFAULT 1000
drying_temp       INTEGER DEFAULT 50
drying_time       INTEGER DEFAULT 8
requires_enclosure BOOLEAN DEFAULT FALSE
requires_hardened_nozzle BOOLEAN DEFAULT FALSE
notes             TEXT
purchase_link     TEXT
stock_count       INTEGER DEFAULT 0
is_active         BOOLEAN DEFAULT TRUE
created_at        TIMESTAMP
updated_at        TIMESTAMP
```

**Table: ams_slot_assignments**
```
id                INTEGER PRIMARY KEY
printer_id        TEXT NOT NULL
slot_number       INTEGER NOT NULL (0-3)
filament_id       INTEGER FK → filament_profiles
remaining_grams   REAL DEFAULT 0
assigned_at       TIMESTAMP
updated_at        TIMESTAMP
UNIQUE(printer_id, slot_number)
```

#### 📝 Files Created/Modified:

| File | Purpose |
|------|---------|
| `src/database/db.py` | FilamentProfile SQLAlchemy model |
| `src/api/filaments.py` | Full CRUD API + slot assignment endpoints |
| `migrate_filament_profiles.py` | Migration script for filament_profiles table |
| `migrate_ams_slots.py` | Migration script for ams_slot_assignments table |
| `frontend/src/components/FilamentInventoryTab.tsx` | Inventory UI component |
| `frontend/src/components/AmsStatusDisplay.tsx` | AMS visual display + slot editing |
| `frontend/src/api/client.ts` | API client methods + transformFilament fix |

#### 🔧 Bug Fixes:

1. **SQL text() wrapper** - Fixed raw SQL queries with `sqlalchemy.text()`
2. **filament_id mapping** - Fixed `transformFilament` to use `f.filament_id || f.id`
3. **Slot assignment API** - Fixed 500 error on `/api/filaments/slots/{printer_id}`

---

### January 1, 2026 - AMS Filament Load/Unload Progress Display 🔄
**Session Focus:** Implement realistic load/unload progress UI matching printer screen

#### ✅ Completed:

1. **AMS Slot Management UI Improvements** (`frontend/src/components/AmsStatusDisplay.tsx`)
   - Removed remaining filament input box from detail modal (user request: "nggak perlu ada remaining fillament input box")
   - Added load/unload progress display matching printer's 6-step process
   - Progress stays visible until user clicks Done/Cancel (tidak langsung hilang)

2. **Load Progress Steps (Matching Printer Display)**
   ```typescript
   const LOAD_STEPS = [
     { name: 'Heat the Nozzle', showTemp: true },      // Step 1 - Shows temperature
     { name: 'Check filament location', showTemp: false },
     { name: 'Cut filament', showTemp: false },
     { name: 'Pull back current filament', showTemp: false },
     { name: 'Push new filament into extruder', showTemp: false },
     { name: 'Purge old filament', showTemp: false },  // Step 6
   ];
   
   const UNLOAD_STEPS = [
     { name: 'Heat the Nozzle', showTemp: true },
     { name: 'Check filament location', showTemp: false },
     { name: 'Pull back filament', showTemp: false },
     { name: 'Complete', showTemp: false },
   ];
   ```

3. **Temperature Display During Heating**
   - Shows real-time nozzle temperature during "Heat the Nozzle" step
   - Format: `(30°C → 220°C)` with yellow color highlight
   - Temperature simulated incrementally (will be replaced with real MQTT data)

4. **Progress State Management**
   ```typescript
   const [loadProgress, setLoadProgress] = useState<{
     active: boolean,      // Is progress display visible
     step: number,         // Current step index (0-5)
     isUnload: boolean,    // Load vs Unload mode
     nozzleTemp: number,   // Current nozzle temperature
     targetTemp: number,   // Target temperature (220°C)
     completed: boolean    // All steps done
   }>({
     active: false, step: 0, isUnload: false, 
     nozzleTemp: 0, targetTemp: 220, completed: false
   });
   ```

5. **Progress UI Features**
   - Dark theme modal matching printer display aesthetic
   - Numbered steps with circular indicators
   - ✓ checkmark for completed steps
   - ⏳ spinner for current step
   - Blue highlight for active step
   - Green "Complete" badge when finished
   - **Done** button - closes progress (green)
   - **Retry** button - runs load/unload again
   - **Cancel** button - stops and closes progress (red)

6. **API Integration**
   - Fixed SQL queries with `sqlalchemy.text()` wrapper for slot assignments
   - Fixed `transformFilament` to use `f.filament_id || f.id` for proper ID mapping
   - Load/Unload commands sent via `printFarmClient.amsLoadFilament()` / `amsUnloadFilament()`

#### 🎨 Visual Design:

```
┌─────────────────────────────────────────┐
│ 🔄 Load Filament              ✓ Complete │
├─────────────────────────────────────────┤
│ ✓ 1  Heat the Nozzle (220°C → 220°C)    │
│ ✓ 2  Check filament location            │
│ ✓ 3  Cut filament                       │
│ ✓ 4  Pull back current filament         │
│ ✓ 5  Push new filament into extruder    │
│ ✓ 6  Purge old filament                 │
├─────────────────────────────────────────┤
│  [  ✓ Done  ]    [  ↻ Retry  ]          │
└─────────────────────────────────────────┘
```

#### 📝 Files Modified:

| File | Changes |
|------|---------|
| `frontend/src/components/AmsStatusDisplay.tsx` | Complete overhaul of load progress system |
| `frontend/src/api/client.ts` | Fixed `transformFilament` ID mapping |
| `src/api/filaments.py` | Added `sqlalchemy.text()` wrapper for raw SQL |

#### 🔧 Technical Details:

**State Flow:**
```
User clicks "Load Filament"
    ↓
setLoadProgress({ active: true, step: 0, nozzleTemp: 0 })
    ↓
Send MQTT load command via API
    ↓
Interval updates temperature (simulated heating)
    ↓
When temp >= 200°C, advance to step 1
    ↓
Auto-advance through steps 2-5
    ↓
setLoadProgress({ completed: true })
    ↓
User clicks "Done" to close
```

**Interval Cleanup:**
```typescript
// Store interval ID for cleanup
(window as any).__loadProgressInterval = progressInterval;

// Cancel function clears interval
const handleCancelProgress = () => {
  if ((window as any).__loadProgressInterval) {
    clearInterval((window as any).__loadProgressInterval);
  }
  setLoadProgress({ active: false, ... });
};
```

#### 🔜 Future Improvements:
- [ ] Poll actual printer temperature via MQTT instead of simulation
- [ ] Get real step status from `mc_print_stage` MQTT field
- [ ] Add error handling if load/unload fails
- [ ] Sound notification when complete

---

### January 1, 2026 - SD Card Print via MQTT (CRITICAL DISCOVERY) 🎉
**Session Focus:** Print file langsung dari SD card printer via MQTT command

#### ✅ SOLVED: Print from SD Card

Setelah mempelajari FDM Monster dan OctoPrint-BambuPrinter, ditemukan format yang benar untuk mengirim perintah print file dari SD card:

**Format MQTT Command yang BENAR untuk Bambu Lab A1:**
```python
project_command = {
    "print": {
        "sequence_id": str(int(time.time() * 1000)),  # Timestamp string, BUKAN "0"
        "command": "project_file",
        "param": "Metadata/plate_1.gcode",  # Gcode path dalam 3MF
        "md5": "",
        "profile_id": "0",
        "project_id": "0",
        "subtask_id": "0",
        "task_id": "0",
        "subtask_name": "filename.3mf",  # Nama file untuk display di UI
        "url": "file:///sdcard/cache/filename.3mf",  # ⚠️ PENTING: format ini!
        "bed_type": "auto",
        "timelapse": False,
        "bed_leveling": True,
        "flow_cali": False,
        "vibration_cali": False,
        "layer_inspect": False,
        "use_ams": True,
        "ams_mapping": ""
    }
}
```

#### 🔑 Key Findings:

| Parameter | Format yang Benar | Catatan |
|-----------|-------------------|---------|
| **URL** | `file:///sdcard/{path}` | Harus ada "sdcard" di path! (dari FDM Monster) |
| **sequence_id** | `str(int(time.time() * 1000))` | Timestamp string, bukan "0" |
| **param** | `Metadata/plate_1.gcode` | Path gcode dalam file 3MF |
| **subtask_name** | Nama file saja | Untuk display di layar printer |

#### ⚠️ Perbedaan Format URL:

| Source | URL Format | Keterangan |
|--------|------------|------------|
| **FDM Monster** ✅ | `file:///sdcard/{filename}` | WORKING untuk A1! |
| **OctoPrint-BambuPrinter (A1/P1)** | `file:///{path}` | Tanpa "sdcard" |
| **OctoPrint-BambuPrinter (X1/X1C)** | `file:///mnt/sdcard/{path}` | Dengan "mnt" |

#### 📍 File Location di SD Card:
- File yang di-upload via FTPS: `cache/filename.3mf`
- File yang di-slice di printer: root folder `filename.3mf`

#### ✅ Test Result:
```
POST /api/printer-files/print/cache%2Fadded%20compensation%2C%200.16mm%20layer%2C%202%20walls%2C%2010%25%20infill.3mf

Response: {"status": "success", "message": "Print started from SD card..."}
Printer: RUNNING ✅ (Heating → Printing)
```

#### 📝 Files Modified:
- `src/services/bambu_service.py` - `start_print_from_sd()` function updated
- `src/api/printer_files.py` - Endpoint `/print/{filename:path}`

#### 🔗 Reference Code:
- FDM Monster: `src/services/bambu/bambu-mqtt.adapter.ts` → `startPrint()`
- OctoPrint-BambuPrinter: `octoprint_bambu_printer/printer/states/idle_state.py` → `_get_print_command_for_file()`
- Home Assistant Bambu Lab: `greghesp/ha-bambulab` → `pybambu/commands.py`
- OpenBambuAPI: `Doridian/OpenBambuAPI` → `mqtt.md`

---

### January 3, 2026 - MQTT Print Command Reference & Troubleshooting 📚
**Session Focus:** Comprehensive documentation for sending print commands to Bambu Lab printers

#### 📤 Complete MQTT Print Command Reference

##### 1. `project_file` Command (Recommended for 3MF files)

This is the primary command to start printing a sliced 3MF file from SD card:

```python
# File: src/services/bambu_service.py - start_print_from_sd()

project_command = {
    "print": {
        # Required fields
        "sequence_id": str(int(time.time() * 1000)),  # Unique timestamp
        "command": "project_file",
        "param": "Metadata/plate_1.gcode",            # Gcode path inside 3MF
        "url": "file:///sdcard/filename.3mf",         # SD card URL
        "subtask_name": "filename.3mf",               # Display name on LCD
        
        # IDs (always "0" for local prints)
        "md5": "",
        "profile_id": "0",
        "project_id": "0", 
        "subtask_id": "0",
        "task_id": "0",
        
        # Print options
        "bed_type": "auto",           # "auto", "textured_plate", "cool_plate", etc.
        "timelapse": False,           # Create timelapse video
        "bed_leveling": True,         # Auto bed leveling before print
        "flow_cali": False,           # Flow calibration
        "vibration_cali": False,      # Vibration/resonance calibration
        "layer_inspect": False,       # First layer inspection
        
        # AMS options
        "use_ams": True,              # Use AMS for filament
        "ams_mapping": [0]            # Array mapping slicer colors to AMS slots
    }
}
```

##### 2. URL Format by Printer Type

| Printer | URL Format | Example |
|---------|------------|---------|
| **A1 / A1 Mini** | `file:///sdcard/{path}` | `file:///sdcard/cache/model.3mf` |
| **P1P / P1S** | `file:///{path}` | `file:///cache/model.3mf` |
| **X1 / X1C** | `file:///mnt/sdcard/{path}` | `file:///mnt/sdcard/cache/model.3mf` |
| **FTP URL** | `ftp:///{path}` | `ftp:///model.3mf` |

##### 3. `param` Field - Gcode Path in 3MF

The `param` field specifies which gcode to use inside the 3MF archive:
- Single plate: `Metadata/plate_1.gcode`
- Multi-plate: `Metadata/plate_2.gcode`, `Metadata/plate_3.gcode`, etc.

##### 4. AMS Mapping

The `ams_mapping` array maps slicer filament colors to physical AMS slots:
```python
# Example: 4-color print
"ams_mapping": [0, 1, 2, 3]  # Colors 1-4 → Slots 1-4

# Example: Skip colors (use -1)
"ams_mapping": [0, -1, 2, -1]  # Color 1→Slot 1, Color 3→Slot 3

# Single color print
"ams_mapping": [0]  # Use slot 1
```

#### 📁 3MF File Structure Requirements

A properly sliced 3MF file must contain these files for printer to work correctly:

```
model.3mf (ZIP archive)
├── 3D/
│   └── 3dmodel.model              # 3D model data
├── Metadata/
│   ├── plate_1.gcode              # ✅ REQUIRED - Sliced gcode
│   ├── plate_1.gcode.md5          # MD5 checksum
│   ├── plate_1.json               # Plate settings (bed type, etc.)
│   ├── plate_1.png                # ✅ Thumbnail (shown on LCD)
│   ├── plate_1_small.png          # Small thumbnail
│   ├── top_1.png                  # Top view
│   ├── pick_1.png                 # Pick image for object detection
│   ├── model_settings.config      # Model configuration
│   ├── slice_info.config          # ✅ Slice metadata (time, weight)
│   └── project_settings.config    # Project settings
├── [Content_Types].xml
└── _rels/.rels
```

##### `slice_info.config` Contents (Metadata)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<config>
  <header>
    <header_item key="X-BBL-Client-Type" value="slicer"/>
    <header_item key="X-BBL-Client-Version" value="01.07.08.02"/>
  </header>
  <plate>
    <metadata key="index" value="1"/>
    <metadata key="prediction" value="1302"/>      <!-- Print time in seconds -->
    <metadata key="weight" value="10.99"/>          <!-- Filament weight in grams -->
    <metadata key="timelapse_type" value="0"/>
    <metadata key="outside" value="false"/>
    <metadata key="support_used" value="false"/>
  </plate>
</config>
```

#### ⚠️ Known Issue: Thumbnail/Time/Weight Not Showing on Printer LCD

**Problem:** When printing via MQTT `project_file` command, the printer LCD may not show:
- Thumbnail image
- Estimated print time
- Filament weight (grams)

**Root Cause:** 
The Bambu printer reads metadata (thumbnail, time, weight) directly from the **3MF file itself**, not from the MQTT command. The printer extracts this data from:
- `Metadata/plate_X.png` → Thumbnail
- `Metadata/slice_info.config` → Time & weight

**Solutions:**

1. **Ensure file is sliced with OrcaSlicer/Bambu Studio**
   - Files sliced with these tools contain all required metadata
   - Avoid manually creating or modifying 3MF archives

2. **Verify 3MF structure before upload**
   ```python
   # Use check_3mf_structure.py to verify
   python check_3mf_structure.py
   
   # Should show:
   # 🔧 Metadata/plate_1.gcode (1,486,275 bytes) <-- GCODE
   # 🖼️ Metadata/plate_1.png (21,870 bytes) <-- THUMBNAIL
   ```

3. **Check slice_info.config has prediction and weight**
   ```xml
   <metadata key="prediction" value="1302"/>  <!-- Time in seconds -->
   <metadata key="weight" value="10.99"/>     <!-- Weight in grams -->
   ```

4. **Known limitation:** For LAN mode prints started via MQTT, some metadata display features may be limited compared to prints started from Bambu Studio directly.

#### 🔧 Troubleshooting Print Command Errors

##### Error: "Print command failed"

| Symptom | Cause | Solution |
|---------|-------|----------|
| File not found | Wrong URL path | Check file exists in SD card, use correct path prefix |
| Printer busy | Already printing | Wait for current job or send stop command first |
| Invalid gcode path | Wrong `param` value | Use `Metadata/plate_1.gcode` format |
| AMS error | Wrong ams_mapping | Check slot numbers match loaded filaments |

##### Error: "sequence_id" issues

```python
# ❌ WRONG - Static sequence_id
"sequence_id": "0"

# ✅ CORRECT - Unique timestamp
"sequence_id": str(int(time.time() * 1000))
```

##### Error: File in cache vs root

| Location | Path in URL | When |
|----------|-------------|------|
| Root `/` | `file:///sdcard/model.3mf` | Sliced directly on printer |
| Cache `/cache/` | `file:///sdcard/cache/model.3mf` | Uploaded via FTPS/Studio |

##### Debug: Check file exists on SD card

```python
# Use FTPS to list files
python explore_sd_card.py

# Or via API
GET /api/printer-files
```

#### 📊 MQTT Topics for Bambu Lab

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `device/{printer_id}/request` | Client → Printer | Send commands |
| `device/{printer_id}/report` | Printer → Client | Receive status |

#### 🔄 Print Control Commands

```python
# Pause print
{"print": {"sequence_id": "0", "command": "pause"}}

# Resume print  
{"print": {"sequence_id": "0", "command": "resume"}}

# Stop/Cancel print
{"print": {"sequence_id": "0", "command": "stop"}}

# Send raw G-code
{"print": {"sequence_id": "0", "command": "gcode_line", "param": "G28 X Y\n"}}
```

#### 📝 Implementation Reference

**Backend file:** `src/services/bambu_service.py`
```python
def start_print_from_sd(self, filename: str, plate_number: int = 1, 
                        use_ams: bool = True, ams_mapping = None) -> bool:
    """
    Start printing a file from printer's SD card
    
    Args:
        filename: File path on SD card (e.g., "cache/model.3mf")
        plate_number: Which plate to print (1-4)
        use_ams: Whether to use AMS for filament
        ams_mapping: List mapping slicer colors to AMS slots
    
    Returns:
        bool: True if command sent successfully
    """
```

**API Endpoint:** `src/api/printer_files.py`
```python
@router.post("/print/{filename:path}")
async def start_print_from_sd_card(filename: str, plate: int = 1):
    """
    Start print from SD card file
    
    - filename: URL-encoded path (e.g., cache%2Fmodel.3mf)
    - plate: Plate number (default 1)
    """
```

---

### December 30, 2025 - UI/UX Enhancement Session
**Session Focus:** Improve user feedback for file operations and implement visual progress indicators

#### ✅ Completed:

1. **Enhanced Upload Success Messages** (`src/api/jobs.py` + `frontend/src/components/QueueDashboard.tsx`)
   - Added file size display in MB (calculated from file bytes)
   - Display printer name in success message
   - Show job ID for reference
   - Added emoji indicators (📤, ✅) for visual clarity
   - Example output: `"✅ Successfully uploaded 'model.3mf' (5.23MB) - Added to Bambu Lab A1 queue (Job #3)"`
   
   **Backend Changes:**
   ```python
   file_size_mb = len(content) / (1024 * 1024)
   logger.info(f"📤 Uploaded file: {filename}, size: {file_size_mb:.2f} MB")
   logger.info(f"✅ Job created successfully: job_id={job_response.job_id}, name={job_response.job_name}, loops={loop_count}, size={file_size_mb:.2f}MB")
   ```
   
   **Frontend Changes:**
   ```typescript
   const fileSizeMB = (selectedFile.size / (1024 * 1024)).toFixed(2);
   const printerName = printers.find(p => p.printerId === selectedUploadPrinter)?.printerName || 'printer';
   setMessage({ 
       type: 'success', 
       text: `✅ Successfully uploaded "${job.jobName}" (${fileSizeMB}MB) - Added to ${printerName} queue (Job #${job.jobId})` 
   });
   ```

2. **Enhanced Delete Messages with Location Awareness** (`src/services/ftps_service.py` + `src/api/printer_files.py` + `frontend/src/components/PrinterFilesTab.tsx`)
   - Added location detection (root directory vs cache directory)
   - Display file location in delete messages
   - Enhanced logging with directory information
   - Added location emoji indicators (📁 root/, 📂 cache/)
   - Example output: `"🗑️ Successfully deleted: 📂 cache/model.3mf"`
   
   **FTPS Service Enhancement:**
   ```python
   def delete_file(self, remote_filename: str) -> bool:
       location = "cache directory" if remote_filename.startswith("cache/") else "root directory"
       logger.info(f"🗑️ Deleting file from {location}: {remote_filename}")
       self.ftp.delete(remote_filename)
       logger.info(f"✅ Successfully deleted from SD card ({location}): {remote_filename}")
       return True
   ```
   
   **API Response Enhancement:**
   ```python
   location = "cache" if filename.startswith("cache/") else "root"
   display_name = filename.split("/")[-1]
   return {
       "status": "success",
       "message": f"Successfully deleted from {location} directory: {display_name}",
       "filename": filename,
       "location": location,
       "display_name": display_name
   }
   ```
   
   **Frontend Display:**
   ```typescript
   const location = data.location || (fileToDelete.includes('/') ? 'cache' : 'root');
   const locationLabel = location === 'cache' ? '📂 cache/' : '📁 root/';
   const successMsg = `🗑️ Successfully deleted: ${locationLabel}${filename}`;
   ```

3. **Upload Progress Bar Implementation** (`frontend/src/api/client.ts` + `frontend/src/components/QueueDashboard.tsx`)
   - Real-time upload progress tracking using Axios onUploadProgress
   - Visual progress bar with percentage display (0-100%)
   - Color transition: Blue (uploading) → Green (complete)
   - Dynamic status text: "📤 Uploading file to server..." → "✓ Processing..."
   - Smooth animations and transitions
   
   **API Client Update:**
   ```typescript
   async uploadJob(file: File, loopCount: number, onProgress?: (percent: number) => void): Promise<JobResponse> {
       const response = await this.apiClient.post('/jobs/upload', formData, {
           headers: { 'Content-Type': 'multipart/form-data' },
           onUploadProgress: (progressEvent) => {
               if (progressEvent.total && onProgress) {
                   const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                   onProgress(percentCompleted);
               }
           },
       });
       return transformedJobResponse;
   }
   ```
   
   **Progress Bar UI:**
   ```tsx
   const [uploadProgress, setUploadProgress] = useState(0);
   
   // Upload with progress callback
   const job = await printFarmClient.uploadJob(selectedFile, loopCount, (percent) => {
       setUploadProgress(percent);
   });
   
   // Progress bar component
   {isUploading && (
       <div style={{ marginTop: '16px' }}>
           <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
               <span style={{ fontSize: '13px', color: '#6b7280', fontWeight: 500 }}>Uploading...</span>
               <span style={{ fontSize: '13px', color: '#2563eb', fontWeight: 600 }}>{uploadProgress}%</span>
           </div>
           <div style={{ width: '100%', height: '8px', backgroundColor: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
               <div style={{
                   width: `${uploadProgress}%`,
                   height: '100%',
                   backgroundColor: uploadProgress === 100 ? '#10b981' : '#2563eb',
                   transition: 'width 0.3s ease, background-color 0.3s ease',
                   borderRadius: '4px'
               }} />
           </div>
           <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '6px' }}>
               {uploadProgress < 100 ? '📤 Uploading file to server...' : '✓ Processing...'}
           </div>
       </div>
   )}
   ```

4. **Queue Management**
   - Cleared queue using `clear_queue.py` utility
   - Removed 2 pending jobs from database
   - Database reset to clean state (0 jobs)

5. **Server Restart Workflow Standardization**
   - Established mandatory restart procedure:
     1. Kill all Python and Node.js processes
     2. Execute `start.bat` to launch all services
   - **CRITICAL WORKFLOW**: Must always follow this sequence
   - Commands:
     ```powershell
     taskkill /F /IM python.exe 2>$null
     taskkill /F /IM node.exe 2>$null
     Start-Sleep 3
     cd "c:\Users\GIGABYTE\Documents\3d Print farm\cooking-ai-agent"
     .\start.bat
     ```
   - Successfully restarted services:
     - Backend: Running on port 5000 ✅
     - Frontend: Running on port 3000 ✅

#### 🎯 Key Improvements:

**User Experience:**
- Upload operations now provide comprehensive feedback (file size, printer, job ID)
- Delete operations show file location context (root vs cache)
- Visual progress bar provides real-time upload feedback
- Emoji indicators improve message scannability
- Color-coded progress states (blue → green) for visual confirmation

**Code Quality:**
- Consistent emoji usage across backend logs and frontend messages
- Proper metadata passing from backend to frontend
- Reusable progress callback pattern for future features
- Location-aware file operations for better context

**System Stability:**
- Standardized server restart workflow prevents port conflicts
- Clean process termination before restart
- Documented procedure for consistent operations

#### 📊 Test Results:

**Manual Testing:**
- ✅ Upload with progress bar: Visual feedback working correctly
- ✅ Upload success message: Shows file size, printer name, job ID
- ✅ Delete from root directory: Shows "📁 root/filename"
- ✅ Delete from cache: Shows "📂 cache/filename"
- ✅ Progress bar color transition: Blue → Green at 100%
- ✅ Status text changes: "Uploading..." → "Processing..."
- ✅ Server restart: All processes killed, services restarted successfully

**Performance:**
- Progress bar updates smoothly (no lag)
- Messages display instantly after operations
- No performance degradation from enhancements

#### 🔜 Next Steps:
- User validation of enhanced messages in real workflow
- Test progress bar with larger files (>100MB)
- Consider adding progress bar for delete operations
- Add error state indicators to progress bar
- Implement similar feedback for print operations

#### 📝 Modified Files:
```
Backend:
├── src/api/jobs.py                 (Upload message enhancement)
├── src/api/printer_files.py        (Delete response with location metadata)
└── src/services/ftps_service.py    (Delete logging with location)

Frontend:
├── src/api/client.ts               (Upload progress callback support)
├── src/components/QueueDashboard.tsx    (Progress bar + upload messages)
└── src/components/PrinterFilesTab.tsx   (Location-aware delete messages)

Scripts:
└── clear_queue.py                  (Executed to clear database)
```

---

### December 30, 2025 - Direct FTPS Upload Implementation
**Session Focus:** Implement direct SD card upload without HTTP server

#### ✅ Completed:

1. **FTPS Direct Upload Service** (`src/services/ftps_service.py`)
   - `SimpleFTPSClient` - Core FTPS client with implicit SSL/TLS
   - `BambuFTPSClient` - Wrapper for easy use
   - `BambuDirectUploadService` - High-level upload service
   - Features:
     - Implicit FTPS connection (port 990)
     - Binary file transfer with chunked uploads (64KB blocks)
     - Progress callback support
     - SSL certificate validation disabled (self-signed printer certs)
     - Context manager support for safe connections

2. **Integration with MQTT** (`src/services/bambu_service.py`)
   - New method: `send_print_file_direct()`
   - Workflow:
     1. Upload file via FTPS to printer SD card
     2. Wait 1 second for printer to register
     3. Send MQTT start command
   - Tested and working!

3. **API Endpoint** (`src/api/jobs.py`)
   - `POST /api/jobs/upload-direct/{job_id}/print`
   - Handles job lookup, file verification, and direct upload
   - Returns success message with method confirmation

4. **Test Suite** (`test_direct_upload.py`)
   - Test 1: FTPS Connection ✅ PASS
   - Test 2: MQTT Connection ✅ PASS
   - Test 3: Direct Upload + Print ✅ PASS
   - Full end-to-end workflow validated

#### Test Results:
```
FTPS Connection......................... ✅ PASS
MQTT Connection......................... ✅ PASS
Direct Upload + Print................... ✅ PASS

✅ All tests passed!
```

#### Key Achievements:
- ✅ Port 990 FTPS connection successful
- ✅ File upload to printer SD card verified
- ✅ MQTT start command integration working
- ✅ No HTTP server required
- ✅ Full automation pipeline functional

#### Code Example - Direct Upload:
```python
# Upload file directly and start print
PRINTER_IP = "192.168.4.101"
ACCESS_CODE = "34782589"

mqtt_client = BambuLabMQTTClient(
    printer_id="03900D5A2402051",
    printer_ip=PRINTER_IP,
    access_code=ACCESS_CODE,
    use_lan_mode=True
)

mqtt_client.connect()

# Direct FTPS upload + MQTT print
success = mqtt_client.send_print_file_direct("model.3mf")

if success:
    print("✅ Upload successful, print started!")
    # Check printer LCD to see print starting
```

---

### December 30, 2025 - Earlier Sessions
**Session Focus:** Printer Integration Testing

#### ✅ Completed:
1. **MQTT LAN Mode Connection**
   - Switched from Cloud API to LAN mode
   - Connected via `192.168.4.101:8883` with TLS
   - Username: `bblp`, Password: Access Code
   - Status push working - receiving printer telemetry

2. **Auto-Eject Feature**
   - Endpoint: `POST /api/print-control/{printer_id}/eject`
   - G-code sequence: `G28 X Y` → `G1 Y 230 F6000` → `M400`
   - **Tested & Working!** Printer moves bed forward for easy part removal

3. **Print Control API**
   - Start print: `POST /api/print-control/{printer_id}/start-print`
   - Pause/Resume/Stop endpoints functional
   - Queue integration working

4. **WebSocket Real-time Updates**
   - Backend: `src/api/websocket.py` with ConnectionManager
   - Frontend: `useWebSocket.ts` hook
   - Broadcasts printer status changes

5. **Frontend Dashboard**
   - Tabbed interface: Status | Queue | Upload | History
   - Components: Dashboard, QueueDashboard, HistoryViewer, JobUploadForm
   - Clean modern UI with Tailwind CSS

6. **Camera Integration**
   - Live MJPEG stream from printer camera
   - Endpoints: `/api/camera/snapshot`, `/api/camera/stream`
   - Printer info display: Model, serial number, IP, access code
   - Auto-refresh with 500ms polling

#### ⚠️ Known Issues (RESOLVED):
1. **FTP Upload Not Available (FIXED)**
   - Bambu A1 port 990 (FTPS) in LAN mode uses implicit TLS
   - **Solution**: Implemented proper FTPS client with implicit SSL wrapping
   - Result: Direct FTPS upload now working perfectly ✅

2. **HTTP Server Alternative (Still Available)**
   - If FTPS fails for any reason, HTTP server method available as fallback
   - Backend serves files via `/uploads` endpoint at port 5000

#### 🔜 Next Steps:
1. Test HTTP camera streaming from outside network
2. Implement loop counter for repeated prints
3. Auto-eject integration with job queue
4. Printer status monitoring improvements
5. Multi-printer scalability

---

## ✨ Recent Session Accomplishments

### Direct FTPS Upload - Technical Implementation

**Architecture:**
```
User uploads file
    ↓
Database stores job reference
    ↓
POST /api/jobs/upload-direct/{job_id}/print
    ↓
Backend retrieves file path from job_id
    ↓
FTPS Client connects to 192.168.4.101:990
    ↓
Implicit SSL/TLS wrap socket
    ↓
Authenticate: username="bblp", password=access_code
    ↓
Binary upload with chunked transfer
    ↓
Monitor progress via callback
    ↓
MQTT start command sent
    ↓
Printer begins print immediately
```

**File: `src/services/ftps_service.py`**
```python
class SimpleFTPSClient:
    """Pure socket-based FTPS with implicit SSL"""
    - connect() - Establish FTPS connection
    - upload_file() - Transfer file with progress tracking
    - _send_command() - FTP command execution
    - Context manager support

class BambuFTPSClient:
    """Wrapper for easier usage"""
    
class BambuDirectUploadService:
    """High-level service interface"""
    - upload_to_sd() - Simple method for uploads
```

**File: `src/services/bambu_service.py`**
```python
def send_print_file_direct(self, file_path: str) -> bool:
    """
    Step 1: Upload file via FTPS to printer
    Step 2: Wait 1 second
    Step 3: Send MQTT start command
    
    Returns: True if successful
    """
```

**File: `src/api/jobs.py`**
```python
@router.post("/upload-direct/{job_id}/print")
async def upload_and_print_direct(job_id: int):
    """
    1. Look up job by ID
    2. Get file path from database
    3. Call mqtt_client.send_print_file_direct()
    4. Return result
    """
```

### Performance Metrics

| Operation | Time | Status |
|-----------|------|--------|
| FTPS connect | ~1 second | ✅ |
| File upload (280 bytes) | ~2 seconds | ✅ |
| Upload progress callback | Real-time | ✅ |
| MQTT start command | Instant | ✅ |
| Total end-to-end | ~3-5 seconds | ✅ |

### File Structure
```
src/services/
├── bambu_service.py        (MQTT + send_print_file_direct method)
├── ftps_service.py         (NEW - FTPS client implementation)
├── job_service.py
└── ...

src/api/
├── jobs.py                 (New endpoint: upload-direct/{job_id}/print)
└── ...

tests/
├── test_direct_upload.py   (NEW - Full test suite)
└── ...

Documentation:
├── README.md               (This file - updated)
└── DIRECT_UPLOAD.md        (Detailed technical docs)
```

### Testing & Validation

**All 3 Tests Passing:**
```
✅ Test 1: FTPS Connection
   - Connect to 192.168.4.101:990
   - Implicit SSL/TLS wrapping
   - User authentication
   
✅ Test 2: MQTT Connection  
   - Connect to 192.168.4.101:8883
   - Retrieve printer status
   - Verify online status
   
✅ Test 3: Direct Upload + Print
   - End-to-end workflow
   - FTPS file transfer
   - MQTT start command
   - Monitor progress
```

**Run Tests:**
```bash
cd cooking-ai-agent
python test_direct_upload.py
# Or with auto-test mode:
$env:AUTO_TEST='true'; python test_direct_upload.py
```

---

## 📝 Changelog

### January 7, 2026 - Filament Temperature Override & Placeholder Fix

#### ✅ Completed Changes

**1. Filament Profile Temperature Override**
- Added `filament_id` parameter throughout the queue processing pipeline
- Queue items now store `filament_id` from selected AMS slot assignment
- Backend fetches filament profile from database and uses temperatures for G-code processing
- Files: `src/services/queue_service.py`, `src/api/queue.py`

**2. OrcaSlicer Placeholder Replacement**
- Fixed `{filament_already_loaded}` placeholder not being replaced in template mode
- Modified `_replace_filament_variables()` to accept `print_settings` parameter
- Added replacement: `{filament_already_loaded}` → `1` (skip flush) or `0` (do flush)
- Both template mode and section toggle mode now properly replace placeholders
- File: `src/services/gcode_preprocessor.py`

**3. Frontend Filament ID Passing**
- Added `filament_id` field to `AmsTray` interface
- Slot assignments now store `filament_id` when merged with AMS trays
- `handleAddToQueue` now looks up `filament_id` from selected slot and sends to API
- Files: `frontend/src/components/QueueDashboard.tsx`, `frontend/src/api/client.ts`

**4. Block Preservation in Template Mode**
- Template processing now preserves HEADER_BLOCK, CONFIG_BLOCK, and filament footer
- Original OrcaSlicer metadata comments maintained in output files
- Print layers section preserved without modification
- File: `src/services/gcode_templates.py`

#### 🔄 Known Issues / To-Do

**1. AMS Extruder Display Shows "External Spool"**
- UI shows "External Spool" even when AMS filament is loaded
- Backend returns correct `tray_now` value (e.g., 3)
- Possible frontend state/caching issue
- Workaround: Hard refresh (Ctrl+F5) after slot changes

**2. Temperature Placeholders in Comment Headers**
- Comment lines like `; change_filament_gcode = ...` still contain raw placeholders
- These are metadata comments, NOT executed G-code
- Actual temperature commands (M104, M109, M140) are correctly set
- Low priority - cosmetic only

**3. File Naming Convention**
- Output files still named based on original file (e.g., `PLA-CF_20m55s.gcode.3mf`)
- Doesn't reflect the selected filament type
- Enhancement: Rename output based on selected filament

#### 📋 Testing Checklist

- [ ] Upload 3MF file with PLA-CF preset
- [ ] Select Slot 4 (eSUN PLA+ Red, 215°C nozzle, 60°C bed)
- [ ] Check "Filament Already Loaded"
- [ ] Select "Quick Print" preset
- [ ] Add to Queue
- [ ] Verify output file has:
  - [ ] `M109 S215` (not S230)
  - [ ] `M140 S60` (not S55)
  - [ ] `M1002 set_filament_type:PLA+` (not PLA-CF)
  - [ ] `M622 J1` (filament_already_loaded = 1)

---

#### Bambu Lab A1 Combo AMS
```
Printer IP:      192.168.4.101
Printer Serial:  03900D5A2402051
Access Code:     34782589
MQTT Port:       8883 (TLS)
FTPS Port:       990 (Implicit SSL)
MQTT Username:   bblp
Mode:            LAN Mode (local network only)
```

#### Connection Status (Dec 30, 2025 - Latest)
- ✅ MQTT Connection: Working
- ✅ Status Push: Receiving printer status
- ✅ Auto-Eject: Working (G28 X Y + G1 Y 230)
- ✅ Print Start Command: API responds successfully
- ✅ **Direct FTPS Upload: NOW WORKING!** (NEW)
- ✅ Camera Streaming: Live MJPEG feed available
- ✅ HTTP File Serving: Available as fallback

---
