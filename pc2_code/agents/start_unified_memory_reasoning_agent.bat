@echo off
echo Starting Unified Memory and Reasoning Agent for PC2...

:: Set Python path
set PYTHONPATH=%PYTHONPATH%;%~dp0

:: Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:: Start the agent
python unified_memory_reasoning_agent.py

:: If the agent exits, wait before restarting
:restart
echo Agent stopped. Restarting in 5 seconds...
timeout /t 5 /nobreak
goto start 