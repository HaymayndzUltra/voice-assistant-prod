@echo off
echo Setting up Python environment on Second PC...

REM Set the IP address of your second PC
set SECOND_PC=192.168.1.2
set SECOND_PC_PATH=\\%SECOND_PC%\D$\DISKARTE\Voice Assistant

REM Check if second PC is reachable
ping -n 1 %SECOND_PC% >nul
if errorlevel 1 (
    echo Cannot reach Second PC at %SECOND_PC%
    echo Please make sure it's turned on and connected to the network.
    pause
    exit /b
)

REM Copy requirements.txt to second PC
echo Copying requirements.txt to Second PC...
copy "requirements.txt" "%SECOND_PC_PATH%\requirements.txt" /Y

REM Create setup.py script
echo Creating setup script on Second PC...
echo import os > "%SECOND_PC_PATH%\setup.py"
echo import subprocess >> "%SECOND_PC_PATH%\setup.py"
echo print("Setting up Python environment...") >> "%SECOND_PC_PATH%\setup.py"
echo venv_path = os.path.join(os.getcwd(), "venv") >> "%SECOND_PC_PATH%\setup.py"
echo if not os.path.exists(venv_path): >> "%SECOND_PC_PATH%\setup.py"
echo     print("Creating virtual environment...") >> "%SECOND_PC_PATH%\setup.py"
echo     subprocess.run(["python", "-m", "venv", "venv"]) >> "%SECOND_PC_PATH%\setup.py"
echo activate_script = os.path.join(venv_path, "Scripts", "activate.bat") >> "%SECOND_PC_PATH%\setup.py"
echo print("Installing required packages...") >> "%SECOND_PC_PATH%\setup.py"
echo subprocess.run(["cmd", "/c", f"{activate_script} && pip install -r requirements.txt"]) >> "%SECOND_PC_PATH%\setup.py"
echo print("Installing additional packages...") >> "%SECOND_PC_PATH%\setup.py"
echo subprocess.run(["cmd", "/c", f"{activate_script} && pip install pyzmq torch torchvision torchaudio psutil"]) >> "%SECOND_PC_PATH%\setup.py"
echo print("Setup complete!") >> "%SECOND_PC_PATH%\setup.py"

REM Create batch file to run setup.py
echo @echo off > "%SECOND_PC_PATH%\run_setup.bat"
echo python setup.py >> "%SECOND_PC_PATH%\run_setup.bat"
echo pause >> "%SECOND_PC_PATH%\run_setup.bat"

echo Setup files created on Second PC.
echo.
echo Please go to your Second PC and run:
echo D:\DISKARTE\Voice Assistant\run_setup.bat
echo.
echo After setup is complete, you can run:
echo D:\DISKARTE\Voice Assistant\venv\Scripts\activate
echo python agents\orchestrator.py --distributed --machine-id second_pc
echo.
pause
