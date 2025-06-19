@echo off
title PC2 Critical Services Launcher
echo PC2 CRITICAL SERVICES LAUNCHER
echo ==============================
echo.

REM Kill any existing Python processes
echo Stopping any existing Python processes...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM Set working directory
cd /d D:\DISKARTE\Voice Assistant

REM Start critical services in separate windows
echo.
echo Starting NLLB Translation Adapter (Port 5581)...
start "NLLB Translation Adapter" cmd /k "python agents\nllb_translation_adapter.py"
timeout /t 10 /nobreak >nul

echo.
echo Starting TinyLlama Service (Port 5615)...
start "TinyLlama Service" cmd /k "python agents\tinyllama_service_enhanced.py"
timeout /t 10 /nobreak >nul

echo.
echo Starting Quick Translator Fix (Port 5563)...
start "Quick Translator Fix" cmd /k "python quick_translator_fix.py"
timeout /t 5 /nobreak >nul

echo.
echo All critical services have been started in separate windows.
echo DO NOT CLOSE any service windows or they will terminate!
echo.
echo Press any key to run health check...
pause >nul

echo Running health check...
python pc2_health_check.py

echo.
echo PC2 service startup complete.
echo.
