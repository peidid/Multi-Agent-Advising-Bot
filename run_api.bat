@echo off
REM Run the Multi-Agent Advising API on Windows

echo ============================================================
echo Starting Multi-Agent Academic Advising API
echo ============================================================

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found. Using system Python.
)

REM Check for .env
if not exist ".env" (
    echo WARNING: No .env file found!
    echo Copy .env.example to .env and configure it.
    echo.
)

REM Run the API
python run_api.py --reload

pause
