@echo off
title Opus Local - AI YouTube to Shorts Generator
echo ===================================================
echo     Opus Local: 100%% Local AI Shorts Generator
echo          (Zero API Keys - 100%% Offline AI)
echo ===================================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10 or 3.11 from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

:: Check for FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] FFmpeg was not detected in your PATH.
    echo FFmpeg is required for video rendering.
    echo If you encounter rendering errors, please install FFmpeg (e.g. winget install Gyan.FFmpeg or download from ffmpeg.org).
    echo.
)

:: Check if virtual environment exists
if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

echo [2/3] Activating virtual environment and checking dependencies...
call venv\Scripts\activate.bat

pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

echo.
echo [3/3] Starting Opus Local Server...
echo Opening browser at http://localhost:5000 ...
start http://localhost:5000

python app.py

pause
