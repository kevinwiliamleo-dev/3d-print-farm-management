@echo off
REM ============================================
REM Frontend Server Auto-Restart Batch File
REM Automatically restarts server if it crashes
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

:start_frontend
echo.
echo ========================================
echo Starting Frontend Server at %date% %time%
echo ========================================
echo.

cd frontend

REM Start npm development server
call npm start

REM If we get here, server crashed - restart it
echo.
echo [ERROR] Frontend server crashed at %date% %time%
echo [INFO] Restarting in 5 seconds...
echo.
timeout /t 5 /nobreak

cd ..
goto start_frontend

:end
pause
