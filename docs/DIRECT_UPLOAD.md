# Direct FTPS Upload to Bambu Lab Printer

## Overview

**Direct FTPS Upload** adalah metode alternatif yang **tidak memerlukan HTTP server**. File di-upload langsung ke SD card printer via FTPS (port 990), kemudian dicetak.

Metode ini didasarkan pada implementasi **OctoPrint-BambuPrinter plugin**.

## Perbandingan Metode

### ❌ HTTP Download (Lama)
```
PC → HTTP Server (:5000) → Printer (downloads)
```
- Requires HTTP server running
- File cached on printer
- Slower (need HTTP server + download)

### ✅ FTPS Direct (Baru)
```
PC → FTPS Direct (:990) → Printer SD Card
```
- No HTTP server needed
- Direct file transfer
- Uses FTPS implicit SSL/TLS
- Faster and simpler

---

## Implementasi

### 1. FTPS Client (`src/services/ftps_service.py`)

**`ImplicitTLS` class** - Custom FTP with implicit SSL wrapping
```python
from src.services.ftps_service import ImplicitTLS, BambuFTPSClient

# Connect and upload
with BambuFTPSClient("192.168.4.101", "34782589") as client:
    client.upload_file("model.3mf", "model.3mf")
```

**Features:**
- Implicit FTPS on port 990
- Username: `bblp` (Bambu Printer Linux Printer)
- Password: Access code from printer
- SSL certificate validation disabled (self-signed)
- Chunked upload (64KB blocks)

### 2. Service Integration (`src/services/bambu_service.py`)

**New method: `send_print_file_direct()`**
```python
mqtt_client = BambuLabMQTTClient(...)

# Step 1: Upload via FTPS
# Step 2: Send MQTT start command
success = mqtt_client.send_print_file_direct("model.3mf")
```

### 3. API Endpoint (`src/api/jobs.py`)

```
POST /api/jobs/upload-direct/{job_id}/print
```

**Usage:**
```bash
# 1. Upload file
curl -X POST -F "file=@model.3mf" \
  http://localhost:5000/api/jobs/upload

# Response:
# {"job_id": 1, "job_name": "model.3mf", "status": "pending"}

# 2. Start direct print
curl -X POST \
  http://localhost:5000/api/jobs/upload-direct/1/print

# Response:
# {
#   "message": "Direct upload successful, print started",
#   "job_id": 1,
#   "file": "model.3mf",
#   "method": "FTPS direct upload"
# }
```

---

## Network Configuration

| Component | Port | Protocol | Usage |
|-----------|------|----------|-------|
| Backend | 5000 | HTTP/WebSocket | REST API, camera stream |
| Printer FTPS | 990 | FTPS (implicit SSL) | Direct file upload |
| Printer MQTT | 8883 | MQTT + TLS | Status, commands |

---

## Printer Credentials (A1)

```python
PRINTER_IP = "192.168.4.101"
PRINTER_SERIAL = "03900D5A2402051"
ACCESS_CODE = "34782589"  # From printer LCD/Bambu app
FTPS_USERNAME = "bblp"    # Hardcoded
FTPS_PORT = 990           # Hardcoded
```

---

## Troubleshooting

### FTPS Connection Refused

**Problem:** Port 990 refused/not responding

**Solution:**
1. Check printer IP: `ping 192.168.4.101`
2. Check printer is in LAN mode (not cloud mode)
3. Check access code is correct (6 digits)
4. Restart printer if needed

### Upload Timeout

**Problem:** Upload hangs after 30 seconds

**Solution:**
1. Increase timeout in `BambuFTPSClient(timeout=60)`
2. Check file size (split large files)
3. Check network stability

### SSL Certificate Error

**Problem:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution:**
- Normal for self-signed printer certs
- Already disabled in ImplicitTLS class
- If still failing, check `context.verify_mode = ssl.CERT_NONE`

---

## Performance

**Upload Speed (typical):**
- 50MB file: ~30 seconds (LAN 100Mbps)
- 100MB file: ~60 seconds

**Comparison:**
- Direct FTPS: Fastest (no intermediate steps)
- HTTP: Slower (needs HTTP server download)

---

## References

- **OctoPrint-BambuPrinter Plugin:** https://github.com/jneilliii/OctoPrint-BambuPrinter
- **Bambu Lab API:** Internal docs
- **FTPS Specification:** RFC 4217

---

## Development Notes

**If port 990 still blocked:**

Option 1: Fallback to HTTP server method (auto-fallback not yet implemented)

Option 2: Check if printer supports alternative port

Option 3: Use network sniffer to debug FTPS handshake

Current status: ✅ Direct FTPS implemented and ready to test
