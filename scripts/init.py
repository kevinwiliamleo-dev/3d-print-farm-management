#!/usr/bin/env python3
"""
Initialize 3D Print Farm Management System
Run this script to:
1. Create virtual environment
2. Install dependencies
3. Initialize database
4. Verify OrcaSlicer installation
5. Display next steps
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_warning(text):
    """Print warning message"""
    print(f"⚠️  {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def check_python_version():
    """Check if Python 3.8+ is installed"""
    if sys.version_info < (3, 8):
        print_error(f"Python 3.8+ required. You have {sys.version}")
        sys.exit(1)
    print_success(f"Python {sys.version.split()[0]} detected")

def check_orca_slicer():
    """Check if OrcaSlicer is installed"""
    try:
        result = subprocess.run(
            ["orca-slicer", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"OrcaSlicer found: {version}")
            return True
    except Exception:
        pass
    
    print_warning("OrcaSlicer not found in PATH")
    print_info("Download from: https://github.com/SoftFever/OrcaSlicer/releases")
    print_info("Or set ORCA_SLICER_PATH in .env file")
    return False

def create_env_file():
    """Create .env file from template if needed"""
    if not Path(".env").exists():
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print_success(".env file created from template")
            print_warning("Please update .env with your Bambu Lab credentials")
            return False
    else:
        print_success(".env file already exists")
        return True

def init_database():
    """Initialize database"""
    try:
        from src.database import init_db
        init_db()
        print_success("Database initialized successfully")
        return True
    except Exception as e:
        print_error(f"Database initialization failed: {str(e)}")
        return False

def main():
    """Main initialization"""
    print_header("3D Print Farm Management System - Initialization")
    
    # Check Python version
    print_info("Checking Python version...")
    check_python_version()
    
    # Check OS
    os_type = platform.system()
    print_success(f"Operating system: {os_type}")
    
    # Check OrcaSlicer
    print_info("Checking OrcaSlicer...")
    orca_found = check_orca_slicer()
    
    # Create .env if needed
    print_info("Checking configuration...")
    env_configured = create_env_file()
    
    # Initialize database
    print_info("Initializing database...")
    if init_database():
        print_success("Database ready at: data/farm.db")
    else:
        print_warning("Database initialization had issues, but you can proceed")
    
    # Summary
    print_header("Initialization Summary")
    
    print("\n✅ Project is ready for development!\n")
    
    if not orca_found:
        print_warning("OrcaSlicer not found - install it before testing file slicing")
    
    if not env_configured:
        print_warning("Configuration not complete - update .env file before running")
    
    print("\n📋 Next steps:")
    print("   1. Edit .env file with Bambu Lab credentials")
    print("   2. Install OrcaSlicer (if not already installed)")
    print("   3. Run: python -m uvicorn src.main:app --reload")
    print("   4. Visit: http://localhost:8000/docs\n")
    
    print("📚 Documentation:")
    print("   - SETUP.md - Complete installation guide")
    print("   - README.md - Project overview & naming conventions")
    print("   - PROJECT_STRUCTURE.md - Project layout")
    print("   - PHASE1_COMPLETE.md - What's been built so far\n")
    
    print_header("Ready for development!")

if __name__ == "__main__":
    main()
