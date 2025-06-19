@echo off
echo ===============================================
echo LAUNCHING ALL CORE DISTRIBUTED AGENTS - PC2
echo ===============================================
echo Timestamp: %date% %time%
echo.

echo 1. Checking for existing processes...
tasklist | findstr python

echo.
echo 2. Creating logs directory...
if not exist logs mkdir logs

echo.
echo 3. Launching core agents on required ports...

:: Enhanced Router - Port 5555
echo Starting Enhanced Router (port 5555)...
start "Enhanced Router" /min python "d:\DISKARTE\Voice Assistant\agents\remote_connector_agent.py" --port=5555

:: Task Router - Port 5556
echo Starting Task Router (port 5556)...
start "Task Router" /min python "d:\DISKARTE\Voice Assistant\agents\remote_connector_agent.py" --port=5556

:: Remote Connector - Port 5557
echo Starting Remote Connector (port 5557)...
start "Remote Connector" /min python "d:\DISKARTE\Voice Assistant\agents\remote_connector_agent.py" --port=5557

:: Context Memory - Port 5558
echo Starting Context Memory (port 5558)...
start "Context Memory" /min python "d:\DISKARTE\Voice Assistant\agents\contextual_memory_agent.py" --port=5558

:: Memory Agent - Port 5590 (Consolidated)
echo Starting Memory Agent (port 5590)...
start "Memory Agent" /min python "d:\DISKARTE\Voice Assistant\agents\memory.py"
:: NOTE: Jarvis Memory Agent (Port 5559) is DEPRECATED - all functionality consolidated into memory.py

:: Digital Twin - Port 5560
echo Starting Digital Twin (port 5560)...
start "Digital Twin" /min python "d:\DISKARTE\Voice Assistant\agents\digital_twin_agent.py" --port=5560

:: Learning Mode - Port 5561
echo Starting Learning Mode (port 5561)...
start "Learning Mode" /min python "d:\DISKARTE\Voice Assistant\agents\learning_mode_agent.py" --port=5561

:: Translator Agent - Port 5562
echo Starting Translator Agent (port 5562)...
start "Translator Agent" /min python "d:\DISKARTE\Voice Assistant\agents\translator_agent.py" --port=5562

:: Web Scraper - Port 5563
echo Starting Web Scraper (port 5563)...
start "Web Scraper" /min python "d:\DISKARTE\Voice Assistant\agents\web_scraper_agent.py" --port=5563

:: TinyLlama - Port 5564
echo Starting TinyLlama (port 5564)...
start "TinyLlama" /min python "d:\DISKARTE\Voice Assistant\agents\model_manager_agent.py" --model=tinyllama --port=5564

echo.
echo 4. Waiting 15 seconds for all agents to initialize...
ping 127.0.0.1 -n 16 > nul

echo.
echo 5. Checking active agent ports...
netstat -ano | findstr :5555
netstat -ano | findstr :5556
netstat -ano | findstr :5557
netstat -ano | findstr :5558
netstat -ano | findstr :5559
netstat -ano | findstr :5560
netstat -ano | findstr :5561
netstat -ano | findstr :5562
netstat -ano | findstr :5563
netstat -ano | findstr :5564

echo.
echo ===============================================
echo DISTRIBUTED SYSTEM STATUS
echo ===============================================
echo Phi Translator: Running on port 5581
echo All core agents launched (ports 5555-5564)
echo.
echo SYSTEM READY FOR CONNECTION FROM MAIN PC (192.168.1.27)
echo ===============================================
echo.
echo Press any key to exit...
pause > nul
