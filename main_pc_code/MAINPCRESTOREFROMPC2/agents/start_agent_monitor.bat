@echo off
echo ===============================================
echo VOICE ASSISTANT AGENT MONITORING SYSTEM
echo ===============================================
echo.

echo Starting Agent Monitor...
python agent_monitor.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to start Agent Monitor!
    echo Please check dependencies and permissions.
    echo.
    pause
    exit /b 1
)
