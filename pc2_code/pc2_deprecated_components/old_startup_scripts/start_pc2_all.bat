@echo off
echo Starting PC2 Voice Assistant Services...
echo.
echo This will start:
echo  - NLLB Translation Adapter
echo  - TinyLlama Service
echo  - Translator Agent
echo.
echo Services will be started in separate windows to ensure they remain running.
echo.

:: Start each service in a separate window
start "NLLB Translation Adapter" cmd /k python agents/nllb_translation_adapter.py

:: Wait for NLLB adapter to initialize (it's a dependency for other services)
echo Waiting for NLLB adapter to initialize (15 seconds)...
timeout /t 15

:: Start TinyLlama Service
start "TinyLlama Service" cmd /k python agents/tinyllama_service_enhanced.py

:: Wait for TinyLlama to initialize
echo Waiting for TinyLlama to initialize (5 seconds)...
timeout /t 5

:: Start Translator Agent
start "Translator Agent" cmd /k python agents/translator_fixed.py

:: Run health check
echo.
echo Running health check after 10 seconds...
timeout /t 10
python pc2_health_check.py

echo.
echo All services have been started in separate windows.
echo DO NOT close these windows or the services will stop.
pause
