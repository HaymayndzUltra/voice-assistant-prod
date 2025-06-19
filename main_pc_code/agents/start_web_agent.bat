@echo off
set PYTHONPATH=%PYTHONPATH%;%CD%

echo Starting Web Agent...
python -c "from agents.unified_web_agent import UnifiedWebAgent; agent = UnifiedWebAgent(); print('Web Agent started successfully')"

if errorlevel 1 (
    echo Failed to start Web Agent
    exit /b 1
)

echo Web Agent started successfully 