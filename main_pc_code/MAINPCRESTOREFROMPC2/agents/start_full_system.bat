@echo off
echo ===============================================
echo   VOICE ASSISTANT COMPLETE SYSTEM
echo ===============================================
echo.

REM Kill running Python processes
echo Stopping any running processes...
taskkill /F /IM python.exe 2>nul
ping 127.0.0.1 -n 3 >nul

REM Set up voice
echo Setting up tetey1.wav voice...
if exist tetey1.wav (
  if not exist agents\voice_samples mkdir agents\voice_samples
  copy /Y tetey1.wav agents\voice_samples\filipino_sample.wav >nul
  echo Voice sample configured.
)

REM Create logs directory
if not exist logs mkdir logs

REM Start XTTS with tetey voice
echo Step 1: Starting XTTS Voice Service...
set XTTS_USE_FILIPINO=1
start "XTTS Voice" cmd /c "python agents\xtts_agent.py --use_filipino"
ping 127.0.0.1 -n 3 >nul

REM Start Media Pose Detection
echo Step 2: Starting Media Pose Detection...
start "Media Pose" cmd /c "python human_awareness_agent\media_pose_detector.py"
ping 127.0.0.1 -n 3 >nul

REM Start TagaBERTa Analyzer
echo Step 3: Starting Tagalog Analyzer...
start "Tagalog Analyzer" cmd /c "python human_awareness_agent\tagalog_analyzer.py"
ping 127.0.0.1 -n 3 >nul

REM Start Wake Word Detection
echo Step 4: Starting Wake Word Detection...
start "Wake Word" cmd /c "python modular_system\wake_word_system\highmindswakeword.py"
ping 127.0.0.1 -n 3 >nul

REM Start Voice Pipeline Test
echo Step 5: Starting Voice Recognition...
start "Voice Recognition" cmd /c "python quick_voice_test.py"

echo.
echo ===============================================
echo VOICE ASSISTANT SYSTEM STARTED!
echo ===============================================
echo.
echo Active Components:
echo  - XTTS with tetey1.wav voice
echo  - Media Pose Detection
echo  - Tagalog Analyzer with TagaBERTa
echo  - Wake Word Detection
echo  - Voice Recognition
echo.
echo To stop all components: taskkill /F /IM python.exe
echo ===============================================
