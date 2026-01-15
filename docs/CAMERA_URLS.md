# 📷 Bambu Lab Camera Integration URLs

## Kamera Bambu Lab A1 Integration

Backend kami sudah menyediakan endpoint untuk mengakses camera printer Bambu Lab dengan mudah.

### Endpoint yang Tersedia

#### 1. **Live MJPEG Stream** (Continuous Video)
```
http://localhost:5000/api/camera/stream
```
**Gunakan untuk:**
- HTML `<img>` tag dengan MJPEG stream
- Live video preview
- Real-time monitoring

**Contoh HTML:**
```html
<img src="http://localhost:5000/api/camera/stream" alt="Printer Camera" style="width: 100%; height: auto;" />
```

#### 2. **Single Snapshot** (Still Image)
```
http://localhost:5000/api/camera/snapshot
```
**Gunakan untuk:**
- Refresh manual dengan button
- Hemat bandwidth
- Polling dengan interval tertentu

**Contoh dengan polling setiap 2 detik:**
```html
<img id="camera" src="http://localhost:5000/api/camera/snapshot" alt="Printer Camera" />

<script>
  setInterval(() => {
    document.getElementById('camera').src = 
      `http://localhost:5000/api/camera/snapshot?t=${Date.now()}`;
  }, 2000);
</script>
```

#### 3. **Camera Status**
```
http://localhost:5000/api/camera/status
```
**Response:**
```json
{
  "camera_available": true,
  "has_recent_frame": true,
  "last_frame_age": 0.5,
  "printer_ip": "192.168.4.101",
  "stream_url": "/api/camera/stream",
  "snapshot_url": "/api/camera/snapshot"
}
```

#### 4. **Reconnect Camera** (Force Fresh Connection)
```
POST http://localhost:5000/api/camera/reconnect
```
**Gunakan untuk:**
- Reset koneksi kamera jika stuck
- Reconnect ke printer

---

## 🔧 OctoPrint Integration

### ⚙️ PC Configuration
- **IP Address:** `192.168.4.26`
- **Port:** `5000`
- **Printer IP:** `192.168.4.101`

### 🎬 URL untuk OctoPrint Setup Wizard

**Stream URL (untuk embedded webcam stream):**
```
http://192.168.4.26:5000/api/camera/stream
```

**Snapshot URL (untuk timelapse & preview):**
```
http://192.168.4.26:5000/api/camera/snapshot
```

### 🔧 Langkah Setup di OctoPrint:

1. **Buka OctoPrint** (di Raspberry Pi atau device lain)
2. **Settings → Webcam & Timelapse**
3. Pada **"Classic Webcam Wizard":**
   - **Stream URL:** `http://192.168.4.26:5000/api/camera/stream`
   - **Snapshot URL:** `http://192.168.4.26:5000/api/camera/snapshot`
4. Klik **"Test"** untuk verifikasi (browser harus bisa reach IP ini)
5. Jika keluar gambar printer, selesai! ✅

### ⚠️ PENTING - Browser Accessibility

**URL harus reachable dari browser yang membuka OctoPrint UI!**

- Jika browser di **PC yang sama:** gunakan `http://localhost:5000/api/camera/stream`
- Jika browser di **device lain:** gunakan `http://192.168.4.26:5000/api/camera/stream`

### 🐛 Jika Stream Tidak Tampil:

OctoPrint/browser kadang tidak support MJPEG streaming. Gunakan **Snapshot Polling** sebagai alternatif:

**Konfigurasi snapshot URL yang sudah tested:**
```
http://192.168.4.26:5000/api/camera/snapshot
```

OctoPrint akan auto-refresh snapshot setiap 1-2 detik, memberikan efek video.

---

## 📊 Current Implementation

**Printer Configuration:**
- IP: `192.168.4.101`
- Access Code: `34782589`
- Camera API: JPEGFrameStream (bambulab library)
- Cache: Auto-refresh setiap ~1 detik
- FPS: ~2 FPS untuk stream MJPEG

**Frontend Implementation:**
- React component dengan `useEffect` hook
- Periodic refresh: 500ms (untuk smoother preview)
- Auto-fallback ke cached frame jika koneksi error
- Live status indicator (green dot = live, red = offline)

**File yang berubah:**
- `src/api/camera.py` - Camera API endpoints
- `frontend/src/components/PrinterStatus.tsx` - Camera display component
- URLs updated dari port 8002 → 5000

---

## 🚀 Testing URLs

Buka di browser untuk test:

```
# Test Stream
http://localhost:5000/api/camera/stream

# Test Snapshot
http://localhost:5000/api/camera/snapshot

# Check Status
http://localhost:5000/api/camera/status

# Frontend
http://localhost:3000
```

---

## 📝 Notes

- Stream URL bisa diakses dari browser berbeda dan device berbeda (asalkan bisa reach IP 192.168.4.101)
- MJPEG format universal, kompatibel dengan hampir semua player
- Snapshot bisa di-cache dengan query string timestamp: `?t=1234567890`
- Camera akan auto-reconnect jika koneksi terputus

