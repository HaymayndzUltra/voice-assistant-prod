@echo off
echo ===============================================
echo   VOICE ASSISTANT SYSTEM STARTUP
echo ===============================================
echo.

:: Create logs directory if it doesn't exist
if not exist "%~dp0logs" mkdir "%~dp0logs"

:: Kill any existing Python processes (optional, commented out by default)
:: echo Stopping any running Python processes...
:: taskkill /F /IM python.exe > nul 2>&1

:: Activate the Python virtual environment if it exists
if exist "%~dp0venv\Scripts\activate.bat" (
    echo Activating Python virtual environment...
    call "%~dp0venv\Scripts\activate.bat"
)

:: Free up ports used by previous instances
echo Freeing up ports used by previous instances...
python "%~dp0port_manager.py" > "%~dp0logs\port_manager.log" 2>&1

:: Prepare tetey1.wav voice for XTTS
echo Setting up custom voice (tetey1.wav)...
if exist "%~dp0tetey1.wav" (
    if not exist "%~dp0agents\voice_samples" mkdir "%~dp0agents\voice_samples"
    copy /Y "%~dp0tetey1.wav" "%~dp0agents\voice_samples\filipino_sample.wav" >nul 2>nul
    echo Custom voice sample ready.
) else (
    echo Custom voice sample (tetey1.wav) not found. Using default voice.
)

:: Connect AI models
echo Step 1: Ensuring all AI models are connected and running...
python "%~dp0auto_connect_models.py" > "%~dp0logs\auto_connect.log" 2>&1

:: Wait a moment for the models to initialize
timeout /t 2 /nobreak

:: Start the XTTS agent with tetey1 voice
echo Step 2: Starting XTTS Voice Service (tetey1.wav)...
set XTTS_USE_FILIPINO=1
start "XTTS Voice Service" cmd /k "cd /d "%~dp0" && python agents\xtts_agent.py --use_filipino"

:: Start the Media Pose Detector
echo Step 3: Starting Media Pose Detection...
start "Media Pose Detector" cmd /k "cd /d "%~dp0" && python human_awareness_agent\media_pose_detector.py"

:: Start the Remote Connector agent
echo Step 4: Starting Remote Connector agent...
start "Remote Connector" cmd /k "cd /d "%~dp0" && python agents\remote_connector_agent.py"

:: Start the Task Router agent
echo Step 5: Starting Task Router agent...
start "Task Router" cmd /k "cd /d "%~dp0" && python agents\task_router_agent.py"

:: Start the Context Manager agent
echo Step 6: Starting Context Manager agent...
start "Context Manager" cmd /k "cd /d "%~dp0" && python agents\context_manager.py"

:: Start the Face Recognition agent
echo Step 7: Starting Face Recognition agent...
start "Face Recognition" cmd /k "cd /d "%~dp0" && python agents\face_recognition_agent.py"

:: Start the Listener agent
echo Step 8: Starting Listener agent...
start "Listener" cmd /k "cd /d "%~dp0" && python agents\listener.py"

:: Start the Dashboard
echo Step 9: Starting Dashboard...
start "Dashboard" cmd /k "cd /d "%~dp0" && python dashboard\dashboard.py"

:: Wait for the Dashboard to initialize
timeout /t 3 /nobreak

:: Open the Dashboard in the default browser
start http://localhost:8080

echo.
echo Voice Assistant System started successfully!
echo.
echo Components running:
echo - XTTS with tetey1.wav voice
echo - Media Pose Detection
echo - Remote Connector
echo - Task Router
echo - Context Manager
echo - Face Recognition
echo - Listener
echo - Dashboard
echo.
echo Dashboard available at: http://localhost:8080
echo.
echo Press Ctrl+C in each console window to stop individual services when done.
echo To stop all services at once, run kill_python.bat
