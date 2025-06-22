@echo off
echo Starting Unified Memory and Reasoning Agent...

:: Activate Python environment if needed
:: call venv\Scripts\activate

:: Start the agent
python agents/unified_memory_reasoning_agent.py

:: Keep the window open if there's an error
if errorlevel 1 (
    echo Error starting Unified Memory and Reasoning Agent
    pause
) 