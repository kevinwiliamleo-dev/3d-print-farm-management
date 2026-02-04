# 🏠 Homelab Deployment Guide
## Deploy 3D Print Farm ke Proxmox + Portainer

---

## 📋 Prerequisites

- ✅ Proxmox sudah running
- ✅ Portainer sudah installed
- ✅ Git repository (GitHub/GitLab)
- ✅ Network printer Bambu Lab accessible dari server

---

## 🚀 Quick Start Guide

**Existing Repository:**
- URL: https://github.com/kevinwiliamleo-dev/3d-print-farm-management
- Branch: `development` (active) | `main` (stable)

### Step-by-Step:

```bash
# 1. Check current branch and status
git status
git branch

# 2. Add Docker files (jika belum)
git add Dockerfile* docker-compose* .dockerignore DEPLOYMENT.md frontend/nginx.conf

# 3. Commit changes
git commit -m "Docker deployment configuration"

# 4. Push ke development branch
git push origin development

# 5. Setup Portainer (one-time setup)
#    - Stacks → Add stack
#    - Name: 3d-print-farm
#    - Repository: https://github.com/kevinwiliamleo-dev/3d-print-farm-management
#    - Branch: development
#    - Compose path: docker-compose.yml
#    - Auto-update: ON (5 min)
#    - Deploy!

# 6. Access aplikasi
#    Frontend: http://SERVER_IP:3051
#    Backend:  http://SERVER_IP:5051
```

### Workflow Sehari-hari:

```bash
# Edit code → Test local → Push
git add .
git commit -m "Feature X"
git push origin development

# Wait 5 minutes → Portainer auto-deploy → Test di homelab
```

### Merge to Production:

```bash
# Setelah testing di development OK
git checkout main
git merge development
git push origin main

# Update Portainer stack ke branch main (or create new prod stack)
```

**✅ Repo sudah ada:** https://github.com/kevinwiliamleo-dev/3d-print-farm-management

```bash
# Di laptop Windows Anda
cd "C:\Users\GIGABYTE\Documents\3d Print farm\cooking-ai-agent"

# Cek status git dan branch
git status
git branch

# Anda sedang di branch: development (atau main)
# Add Docker files
git add .
git commit -m "Add Docker deployment configuration"

# Push ke existing repo
git push origin development
# Atau jika di main:
# git push origin main
```

**Branch Strategy:**
- `development` - Development work (current branch)
- `main` - Production-ready stable code

**Workflow:**
1. Development → Push ke `development` branch
2. Testing → Test di Portainer dengan `development` branch
3. Stable → Merge `development` → `main`
4. Production → Deploy dari `main` branch

---

### 2️⃣ Setup di Portainer

**A. Buat Stack Baru:**
1. Buka Portainer → Stacks → Add stack
2. Name: `3d-print-farm`
3. Build method: **Repository**
4. Repository URL: `https://github.com/kevinwiliamleo-dev/3d-print-farm-management`
5. Branch: `development` (untuk testing) atau `main` (untuk production)
6. Compose path: `docker-compose.yml`

**B. Environment Variables (OPSIONAL):**

> **Catatan:** Environment variables **TIDAK WAJIB** karena printer data sudah ada di database.
> Hanya diperlukan untuk first run atau testing.

```env
# Opsional - hanya untuk first run sebelum add printer via UI
BAMBU_PRINTER_IP=192.168.4.101
BAMBU_PRINTER_ID=03900D5A2402051
BAMBU_ACCESS_CODE=34782589
```

**Atau bisa dikosongkan saja:**
```env
# Printer akan diambil dari database
# (tidak perlu env vars)
```

**C. Advanced Settings:**
- ✅ Enable Automatic Updates
- Poll interval: `5 minutes`
- ✅ Re-pull image
- ✅ Prune old images

**D. Deploy!**
- Click **Deploy the stack**
- Wait 2-3 minutes untuk build

---

### 3️⃣ Akses Aplikasi

```
Frontend: http://SERVER_IP:3051
Backend:  http://SERVER_IP:5051
API Docs: http://SERVER_IP:5051/docs
```

---

## 🔄 Development Workflow (Hot Reload)

### Mode Development (Recommended untuk Testing)

**Setup saat ini menggunakan volume mounts:**
```yaml
volumes:
  - ./src:/app/src:ro          # Backend source
  - ./frontend/src:/app/src:ro # Frontend source
```

**Workflow:**

1. **Edit di Laptop:**
   ```bash
   # Edit file di VS Code
   # Misalnya: src/api/queue.py
   ```

2. **Test Local (Optional):**
   ```bash
   # Test di laptop dulu
   .\run.bat
   ```

3. **Push ke Git (Existing Repo):**
   ```bash
   git add .
   git commit -m "Update: add new feature"
   git push origin development
   # Atau push ke main jika sudah stable
   ```

4. **Portainer Auto-Update:**
   - Tunggu 5 menit (polling interval)
   - Portainer detect changes di `development` branch
   - Pull latest code
   - Restart containers dengan source baru
   - **Hot reload** akan detect perubahan

5. **Verify:**
   - Buka http://SERVER_IP:3051
   - Test fitur baru

**Branch Strategy di Portainer:**
- **Development Server:** Point ke branch `development`
  - Auto-update enabled
  - Poll every 5 minutes
  - Untuk testing dan development
  
- **Production Server:** Point ke branch `main`
  - Auto-update enabled (optional)
  - Poll every 30 minutes (lebih jarang)
  - Hanya deploy setelah testing di development

---

## 🏗️ Production Mode (Nanti kalau sudah stable)

**Ganti docker-compose.yml dengan production:**

```bash
# Di Portainer, edit stack
# Ganti Compose path: docker-compose.prod.yml
```

**Perbedaan:**
- ❌ No source code mounts (lebih aman)
- ❌ No hot reload (lebih stabil)
- ✅ Nginx serving static files (lebih cepat)
- ✅ Optimized build
- ✅ Port 80 (production standard)

---

## 🔧 Troubleshooting

### 1. Printer Configuration (Penting!)

**Printer data diambil dari DATABASE, bukan environment variables!**

**Cara Add Printer (First Run):**
1. Akses frontend: http://SERVER_IP:3051
2. Klik menu **"Printers"** atau **"Settings"**
3. Add Printer dengan data:
   - IP: 192.168.4.101
   - Printer ID: 03900D5A2402051
   - Access Code: 34782589
4. Save → Printer tersimpan di database (persistent)

**Catatan:**
- Environment variables di Portainer **OPSIONAL**
- Hanya diperlukan untuk fallback/testing
- Data printer di database lebih prioritas

### 2. Container tidak bisa akses printer

**Solusi:**
- Pastikan Proxmox VM bisa ping printer:
  ```bash
  ping 192.168.4.101
  ```
- Cek firewall: port 8883 (MQTT) dan 990 (FTPS) harus terbuka

### 2. Hot reload tidak jalan

**Solusi:**
- Restart Portainer stack
- Cek logs: Portainer → Containers → 3d-farm-frontend → Logs
- Pastikan `CHOKIDAR_USEPOLLING=true` ada di environment

### 3. Database hilang setelah restart

**Solusi:**
- Volume data sudah di-mount: `./data:/app/data`
- Cek Portainer → Volumes → pastikan `data` volume ada

### 4. Auto-update tidak jalan

**Solusi A (Portainer):**
- Stack → 3d-print-farm → Edit
- Cek "Enable Automatic Updates"
- Reduce poll interval ke 1 minute untuk testing

**Solusi B (Watchtower - lebih cepat):**
- Service `watchtower` sudah ada di docker-compose.yml
- Auto-check setiap 5 menit
- Rebuild image jika ada perubahan di Git

---

## 📊 Monitoring

### Cek Status Containers:
```bash
# Via Portainer UI
Containers → 3d-farm-backend → Stats
Containers → 3d-farm-frontend → Stats

# Via Docker CLI (di Proxmox VM)
docker ps
docker stats
docker logs 3d-farm-backend
docker logs 3d-farm-frontend
```

### Cek Health:
```bash
curl http://SERVER_IP:5051/health
curl http://SERVER_IP:5051/api/printers
```

---

## 🎯 Testing Checklist

Setelah deploy, test:

- ✅ Frontend accessible (http://SERVER_IP:3051)
- ✅ Backend API working (http://SERVER_IP:5051/docs)
- ✅ MQTT connection ke printer (check printer status)
- ✅ File upload working
- ✅ Queue management working
- ✅ Hot reload working (edit file, git push, wait 5 min, check changes)

---

## 🔐 Security Notes (Production Nanti)

Untuk production, tambahkan:

1. **Reverse Proxy (Nginx/Traefik):**
   - SSL/TLS certificates
   - Single entry point
   - Rate limiting

2. **Environment Variables:**
   - Jangan hardcode passwords di docker-compose.yml
   - Use Portainer secrets

3. **Network Isolation:**
   - Backend tidak perlu expose port 5051 ke public
   - Frontend proxy ke backend via internal network

4. **Database Backup:**
   - Automated backup SQLite database
   - Volume snapshots

---

## 📝 File Structure Summary

```
.
├── Dockerfile.backend          # Backend container
├── Dockerfile.frontend         # Frontend container
├── docker-compose.yml          # Development (hot reload)
├── docker-compose.prod.yml     # Production (optimized)
├── .dockerignore              # Exclude files dari build
├── frontend/
│   └── nginx.conf             # Nginx config untuk production
└── DEPLOYMENT.md              # This file
```

---

## 🆘 Support

Jika ada masalah:
1. Check logs: `docker logs CONTAINER_NAME`
2. Check Portainer UI untuk resource usage
3. Restart stack: Portainer → Stacks → 3d-print-farm → Stop/Start
4. Rebuild: Portainer → Stacks → 3d-print-farm → Pull and redeploy

---

**Last Updated:** February 4, 2026
**Status:** Development-ready dengan hot reload
**Next Step:** Test deployment di homelab Anda!
