@echo off
echo Starting Chain of Thought Agent...

:: Activate Python environment if needed
:: call venv\Scripts\activate

:: Start the agent
python agents/chain_of_thought_agent.py

:: Keep the window open if there's an error
if errorlevel 1 (
    echo Error starting Chain of Thought Agent
    pause
) 