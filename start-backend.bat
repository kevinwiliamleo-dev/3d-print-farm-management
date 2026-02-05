@echo off
REM ============================================
REM Backend Server Startup Script
REM Python FastAPI Server (Port 5051)
REM ============================================

cd /d "%~dp0"

echo.
echo ============================================
echo    Starting Backend Server (Port 5051)
echo ============================================
echo.

REM Check if virtual environment exists
if not exist "venv_clean\Scripts\activate.bat" (
    echo [!] Virtual environment not found!
    echo [!] Please run: python -m venv venv_clean
    echo [!] Then: venv_clean\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
call venv_clean\Scripts\activate.bat

REM Check if dependencies are installed
python -c "import fastapi" 2>NUL
if !ERRORLEVEL! NEQ 0 (
    echo [!] Dependencies not installed!
    echo [*] Installing dependencies...
    pip install -r requirements.txt
)

echo [*] Starting FastAPI server...
echo.

REM Start the backend server
python -m uvicorn src.main:app --host 0.0.0.0 --port 5051 --reload

pause
