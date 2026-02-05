@echo off
REM Startup script for 3D Print Farm Management System
REM Auto-restarts servers if they crash

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ========================================
echo 3D Print Farm Management System
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv_clean\" (
    echo Creating virtual environment...
    python -m venv venv_clean
    echo Virtual environment created.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv_clean\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q

REM Check OrcaSlicer installation
echo.
echo Checking OrcaSlicer installation...
where orca-slicer >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo WARNING: OrcaSlicer not found in PATH
    echo Please install OrcaSlicer from: https://github.com/SoftFever/OrcaSlicer/releases
) else (
    echo OrcaSlicer found!
)

REM Initialize database
echo.
echo Initializing database...
python -c "from src.database import init_db; init_db()" >nul 2>&1

REM Build frontend
echo.
echo Building frontend...
cd frontend
call npm run build
cd ..

echo.
echo ========================================
echo Starting All Servers with Auto-Restart
echo ========================================
echo.

REM Open Backend Server window
echo [1] Starting Backend Server...
start "BACKEND SERVER [Auto-Restart]" cmd /k "%~dp0\start-backend.bat"

timeout /t 3 /nobreak

REM Open Frontend Server window
echo [2] Starting Frontend Server...
start "FRONTEND SERVER [Auto-Restart]" cmd /k "%~dp0\start-frontend.bat"

echo.
echo ========================================
echo ✅ Servers Started!
echo ========================================
echo.
echo Backend:  http://localhost:5000
echo API Docs: http://localhost:5000/docs
echo Frontend: http://localhost:3000
echo.
echo Both servers will auto-restart if crashed!
echo.
echo Press any key to exit this window...
echo (Servers will continue running in their own windows)
pause >nul
exit
