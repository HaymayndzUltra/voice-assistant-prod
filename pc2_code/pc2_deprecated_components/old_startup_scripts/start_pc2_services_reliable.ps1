# Reliable PC2 Services Startup Script (PowerShell)
# This script starts all PC2 services in the correct sequence,
# ensures they bind to all network interfaces (0.0.0.0),
# and verifies they're accessible from the Main PC.

# Stop any existing Python processes to avoid port conflicts
Write-Host "Stopping any existing Python processes..."
Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping process $($_.Id)..."
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
        $true
    } catch {
        $false
    } finally {
        $tcpClient.Close()
    }
}

function CheckBinding($port) {
    $netstat = netstat -ano | findstr "LISTENING" | findstr ":$port"
    if ($netstat -match "0.0.0.0:$port") {
        Write-Host "Port $port is correctly bound to 0.0.0.0 (all interfaces)" -ForegroundColor Green
        $true
    } else {
        Write-Host "Port $port may not be bound to all interfaces. Netstat output: $netstat" -ForegroundColor Yellow
        $false
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

# Services configuration
$services = @(
    @{
        Name = "NLLB Translation Adapter"
        Script = "agents/nllb_translation_adapter.py"
        Port = 5581
        WaitTime = 15
    },
    @{
        Name = "TinyLlama Service"
        Script = "agents/tinyllama_service_enhanced.py"
        Port = 5615
        WaitTime = 10
    },
    @{
        Name = "Translator Agent"
        Script = "agents/translator_fixed.py"
        Port = 5563
        WaitTime = 5
    }
)

# Start each service
foreach ($service in $services) {
    Write-Host "`nStarting $($service.Name)..." -ForegroundColor Cyan
    
    # Start the service
    $process = Start-Process -FilePath "python" -ArgumentList $service.Script -WindowStyle Normal -PassThru
    
    Write-Host "Started $($service.Name) with PID $($process.Id)"
    
    # Wait for service to initialize
    Write-Host "Waiting $($service.WaitTime) seconds for initialization..."
    $portOpen = $false
    
    for ($i = 1; $i -le $service.WaitTime; $i++) {
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
        
        if (CheckPort $service.Port) {
            $portOpen = $true
            Write-Host "`nPort $($service.Port) is now open after $i seconds"
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
