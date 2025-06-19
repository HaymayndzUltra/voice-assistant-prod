@echo off
echo Starting Voice Assistant Agents for Second PC...

:: Set the working directory
cd /d "C:\Users\haymayndz\Desktop\Voice assistant"

:: Activate virtual environment
call venv\Scripts\activate

:: Start the distributed launcher
python distributed_launcher.py --machine second_pc --launch

:: Keep the window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo An error occurred while starting agents.
    pause
)
