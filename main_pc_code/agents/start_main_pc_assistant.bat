@echo off
REM Start voice assistant on main PC
cd "C:\Users\haymayndz\Desktop\Voice assistant"
call venv\Scripts\activate
python agents\orchestrator.py --distributed --machine-id main_pc
