@echo off
echo Stopping all Ollama processes...
taskkill /f /im ollama.exe
taskkill /f /im "ollama app.exe"

echo Creating Ollama config directory...
mkdir "%USERPROFILE%\.ollama" 2>nul

echo Writing network configuration...
echo {"listen": "0.0.0.0:11434"} > "%USERPROFILE%\.ollama\config.json"

echo Starting Ollama with network access...
start "" "C:\Users\63956\AppData\Local\Programs\Ollama\ollama.exe" serve

echo Waiting for Ollama to start...
timeout /t 5

echo Testing Ollama network binding...
netstat -ano | findstr :11434

echo IMPORTANT: If you see 0.0.0.0:11434 in the output above, Ollama is properly configured for network access.
echo If you only see 127.0.0.1:11434, then your Ollama version may not support the network binding option.

echo.
echo Run this batch file with administrator privileges if it didn't work.
