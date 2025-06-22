# PC2 Service Recovery Script
# This script systematically restarts all PC2 services with proper binding to 0.0.0.0
# Created by Cascade - 2025-05-30

# Clear screen and show header
Clear-Host
Write-Host "PC2 SERVICE RECOVERY SCRIPT" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "This script will:"
Write-Host "1. Stop all running Python processes"
Write-Host "2. Apply firewall rules for all PC2 service ports"
Write-Host "3. Start essential PC2 services with proper external binding (0.0.0.0)"
Write-Host "4. Verify connectivity from both local and Main PC perspective"
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# Stop any existing Python processes to avoid port conflicts
Write-Host "Stopping any existing Python processes..." -ForegroundColor Yellow
Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping process $($_.Id)..." -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -Path "logs" -ItemType Directory | Out-Null
}

# Start logging
$logFile = "logs\pc2_recovery_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $logFile -ErrorAction SilentlyContinue

# PC2 services configuration with dependencies
$services = @(
    # Critical Translation Services
    @{
        Name = "NLLB Translation Adapter" 
        Script = "agents/nllb_translation_adapter.py"
        Port = 5581
        WaitTime = 20
        Critical = $true
    },
    @{
        Name = "TinyLlama Service"
        Script = "agents/tinyllama_service_enhanced.py"
        Port = 5615
        WaitTime = 10
        Critical = $true
    },
    @{
        Name = "Translator Agent"
        Script = "agents/translator_fixed.py"
        Port = 5563
        WaitTime = 5
        Critical = $true
    },
    
    # Memory Services
    @{
        Name = "Memory Agent (Base)"
        Script = "agents/memory.py"
        Port = 5590
        WaitTime = 10
        Critical = $true
    },
    @{
        Name = "Contextual Memory Agent"
        Script = "agents/contextual_memory_agent.py"
        Port = 5596
        WaitTime = 5
        Critical = $false
    },
    @{
        Name = "Digital Twin Agent"
        Script = "agents/digital_twin_agent.py"
        Port = 5597
        WaitTime = 5
        Critical = $false
    },
    @{
        Name = "Jarvis Memory Agent"
        Script = "agents/jarvis_memory_agent.py"
        Port = 5598
        WaitTime = 5
        Critical = $false
    },
    @{
        Name = "Error Pattern Memory"
        Script = "agents/error_pattern_memory.py"
        Port = 5611
        WaitTime = 5
        Critical = $false
    },
    
    # Chain of Thought Agent
    @{
        Name = "Chain of Thought Agent"
        Script = "agents/chain_of_thought_agent.py"
        Port = 5612
        WaitTime = 5
        Critical = $false
    },

    # Other Services
    @{
        Name = "Learning Mode Agent"
        Script = "agents/learning_mode_agent.py"
        Port = 5599
        WaitTime = 5
        Critical = $false
    },
    @{
        Name = "Context Summarizer Agent"
        Script = "agents/context_summarizer_agent.py"
        Port = 5610
        WaitTime = 5
        Critical = $false
    }
)

function CheckPort($port) {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    try {
        $tcpClient.Connect("localhost", $port)
        return $true
    } catch {
        return $false
    } finally {
        $tcpClient.Close()
    }
}

function CheckBinding($port) {
    $netstat = netstat -ano | findstr "LISTENING" | findstr ":$port"
    if ($netstat -match "0.0.0.0:$port") {
        Write-Host "Port $port is correctly bound to 0.0.0.0 (all interfaces)" -ForegroundColor Green
        return $true
    } else {
        Write-Host "Port $port may not be bound to all interfaces. Netstat output: $netstat" -ForegroundColor Yellow
        return $false
    }
}

# Apply firewall rules to ensure connectivity
Write-Host "`nApplying firewall rules..." -ForegroundColor Cyan
$firewallScript = "$PWD\add_pc2_firewall_rules.ps1"
if (Test-Path $firewallScript) {
    # Launch firewall script with admin privileges - USER WILL NEED TO APPROVE UAC
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$firewallScript`"" -Verb RunAs -Wait
    Write-Host "Firewall rules have been applied!" -ForegroundColor Green
} else {
    Write-Host "WARNING: Firewall script not found at $firewallScript" -ForegroundColor Red
    
    # Create basic firewall rule to ensure essential ports are open
    Write-Host "Creating basic firewall rules for essential PC2 services..." -ForegroundColor Yellow
    $ports = @(5563, 5581, 5615, 5590, 5596, 5597, 5598, 5611, 5612, 5599, 5610)
    
    # Launch PowerShell with admin rights to create firewall rule
    $command = "New-NetFirewallRule -DisplayName 'PC2 Essential Services' -Direction Inbound -Protocol TCP -LocalPort $($ports -join ',') -Action Allow"
    Start-Process powershell -ArgumentList "-Command `"$command`"" -Verb RunAs -Wait
}

# Start critical services first
Write-Host "`n=== STARTING CRITICAL PC2 SERVICES ===" -ForegroundColor Magenta
$criticalServices = $services | Where-Object { $_.Critical -eq $true }

foreach ($service in $criticalServices) {
    Write-Host "`nStarting $($service.Name)..." -ForegroundColor Cyan
    
    # Check if script file exists
    if (-not (Test-Path $service.Script)) {
        Write-Host "ERROR: Script not found at $($service.Script)" -ForegroundColor Red
        continue
    }
    
    # Start the service process
    try {
        $process = Start-Process -FilePath "python" -ArgumentList $service.Script -WindowStyle Normal -PassThru
        Write-Host "Started $($service.Name) with PID $($process.Id)" -ForegroundColor Green
        
        # Wait for service to initialize
        Write-Host "Waiting $($service.WaitTime) seconds for initialization..." -ForegroundColor Yellow
        $portOpen = $false
        
        for ($i = 1; $i -le $service.WaitTime; $i++) {
            Start-Sleep -Seconds 1
            Write-Host "." -NoNewline
            
            if (CheckPort $service.Port) {
                $portOpen = $true
                Write-Host "`nPort $($service.Port) is now open after $i seconds" -ForegroundColor Green
                break
            }
        }
        
        if (-not $portOpen) {
            Write-Host "`nWARNING: Timeout waiting for $($service.Name) port $($service.Port) to open" -ForegroundColor Yellow
        } else {
            # Verify external binding
            Start-Sleep -Seconds 2
            CheckBinding $service.Port
        }
    }
    catch {
        Write-Host "Error starting $($service.Name): $_" -ForegroundColor Red
    }
}

# Start non-critical services
Write-Host "`n=== STARTING NON-CRITICAL PC2 SERVICES ===" -ForegroundColor Magenta
$nonCriticalServices = $services | Where-Object { $_.Critical -eq $false }

foreach ($service in $nonCriticalServices) {
    Write-Host "`nStarting $($service.Name)..." -ForegroundColor Cyan
    
    # Check if script file exists
    if (-not (Test-Path $service.Script)) {
        Write-Host "ERROR: Script not found at $($service.Script)" -ForegroundColor Red
        continue
    }
    
    # Start the service process
    try {
        $process = Start-Process -FilePath "python" -ArgumentList $service.Script -WindowStyle Normal -PassThru
        Write-Host "Started $($service.Name) with PID $($process.Id)" -ForegroundColor Green
        
        # Wait for service to initialize
        Write-Host "Waiting $($service.WaitTime) seconds for initialization..." -ForegroundColor Yellow
        $portOpen = $false
        
        for ($i = 1; $i -le $service.WaitTime; $i++) {
            Start-Sleep -Seconds 1
            Write-Host "." -NoNewline
            
            if (CheckPort $service.Port) {
                $portOpen = $true
                Write-Host "`nPort $($service.Port) is now open after $i seconds" -ForegroundColor Green
                break
            }
        }
        
        if (-not $portOpen) {
            Write-Host "`nWARNING: Timeout waiting for $($service.Name) port $($service.Port) to open" -ForegroundColor Yellow
        } else {
            # Verify external binding
            Start-Sleep -Seconds 2
            CheckBinding $service.Port
        }
    }
    catch {
        Write-Host "Error starting $($service.Name): $_" -ForegroundColor Red
    }
}

# Start critical services first
Write-Host "`n=== STARTING CRITICAL PC2 SERVICES ===" -ForegroundColor Magenta
$criticalServices = $services | Where-Object { $_.Critical -eq $true }

foreach ($service in $criticalServices) {
    Write-Host "`nStarting $($service.Name)..." -ForegroundColor Cyan
    
    # Check if script file exists
    if (-not (Test-Path $service.Script)) {
        Write-Host "ERROR: Script not found at $($service.Script)" -ForegroundColor Red
        continue
    }
    
    # Start the service process
    try {
        $process = Start-Process -FilePath "python" -ArgumentList $service.Script -WindowStyle Normal -PassThru
        Write-Host "Started $($service.Name) with PID $($process.Id)" -ForegroundColor Green
        
        # Wait for service to initialize
        Write-Host "Waiting $($service.WaitTime) seconds for initialization..." -ForegroundColor Yellow
        $portOpen = $false
        
        for ($i = 1; $i -le $service.WaitTime; $i++) {
            Start-Sleep -Seconds 1
            Write-Host "." -NoNewline
            
            if (CheckPort $service.Port) {
                $portOpen = $true
                Write-Host "`nPort $($service.Port) is now open after $i seconds" -ForegroundColor Green
                break
            }
        }
        
        if (-not $portOpen) {
            Write-Host "`nWARNING: Timeout waiting for $($service.Name) port $($service.Port) to open" -ForegroundColor Yellow
        } else {
            # Verify external binding
            Start-Sleep -Seconds 2
            CheckBinding $service.Port
        }
    }
    catch {
        Write-Host "Error starting $($service.Name): $_" -ForegroundColor Red
    }
}

# Start non-critical services
Write-Host "`n=== STARTING NON-CRITICAL PC2 SERVICES ===" -ForegroundColor Magenta
$nonCriticalServices = $services | Where-Object { $_.Critical -eq $false }

foreach ($service in $nonCriticalServices) {
    Write-Host "`nStarting $($service.Name)..." -ForegroundColor Cyan
    
    # Check if script file exists
    if (-not (Test-Path $service.Script)) {
        Write-Host "ERROR: Script not found at $($service.Script)" -ForegroundColor Red
        continue
    }
    
    # Start the service process
    try {
        $process = Start-Process -FilePath "python" -ArgumentList $service.Script -WindowStyle Normal -PassThru
        Write-Host "Started $($service.Name) with PID $($process.Id)" -ForegroundColor Green
        
        # Wait for service to initialize
        Write-Host "Waiting $($service.WaitTime) seconds for initialization..." -ForegroundColor Yellow
        $portOpen = $false
        
        for ($i = 1; $i -le $service.WaitTime; $i++) {
            Start-Sleep -Seconds 1
            Write-Host "." -NoNewline
            
            if (CheckPort $service.Port) {
                $portOpen = $true
                Write-Host "`nPort $($service.Port) is now open after $i seconds" -ForegroundColor Green
                break
            }
        }
        
        if (-not $portOpen) {
            Write-Host "`nWARNING: Timeout waiting for $($service.Name) port $($service.Port) to open" -ForegroundColor Yellow
        } else {
            # Verify external binding
            Start-Sleep -Seconds 2
            CheckBinding $service.Port
        }
    }
    catch {
        Write-Host "Error starting $($service.Name): $_" -ForegroundColor Red
    }
}

# Verify services are running with netstat
Write-Host "`n=== VERIFYING ALL PC2 SERVICES ===" -ForegroundColor Magenta
Write-Host "Checking active network connections for PC2 service ports..." -ForegroundColor Cyan
$servicesPorts = $services.Port -join "|"
$netstatCommand = "netstat -ano | findstr ""LISTENING"" | findstr /E ""$servicesPorts"""
Write-Host "Running: $netstatCommand" -ForegroundColor Yellow
Invoke-Expression $netstatCommand | ForEach-Object {
    if ($_ -match "0.0.0.0:(\d+)") {
        $port = $matches[1]
        $service = $services | Where-Object { $_.Port -eq $port }
        if ($service) {
            Write-Host "$($service.Name) (Port $port): CORRECTLY BOUND TO ALL INTERFACES ✓" -ForegroundColor Green
        } else {
            Write-Host "Unknown service on port $port: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "Service not properly bound to 0.0.0.0: $_" -ForegroundColor Red
    }
}

# Verify connectivity with local health check
Write-Host "`n=== RUNNING LOCAL HEALTH CHECK ===" -ForegroundColor Magenta
python pc2_health_check.py

Write-Host "`n=== PC2 SERVICE RECOVERY COMPLETE ===" -ForegroundColor Cyan
Write-Host "Services have been started with proper external binding (0.0.0.0)" -ForegroundColor Green
Write-Host "Main PC should now be able to connect to these services at 192.168.1.2" -ForegroundColor Green
Write-Host "DO NOT CLOSE any service windows or they will terminate!" -ForegroundColor Yellow

# Clean up and finalize
Stop-Transcript

Write-Host "`nPress Enter to close this recovery script. Services will continue running in their own windows." -ForegroundColor Magenta
Read-Host

# Verify connectivity with local health check
Write-Host "`n=== RUNNING LOCAL HEALTH CHECK ===" -ForegroundColor Magenta
python pc2_health_check.py

Write-Host "`n=== PC2 SERVICE RECOVERY COMPLETE ===" -ForegroundColor Cyan
Write-Host "Services have been started with proper external binding (0.0.0.0)" -ForegroundColor Green
Write-Host "Main PC should now be able to connect to these services at 192.168.1.2" -ForegroundColor Green
Write-Host "DO NOT CLOSE any service windows or they will terminate!" -ForegroundColor Yellow

# Clean up and finalize
Stop-Transcript

Write-Host "`nPress Enter to close this recovery script. Services will continue running in their own windows." -ForegroundColor Magenta
Read-Host
