@echo off
title PC2 Complete Agent Launcher
echo PC2 COMPLETE AGENT LAUNCHER
echo ============================
echo.

REM Check if critical services are already running
echo Checking if critical services are already running...
netstat -ano | findstr ":5563 :5581 :5615" > nul
if %ERRORLEVEL% NEQ 0 (
    echo Critical services not detected. Please run start_critical_services.bat first.
    echo Press any key to continue anyway...
    pause > nul
)

REM Set working directory
cd /d D:\DISKARTE\Voice Assistant

REM Sequence for all remaining agents with dependencies in order
echo.
echo Starting Memory Agent (Base) (Port 5590)...
start "Memory Agent" cmd /k "python agents\memory.py"
timeout /t 10 /nobreak > nul

echo.
echo Starting Contextual Memory Agent (Port 5596)...
start "Contextual Memory Agent" cmd /k "python agents\contextual_memory_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Digital Twin Agent (Port 5597)...
start "Digital Twin Agent" cmd /k "python agents\digital_twin_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Jarvis Memory Agent (Port 5598)...
start "Jarvis Memory Agent" cmd /k "python agents\jarvis_memory_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Error Pattern Memory (Port 5611)...
start "Error Pattern Memory" cmd /k "python agents\error_pattern_memory.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Chain of Thought Agent (Port 5612)...
start "Chain of Thought Agent" cmd /k "python agents\chain_of_thought_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Learning Mode Agent (Port 5599)...
start "Learning Mode Agent" cmd /k "python agents\learning_mode_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Context Summarizer Agent (Port 5610)...
start "Context Summarizer Agent" cmd /k "python agents\context_summarizer_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Web Scraper Agent (Port 5601)...
start "Web Scraper Agent" cmd /k "python agents\web_scraper_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Code Generator Agent (Port 5602)...
start "Code Generator Agent" cmd /k "python agents\code_generator_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Executor Agent (Port 5603)...
start "Executor Agent" cmd /k "python agents\executor_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Progressive Code Generator (Port 5604)...
start "Progressive Code Generator" cmd /k "python agents\progressive_code_generator.py"
timeout /t 5 /nobreak > nul

echo.
echo Starting Model Manager Agent (Port 5605)...
start "Model Manager Agent" cmd /k "python agents\model_manager_agent.py"
timeout /t 5 /nobreak > nul

echo.
echo All PC2 agents have been started in separate windows.
echo DO NOT CLOSE any agent windows or they will terminate!
echo.
echo Press any key to run full health check...
pause >nul

echo Running comprehensive health check...
python pc2_health_check.py --all

echo.
echo PC2 agent startup complete.
echo.
