@echo off
echo Starting Unified Web Agent Tests...

REM Set Python path
set PYTHONPATH=%PYTHONPATH%;%CD%

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Start the agent in a new window
start "Unified Web Agent" cmd /c "python unified_web_agent.py"

REM Wait for agent to start
timeout /t 5 /nobreak

REM Run tests
echo Running tests...
python test_unified_web_agent.py

REM Wait for tests to complete
timeout /t 2 /nobreak

REM Kill the agent process
taskkill /FI "WINDOWTITLE eq Unified Web Agent" /F

echo Tests completed. 