@echo off
echo Starting Unified Web Agent...

REM Set Python path
set PYTHONPATH=%PYTHONPATH%;%CD%

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

:start
echo Starting agent...
python unified_web_agent.py

REM If agent exits, wait 5 seconds and restart
timeout /t 5 /nobreak
goto start 