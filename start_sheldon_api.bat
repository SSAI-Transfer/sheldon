@echo off
echo ============================================
echo SHELDON API Server Startup
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install requirements if needed
echo Checking dependencies...
pip install flask flask-cors --quiet

echo.
echo Starting SHELDON API Server on http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

python "%~dp0sheldon_api.py"

pause
