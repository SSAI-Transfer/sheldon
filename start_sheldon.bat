@echo off
echo ============================================
echo  SHELDON Executive Intelligence System
echo  API Server + Dashboard
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Install from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install flask flask-cors openai pyodbc waitress --quiet 2>nul

REM Check for pyodbc (needed for on-network DB queries)
python -c "import pyodbc; print('  pyodbc: OK')" 2>nul
if errorlevel 1 (
    echo.
    echo  WARNING: pyodbc not installed. Internal DB queries will be unavailable.
    echo  Run: pip install pyodbc
    echo  Also need: ODBC Driver 17 for SQL Server
    echo  https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
    echo.
)

echo.
echo Starting SHELDON API on http://localhost:5000 ...
echo Dashboard: Open SHELDON.html in your browser
echo.
echo Data sources:
echo   Snowflake (Redzone)  - OEE, production, downtime
echo   Sage X3              - Revenue, inventory, AR, cash
echo   CI / AQFDB6          - Quality, safety, warehouse KPIs
echo   MANUFACTURING        - EOP shift notes, attainment
echo   AMMS / AQFAM1        - Supply + repair costs
echo   MANNINGS / AQFDB7    - Retort cycles, deviations, allocations
echo   Donna QA (port 5002) - Preshipment reviews (if running)
echo.
echo Press Ctrl+C to stop
echo ============================================

python "%~dp0sheldon_api.py"

pause
