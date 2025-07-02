@echo off
echo ===============================================
echo   START TAGALOG ANALYZER SERVICE
echo ===============================================
echo.
echo This script will start the TagalogAnalyzer service on port 6010
echo.
echo Press Ctrl+C to stop the service when done.
echo.
echo ===============================================

cd /d %~dp0

:: Start the service
python human_awareness_agent\run_tagalog_analyzer.py
