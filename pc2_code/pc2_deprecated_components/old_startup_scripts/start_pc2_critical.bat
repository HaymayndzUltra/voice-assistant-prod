@echo off
title PC2 Critical Services Launcher
echo PC2 CRITICAL SERVICES LAUNCHER
echo =============================
echo.

REM Stop any existing Python processes
echo Stopping any existing Python processes...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

REM Directory for the services
set SERVICE_DIR=d:\DISKARTE\Voice Assistant

REM Start services in separate windows

echo Starting NLLB Translation Adapter (Port 5581)...
start "NLLB Translation Adapter" cmd /k "cd /d %SERVICE_DIR% && python agents/nllb_translation_adapter.py"
timeout /t 5 /nobreak >nul

echo Starting TinyLlama Service (Port 5615)...
start "TinyLlama Service" cmd /k "cd /d %SERVICE_DIR% && python agents/tinyllama_service_enhanced.py"
timeout /t 5 /nobreak >nul

echo Starting Quick Translator Service (Port 5563)...
start "Quick Translator Service" cmd /k "cd /d %SERVICE_DIR% && python quick_translator_fix.py"
timeout /t 5 /nobreak >nul

echo.
echo All critical PC2 services have been started.
echo DO NOT CLOSE any service windows or they will terminate!
echo.
echo Press any key to run health check...
pause >nul

echo Running health check...
cd /d %SERVICE_DIR%
python pc2_health_check.py

echo.
echo PC2 service startup complete. Service windows should remain open.
echo.
