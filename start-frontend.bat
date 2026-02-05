@echo off
setlocal enabledelayedexpansion
REM ============================================
REM Frontend Server Startup Script
REM React Development Server (Port 3051)
REM ============================================

cd /d "%~dp0\frontend"

echo.
echo ============================================
echo    Starting Frontend Server (Port 3051)
echo ============================================
echo.

REM Check if node_modules exists
if not exist "node_modules" (
    echo [!] Dependencies not installed!
    echo [*] Installing dependencies...
    call npm install
)

echo [*] Starting React development server...
echo.

REM Start the frontend server
npm start

pause
