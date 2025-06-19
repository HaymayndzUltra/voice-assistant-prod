@echo off
echo === Translation Adapter Setup for PC2 ===
echo.

:: Advanced checks for Ollama service
echo [1/4] Checking Ollama service status...

:: Use timeout to prevent hanging
powershell -Command "$startTime = Get-Date; try { $response = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -Method GET -TimeoutSec 5 -ErrorAction Stop; if ($response.StatusCode -eq 200) { Write-Host '[SUCCESS] Ollama API is responding' } } catch { Write-Host '[ERROR] ' $_.Exception.Message; exit 1 }" > nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] Ollama service is not responding. Attempting to restart...
    taskkill /F /IM ollama.exe /T 2>nul
    timeout /t 2 /nobreak > nul
    start "" "C:\Users\63956\AppData\Local\Programs\Ollama\ollama.exe"
    echo Waiting for Ollama to initialize (15 seconds)...
    timeout /t 15 /nobreak > nul
    
    :: Check again after restart
    powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -Method GET -TimeoutSec 5; if ($response.StatusCode -eq 200) { Write-Host '[SUCCESS] Ollama successfully restarted' } else { exit 1 } } catch { exit 1 }" > nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to restart Ollama service.
        echo Please start Ollama manually by running:
        echo     ollama serve
        echo.
        goto :error
    )
) else (
    echo [SUCCESS] Ollama service is running
)

:: Check if phi model is available
echo Checking if phi model is available...
curl -s http://localhost:11434/api/tags | findstr "phi" > nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] The phi model might not be available in Ollama.
    echo If the adapter fails, please pull the model by opening a separate command prompt and typing:
    echo     ollama pull phi
    echo.
)

echo [SUCCESS] Ollama is running and accessible!
echo.

:: Start the translation adapter
echo Starting the translation adapter...
echo Using phi:latest model from Ollama on port 5581
cd %~dp0agents
python llm_translation_adapter.py --model=phi --port=5581 --log-level=DEBUG
if %errorlevel% neq 0 goto :error
goto :end

:error
echo.
echo [ERROR] Failed to start the translation adapter.
echo Please check the logs above for more information.
echo.

:end
pause
