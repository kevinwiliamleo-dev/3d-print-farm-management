# ✅ Project Setup Checklist & Quick Start

## 🎯 Phase 1 Complete - What You Have Now

Your **3D Print Farm Management System** project structure is complete with:

### Files Created ✅
- [x] 5 Documentation files (README, SETUP, DEVELOPMENT, etc)
- [x] 11 Python source files (FastAPI, database, models, utils)
- [x] 2 Startup scripts (Windows & Linux/macOS)
- [x] 1 Initialization script
- [x] Configuration files (.env, requirements.txt)
- [x] Complete database schema (5 tables)
- [x] 15+ API models (Pydantic schemas)
- [x] OrcaSlicer integration ready

---

## 🚀 Quick Start (Next 5 Minutes)

### Step 1: Navigate to Project
```bash
cd "c:\Users\GIGABYTE\Documents\3d Print farm\cooking-ai-agent"
```

### Step 2: Run Startup Script
```bash
start.bat    # Windows
# or
./start.sh   # Linux/macOS
```

This will automatically:
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Initialize database
- ✅ Check OrcaSlicer
- ✅ Create .env file (if needed)
- ✅ Start FastAPI server

### Step 3: Access API Documentation
```
Open browser: http://localhost:8000/docs
```

### Step 4: Configure Credentials
Edit `.env` file with your Bambu Lab credentials:
```
BAMBU_USERNAME=your_email@example.com
BAMBU_PASSWORD=your_password
BAMBU_PRINTER_ID=your_printer_serial
```

---

## 📚 Documentation to Review

**Read in this order:**

1. **README.md** (15 min read)
   - Project overview
   - Naming conventions (IMPORTANT!)
   - Architecture diagram
   - Tech stack

2. **SETUP.md** (10 min read)
   - Installation steps
   - Troubleshooting
   - Prerequisites

3. **PROJECT_STRUCTURE.md** (5 min read)
   - Directory layout
   - File purposes
   - Development workflow

4. **DEVELOPMENT.md** (10 min read)
   - What's been built
   - Phase 2 planning
   - Endpoints to build

---

## 🔧 Manual Setup (If start.bat doesn't work)

### 1. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate    # Windows
# or
source venv/bin/activate # Linux/macOS
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python -c "from src.database import init_db; init_db()"
```

### 4. Start Server
```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ✅ Verification Steps

After starting the server:

1. **Check API Health**
   ```
   curl http://localhost:8000/health
   ```
   Expected: `{"status":"healthy","service":"3D Print Farm Management System"}`

2. **Check API Docs**
   ```
   http://localhost:8000/docs
   ```
   Should load Swagger UI

3. **Check Database**
   - Look for `data/farm.db` file
   - Should be created automatically

4. **Check Configuration**
   - Look for `.env` file
   - Should have template values

---

## 🎓 Code Standards to Remember

### From README.md - Naming Conventions

**Variables (Python):**
```python
job_id              # Not job_ID or jobId
printer_name        # Not printer_Name
queue_position      # Not queuePosition
layer_height        # Not layerHeight (in Python!)
```

**Variables (JavaScript):**
```javascript
jobId               # camelCase in JavaScript
printerName
queuePosition
layerHeight         # camelCase for consistency
```

**Functions:**
```python
def slice_model()           # snake_case
def send_gcode_to_printer() # descriptive names
def add_job_to_queue()      # verb_noun pattern
```

**Database Fields:**
```
job_id (PK)
printer_id (FK)
layer_height (REAL)
infill_density (INTEGER 0-100)
status (TEXT: pending|running|completed|failed)
```

---

## 🔑 Important Configuration

### .env File Setup
```
# Copy from .env.example then edit:
BAMBU_USERNAME=your_email@example.com
BAMBU_PASSWORD=your_password
BAMBU_PRINTER_ID=printer_serial
MQTT_BROKER=mqtt.bambulab.com
```

### OrcaSlicer Check
```bash
# Verify installation:
orca-slicer --version

# If not found:
# Download: https://github.com/SoftFever/OrcaSlicer/releases
```

---

## 📊 Database Tables Reference

Quick reference for database structure:

### `jobs` table
```sql
job_id (PK) | job_name | filename | loop_count | status
```

### `queue` table
```sql
queue_id (PK) | job_id (FK) | printer_id | position_in_queue | status
```

### `print_history` table
```sql
history_id (PK) | job_id (FK) | start_time | end_time | material_used_grams | print_success
```

---

## 🚨 Troubleshooting Quick Fixes

### "OrcaSlicer not found"
```bash
# Check if installed
orca-slicer --version

# If missing, download from:
# https://github.com/SoftFever/OrcaSlicer/releases
```

### "Module not found" errors
```bash
# Make sure virtual environment is activated:
venv\Scripts\activate    # Windows
source venv/bin/activate # Linux/macOS

# Reinstall dependencies:
pip install -r requirements.txt
```

### "Port 8000 already in use"
```bash
# Use different port:
python -m uvicorn src.main:app --port 8001

# Then visit: http://localhost:8001/docs
```

### "Database locked"
```bash
# Delete old database and reinitialize:
rm data/farm.db
python -c "from src.database import init_db; init_db()"
```

---

## 📋 Folder Structure at a Glance

```
cooking-ai-agent/
├── src/                  ← Your code goes here
├── data/                 ← Database & files (ignore in git)
├── logs/                 ← Application logs
├── README.md             ← Read this first!
├── SETUP.md              ← Setup instructions
├── requirements.txt      ← Python packages
├── .env                  ← Your secrets (don't commit)
└── start.bat             ← Run this to start
```

---

## 🎯 Your Next Tasks

### Today (Phase 1 Complete)
- [x] Download/install project
- [x] Review documentation
- [x] Run start.bat
- [x] Access http://localhost:8000/docs
- [x] Configure .env with credentials

### This Week (Phase 2)
- [ ] Build job upload endpoint
- [ ] Build queue management endpoints
- [ ] Test with mock printer
- [ ] Test OrcaSlicer integration

### Next Week (Phase 3)
- [ ] Build React frontend
- [ ] Create dashboard UI
- [ ] Test with real printer
- [ ] Setup auto-eject logic

---

## 💡 Pro Tips

1. **Always activate virtual environment first**
   ```bash
   venv\Scripts\activate
   ```

2. **Use `--reload` during development**
   ```bash
   python -m uvicorn src.main:app --reload
   ```

3. **Check .env before starting**
   - Make sure credentials are set
   - Make sure file exists (copy from .env.example)

4. **Monitor logs for errors**
   - Check `logs/` directory
   - Watch console output

5. **Use API docs to test endpoints**
   - Go to http://localhost:8000/docs
   - Try endpoints interactively
   - See request/response formats

---

## 🔗 Quick Links

- **Start Server:** `python -m uvicorn src.main:app --reload`
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Config File:** `.env`
- **Database File:** `data/farm.db`
- **Main Code:** `src/main.py`

---

## ✨ You're All Set!

Everything is ready for development. Start with `start.bat` and you'll be up and running in seconds! 🚀

Questions? Check the documentation files:
- README.md - General info
- SETUP.md - Installation help
- PROJECT_STRUCTURE.md - Where things are
- DEVELOPMENT.md - What's built & what's next

**Happy coding!** 🎉

---

**Status:** ✅ Phase 1 Complete
**Next:** Phase 2 - Build API Endpoints
**Date:** December 28, 2025
