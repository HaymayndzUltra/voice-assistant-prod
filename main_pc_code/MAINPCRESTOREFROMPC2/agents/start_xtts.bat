@echo off
echo ===============================================
echo   XTTS VOICE AGENT
echo ===============================================
echo.
echo Starting XTTS Text-to-Speech Agent...
echo This agent handles high-quality speech synthesis
echo using XTTS (XTreme Text-To-Speech) model.
echo.
echo Press Ctrl+C to stop.
echo.
echo ===============================================

cd /d %~dp0

:: Run the XTTS agent
python agents/xtts_agent.py

pause
