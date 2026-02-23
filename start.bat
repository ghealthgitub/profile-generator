@echo off
REM 🫚 GINGER UNIVERSE - Quick Start Script (Windows)

echo ========================================
echo 🫚 GINGER UNIVERSE
echo Doctor Profile Generator
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo 📥 Installing dependencies...
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo.
echo ✅ Setup complete!
echo.
echo ========================================
echo 🚀 Starting Ginger Universe...
echo ========================================
echo.
echo 🌐 Access the application at:
echo    http://localhost:5000
echo.
echo 🔑 Default login:
echo    Username: admin@ginger.healthcare
echo    Password: GingerUniverse2026!
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Run the application
python app.py

pause
