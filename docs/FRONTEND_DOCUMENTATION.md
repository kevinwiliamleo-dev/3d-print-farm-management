# 3D Print Farm Frontend Documentation

## Table of Contents
1. [Overview](#overview)
2. [Tech Stack & Dependencies](#tech-stack--dependencies)
3. [Architecture](#architecture)
4. [API Client](#api-client)
5. [Components Reference](#components-reference)
6. [Hooks & Services](#hooks--services)
7. [UI Flow](#ui-flow)
8. [Data Flow](#data-flow)

---

## Overview

The 3D Print Farm Frontend is a React-based single-page application (SPA) that provides a comprehensive management interface for controlling multiple Bambu Lab 3D printers. It connects to a Python/FastAPI backend running on port 5000 and provides real-time status updates via WebSocket.

**Key Features:**
- Multi-printer management with status monitoring
- File upload and job queue management
- Real-time printer status via WebSocket
- AMS (Automatic Material System) filament management
- G-Code template customization
- Print history tracking
- Camera live feed integration

---

## Tech Stack & Dependencies

### Core Dependencies
| Package | Version | Purpose |
|---------|---------|---------|
| React | ^19.2.3 | UI Framework |
| React DOM | ^19.2.3 | DOM Renderer |
| React Router DOM | ^7.11.0 | Routing |
| Axios | ^1.13.2 | HTTP Client |
| TypeScript | ^4.9.5 | Type Safety |
| TailwindCSS | ^4.1.18 | CSS Framework |

### Dev Dependencies
- React Scripts 5.0.1 (Create React App)
- Testing Library (Jest + React Testing Library)

### Build Scripts
```json
{
  "start": "react-scripts start",      // Dev server on port 3000
  "build": "react-scripts build",      // Production build
  "test": "react-scripts test",        // Run tests
  "eject": "react-scripts eject"       // Eject CRA
}
```

---

## Architecture

### Directory Structure
```
frontend/src/
├── App.tsx                 # Root component (renders Dashboard)
├── App.css                 # Global styles
├── index.tsx               # Entry point
├── api/
│   └── client.ts          # API client with all backend methods
├── components/
│   ├── index.ts           # Component exports
│   ├── Dashboard.tsx      # Main layout & navigation
│   ├── PrinterCard.tsx    # Individual printer display
│   ├── PrinterStatus.tsx  # Detailed printer view with camera
│   ├── QueueDashboard.tsx # Upload & queue management (~2929 lines)
│   ├── QueueManager.tsx   # Basic queue table view
│   ├── JobUploadForm.tsx  # Simple upload form
│   ├── JobsList.tsx       # All jobs table
│   ├── FilamentInventory.tsx  # Filament CRUD (~1353 lines)
│   ├── GCodeTemplates.tsx # Template & preset editor (~1744 lines)
│   ├── HistoryViewer.tsx  # Print history with stats
│   ├── AmsStatusDisplay.tsx   # AMS slot management (~1183 lines)
│   ├── PrinterFilesTab.tsx    # SD card file browser
│   ├── GCodeViewer.tsx    # G-Code syntax viewer
│   └── PrintPreviewModal.tsx  # Print steps preview
├── hooks/
│   ├── index.ts
│   └── useWebSocket.ts    # Real-time status hook
└── services/
    └── WebSocketManager.ts # Singleton WS connection manager
```

### Component Hierarchy
```
App
└── Dashboard (main layout)
    ├── PrinterCard (sidebar - for each printer)
    ├── Tab Content Area
    │   ├── [status tab]
    │   │   └── PrinterStatus
    │   │       └── AmsStatusDisplay
    │   ├── [queue tab]
    │   │   └── QueueDashboard
    │   │       └── PrinterFilesTab
    │   ├── [inventory tab]
    │   │   └── FilamentInventory
    │   ├── [history tab]
    │   │   └── HistoryViewer
    │   ├── [templates tab]
    │   │   └── GCodeTemplates
    │   └── [settings tab]
    │       └── (inline settings UI)
    └── Modals
        ├── Add Printer Modal
        ├── PrintPreviewModal
        └── GCodeViewer
```

---

## API Client

The API client is located at [frontend/src/api/client.ts](frontend/src/api/client.ts) and provides all backend communication.

### Client Configuration
```typescript
class PrintFarmClient {
  private apiClient: AxiosInstance;
  private baseURL: string = 'http://localhost:5000';
  // All API calls go to: {baseURL}/api/*
}

export const printFarmClient = new PrintFarmClient();
```

### Type Definitions

| Interface | Description |
|-----------|-------------|
| `JobResponse` | Uploaded job data (id, name, filename, loops, status) |
| `JobMetadata` | Parsed metadata from 3MF/G-Code (temps, time, filament, plates) |
| `PrinterResponse` | Printer info (id, name, status, temps, MQTT, progress) |
| `QueueItemResponse` | Queue entry (position, loops, status) |
| `FilamentProfile` | Filament specs (temps, material, color, density) |
| `PrintPreset` | Print automation settings (27 templates + settings) |
| `PrintPreviewResponse` | Print steps preview with G-Code references |

### API Methods Reference

#### Job Endpoints
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `uploadJob(file, loopCount, onProgress?)` | File, number, callback | `JobResponse` | Upload 3MF/G-Code file |
| `getAllJobs()` | - | `JobResponse[]` | List all jobs |
| `getJobById(jobId)` | number | `JobResponse` | Get single job |
| `getJobMetadata(jobId)` | number | `JobMetadata` | Parsed file metadata |
| `getPrintPreview(jobId)` | number | `PrintPreviewResponse` | Print steps breakdown |
| `getJobGCode(jobId, plate?, maxLines?, structured?)` | number, options | GCode data | Raw/structured G-Code |
| `modifyGCodeSections(jobId, modifications, plate?)` | number, mods | result | Modify G-Code sections |
| `getJobThumbnailUrl(jobId)` | number | string | Thumbnail URL |
| `deleteJob(jobId)` | number | void | Delete job |

#### Printer Endpoints
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `registerPrinter(printerId, printerName)` | strings | `PrinterResponse` | Add printer |
| `getAllPrinters()` | - | `PrinterResponse[]` | List printers |
| `getPrinterById(printerId)` | string | `PrinterResponse` | Get printer details |
| `updatePrinterStatus(printerId, status)` | strings | `PrinterResponse` | Update status |
| `discoverPrintersOnNetwork()` | - | `PrinterResponse[]` | Network scan |
| `discoverByIp(ipAddress)` | string | result | Find by IP |
| `refreshPrinterStatus(printerId)` | string | result | Force refresh |
| `deletePrinter(printerId)` | string | void | Remove printer |

#### AMS Endpoints
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `getAmsTrays(printerId)` | string | AMS data | Get slot info |
| `getAmsStatus(printerId)` | string | status | Full AMS status |
| `amsLoadFilament(printerId, slot, temp?)` | string, number, number | result | Load filament |
| `amsUnloadFilament(printerId)` | string | result | Unload current |
| `amsFilamentSettings(printerId, slot, type, color)` | params | result | Update slot settings |
| `getAmsLoadingStatus(printerId)` | string | progress | Real-time load progress |
| `getSlotAssignments(printerId)` | string | slots | Database assignments |
| `assignFilamentToSlot(printerId, slot, filamentId, grams?)` | params | result | Assign from inventory |
| `updateSlotRemaining(printerId, slot, grams)` | params | result | Update remaining |

#### Queue Endpoints
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `addJobToQueue(jobId, printerId, settings?)` | params | `QueueItemResponse` | Add to queue |
| `getQueueForPrinter(printerId)` | string | `QueueItemResponse[]` | Printer's queue |
| `removeFromQueue(queueId)` | number | void | Remove item |
| `getQueueItemDetails(queueId)` | number | details | Full queue info |
| `updateQueueSettings(queueId, settings)` | number, settings | void | Modify settings |
| `downloadQueueFile(queueId)` | number | void | Download modified file |
| `getQueueStatus(printerId)` | string | status | Queue stats |
| `updateQueuePosition(queueId, newPosition)` | numbers | result | Reorder |
| `startNextJob(printerId)` | string | result | Start print |

#### Print Control Endpoints
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `startPrint(printerId)` | string | result | Start next queue item |
| `pausePrint(printerId)` | string | result | Pause print |
| `resumePrint(printerId)` | string | result | Resume print |
| `cancelPrint(printerId)` | string | result | Cancel/stop print |
| `getPrintStatus(printerId)` | string | status | Current status |
| `getMqttStatus(printerId)` | string | status | MQTT + temps |

#### Filament Endpoints
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `getAllFilaments()` | - | `FilamentProfile[]` | List inventory |
| `getFilamentById(id)` | number | `FilamentProfile` | Single filament |
| `createFilament(filament)` | data | `FilamentProfile` | Add new |
| `updateFilament(id, filament)` | number, data | `FilamentProfile` | Update |
| `deleteFilament(id)` | number | void | Delete |
| `getFilamentMaterials()` | - | string[] | Material types |
| `getFilamentBrands()` | - | string[] | Brand list |
| `addFilamentStock(id, grams?)` | number, number | `FilamentProfile` | Add spool |
| `useFilamentStock(id, grams?)` | number, number | `FilamentProfile` | Use filament |

#### Preset Endpoints
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `getPresets()` | - | `PrintPreset[]` | List presets |
| `getDefaultPreset()` | - | `PrintPreset | null` | Get default |
| `getPresetById(presetId)` | number | `PrintPreset` | Single preset |
| `createPreset(preset)` | data | `PrintPreset` | Create new |
| `updatePreset(presetId, preset)` | number, data | `PrintPreset` | Update |
| `deletePreset(presetId)` | number | void | Delete |
| `setDefaultPreset(presetId)` | number | void | Set as default |
| `createDefaultPresets()` | - | result | Initialize defaults |

#### Other Endpoints
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `getPrintHistory(printerId?, limit?)` | optional | history[] | Print history |
| `getHistoryStats()` | - | stats | Aggregate stats |
| `getBucketList(printerId)` | string | items[] | Parked jobs |
| `moveQueueToBucket(queueId)` | number | result | Park job |
| `moveBucketToQueue(bucketId, printerId?)` | params | result | Restore job |

---

## Components Reference

### Dashboard.tsx (~1201 lines)
**Purpose:** Main application layout and navigation hub.

**Key State:**
```typescript
const [printers, setPrinters] = useState<PrinterResponse[]>([]);
const [selectedPrinterId, setSelectedPrinterId] = useState<string | null>(null);
const [activeTab, setActiveTab] = useState<TabType>('status'); // status|queue|history|inventory|settings|templates
const [showAddModal, setShowAddModal] = useState(false);
const [kits, setKits] = useState<Kit[]>([]);  // External camera/fan kits
const [discoveredPrinters, setDiscoveredPrinters] = useState<DiscoveredPrinter[]>([]);
```

**Key Functions:**
| Function | Description |
|----------|-------------|
| `loadPrinters()` | Fetch all printers from API |
| `loadMqttStatus()` | Poll MQTT status for temps/progress |
| `handleScanNetwork()` | Discover printers on network |
| `handleAddPrinter()` | Add printer by IP |
| `handleAddDiscoveredPrinter()` | Add from scan results |
| `refreshQueue()` | Trigger queue reload |
| `handleAddKit()` | Add external camera kit |
| `toggleFan()` | Control kit fan |

**WebSocket:** Uses `useWebSocket` hook for real-time printer status updates.

**Tabs:**
1. **Status** - PrinterStatus with camera feed
2. **Queue** - QueueDashboard with upload
3. **Inventory** - FilamentInventory
4. **History** - HistoryViewer
5. **Templates** - GCodeTemplates
6. **Settings** - Kit configuration

---

### PrinterCard.tsx (~407 lines)
**Purpose:** Display a single printer in the sidebar with drag-drop upload.

**Props:**
```typescript
interface PrinterCardProps {
  printer: PrinterResponse;
  isSelected: boolean;
  onSelect: () => void;
  onRefresh: () => void;
  onDelete: () => void;
  onJobAdded?: () => void;
}
```

**Key State:**
```typescript
const [isRefreshing, setIsRefreshing] = useState(false);
const [isDragOver, setIsDragOver] = useState(false);
const [isUploading, setIsUploading] = useState(false);
const [uploadMessage, setUploadMessage] = useState<Message | null>(null);
```

**Key Functions:**
- `handleRefresh()` - Refresh printer status
- `handleConnect()` - Force MQTT reconnection
- `handleDelete()` - Remove printer
- `handleDrop()` - Drag-drop file upload → add to queue

**Features:**
- Status badge (Printing/Ready/Offline)
- MQTT connection indicator
- Progress bar when printing
- Drag-drop zone for quick upload

---

### PrinterStatus.tsx (~500 lines)
**Purpose:** Detailed printer view with camera feed and print controls.

**Props:**
```typescript
interface PrinterStatusProps {
  printer: PrinterResponse | null;
  cameraSource?: 'bambu' | 'custom';
  customCameraUrl?: string;
}
```

**Key State:**
```typescript
const [cameraLive, setCameraLive] = useState(false);
const [cameraError, setCameraError] = useState(false);
const [useStream, setUseStream] = useState(true);
const [isPaused, setIsPaused] = useState(false);
const [actionLoading, setActionLoading] = useState<string | null>(null);
```

**Key Functions:**
- `handlePauseResume()` - Toggle pause/resume
- `handleStop()` - Cancel print with confirmation
- `formatRemainingTime()` - Convert seconds to human readable

**Features:**
- Live camera feed (MJPEG stream or snapshot polling)
- Print progress bar
- Pause/Resume/Stop controls
- Remaining time display
- AmsStatusDisplay component

---

### QueueDashboard.tsx (~2929 lines)
**Purpose:** Complete upload workflow, queue management, and print settings.

**Props:**
```typescript
interface QueueDashboardProps {
  printerId: string;
  onRefresh?: () => void;
  showUpload?: boolean;
  printers?: PrinterInfo[];
}
```

**Key State:**
```typescript
// Upload
const [selectedFile, setSelectedFile] = useState<File | null>(null);
const [isUploading, setIsUploading] = useState(false);
const [uploadProgress, setUploadProgress] = useState(0);

// Preview
const [uploadedJobId, setUploadedJobId] = useState<number | null>(null);
const [jobMetadata, setJobMetadata] = useState<JobMetadata | null>(null);
const [showPreview, setShowPreview] = useState(false);
const [printPreview, setPrintPreview] = useState<PrintPreviewResponse | null>(null);

// AMS
const [amsTrays, setAmsTrays] = useState<AmsTray[]>([]);
const [selectedAmsSlot, setSelectedAmsSlot] = useState<number>(0);
const [useAms, setUseAms] = useState<boolean>(true);

// Presets
const [presets, setPresets] = useState<PrintPreset[]>([]);
const [selectedPresetId, setSelectedPresetId] = useState<number | null>(null);

// Queue
const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
```

**Workflow:**
1. User selects file → Upload to server
2. Preview modal shows metadata + print steps
3. User selects AMS slot + preset
4. Add to queue → Generate modified G-Code
5. Start print when ready

**Dynamic Steps:** Generates print steps based on selected preset settings (bed leveling, vibration test, etc.)

---

### FilamentInventory.tsx (~1353 lines)
**Purpose:** CRUD for filament inventory with preset profiles.

**Key State:**
```typescript
const [filaments, setFilaments] = useState<FilamentProfile[]>([]);
const [showForm, setShowForm] = useState(false);
const [editingFilament, setEditingFilament] = useState<FilamentProfile | null>(null);
const [simpleForm, setSimpleForm] = useState<SimpleFormData>(defaultSimpleForm);
```

**Features:**
- Preset database for common brands (Bambu Lab, eSUN, Sunlu, Anycubic, Elegoo)
- Temperature profiles auto-fill
- Color picker with common colors
- Stock count management
- Semi-transparent color support with checkered preview

**Key Functions:**
- `loadFilaments()` - Fetch from API
- `handleSave()` - Create/update filament
- `handleDelete()` - Remove filament
- `applyPreset()` - Load brand/material defaults

---

### GCodeTemplates.tsx (~1744 lines)
**Purpose:** G-Code template editor and print preset management.

**Tabs:**
1. **Templates** - Edit individual G-Code templates
2. **Presets** - Create/manage automation presets

**Key State:**
```typescript
// Templates
const [templates, setTemplates] = useState<TemplatesData | null>(null);
const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
const [previewGcode, setPreviewGcode] = useState<{ start: string; end: string } | null>(null);

// Presets
const [presets, setPresets] = useState<PrintPreset[]>([]);
const [showPresetForm, setShowPresetForm] = useState(false);
const [presetFormData, setPresetFormData] = useState<PrintPresetCreate>({...});
```

**Template Types:**
- **Start Templates (21):** Machine init, heating, sounds, AMS, calibration, leveling, etc.
- **End Templates (6):** End print, timelapse, safe position, auto-eject, sounds, final

**Preset Settings:**
- All 27 template toggles
- `preheat_offset` (default: 20°C)
- `cooldown_temp` (default: 32°C)
- `use_template_mode` flag

---

### AmsStatusDisplay.tsx (~1183 lines)
**Purpose:** Visual AMS slot management with load/unload operations.

**Props:**
```typescript
interface AmsStatusDisplayProps {
  printerId: string;
  compact?: boolean;
}
```

**Key State:**
```typescript
const [amsData, setAmsData] = useState<AmsStatusData | null>(null);
const [slotAssignments, setSlotAssignments] = useState<Record<number, SlotAssignment>>({});
const [modalOpen, setModalOpen] = useState(false);
const [modalStage, setModalStage] = useState<'select' | 'detail'>('select');
const [loadProgress, setLoadProgress] = useState<LoadProgress>({...});
```

**Modal Stages:**
1. **Select** - Choose filament from inventory
2. **Detail** - Load/Unload controls + remaining input

**Load Progress Steps:**
```typescript
const LOAD_STEPS = [
  'Heat the Nozzle',
  'Check filament location',
  'Cut filament',
  'Pull back current filament',
  'Push new filament into extruder',
  'Purge old filament'
];
```

**Real-time Progress:** Polls `getAmsLoadingStatus()` every 500ms during load/unload.

---

### HistoryViewer.tsx (~268 lines)
**Purpose:** Display print history with statistics.

**Props:**
```typescript
interface HistoryViewerProps {
  printerId?: string;
}
```

**Key State:**
```typescript
const [history, setHistory] = useState<HistoryItem[]>([]);
const [filter, setFilter] = useState<'all' | 'success' | 'failed'>('all');
```

**Stats Displayed:**
- Total prints count
- Successful prints
- Failed prints
- Total print time
- Total material used

---

### PrinterFilesTab.tsx (~399 lines)
**Purpose:** Browse and manage files on printer's SD card.

**Key State:**
```typescript
const [files, setFiles] = useState<PrinterFile[]>([]);
const [isCollapsed, setIsCollapsed] = useState(true); // Lazy loading
const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
```

**Key Functions:**
- `loadFiles()` - Fetch SD card contents via FTPS
- `printFile()` - Start print from SD card
- `deleteFile()` - Remove file from printer

**Features:**
- Collapsible to avoid slow FTPS loading
- File type badges (3MF/G-CODE/OTHER)
- Cache folder support

---

### GCodeViewer.tsx (~308 lines)
**Purpose:** Syntax-highlighted G-Code viewer with search.

**Props:**
```typescript
interface GCodeViewerProps {
  jobId: number;
  isOpen: boolean;
  onClose: () => void;
}
```

**Features:**
- Syntax highlighting by line type
- Search/filter functionality
- Virtual scrolling for performance
- Plate selector for multi-plate jobs
- Line number toggle

**Line Types & Colors:**
| Type | Pattern | Color |
|------|---------|-------|
| comment | `;...` | gray |
| move | `G0`, `G1` | blue |
| temp | `M104`, `M109`, `M140`, `M190` | orange |
| layer | `;LAYER:` | green (bold) |
| retract | `G10`, `G11` | yellow |
| setting | `M...` | purple |
| special | `G...` | cyan |

---

### PrintPreviewModal.tsx (~533 lines)
**Purpose:** Show print steps preview before adding to queue.

**Props:**
```typescript
interface PrintPreviewModalProps {
  jobId: number | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm?: () => void;
}
```

**Tabs:**
1. **Job** - Print steps with G-Code references
2. **G-Code** - Raw G-Code viewer

**Step Phases:**
- 🔧 Preparation (blue)
- 📐 Calibration (yellow)
- 🖨️ Printing (green)
- ✅ Completion (purple)

---

### JobsList.tsx (~139 lines)
**Purpose:** Simple table view of all uploaded jobs.

**Key State:**
```typescript
const [jobs, setJobs] = useState<JobResponse[]>([]);
const [previewJobId, setPreviewJobId] = useState<number | null>(null);
```

**Features:**
- Auto-refresh every 10 seconds
- Delete job with confirmation
- Preview modal trigger
- Status badges

---

### JobUploadForm.tsx (~113 lines)
**Purpose:** Simple standalone upload form component.

**Props:**
```typescript
interface JobUploadFormProps {
  onSuccess?: (job: JobResponse) => void;
}
```

**Validation:**
- Accepts `.3mf` and `.stl` files
- Loop count: 1-100

---

### QueueManager.tsx (~115 lines)
**Purpose:** Basic queue table (simpler than QueueDashboard).

**Props:**
```typescript
interface QueueManagerProps {
  printerId: string;
}
```

**Features:**
- Auto-refresh every 5 seconds
- Position indicator (▶️ for first)
- Status badges
- Remove action

---

## Hooks & Services

### useWebSocket.ts (~242 lines)
**Purpose:** React hook for real-time WebSocket communication.

**Usage:**
```typescript
const { isConnected, printers, printerDetail, lastMessage } = useWebSocket({
  onStatusUpdate: (printers) => { /* handle status */ },
  onPrinterUpdate: (detail) => { /* handle printer */ },
  onUploadProgress: (printerId, progress) => { /* handle upload */ },
});
```

**Options:**
```typescript
interface UseWebSocketOptions {
  printerId?: string;
  onMessage?: (message: WebSocketMessage) => void;
  onStatusUpdate?: (printers: PrinterStatus[]) => void;
  onPrinterUpdate?: (status: PrinterDetailStatus) => void;
  onUploadProgress?: (printerId: string, progress: UploadProgress) => void;
}
```

**Message Types:**
- `status_update` - All printers status
- `printer_status` - Single printer + queue
- `printer_update` - Individual update
- `upload_progress` - File upload progress
- `pong` - Heartbeat response
- `error` - Error message

---

### WebSocketManager.ts (~201 lines)
**Purpose:** Singleton WebSocket connection manager.

**Features:**
- Single shared connection across components
- Auto-reconnect on disconnect (5s interval)
- Heartbeat ping every 30s
- Reference counting for disconnect

**API:**
```typescript
wsManager.connect(options?);  // Initialize connection
wsManager.subscribe(handler); // Returns unsubscribe function
wsManager.send(message);      // Send message
wsManager.isConnected();      // Check status
wsManager.disconnect();       // Decrement ref count
wsManager.reconnect();        // Force reconnect
```

**Default URL:** `ws://localhost:5000/ws/status`

---

## UI Flow

### 1. Main Dashboard Flow
```
App → Dashboard
   ├── Header (stats, find printer button)
   ├── Sidebar (printer list, collapsible)
   │   └── PrinterCard × N (click to select)
   ├── Tab Bar (status/queue/inventory/history/templates/settings)
   └── Content Area (based on active tab)
```

### 2. Upload & Print Workflow
```
1. User drops file on PrinterCard
   OR clicks upload in QueueDashboard

2. File uploaded to server
   → JobResponse returned
   → Metadata parsed from 3MF/G-Code

3. Preview Modal opens
   → Shows job info (name, time, filament)
   → Shows print steps preview
   → User selects AMS slot
   → User selects preset

4. Add to Queue
   → Server applies preset settings
   → G-Code templates processed
   → Modified file saved

5. Start Print
   → File uploaded to printer via FTPS
   → Print started via MQTT
```

### 3. Queue Management Flow
```
QueueDashboard
├── Upload Section
│   ├── Drag-drop zone
│   ├── File picker
│   └── Printer selector
├── Queue Table
│   ├── Position (drag to reorder)
│   ├── Job info
│   ├── AMS slot indicator
│   └── Actions (remove, download, settings)
└── Print Controls
    ├── Start Next
    ├── Stop All
    └── Clear Queue
```

### 4. Printer Status Flow
```
PrinterStatus
├── Progress Bar (when printing)
│   ├── Pause/Resume button
│   └── Stop button
├── Camera Feed
│   ├── MJPEG stream (preferred)
│   └── Snapshot fallback (1 FPS)
├── Temperature Display
│   ├── Nozzle temp
│   ├── Bed temp
│   └── Chamber temp
└── AmsStatusDisplay
    ├── Slot visual (4 slots)
    ├── Click slot → Modal
    │   ├── Stage 1: Select filament
    │   └── Stage 2: Load/Unload
    └── Currently loaded indicator
```

### 5. Settings Flow
```
Settings Tab
├── Kit Section
│   ├── Add Kit form (IP input)
│   ├── Kit list
│   │   ├── Camera status + source selector
│   │   └── Fan status + toggle
│   └── Purchase link
└── System Info
    ├── API server status
    └── Printer count
```

---

## Data Flow

### Real-time Updates
```
Backend MQTT → WebSocket Server → Frontend WebSocket Hook → Components
                                        ↓
                              Dashboard state updates
                                        ↓
                              PrinterCard/PrinterStatus re-render
```

### API Polling
```
Dashboard (30s interval) → getAllPrinters() → Update sidebar
Dashboard (5s interval)  → getMqttStatus()  → Update temps/progress
QueueDashboard (5s)      → getQueueStatus() → Update queue
AmsStatusDisplay (5s)    → getAmsTrays()    → Update slots
```

### Upload Flow
```
File → uploadJob() → JobResponse
         ↓
    getJobMetadata() → Show preview
         ↓
    addJobToQueue(settings) → QueueItemResponse
         ↓
    startPrint() → Print starts
```

### State Management Pattern
- Each component manages its own state via `useState`
- Data flows down via props
- Parent callback functions for upward communication
- WebSocket provides real-time sync without polling

---

## Key Features Summary

| Feature | Component | API Calls |
|---------|-----------|-----------|
| File Upload | QueueDashboard | `uploadJob()` |
| Queue Management | QueueDashboard | `addJobToQueue()`, `getQueueForPrinter()`, `removeFromQueue()` |
| Printer Discovery | Dashboard | `discoverPrintersOnNetwork()`, `discoverByIp()` |
| Print Control | PrinterStatus | `startPrint()`, `pausePrint()`, `resumePrint()`, `cancelPrint()` |
| AMS Management | AmsStatusDisplay | `getAmsTrays()`, `amsLoadFilament()`, `amsUnloadFilament()` |
| Filament Inventory | FilamentInventory | `getAllFilaments()`, `createFilament()`, `updateFilament()` |
| G-Code Templates | GCodeTemplates | `getPresets()`, `createPreset()`, `updatePreset()` |
| Print History | HistoryViewer | `getPrintHistory()`, `getHistoryStats()` |
| Camera Feed | PrinterStatus | Backend proxy: `/api/camera/stream`, `/api/camera/snapshot` |
| Real-time Status | useWebSocket | WebSocket: `/ws/status` |

---

*Generated: January 7, 2026*
