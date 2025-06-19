@echo off
echo Setting up Voice Assistant for auto-start on boot for Second PC...

:: Set the working directory
cd /d "C:\Users\haymayndz\Desktop\Voice assistant"

:: Activate virtual environment
call venv\Scripts\activate

:: Run the distributed launcher with setup flag
python distributed_launcher.py --machine second_pc --setup

echo.
echo Setup complete! Voice Assistant will now start automatically when you log in.
echo You can also manually start it by running start_second_pc_agents.bat
echo.
pause
