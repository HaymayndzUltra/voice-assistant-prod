@echo off
set PYTHONPATH=%PYTHONPATH%;%CD%

echo Starting Model Voting Adapter...
python -c "from agents.model_voting_adapter import ModelVotingAdapter; adapter = ModelVotingAdapter(); print('Model Voting Adapter started successfully')"

if errorlevel 1 (
    echo Failed to start Model Voting Adapter
    exit /b 1
)

echo Model Voting Adapter started successfully 