@echo off
echo =========================================
echo   Hotel Room Management System (HRMS)
echo =========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Installing/checking dependencies...
pip install flask pyjwt --quiet

echo.
echo Starting HRMS Backend...
echo Open http://localhost:5000 in your browser
echo.
echo Default Login: admin / admin123
echo.
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0backend"
python server.py

pause
