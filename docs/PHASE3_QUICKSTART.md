# 🚀 Phase 3 Quick Start - Frontend + Backend

Run the complete 3D Print Farm Management System

## Prerequisites

- ✅ Backend dependencies installed (Python, requirements.txt)
- ✅ Frontend dependencies installed (Node.js, npm)
- ✅ Both servers can run on localhost

## Run Both Servers (Parallel)

### Option 1: Separate Terminal Windows (Recommended)

**Terminal 1 - Backend (Python):**
```bash
cd "C:\Users\GIGABYTE\Documents\3d Print farm\cooking-ai-agent"
. venv_clean\Scripts\activate.ps1
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Output:
```
Uvicorn running on http://127.0.0.1:8000
Press CTRL+C to quit
```

**Terminal 2 - Frontend (React):**
```bash
cd "C:\Users\GIGABYTE\Documents\3d Print farm\cooking-ai-agent\frontend"
npm start
```

Output:
```
Compiled successfully!
You can now view my-app in the browser.
  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

### Option 2: Single Terminal with Task Runner

Create a batch file `run-all.bat`:
```batch
@echo off
REM Start backend in new window
start "Backend" cmd /k "cd C:\Users\GIGABYTE\Documents\3d Print farm\cooking-ai-agent && venv_clean\Scripts\activate.ps1 && uvicorn src.main:app --host 0.0.0.0 --port 8000"

REM Start frontend in new window
start "Frontend" cmd /k "cd C:\Users\GIGABYTE\Documents\3d Print farm\cooking-ai-agent\frontend && npm start"

echo.
echo ============================================
echo 🖨️  3D Print Farm Manager
echo ============================================
echo.
echo Backend: http://localhost:8000
echo  - API: http://localhost:8000/api/*
echo  - Docs: http://localhost:8000/docs
echo.
echo Frontend: http://localhost:3000
echo.
pause
```

Run:
```bash
./run-all.bat
```

## Access the Application

Once both servers are running:

1. **Frontend (Web UI):** http://localhost:3000
2. **Backend (API):** http://localhost:8000
3. **API Documentation:** http://localhost:8000/docs

## Quick Test Flow

1. **Open Frontend** → http://localhost:3000
2. **Register a Printer**
   - Click "Register Printer" in sidebar
   - Use printer ID: `03900D5A2402051` (or your printer ID)
   - Use name: `My A1 Printer`

3. **Upload a Job**
   - Click "Upload Job" tab
   - Select a `.3mf` or `.stl` file
   - Set loops (e.g., 2-5)
   - Click "Upload Job"

4. **Add to Queue**
   - Go to "Queue" tab
   - Job should appear (if connected to printer)
   - Check FIFO position

5. **Monitor Status**
   - Watch printer status section
   - Real-time updates every 3-5 seconds
   - MQTT connection status shown

## API Endpoints Being Used

| Method | Endpoint | Used By |
|--------|----------|---------|
| POST | /api/jobs/upload | JobUploadForm |
| GET | /api/jobs | JobsList |
| DELETE | /api/jobs/{id} | JobsList |
| POST | /api/printers | Dashboard |
| GET | /api/printers | Dashboard |
| PATCH | /api/printers/{id}/status | PrinterStatus |
| POST | /api/queue/add | Dashboard |
| GET | /api/queue/{id} | QueueManager |
| POST | /api/queue/{id}/remove | QueueManager |
| GET | /api/print-control/{id}/status | PrinterStatus |
| GET | /api/print-control/{id}/mqtt-status | PrinterStatus |
| POST | /api/print-control/{id}/start-print | PrinterStatus |

## Troubleshooting

### "Connection Refused" Error
```
Error: Failed to load printers
```
**Solution:** Backend not running. Start backend server first.

### "CORS Error" in Browser Console
```
Access to XMLHttpRequest blocked by CORS policy
```
**Solution:** Ensure backend has CORS middleware enabled (should be automatic in FastAPI)

### File Upload Fails
```
"Failed to upload job"
```
**Check:**
- File is .3mf or .stl format
- `data/uploads/` directory exists
- Backend console for detailed error

### Printer Not Showing in Queue
**Check:**
- Printer status is "idle" not "offline"
- MQTT is connected (🟢 green indicator)
- Job was successfully uploaded

### Slow or No Auto-Refresh
**Solution:**
- Click 🔄 Refresh button manually
- Check browser console for errors
- Restart frontend: Ctrl+C and `npm start` again

## Development Notes

### Backend Auto-Reload
The `--reload` flag on uvicorn watches for changes:
- Modify `.py` files → auto-restarts
- Check terminal for reload messages

### Frontend Hot Reload
The React dev server has hot module reloading:
- Modify `.tsx` files → instant browser update
- Check browser console for compile errors

### Debugging

**Backend Logs:**
Check terminal window for:
- API request logs
- Error tracebacks
- Database operations

**Frontend Logs:**
Open browser DevTools (F12):
- Network tab → see API calls
- Console tab → see JS errors
- React tab → inspect components

## Next Steps

1. ✅ Test basic job upload/queue
2. ✅ Verify printer registration works
3. ✅ Check real-time status updates
4. ⏭️ Test with real Bambu Lab A1 (if available)
5. ⏭️ Add print history visualization
6. ⏭️ Implement advanced scheduler

## Performance

**Expected Response Times:**
- Job upload: 1-2 seconds
- Queue operations: <500ms
- Printer status: <500ms
- Auto-refresh: Every 3-5 seconds

**Browser Requirements:**
- Modern browser (Chrome, Firefox, Edge, Safari)
- JavaScript enabled
- Cookies enabled for sessions (if added)

---

**Status:** 🟢 Ready to Run  
**Phase:** Phase 3 - Frontend Complete  
**Last Updated:** December 29, 2025
