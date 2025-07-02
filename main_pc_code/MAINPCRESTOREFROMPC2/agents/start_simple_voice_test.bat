@echo off
echo ===============================================
echo   SIMPLE VOICE ASSISTANT TEST
echo ===============================================
echo.
echo This script will start XTTS with tetey1.wav voice
echo and the Voice Pipeline test.
echo.
echo Press Ctrl+C to stop if needed.
echo.
echo ===============================================

cd /d %~dp0

:: Kill any running Python processes first
echo Stopping any running Python processes...
taskkill /F /IM python.exe

:: Wait for processes to terminate
timeout /t 2 /nobreak

:: Prepare tetey1.wav voice for XTTS
echo Setting up custom voice (tetey1.wav)...
if exist "%~dp0tetey1.wav" (
    if not exist "%~dp0agents\voice_samples" mkdir "%~dp0agents\voice_samples"
    copy /Y "%~dp0tetey1.wav" "%~dp0agents\voice_samples\filipino_sample.wav" >nul
    echo Custom voice sample ready.
) else (
    echo Custom voice sample (tetey1.wav) not found. Using default voice.
)

:: Start the XTTS agent with tetey1 voice
echo Starting XTTS Voice Service (tetey1.wav)...
set XTTS_USE_FILIPINO=1
start "XTTS Voice Service" cmd /k "cd /d "%~dp0" && python agents\xtts_agent.py --use_filipino"

:: Wait for XTTS to initialize
timeout 5 /nobreak

:: Run the voice test
echo Starting Voice Pipeline Test...
start "Voice Pipeline Test" cmd /k "cd /d "%~dp0" && python quick_voice_test.py"

echo.
echo Voice Assistant test components are now running.
echo 1. XTTS with tetey1.wav voice is active
echo 2. Voice Pipeline Test is running
echo.
echo You can speak to test the voice recognition and response.
echo.
echo Press Ctrl+C in each console window to stop when done.
