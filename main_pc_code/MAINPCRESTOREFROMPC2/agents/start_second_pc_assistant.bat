@echo off
REM Change to D: drive first, then navigate to the correct folder
D:
cd \DISKARTE\Voice Assistant
call venv\Scripts\activate
python agents\orchestrator.py --distributed --machine-id second_pc
