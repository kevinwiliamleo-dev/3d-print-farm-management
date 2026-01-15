# 🚀 Setup Guide - 3D Print Farm Management System

This guide will help you set up and run the 3D Print Farm Management System.

## 📋 Prerequisites

- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **OrcaSlicer** - [Download](https://github.com/SoftFever/OrcaSlicer/releases)
- **Bambu Lab A1 Combo AMS** printer
- **Bambu Lab Cloud Account** - For API credentials

## 🔧 Installation Steps

### Step 1: Clone or Create Project Directory

```bash
cd "c:\Users\GIGABYTE\Documents\3d Print farm"
cd cooking-ai-agent
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install OrcaSlicer

**Option A: Automatic (if in PATH)**
```bash
# Windows
winget install orcaslicer

# macOS
brew install orcaslicer

# Linux
sudo apt-get install orcaslicer
```

**Option B: Manual**
1. Download from: https://github.com/SoftFever/OrcaSlicer/releases
2. Install and add to system PATH
3. Verify: `orca-slicer --version`

### Step 4: Configure Environment

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file with your credentials:**
   ```
   # Bambu Lab Cloud API
   BAMBU_USERNAME=your_email@example.com
   BAMBU_PASSWORD=your_password
   BAMBU_PRINTER_ID=your_printer_serial_number
   
   # MQTT Settings (usually auto-detected)
   MQTT_BROKER=mqtt.bambulab.com
   MQTT_USERNAME=your_mqtt_username
   MQTT_PASSWORD=your_mqtt_password
   
   # OrcaSlicer Path (if not in system PATH)
   ORCA_SLICER_PATH=/path/to/orca-slicer
   ```

### Step 5: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6: Initialize Database

```bash
python -c "from src.database import init_db; init_db()"
```

This will create `data/farm.db` with all tables.

## ▶️ Running the Application

### Quick Start (Recommended)

**Windows:**
```bash
start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

### Manual Start

```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Access the API

- **API**: http://localhost:8000
- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc

## ✅ Verification Checklist

After starting, verify everything is working:

- [ ] API is running at http://localhost:8000
- [ ] Swagger UI loads at http://localhost:8000/docs
- [ ] OrcaSlicer is detected: `orca-slicer --version`
- [ ] Database created: `data/farm.db` exists
- [ ] No error messages in console
- [ ] Can see health check: GET http://localhost:8000/health

## 📝 First Time Setup Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] OrcaSlicer installed and in PATH
- [ ] `.env` file created with Bambu Lab credentials
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Database initialized
- [ ] Application started successfully

## 🔐 Getting Bambu Lab Credentials

### 1. Get BAMBU_USERNAME & BAMBU_PASSWORD
- Create account at https://bambulab.com
- Use your email and password

### 2. Get BAMBU_PRINTER_ID
- In Bambu Lab Studio
- Settings → Device → Look for "Device ID" or "Serial Number"
- Or in Bambu Lab Cloud dashboard

### 3. Get MQTT Credentials (if needed)
- Usually same as cloud credentials
- Bambu Lab automatically sets these up

## 🚨 Troubleshooting

### OrcaSlicer Not Found
```bash
# Check if installed
where orca-slicer  (Windows)
which orca-slicer  (Linux/macOS)

# If not found, download from:
# https://github.com/SoftFever/OrcaSlicer/releases
```

### Database Errors
```bash
# Reset database (WARNING: deletes all data)
rm data/farm.db

# Reinitialize
python -c "from src.database import init_db; init_db()"
```

### Python Version Issues
```bash
# Check Python version
python --version

# If Python 3.8+ not default:
python3 -m venv venv
python3 -m pip install -r requirements.txt
```

### Permission Denied on .sh Script
```bash
chmod +x start.sh
./start.sh
```

## 📚 Next Steps

1. **Review Project Structure**: See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
2. **Learn Naming Conventions**: See [README.md - Code Standards](README.md#-naming-conventions--code-standards)
3. **Start Development**: Begin with Phase 1 API endpoints

## 🔗 Useful Resources

- **OrcaSlicer GitHub**: https://github.com/SoftFever/OrcaSlicer
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org
- **Bambu Lab Wiki**: https://wiki.bambulab.com

## 💡 Tips

- Always activate virtual environment before working
- Keep `.env` secure - never commit it to git
- Check logs in `logs/` directory if something goes wrong
- Use `--reload` flag during development for auto-reload

---

**Setup Complete!** You're ready to start development. 🎉
