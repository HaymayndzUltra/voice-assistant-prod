@echo off
set PYTHONPATH=%PYTHONPATH%;%CD%

echo Starting Model Voting System Components...

REM Start the voting manager first
echo Starting Model Voting Manager...
start /B python -c "from agents.model_voting_manager import ModelVotingManager; manager = ModelVotingManager(); print('Model Voting Manager started successfully')"

REM Wait for voting manager to initialize
timeout /t 5 /nobreak

REM Start the voting adapter
echo Starting Model Voting Adapter...
start /B python -c "from agents.model_voting_adapter import ModelVotingAdapter; adapter = ModelVotingAdapter(); print('Model Voting Adapter started successfully')"

REM Wait for adapter to initialize
timeout /t 5 /nobreak

echo Model Voting System started successfully
echo.
echo Components running:
echo - Model Voting Manager (Port 5620)
echo - Model Voting Adapter (Port 5621)
echo.
echo Press Ctrl+C to stop all components 