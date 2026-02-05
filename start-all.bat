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

REM Kill existing Backend Server windows
echo [0] Closing existing server windows...
tasklist /FI "WindowTitle eq Backend Server*" /FO CSV 2>NUL | find /I "cmd.exe" >NUL
if !ERRORLEVEL! EQU 0 (
    echo    - Closing Backend Server window...
    taskkill /FI "WindowTitle eq Backend Server*" /F >NUL 2>&1
)

REM Kill existing Frontend Server windows
tasklist /FI "WindowTitle eq Frontend Server*" /FO CSV 2>NUL | find /I "cmd.exe" >NUL
if !ERRORLEVEL! EQU 0 (
    echo    - Closing Frontend Server window...
    taskkill /FI "WindowTitle eq Frontend Server*" /F >NUL 2>&1
)

REM Kill Python and Node processes
echo    - Stopping Python processes...
taskkill /F /IM python.exe >NUL 2>&1
echo    - Stopping Node processes...
taskkill /F /IM node.exe >NUL 2>&1

timeout /t 1 /nobreak >NUL

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
echo    Backend:  http://localhost:5051
echo    Frontend: http://localhost:3051
echo.
echo    (Servers will auto-restart if they crash)
echo ============================================
echo.

pause
