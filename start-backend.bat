@echo off
REM ============================================
REM Backend Server Auto-Restart Batch File
REM Automatically restarts server if it crashes
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

:start_backend
echo.
echo ========================================
echo Starting Backend Server at %date% %time%
echo ========================================
echo.

REM Activate virtual environment
call venv_clean\Scripts\activate.bat

REM Start uvicorn server
uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload

REM If we get here, server crashed - restart it
echo.
echo [ERROR] Backend server crashed at %date% %time%
echo [INFO] Restarting in 5 seconds...
echo.
timeout /t 5 /nobreak

goto start_backend

:end
pause
