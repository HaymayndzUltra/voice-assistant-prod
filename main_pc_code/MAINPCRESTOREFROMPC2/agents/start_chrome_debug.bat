@echo off
echo Starting Chrome with Remote Debugging enabled...

REM Close any existing Chrome instances
taskkill /F /IM chrome.exe /T
timeout /t 1

REM Start Chrome with remote debugging on port 9222
start chrome.exe --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\AppData\Local\Google\Chrome\User Data" https://aistudio.google.com/

echo Chrome started with remote debugging on port 9222
echo You can now run the AI Studio Assistant script
echo Note: Do not close this window until you're done testing!
