# Complete PC2 Services Startup Script
# This script starts all 16 PC2 services with proper sequencing, binding verification, and health checks
# Created by Cascade - 2025-05-30

# Stop any existing Python processes to avoid port conflicts
Write-Host "Stopping any existing Python processes..." -ForegroundColor Yellow
Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping process $($_.Id)..." -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -Path "logs" -ItemType Directory | Out-Null
}

# Configure logging
$logFile = "logs\pc2_services_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Start-Transcript -Path $logFile

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

function ApplyFirewallRules {
    Write-Host "Applying firewall rules (requires admin privileges)..." -ForegroundColor Cyan
    $firewallScript = "$PWD\add_pc2_firewall_rules.ps1"
    if (Test-Path $firewallScript) {
        Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$firewallScript`"" -Verb RunAs -Wait
        Write-Host "Firewall rules applied successfully." -ForegroundColor Green
    } else {
        Write-Host "Warning: Firewall script not found at $firewallScript" -ForegroundColor Red
    }
}

# Apply firewall rules first
ApplyFirewallRules

# Complete list of all PC2 services with dependencies
$services = @(
    # === Core Translation Services (Tier 1 - most critical) ===
    @{
        Name = "NLLB Translation Adapter"
        Script = "agents/nllb_translation_adapter.py"
        Port = 5581
        WaitTime = 15
        Tier = 1
        Dependencies = @()
    },
    @{
        Name = "TinyLlama Service"
        Script = "agents/tinyllama_service_enhanced.py"
        Port = 5615
        WaitTime = 10
        Tier = 1
        Dependencies = @()
    },
    
    # === Memory & Base Services (Tier 2) ===
    @{
        Name = "Memory Agent (Base)"
        Script = "agents/memory.py"
        Port = 5590
        WaitTime = 8
        Tier = 2
        Dependencies = @()
    },
    
    # === Dependent Memory Services (Tier 3) ===
    @{
        Name = "Contextual Memory Agent"
        Script = "agents/contextual_memory_agent.py"
        Port = 5596
        WaitTime = 5
        Tier = 3
        Dependencies = @("Memory Agent (Base)")
    },
    @{
        Name = "Digital Twin Agent"
        Script = "agents/digital_twin_agent.py"
        Port = 5597
        WaitTime = 5
        Tier = 3
        Dependencies = @("Memory Agent (Base)")
    },
    @{
        Name = "Jarvis Memory Agent"
        Script = "agents/jarvis_memory_agent.py"
        Port = 5598
        WaitTime = 5
        Tier = 3
        Dependencies = @("Memory Agent (Base)")
    },
    @{
        Name = "Error Pattern Memory"
        Script = "agents/error_pattern_memory.py"
        Port = 5611
        WaitTime = 5
        Tier = 3
        Dependencies = @("Memory Agent (Base)")
    },
    @{
        Name = "Chain of Thought Agent"
        Script = "agents/chain_of_thought_agent.py"
        Port = 5612
        WaitTime = 5
        Tier = 3
        Dependencies = @()
    },
    
    # === Router & Core Services (Tier 4) ===
    @{
        Name = "Remote Connector Agent"
        Script = "agents/remote_connector_agent.py"
        Port = 5557
        WaitTime = 5
        Tier = 4
        Dependencies = @()
    },
    
    # === Utility Services (Tier 5) ===
    @{
        Name = "Learning Mode Agent"
        Script = "agents/learning_mode_agent.py"
        Port = 5599
        WaitTime = 5
        Tier = 5
        Dependencies = @("Memory Agent (Base)")
    },
    @{
        Name = "Enhanced Web Scraper"
        Script = "agents/enhanced_web_scraper.py"
        Port = 5602
        WaitTime = 5
        Tier = 5
        Dependencies = @()
    },
    @{
        Name = "Autonomous Web Assistant"
        Script = "agents/autonomous_web_assistant.py"
        Port = 5604
        WaitTime = 5
        Tier = 5
        Dependencies = @("Enhanced Web Scraper")
    },
    @{
        Name = "Filesystem Assistant Agent"
        Script = "agents/filesystem_assistant_agent.py"
        Port = 5606
        WaitTime = 5
        Tier = 5
        Dependencies = @()
    },
    
    # === Monitoring Services (Tier 6) ===
    @{
        Name = "Self-Healing Agent (REP)"
        Script = "agents/self_healing_agent.py"
        Port = 5614
        WaitTime = 5
        Tier = 6
        Dependencies = @()
    },
    
    # === Translator Agent (Final Tier - depends on everything) ===
    @{
        Name = "Translator Agent"
        Script = "agents/translator_fixed.py"
        Port = 5563
        WaitTime = 5
        Tier = 7
        Dependencies = @("NLLB Translation Adapter")
    }
)

# Start services by tier
for ($tier = 1; $tier -le 7; $tier++) {
    $tierServices = $services | Where-Object { $_.Tier -eq $tier }
    
    if ($tierServices.Count -gt 0) {
        Write-Host "`n=== STARTING TIER $tier SERVICES ===" -ForegroundColor Cyan
        
        foreach ($service in $tierServices) {
            # Check dependencies
            $dependenciesOk = $true
            foreach ($dependency in $service.Dependencies) {
                $dependencyService = $services | Where-Object { $_.Name -eq $dependency }
                if ($dependencyService -and -not (CheckPort $dependencyService.Port)) {
                    Write-Host "Dependency not ready: $dependency (port $($dependencyService.Port))" -ForegroundColor Red
                    $dependenciesOk = $false
                }
            }
            
            if (-not $dependenciesOk) {
                Write-Host "Skipping $($service.Name) because dependencies are not ready" -ForegroundColor Yellow
                continue
            }
            
            Write-Host "`nStarting $($service.Name)..." -ForegroundColor Cyan
            
            # Check if the script exists
            if (-not (Test-Path $service.Script)) {
                Write-Host "ERROR: Script not found: $($service.Script)" -ForegroundColor Red
                continue
            }
            
            # Start the service
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
                    Write-Host "`nWarning: Timeout waiting for $($service.Name) port $($service.Port) to open" -ForegroundColor Yellow
                    continue
                }
                
                # Verify external binding
                Start-Sleep -Seconds 2
                if (CheckBinding $service.Port) {
                    Write-Host "$($service.Name) is correctly bound to all network interfaces (0.0.0.0)" -ForegroundColor Green
                } else {
                    Write-Host "Warning: $($service.Name) may not be accessible from external machines" -ForegroundColor Yellow
                }
            }
            catch {
                Write-Host "Error starting $($service.Name): $_" -ForegroundColor Red
            }
        }
    }
}

# Run health check
Write-Host "`nRunning health check to verify all services..." -ForegroundColor Cyan
python pc2_health_check.py

Write-Host "`nRunning remote health check simulation (from Main PC perspective)..." -ForegroundColor Cyan
python pc2_health_check.py --host 192.168.1.2

Write-Host "`nAll PC2 services have been started successfully!" -ForegroundColor Green
Write-Host "Services will continue running in separate windows." -ForegroundColor Green
Write-Host "Main PC can now connect to these services at 192.168.1.2" -ForegroundColor Green

Write-Host "`nService Details:" -ForegroundColor Cyan
foreach ($service in $services) {
    Write-Host "- $($service.Name): tcp://192.168.1.2:$($service.Port)" -ForegroundColor White
}

# Clean up and finalize
Stop-Transcript

Write-Host "`nPress Enter to close this window. Services will continue running in their own windows." -ForegroundColor Yellow
Read-Host
