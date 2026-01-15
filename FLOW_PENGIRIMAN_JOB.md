# 📤 Flow Sistem Pengiriman Job ke Printer Bambu Lab A1

## 🔄 Alur Lengkap: Dari Upload hingga Printer Menerima Print

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER TRIGGERS PRINT                              │
│                    POST /api/print-control/start-print                   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. API ENDPOINT: print_control.py                                        │
│    ✓ Receives printer_id                                                 │
│    ✓ Validates printer exists                                            │
│    ✓ Creates PrintControlService                                         │
│    ✓ Initializes MQTT Client (LAN or Cloud mode)                        │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. PRINT CONTROL SERVICE: print_control_service.py                       │
│    └─ start_next_job(printer_id)                                         │
│       ✓ Query Queue table: WHERE printer_id=? AND status='pending'       │
│       ✓ Get first queue_item (ORDER BY position_in_queue)                │
│       ✓ Fetch Job details (job_name, filename, loop_count)               │
│       ✓ Update Queue status: pending → uploading                         │
│       ✓ Store: current_queue_id, current_job_id, print_start_time        │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. G-CODE PREPROCESSING: _preprocess_gcode_file()                        │
│                                                                           │
│    Input:  Original .gcode atau .3mf dari uploads/                      │
│    Process:                                                               │
│    ✓ Get PrintSettings dari Queue automation settings:                   │
│      - auto_bed_leveling, flow_calibration, vibration_test               │
│      - clean_nozzle, auto_eject, cooldown_temp                           │
│      - startup_sound, end_sound, nozzle_load_line, dll                   │
│                                                                           │
│    ✓ Get FilamentSettings dari filament profile (jika ada):              │
│      - nozzle_temp, bed_temp, filament_type                              │
│      - max_volumetric_speed, color_hex                                    │
│                                                                           │
│    ✓ Call gcode_preprocessor.process_gcode():                           │
│      a) TEMPLATE MODE (use_template_mode=True):                          │
│         - Ganti ALL start/end gcode dengan template optimal               │
│         - Replace {nozzle_temp}, {bed_temp}, {filament_type}, dll        │
│                                                                           │
│      b) SECTION TOGGLE MODE (use_template_mode=False):                   │
│         - Find section markers (start_marker → end_marker)                │
│         - Comment out/enable sections berdasar PrintSettings              │
│         - Contoh: ;===== vibration test → ;===== vibration test end       │
│         - If vibration_test=False → comment out seluruh section           │
│                                                                           │
│    Output: Modified .gcode file (dalam temp folder)                      │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. FILE UPLOAD VIA FTPS: print_control_service.py                        │
│                                                                           │
│    ✓ Initialize BambuFTPSClient:                                         │
│      - host: BAMBU_PRINTER_IP (LAN mode, e.g., 192.168.x.x)              │
│      - port: 990 (FTPS standard)                                         │
│      - access_code: dari config .env                                      │
│                                                                           │
│    ✓ Upload preprocessed file ke printer SD card:                       │
│      - Remote path: /cache/model.3mf (atau .gcode)                       │
│      - Progress callback: Broadcast ke WebSocket                          │
│      - Retry logic jika timeout                                           │
│                                                                           │
│    ✓ Broadcast upload progress ke frontend real-time:                   │
│      {                                                                     │
│        "percent": 45,                                                     │
│        "bytes_sent": 450000,                                              │
│        "total_bytes": 1000000,                                            │
│        "filename": "model.3mf",                                           │
│        "status": "uploading"                                              │
│      }                                                                     │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. START PRINT VIA MQTT: bambu_service.py                                │
│                                                                           │
│    ✓ MQTT Connection (LAN Mode):                                         │
│      - Host: printer_ip (e.g., 192.168.1.100)                            │
│      - Port: 8883 (MQTT with TLS)                                        │
│      - ClientID: device_XXXXXX (device_id)                               │
│      - Username: bblp                                                    │
│      - Password: access_code (dari printer web panel)                     │
│                                                                           │
│    ✓ Subscribe to status topic:                                          │
│      device/{printer_id}/report                                          │
│      → Monitor print progress, temperatures, AMS status                   │
│                                                                           │
│    ✓ Publish start print command:                                        │
│      device/{printer_id}/request                                         │
│      │                                                                     │
│      └─ Payload: {                                                        │
│           "print": {                                                      │
│             "sequence_id": 12345,                                         │
│             "command": "start",                                           │
│             "plate_number": 0,                                            │
│             "param": "model.3mf"  ◄─ File uploaded di step 4              │
│           }                                                                │
│         }                                                                  │
│                                                                           │
│    ✓ Update database:                                                     │
│      - Queue.status: uploading → running                                  │
│      - Job.status: uploading → running                                    │
│      - Queue.started_at: set datetime                                     │
│                                                                           │
│    ✓ Broadcast to WebSocket:                                             │
│      {                                                                     │
│        "event": "print_started",                                          │
│        "printer_id": "bambu-a1-001",                                      │
│        "job_name": "My Model",                                            │
│        "status": "running"                                                │
│      }                                                                     │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. REAL-TIME MONITORING VIA MQTT                                         │
│                                                                           │
│    Printer sends status update setiap X detik:                           │
│    ✓ Parse message dari device/{printer_id}/report                      │
│    ✓ Extract data:                                                        │
│      - gcode_state: RUNNING, IDLE, PAUSE, FAILED                         │
│      - mc_percent: 0-100 (print progress)                                │
│      - mc_remaining_time: seconds                                         │
│      - nozzle_temper, bed_temper, chamber_temper                          │
│      - ams_status: 768=idle, 258=heating, 259=cut, dll                   │
│                                                                           │
│    ✓ Sync to database (Printer table):                                   │
│      - status: "printing"                                                 │
│      - print_progress: 45%                                                │
│      - nozzle_temp: 220°C                                                │
│      - bed_temp: 60°C                                                    │
│                                                                           │
│    ✓ Broadcast ke all WebSocket clients:                                │
│      {                                                                     │
│        "printer_id": "bambu-a1-001",                                      │
│        "status": "printing",                                              │
│        "progress": 45,                                                    │
│        "nozzle": 220,                                                     │
│        "bed": 60,                                                         │
│        "remaining": 1200  (seconds)                                       │
│      }                                                                     │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 7. PRINT COMPLETE DETECTION                                              │
│                                                                           │
│    Printer sends: gcode_state="IDLE" dan mc_percent=100                  │
│                                                                           │
│    ✓ Callback triggered: on_print_complete()                             │
│    ✓ Server detects completion:                                          │
│      - Update Queue.status: running → completed                          │
│      - Update Job.status: running → completed                            │
│      - Calculate print duration                                           │
│                                                                           │
│    ✓ Check loop management:                                              │
│      IF current_loop < job.loop_count:                                    │
│        - Increment current_loop                                           │
│        - Status: completed → pending (will print again)                  │
│      ELSE:                                                                 │
│        - Job done (loop_count reached)                                    │
│                                                                           │
│    ✓ If auto_eject=True:                                                 │
│      - Send eject command via MQTT:                                      │
│        { "print": { "command": "eject_plate" } }                         │
│      - Wait for bed_temp to drop to cooldown_temp                         │
│                                                                           │
│    ✓ Log to PrintHistory table:                                          │
│      - job_id, printer_id, started_at, completed_at, duration             │
│      - status: success/failed                                             │
│      - print_progress: 100%                                               │
│                                                                           │
│    ✓ Start next job automatically (jika ada):                            │
│      - Call start_next_job() lagi untuk queue item berikutnya             │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             ▼
                        🎉 DONE! 🎉
```

---

## 📊 Data Flow Architecture

```
┌──────────────────┐
│  Frontend/User   │  POST /api/print-control/{printer_id}/start-print
│  (React)         │─────────────────────────────────────────────┐
└──────────────────┘                                              │
                                                                  ▼
┌──────────────────┐        ┌────────────────────────────────────────────┐
│  Database        │◄──────│  FastAPI Application (main.py)              │
│  (SQLite)        │        │  ✓ Initialize services                     │
│  - Job           │        │  ✓ Load config (BAMBU_PRINTER_IP, etc)    │
│  - Queue         │        │  ✓ Create MQTT client                      │
│  - PrintHistory  │        │  ✓ Route request to print_control.py       │
│  - Printer       │        └────────────────────────────────────────────┘
│  - FilamentProf  │                        │
└──────────────────┘                        │ Dependency Injection
                                            ▼
                    ┌──────────────────────────────────────────────┐
                    │  PrintControlService (print_control_service) │
                    │  ✓ get next job from queue                   │
                    │  ✓ preprocess gcode                          │
                    │  ✓ upload via FTPS                           │
                    │  ✓ trigger MQTT start print                  │
                    │  ✓ manage loop/auto-eject                    │
                    └──────────┬───────────────────────────────────┘
                               │
                    ┌──────────┴──────────────────────────────┐
                    │                                          │
                    ▼                                          ▼
        ┌─────────────────────────┐      ┌───────────────────────────┐
        │ GCodePreprocessor       │      │ BambuLabMQTTClient        │
        │ (gcode_preprocessor.py) │      │ (bambu_service.py)        │
        │                         │      │                           │
        │ ✓ Toggle sections       │      │ LAN Mode:                 │
        │ ✓ Apply templates       │      │  └─ 192.168.x.x:8883     │
        │ ✓ Replace variables     │      │  └─ TLS + access_code     │
        │  {nozzle_temp} → 220    │      │                           │
        │  {bed_temp} → 60        │      │ Cloud Mode:               │
        │  {filament_type} → PLA  │      │  └─ mqtt.bambulab.com     │
        │  etc                    │      │  └─ bblp / password       │
        └─────────────────────────┘      │                           │
                                         │ ✓ Publish start command   │
                    ┌────────────────────│ ✓ Subscribe to status     │
                    │                    │ ✓ Monitor progress        │
                    │                    │ ✓ Handle completion       │
                    │                    └───────────────────────────┘
                    │                                │
                    ▼                                │
        ┌─────────────────────────┐                 │
        │ BambuFTPSClient         │                 │
        │ (ftps_service.py)       │                 │
        │                         │                 │
        │ 192.168.x.x:990         │                 │
        │ SSL/TLS encrypted       │                 │
        │ Upload to /cache/model  │                 │
        └──────────┬──────────────┘                 │
                   │                                 │
                   └────────┬──────────────────────┐ │
                            │                      │ │
                            ▼                      ▼ ▼
                    ┌─────────────────────────────────────┐
                    │  Bambu Lab A1 Combo Printer         │
                    │                                      │
                    │  FTPS Server:                        │
                    │   └─ Receive file (step 4)           │
                    │                                      │
                    │  MQTT Client:                        │
                    │   ├─ Receive start command (step 5)  │
                    │   └─ Send status reports (step 6)    │
                    │                                      │
                    │  Processor:                          │
                    │   ├─ Parse G-code                    │
                    │   ├─ Execute print                   │
                    │   ├─ Monitor progress                │
                    │   └─ Detect completion               │
                    └──────────────────────────────────────┘
                                    │
                                    │ MQTT Status Updates
                                    │ (Real-time streaming)
                                    ▼
                    ┌──────────────────────────┐
                    │ WebSocket Broadcaster    │
                    │ (websocket.py)           │
                    │                          │
                    │ ✓ broadcast_upload_prg   │
                    │ ✓ broadcast_print_prg    │
                    │ ✓ send_printer_status    │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Frontend (React)          │
                    │                           │
                    │ ✓ Show upload progress    │
                    │ ✓ Show print progress     │
                    │ ✓ Show temps (real-time)  │
                    │ ✓ Show job status         │
                    │ ✓ Show remaining time     │
                    └───────────────────────────┘
```

---

## 🔑 Key Parameters & Configuration

### Queue Table (Per Job)
```python
Queue fields yang digunakan saat pengiriman:
- queue_id: Unique ID untuk job ini
- job_id: Reference ke job (file)
- printer_id: Target printer
- position_in_queue: Order (1=next, 2=after next, dll)
- current_loop: Loop ke berapa (1/5, dll)
- status: pending → uploading → running → completed → failed
- ams_slot: AMS slot (0-3, 254=external)
- use_template_mode: True=replace all start/end, False=toggle sections
- filament_id: Reference ke filament profile (untuk temp override)

Automation settings:
- auto_bed_leveling: Enable G29 before print
- flow_calibration: Enable flow test (disabled if auto_eject=True)
- vibration_test: Enable resonance test
- clean_nozzle: Enable nozzle cleaning
- wipe_nozzle: Enable wipe nozzle section
- nozzle_load_line: Enable purge line di depan bed
- auto_eject: Push-off after print complete
- cooldown_temp: Bed temp before auto eject (default 32°C)
- startup_sound: Play startup melody
- end_sound: Play end melody
- quick_start: Skip calibrations (faster startup)
- preheat_offset: Heat to nozzle_temp - offset (cegah oozing)
- pre_extrude: Enable pre-extrude before print
- pre_extrude_length: How much to extrude (mm)
```

### MQTT Topics
```
Status (subscribe):
  device/{printer_id}/report
  └─ Contains all printer data (temps, progress, AMS status)

Command (publish):
  device/{printer_id}/request
  ├─ "start": Start print
  │   param: "filename.3mf"
  │
  ├─ "stop": Stop print
  │
  ├─ "pause": Pause print
  │
  ├─ "gcode_line": Send single G-code
  │   param: "M104 S220\n"
  │
  ├─ "ams_change_filament": Load filament from slot
  │   target: 0-3 (slot) or 255 (unload)
  │
  └─ "eject_plate": Auto-eject print
```

### Connection Modes

**LAN Mode (Preferred)**
```
Printer IP: 192.168.x.x (pada same network)
Port: 8883 (MQTT TLS)
Auth: access_code dari web panel: http://192.168.x.x
Advantage: Faster, no cloud dependency, lower latency
```

**Cloud Mode (Fallback)**
```
Broker: mqtt.bambulab.com
Port: 8883
Auth: Bambu account + password
Requires: Internet connection + Bambu account setup
```

---

## ⚙️ Section Markers untuk Toggle Mode

```
[nozzle_load_line] - Purge line di depan bed
  Start: ;===== nozzle load line
  End:   ;===== nozzle load line end

[vibration_test] - Resonance test
  Start: ;===== mech mode fast check start
  End:   ;===== mech mode fast check end

[flow_calibration] - Flow test
  Start: ;===== auto extrude cali start
  End:   ;===== auto extrude cali end

[bed_leveling] - Auto leveling
  Start: ;===== bed leveling ==
  End:   ;===== bed leveling end

[clean_nozzle] - Nozzle cleaning
  Start: ;===== brush material wipe nozzle
  End:   ;===== brush material wipe nozzle end

[wipe_nozzle] - Full nozzle wipe
  Start: ;===== wipe nozzle ===
  End:   ;===== wipe nozzle end

[startup_sound] & [end_sound]
  Marker: ;=====start printer sound / ;=====printer finish sound
  Note: Same marker for start & end (Bambu style)
```

---

## 🚀 Example: Complete Print Request

```python
# 1. Frontend sends POST request
POST /api/print-control/bambu-a1-001/start-print
Content-Type: application/json

# 2. Backend processes:
# - Finds: Queue.queue_id=5, job_id=3, status='pending'
# - Gets: Job.filename='model.3mf', loop_count=2, current_loop=0
# - Reads: Queue.nozzle_load_line=True, auto_eject=False, etc
# - Preprocesses: G-code dengan settings di atas
# - Uploads: Via FTPS ke printer SD card
# - Publishes: MQTT start command dengan filename
# - Monitors: MQTT status updates setiap 2-5 detik

# 3. Printer receives dan execute:
# - Parses G-code (dengan nozzle_load_line section)
# - Melakukan start sequence
# - Membuat garis di depan bed (nozzle_load_line=True)
# - Prints job

# 4. Completion:
# - Printer signals completion via MQTT
# - Server logs to PrintHistory
# - Checks: current_loop=1 < loop_count=2 → mark as 'pending' again
# - Auto-starts next loop atau next job di queue
```

---

## 🔍 Debugging Tips

1. **Check MQTT Connection**
   ```python
   mqtt_client.mqtt_connected  # Should be True
   mqtt_client.printer_status   # Should be "idle" or "printing"
   ```

2. **Check G-Code Preprocessing**
   ```
   Look in temp folder: processed_model.gcode
   Should have sections commented/uncommented correctly
   ```

3. **Check FTPS Upload**
   ```
   Printer web panel: http://192.168.x.x → Files
   Should see model.3mf in /cache
   ```

4. **Monitor MQTT Messages**
   ```bash
   mosquitto_sub -h 192.168.x.x -p 8883 -u bblp -P {access_code} \
     -t "device/{printer_id}/report" | jq .
   ```

5. **Check Database**
   ```sql
   SELECT * FROM queue WHERE status != 'completed' ORDER BY position_in_queue;
   SELECT * FROM print_history ORDER BY completed_at DESC LIMIT 5;
   ```

---

## 📝 File References

- API: [src/api/print_control.py](src/api/print_control.py)
- Service: [src/services/print_control_service.py](src/services/print_control_service.py)
- MQTT: [src/services/bambu_service.py](src/services/bambu_service.py)
- G-Code: [src/services/gcode_preprocessor.py](src/services/gcode_preprocessor.py)
- FTPS: [src/services/ftps_service.py](src/services/ftps_service.py)
- WebSocket: [src/api/websocket.py](src/api/websocket.py)
