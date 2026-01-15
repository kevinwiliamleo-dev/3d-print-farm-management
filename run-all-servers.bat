@echo off
REM ============================================
REM Start All Servers with Auto-Restart
REM Simple & Reliable
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

cls
echo.
echo ============================================
echo   3D PRINT FARM - SERVER MANAGER
echo ============================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Servers will auto-restart if they crash!
echo.
echo ============================================
echo.

REM Open first window - Backend
echo Opening Backend Server...
start "BACKEND SERVER [Auto-Restart]" cmd /k "%~dp0\start-backend.bat"

REM Wait a bit before opening frontend
timeout /t 3 /nobreak

REM Open second window - Frontend
echo Opening Frontend Server...
start "FRONTEND SERVER [Auto-Restart]" cmd /k "%~dp0\start-frontend.bat"

echo.
echo Both servers started in separate windows!
echo All windows will auto-restart servers on crash.
echo.
pause
