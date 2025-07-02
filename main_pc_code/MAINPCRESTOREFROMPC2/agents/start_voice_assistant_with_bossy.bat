@echo off
echo ===============================================
echo   VOICE ASSISTANT WITH BOSSY TAGALOG ANALYZER
echo ===============================================
echo.
echo Starting Bossy Tagalog Analyzer Server...
start cmd /k "cd /d %~dp0 && python human_awareness_agent/run_bossy_server.py"
echo.
echo Waiting for Bossy Tagalog Analyzer to initialize...
timeout /t 3 /nobreak > nul
echo.
echo Starting main Voice Assistant...
echo.
echo Voice Assistant is now running with Bossy Tagalog Analyzer support!
echo Press Ctrl+C in each window to stop the services when done.
echo.
echo ===============================================

cd /d %~dp0
python modular_system/core_agents/orchestrator.py
