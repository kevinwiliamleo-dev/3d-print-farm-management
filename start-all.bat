@echo off
REM ============================================
REM Master Control - Start Both Servers
REM Opens both backend & frontend in new windows
REM ============================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================
echo    3D Print Farm Management System
echo    Starting Both Servers...
echo ============================================
echo.
echo [1] Starting Backend Server...
start "Backend Server" cmd /k call start-backend.bat

timeout /t 2 /nobreak

echo [2] Starting Frontend Server...
start "Frontend Server" cmd /k call start-frontend.bat

timeout /t 2 /nobreak

echo.
echo ============================================
echo    ✅ Both servers starting!
echo.
echo    Backend:  http://localhost:5000
echo    Frontend: http://localhost:3000
echo.
echo    (Servers will auto-restart if they crash)
echo ============================================
echo.

pause
