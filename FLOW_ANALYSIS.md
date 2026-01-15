# Flow Analysis - User Upload to Print

## ✅ FLOW YANG DIPAKAI (ACTIVE)

### 1. User Upload File
**Frontend:**
```typescript
// JobUploadForm.tsx, QueueDashboard.tsx, PrinterCard.tsx
printFarmClient.uploadJob(file, loopCount) 
```
**API:** `POST /api/jobs/upload`  
**File:** `src/api/jobs.py` - `upload_and_create_job()`  
**Actions:**
- Validate file (.3mf, .stl)
- Save to `data/uploads/`
- Create Job record in database
- Return job_id

**Status:** ✅ DIPAKAI

---

### 2. User Add to Queue
**Frontend:**
```typescript
// QueueDashboard.tsx, PrinterCard.tsx
printFarmClient.addJobToQueue(jobId, printerId, settings)
```
**API:** `POST /api/queue/add`  
**File:** `src/api/queue.py` - `add_job_to_queue()`  
**Actions:**
- Create Queue record with job_id and printer_id
- Store automation settings (AMS, calibration, etc.)
- Set status: "pending"
- Assign position_in_queue

**Status:** ✅ DIPAKAI

---

### 3. User Click "Start Next Job"
**Frontend:**
```typescript
// QueueDashboard.tsx
printFarmClient.startNextJob(printerId)
```
**API:** `POST /api/print-control/{printer_id}/start-print`  
**File:** `src/api/print_control.py` - `start_print_job()`  
**Service:** `print_control_service.py` - `start_next_job()`  
**Actions:**
1. Find first "pending" queue item for printer
2. Upload file via FTPS to printer SD card (`BambuFTPSClient`)
3. Send MQTT `start_print_from_sd()` command
4. Update queue status: "pending" → "uploading" → "running"
5. Broadcast WebSocket progress updates

**Status:** ✅ DIPAKAI (Main Production Flow)

---

## ❌ FLOW YANG TIDAK DIPAKAI (UNUSED)

### ❌ 1. Direct Upload/Print Endpoint (Old Method)
**API:** `POST /api/jobs/upload-direct/{job_id}/print`  
**File:** `src/api/jobs.py` - `upload_and_print_direct()`  
**Uses:** `mqtt_client.send_print_file_direct()` from `bambu_service.py`

**Why Unused:**
- No frontend calls this endpoint
- Bypasses queue system
- Old direct print approach
- Main flow uses `print_control_service.start_next_job()` instead

**Grep Results:** 
- ❌ No frontend usage found
- ❌ No production code calls this

**Recommendation:** DELETE

---

### ❌ 2. Individual Queue Start Endpoint (Old Method)
**API:** `POST /api/queue/{queue_id}/start`  
**File:** `src/api/queue.py` - `start_queue_job()`  
**Uses:** `queue_service.start_queue_job()` 

**Why Unused:**
- No frontend calls this endpoint
- Frontend uses `startNextJob(printerId)` instead
- This was old per-queue-item start method
- New flow: start by printer_id, not queue_id

**Grep Results:**
- ❌ No frontend usage found
- ❌ Replaced by `/print-control/{printer_id}/start-print`

**Recommendation:** REVIEW (might be fallback)

---

## 📊 Endpoint Usage Summary

### Jobs API (`/api/jobs/`)
| Endpoint | Status | Usage |
|----------|--------|-------|
| `POST /upload` | ✅ ACTIVE | Upload file, create job |
| `GET /{job_id}` | ✅ ACTIVE | Get job details |
| `GET /{job_id}/metadata` | ✅ ACTIVE | Parse file metadata |
| `GET /{job_id}/thumbnail` | ✅ ACTIVE | Get preview image |
| `GET /{job_id}/structure` | ✅ ACTIVE | Get 3MF structure |
| `GET /{job_id}/gcode` | ✅ ACTIVE | Get G-code |
| `GET /{job_id}/print-preview` | ✅ ACTIVE | Full preview data |
| `DELETE /{job_id}` | ✅ ACTIVE | Delete job |
| `POST /upload-direct/{job_id}/print` | ❌ UNUSED | Direct print bypass queue |

### Queue API (`/api/queue/`)
| Endpoint | Status | Usage |
|----------|--------|-------|
| `POST /add` | ✅ ACTIVE | Add job to queue |
| `GET /{printer_id}` | ✅ ACTIVE | Get queue for printer |
| `GET /{printer_id}/status` | ✅ ACTIVE | Get queue status |
| `POST /{queue_id}/start` | ❓ UNCERTAIN | Start single queue job |
| `POST /{queue_id}/next-loop` | ✅ ACTIVE | Repeat loop |
| `POST /{queue_id}/complete` | ✅ ACTIVE | Complete queue job |
| `POST /{queue_id}/remove` | ✅ ACTIVE | Remove from queue |
| `PUT /{queue_id}/position` | ✅ ACTIVE | Reorder queue |
| `GET /{queue_id}/details` | ✅ ACTIVE | Get queue details |
| `GET /{queue_id}/download` | ✅ ACTIVE | Download file |
| `PUT /{queue_id}/settings` | ✅ ACTIVE | Update settings |

### Print Control API (`/api/print-control/`)
| Endpoint | Status | Usage |
|----------|--------|-------|
| `POST /{printer_id}/start-print` | ✅ ACTIVE | **Main start method** |
| `POST /{printer_id}/complete-print` | ✅ ACTIVE | Handle completion |
| `POST /{printer_id}/pause` | ✅ ACTIVE | Pause print |
| `POST /{printer_id}/resume` | ✅ ACTIVE | Resume print |
| `POST /{printer_id}/cancel` | ✅ ACTIVE | Cancel/stop print |
| `POST /{printer_id}/eject` | ✅ ACTIVE | Eject print |
| `GET /{printer_id}/status` | ✅ ACTIVE | Get print status |
| `GET /{printer_id}/mqtt-status` | ✅ ACTIVE | Get MQTT status |

---

## 🎯 Rekomendasi Cleanup

### Priority 1: Hapus Endpoint Tidak Dipakai
1. **DELETE** `POST /api/jobs/upload-direct/{job_id}/print`
   - Function: `upload_and_print_direct()` in `src/api/jobs.py` (lines 294-353)
   - Reason: No frontend usage, bypasses queue system

### Priority 2: Review & Consolidate
1. **REVIEW** `POST /api/queue/{queue_id}/start`
   - Check if any scripts still use this
   - If not, DELETE
   - Replaced by `/print-control/{printer_id}/start-print`

---

## ✅ Verified Active Flow (Keep)

```
1. Upload File
   └─> POST /api/jobs/upload
       └─> Save to data/uploads/
       └─> Create Job record
       └─> Return job_id

2. Add to Queue  
   └─> POST /api/queue/add
       └─> Create Queue record
       └─> Link job_id + printer_id
       └─> Store automation settings
       └─> Set status: "pending"

3. Start Print (Button Click)
   └─> POST /api/print-control/{printer_id}/start-print
       └─> print_control_service.start_next_job()
           └─> Find first "pending" queue item
           └─> Upload via FTPS (BambuFTPSClient)
           └─> Send MQTT start_print_from_sd()
           └─> Update status: uploading → running
           └─> WebSocket broadcast progress

4. Monitor Status
   └─> WebSocket /ws updates
   └─> GET /api/print-control/{printer_id}/mqtt-status
```

---

## 📝 Code to DELETE

### File: src/api/jobs.py

**Lines ~294-353:**
```python
@router.post("/upload-direct/{job_id}/print")
async def upload_and_print_direct(job_id: int, db: Session = Depends(get_db)):
    """..."""
    # ENTIRE FUNCTION - NOT USED
```

**Reason:**
- No frontend calls this
- Bypasses queue system
- Old approach before print_control_service
- `send_print_file_direct()` was experimental

---

## 📊 Impact Analysis

**Functions to Delete:** 1 endpoint function  
**Lines to Remove:** ~60 lines  
**Breaking Changes:** None (unused code)  
**Test Impact:** None (no tests for this endpoint)  

**Verification:**
- ✅ No frontend usage
- ✅ No production workflow uses this
- ✅ Queue system is the standard flow
- ✅ print_control_service.start_next_job() is the active method
