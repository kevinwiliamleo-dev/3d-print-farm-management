#!/usr/bin/env python
"""
Simplified dependency installer for 3D Print Farm Management System
Uses Anaconda python.exe directly with pip module
"""
import subprocess
import sys

def install_packages():
    packages = [
        # Core Framework
        'fastapi==0.104.1',
        'uvicorn==0.24.0',
        'pydantic==2.5.0',
        'python-multipart==0.0.6',
        
        # Database
        'sqlalchemy==2.0.23',
        'alembic==1.12.1',
        
        # Environment & Utilities
        'python-dotenv==1.0.0',
        'aiofiles==23.2.1',
        
        # Bambu Lab Integration
        'requests==2.31.0',
        'paho-mqtt==1.6.1',
        'aiohttp==3.9.1',
        
        # Logging
        'python-json-logger==2.0.7',
        
        # Testing & Code Quality (optional)
        'pytest==7.4.3',
        'black==23.12.0',
        'flake8==6.1.0',
    ]
    
    for package in packages:
        print(f"\n✓ Installing {package}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', package])
        except subprocess.CalledProcessError as e:
            print(f"⚠ Warning: Failed to install {package}, continuing...")
    
    print("\n✓ Installation complete!")

if __name__ == '__main__':
    install_packages()
