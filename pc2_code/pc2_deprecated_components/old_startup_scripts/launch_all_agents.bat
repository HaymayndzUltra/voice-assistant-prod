@echo off
echo ===============================================
echo LAUNCHING ALL CORE DISTRIBUTED AGENTS - PC2
echo ===============================================
echo Timestamp: %date% %time%
echo.

echo 1. Checking for existing processes...
tasklist | findstr python > current_processes.txt

echo 2. Preparing to launch agents on required ports...
echo.

:: Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:: Enhanced Router - Port 5555
echo Starting Enhanced Router on port 5555...
start "Enhanced Router" cmd /c "python agents\remote_connector_agent.py --port=5555 > logs\router_5555.log 2>&1"
timeout /t 2 > nul

:: Task Router - Port 5556
echo Starting Task Router on port 5556...
start "Task Router" cmd /c "python agents\remote_connector_agent.py --port=5556 > logs\task_router_5556.log 2>&1"
timeout /t 2 > nul

:: Remote Connector - Port 5557
echo Starting Remote Connector on port 5557...
start "Remote Connector" cmd /c "python agents\remote_connector_agent.py --port=5557 > logs\remote_connector_5557.log 2>&1"
timeout /t 2 > nul

:: Context Memory - Port 5558
echo Starting Context Memory on port 5558...
start "Context Memory" cmd /c "python agents\contextual_memory_agent.py --port=5558 > logs\context_memory_5558.log 2>&1"
timeout /t 2 > nul

:: Memory Agent - Port 5590 (Consolidated)
echo Starting Memory Agent on port 5590...
start "Memory Agent" cmd /c "python agents\memory.py > logs\memory_5590.log 2>&1"
timeout /t 2 > nul
:: NOTE: Jarvis Memory Agent (Port 5559) is DEPRECATED - all functionality consolidated into memory.py

:: Digital Twin - Port 5560
echo Starting Digital Twin on port 5560...
start "Digital Twin" cmd /c "python agents\digital_twin_agent.py --port=5560 > logs\digital_twin_5560.log 2>&1"
timeout /t 2 > nul

:: Learning Mode - Port 5561
echo Starting Learning Mode on port 5561...
start "Learning Mode" cmd /c "python agents\learning_mode_agent.py --port=5561 > logs\learning_mode_5561.log 2>&1"
timeout /t 2 > nul

:: Translator Agent - Port 5562
echo Starting Translator Agent on port 5562...
start "Translator Agent" cmd /c "python agents\translator_agent.py --port=5562 > logs\translator_5562.log 2>&1"
timeout /t 2 > nul

:: Web Scraper - Port 5563
echo Starting Web Scraper on port 5563...
start "Web Scraper" cmd /c "python agents\web_scraper_agent.py --port=5563 > logs\web_scraper_5563.log 2>&1"
timeout /t 2 > nul

:: TinyLlama - Port 5564
echo Starting TinyLlama on port 5564...
start "TinyLlama" cmd /c "python agents\model_manager_agent.py --model=tinyllama --port=5564 > logs\tinyllama_5564.log 2>&1"
timeout /t 2 > nul

echo.
echo All agents launched. Waiting 10 seconds before checking status...
timeout /t 10 > nul

:: Check which agents are running
echo.
echo Checking running agents...
netstat -ano | findstr :5555 :5556 :5557 :5558 :5559 :5560 :5561 :5562 :5563 :5564 > agent_status.txt

echo.
echo Agent status saved to agent_status.txt
echo Logs for each agent available in the logs directory
echo.
echo DISTRIBUTED SYSTEM READY FOR CONNECTION FROM MAIN PC (192.168.1.27)
echo ===============================================

:: Display agent status
type agent_status.txt

echo.
echo Press any key to view the logs directory...
pause > nul
start explorer logs\
