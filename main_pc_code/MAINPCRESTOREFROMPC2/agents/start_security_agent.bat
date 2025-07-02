@echo off
echo ===============================================
echo   START SECURITY AGENT
echo ===============================================
echo.
echo This script will start the Security/Audit Agent on port 6020
echo.
echo Press Ctrl+C to stop the service when done.
echo.
echo ===============================================

cd /d %~dp0

:: Start the service
python human_awareness_agent\security_agent.py
