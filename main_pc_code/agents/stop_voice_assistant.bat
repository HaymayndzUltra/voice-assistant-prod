@echo off
echo Stopping Voice Assistant services...

:: Activate the Python virtual environment
call "%~dp0venv\Scripts\activate.bat"

:: Run the port manager to kill all processes using the voice assistant ports
python "%~dp0port_manager.py"

:: Also try to find and kill any remaining Python processes related to the voice assistant
echo Stopping any remaining Python processes...
taskkill /F /FI "WINDOWTITLE eq Model Manager*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Remote Connector*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Task Router*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Context Manager*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Face Recognition*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Listener*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Dashboard*" /T 2>nul

echo Voice Assistant services stopped successfully.
