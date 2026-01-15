# Printer Discovery Guide - Bambu Lab A1

## Problem
Auto-discovery mungkin tidak bekerja di semua network (tergantung router WiFi, mDNS support, dll).

## Solutions

### ✅ Solution 1: Lookup Printer ID Directly

Jika Anda tahu **Printer ID** (serial number), gunakan fitur **"Lookup by ID"** di dashboard:

1. Ambil Printer ID dari:
   - **Printer Settings** → Serial Number (di printer display)
   - **QR Code** di belakang printer
   - **Bambu Lab App** → Settings → Serial Number
   - Contoh format: `03900D5A2402051`

2. Di dashboard, buka tab **"Lookup Printer"** (akan ditambah UI)
3. Masukkan Printer ID dan klik **"Find"**
4. Sistem akan mencoba akses printer via mDNS hostname: `BambuLab_03900D5A2402051.local`

### ✅ Solution 2: Manual Registration with IP Address

Jika mDNS tidak bekerja, cari IP printer:

1. **Di Router Settings:**
   - Akses admin panel router (biasanya 192.168.1.1)
   - Cari device "BambuLab" atau "Bambu"
   - Catat IP address-nya

2. **Di Bambu Lab App:**
   - Buka Settings → Network
   - Lihat IP Address yang ditampilkan

3. **Ping dari Command Line:**
   ```bash
   ping BambuLab_03900D.local
   # Jika berhasil, akan menampilkan IP address
   ```

4. **Di Dashboard:**
   - Masukkan IP address langsung ke printer settings
   - Atau gunakan `BambuLab_XXXXX.local` format

### ✅ Solution 3: Network Scan (Auto-Discovery)

Fitur yang sudah ada - cukup klik **"🔍 Auto-Discover"** button.

Sistem akan:
1. Scan mDNS untuk `_bambulab._tcp` service
2. Jika mDNS gagal, fallback ke port scanning pada subnet lokal
3. Auto-register semua printer yang ditemukan

## How the System Works

### Discovery Methods (in order):
1. **mDNS (Zeroconf)** - Fastest, requires zeroconf library
2. **mDNS Hostname Lookup** - Try common patterns like `BambuLab_03900D.local`
3. **Network Subnet Scan** - Scan 192.168.x.100-200 on ports 22, 80, 443, 8080

### Printer ID Format
- Bambu Lab uses **14-character hex serial**: `03900D5A2402051`
- mDNS hostname: `BambuLab_03900D.local` (first 6 chars)
- Or full: `BambuLab_03900D5A2402051.local`

## Troubleshooting

### Q: "No printers found" - what to do?

1. **Check Printer is Online:**
   - Printer powered ON
   - Connected to WiFi (check LCD screen)
   - On same network as computer

2. **Check Network:**
   - Open command prompt: `ipconfig`
   - Check your IP (e.g., 192.168.1.x)
   - Printer should be on same subnet

3. **Check Router mDNS Support:**
   - Some routers disable mDNS
   - Try accessing `BambuLab_XXXXX.local` directly in browser
   - If doesn't work, need to use IP address directly

4. **Try Manual Lookup:**
   - Get Printer ID from serial number
   - Use **"Lookup by ID"** feature
   - Or manually enter IP address

### Q: How to find my printer's IP?

**Method 1: Router Admin Panel**
```
1. Open browser: http://192.168.1.1 (or 192.168.0.1)
2. Login with router credentials
3. Find "Connected Devices" or "DHCP Clients"
4. Look for device name containing "BambuLab" or "Bambu"
5. Note the IP address
```

**Method 2: Bambu Lab App**
```
1. Open Bambu Lab app on phone
2. Go to Settings
3. Select printer
4. Check Network info - shows IP address
```

**Method 3: Command Line (Windows)**
```powershell
# Find all devices on network
arp -a

# Or try to ping (may not work if mDNS disabled)
ping BambuLab_03900D.local
```

**Method 4: From Printer Display**
```
On printer A1 LCD screen:
Settings → Network → IP Address
```

## API Endpoints

### Auto-Discovery
- `POST /api/printers/discover/scan` - Scan and auto-register
- `GET /api/printers/discover/async` - Start async scan
- `GET /api/printers/discover/results` - Get async results

### Manual Lookup
- `POST /api/printers/lookup-by-id/{printer_id}` - Find printer by ID
- `POST /api/printers` - Manually register printer with ID + Name

## Example Workflow

### Scenario: Can't find printer automatically

```
1. User clicks "🔍 Auto-Discover" → No printers found
2. User gets Printer ID from serial: "03900D5A2402051"
3. User clicks "Lookup by ID" → Enters "03900D5A2402051"
4. System finds printer at: 192.168.1.105
5. User registers with ID "03900D5A2402051" and Name "My A1"
6. Dashboard shows printer in sidebar ✅
```

## Notes

- **Printer ID** is the serial number (14 chars, hexadecimal)
- **mDNS hostname** is auto-generated from serial
- **IP address** is dynamic (may change after reboot)
- Keep printer on same WiFi network for reliable connection
- Bambu Lab default mDNS domain is `.local`
