# PC2 Services Launcher
# Starts all required services for cross-machine communication

Write-Host "===== Starting PC2 Services for Cross-Machine Communication =====" -ForegroundColor Cyan

# Activate the virtual environment if needed
# Uncomment the line below if you want to activate venv
# & D:\DISKARTE\Voice Assistant\venv\Scripts\activate

# Start services in separate PowerShell windows with distinct titles

# 1. Remote Connector Agent
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\DISKARTE\Voice Assistant'; Write-Host 'Starting Remote Connector Agent...' -ForegroundColor Yellow; python agents/remote_connector_agent.py" -WindowStyle Normal

# 2. Task Router Agent
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\DISKARTE\Voice Assistant'; Write-Host 'Starting Task Router Agent...' -ForegroundColor Yellow; python agents/task_router_agent.py" -WindowStyle Normal

# 3. LLM Translation Adapter 
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\DISKARTE\Voice Assistant'; Write-Host 'Starting LLM Translation Adapter...' -ForegroundColor Yellow; python agents/llm_translation_adapter.py" -WindowStyle Normal

# 5. Start ZMQ Bridge
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\DISKARTE\Voice Assistant'; Write-Host 'Starting ZMQ Bridge Test (Receive Mode)...' -ForegroundColor Yellow; python test_cross_machine_comm.py --mode receive" -WindowStyle Normal

Write-Host "`nAll PC2 services have been started!" -ForegroundColor Green
Write-Host "Each service is running in its own PowerShell window." -ForegroundColor Green
Write-Host "`nTo test connectivity from Main PC, run:" -ForegroundColor Cyan
Write-Host "python test_cross_machine_comm.py --test components" -ForegroundColor White
Write-Host "from the Voice Assistant directory on the Main PC." -ForegroundColor White
