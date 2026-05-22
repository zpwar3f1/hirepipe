@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  HirePipe - one-click demo
echo ============================================================

where python >nul 2>nul
if errorlevel 1 (
    echo Python is not installed or not on PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist .venv (
    echo Creating virtual environment in .venv ...
    python -m venv .venv
    if errorlevel 1 ( pause & exit /b 1 )
)

call ".venv\Scripts\activate.bat"

echo.
echo Installing dependencies ...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo.
echo Generating mock applications ...
python scripts\seed_applications.py

echo.
echo ============================================================
echo  Running HirePipe (5 applicants across all 4 scenarios)
echo ============================================================
python scripts\run_pipeline.py

echo.
echo ============================================================
echo  Done. Per-applicant artifacts in data\output\
echo ============================================================
pause
