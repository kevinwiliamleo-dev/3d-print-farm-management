@echo off
REM ============================================
REM Smart Start/Restart Script
REM - Checks if servers are running
REM - If running: stops and restarts
REM - If not running: starts fresh
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ========================================
echo 3D Print Farm Management System
echo Smart Start/Restart
echo ========================================
echo.

REM Check if backend is running (port 5051)
echo [1/3] Checking server status...
netstat -ano | findstr ":5051" | findstr "LISTENING" >nul 2>&1
set BACKEND_RUNNING=%ERRORLEVEL%

netstat -ano | findstr ":3051" | findstr "LISTENING" >nul 2>&1
set FRONTEND_RUNNING=%ERRORLEVEL%

if %BACKEND_RUNNING%==0 (
    echo    Backend: RUNNING
) else (
    echo    Backend: NOT RUNNING
)

if %FRONTEND_RUNNING%==0 (
    echo    Frontend: RUNNING
) else (
    echo    Frontend: NOT RUNNING
)

echo.

REM If any server is running, kill all processes
if %BACKEND_RUNNING%==0 (
    echo [2/3] Servers detected. Stopping all processes...
    echo    Closing all terminals and processes...
    
    REM Kill all Python processes
    taskkill /F /IM python.exe /T >nul 2>&1
    
    REM Kill all Node processes
    taskkill /F /IM node.exe /T >nul 2>&1
    
    REM Kill all cmd windows with specific titles
    taskkill /FI "WINDOWTITLE eq BACKEND*" >nul 2>&1
    taskkill /FI "WINDOWTITLE eq FRONTEND*" >nul 2>&1
    taskkill /FI "WINDOWTITLE eq 3D Print Farm*" >nul 2>&1
    
    echo    All processes stopped.
    timeout /t 3 /nobreak >nul
    echo.
) else if %FRONTEND_RUNNING%==0 (
    echo [2/3] Servers detected. Stopping all processes...
    echo    Closing all terminals and processes...
    
    REM Kill all Python processes
    taskkill /F /IM python.exe /T >nul 2>&1
    
    REM Kill all Node processes
    taskkill /F /IM node.exe /T >nul 2>&1
    
    REM Kill all cmd windows with specific titles
    taskkill /FI "WINDOWTITLE eq BACKEND*" >nul 2>&1
    taskkill /FI "WINDOWTITLE eq FRONTEND*" >nul 2>&1
    taskkill /FI "WINDOWTITLE eq 3D Print Farm*" >nul 2>&1
    
    echo    All processes stopped.
    timeout /t 3 /nobreak >nul
    echo.
) else (
    echo [2/3] No servers running. Starting fresh...
    echo.
)

REM Check if virtual environment exists
if not exist "venv_clean\" (
    echo    Creating virtual environment...
    python -m venv venv_clean
    echo    Virtual environment created.
)

REM Activate virtual environment
call venv_clean\Scripts\activate.bat

REM Install/upgrade dependencies quietly
pip install --upgrade pip -q >nul 2>&1
pip install -r requirements.txt -q >nul 2>&1

REM Initialize database
python -c "from src.database import init_db; init_db()" >nul 2>&1

echo [3/3] Starting servers...
echo.

REM Start Backend Server
echo    Starting Backend Server...
start "BACKEND SERVER [Auto-Restart]" cmd /k "cd /d "%~dp0" && call venv_clean\Scripts\activate.bat && :loop && echo. && echo ======================================== && echo Backend Server - %date% %time% && echo ======================================== && echo. && uvicorn src.main:app --host 0.0.0.0 --port 5051 --reload && echo. && echo [ERROR] Server crashed! Restarting in 5 seconds... && timeout /t 5 /nobreak && goto loop"

REM Wait for backend to initialize
timeout /t 4 /nobreak >nul

REM Start Frontend Server
echo    Starting Frontend Server...
start "FRONTEND SERVER [Auto-Restart]" cmd /k "cd /d "%~dp0frontend" && :loop && echo. && echo ======================================== && echo Frontend Server - %date% %time% && echo ======================================== && echo. && npm start && echo. && echo [ERROR] Server crashed! Restarting in 5 seconds... && timeout /t 5 /nobreak && goto loop"

echo.
echo ========================================
echo SERVERS STARTED SUCCESSFULLY
echo ========================================
echo.
echo Backend:  http://localhost:5051
echo API Docs: http://localhost:5051/docs
echo Frontend: http://localhost:3051
echo.
echo Both servers running with auto-restart!
echo Close terminal windows to stop servers.
echo.
echo Press any key to exit this launcher...
pause >nul
exit
