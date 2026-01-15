@echo off
REM ============================================
REM Advanced Server Manager with Logging
REM Auto-restart + Logging to file
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Create logs directory if not exists
if not exist "logs" mkdir logs

set LOG_DIR=logs
set BACKEND_LOG=%LOG_DIR%\backend.log
set FRONTEND_LOG=%LOG_DIR%\frontend.log
set MASTER_LOG=%LOG_DIR%\master.log

echo.
echo ============================================
echo    3D Print Farm Management System
echo    Advanced Server Manager
echo ============================================
echo.

REM Log to master log
(
    echo [%date% %time%] Starting Master Control
    echo Backend Log: %BACKEND_LOG%
    echo Frontend Log: %FRONTEND_LOG%
) >> %MASTER_LOG%

echo [1] Starting Backend Server...
echo [%date% %time%] Backend server starting...>> %BACKEND_LOG%
start "Backend Server [Auto-Restart]" cmd /k ^
    "cd /d %CD% && call venv_clean\Scripts\activate.bat && (for /l %%%%X in (1,0,2) do (echo [%%%%date%%%% %%%%time%%%%] Starting backend... && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload && echo [%%%%date%%%% %%%%time%%%%] Server crashed, restarting in 5s && timeout /t 5)) >> %BACKEND_LOG% 2>&1"

timeout /t 2 /nobreak

echo [2] Starting Frontend Server...
echo [%date% %time%] Frontend server starting...>> %FRONTEND_LOG%
start "Frontend Server [Auto-Restart]" cmd /k ^
    "cd /d %CD%\frontend && (for /l %%%%X in (1,0,2) do (echo [%%%%date%%%% %%%%time%%%%] Starting frontend... && npm start && echo [%%%%date%%%% %%%%time%%%%] Server crashed, restarting in 5s && timeout /t 5)) >> %FRONTEND_LOG% 2>&1"

timeout /t 2 /nobreak

echo.
echo ============================================
echo    ✅ Both servers starting!
echo.
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo    Frontend: http://localhost:3000
echo.
echo    Logs:
echo    - Backend:  %BACKEND_LOG%
echo    - Frontend: %FRONTEND_LOG%
echo    - Master:   %MASTER_LOG%
echo.
echo    Servers auto-restart on crash!
echo ============================================
echo.

pause
