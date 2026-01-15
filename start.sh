#!/bin/bash
# Startup script for 3D Print Farm Management System on Linux/macOS

echo ""
echo "========================================"
echo "3D Print Farm Management System"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check OrcaSlicer installation
echo ""
echo "Checking OrcaSlicer installation..."
if command -v orca-slicer &> /dev/null; then
    orca-slicer --version
else
    echo "WARNING: OrcaSlicer not found in PATH"
    echo "Please install OrcaSlicer from: https://github.com/SoftFever/OrcaSlicer/releases"
    echo "Or set ORCA_SLICER_PATH in .env file"
fi

# Check environment file
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "NOTE: Please update .env with your Bambu Lab credentials"
fi

# Initialize database
echo ""
echo "Initializing database..."
python -c "from src.database import init_db; init_db()"

# Start server
echo ""
echo "========================================"
echo "Starting FastAPI server..."
echo "========================================"
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""

python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
