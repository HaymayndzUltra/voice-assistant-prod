# Simple PC2 Service Recovery Script
# This script focuses on the essential PC2 services needed for Main PC connectivity

Write-Host "PC2 CONNECTIVITY FIX SCRIPT" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host ""

# Stop any existing Python processes
Write-Host "Stopping any running Python processes..." -ForegroundColor Yellow
Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping process $($_.Id)..." -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Essential services that need to be running
$services = @(
    @{Name="NLLB Translation Adapter"; Script="agents/nllb_translation_adapter.py"; Port=5581},
    @{Name="TinyLlama Service"; Script="agents/tinyllama_service_enhanced.py"; Port=5615},
    @{Name="Translator Agent"; Script="agents/translator_fixed.py"; Port=5563}
)

# Apply firewall rules
Write-Host "`nEnsuring firewall rules are applied..." -ForegroundColor Cyan
$firewallScript = "add_pc2_firewall_rules.ps1"
if (Test-Path $firewallScript) {
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File $firewallScript" -Verb RunAs
    Write-Host "Firewall rules script initiated." -ForegroundColor Green
} else {
    Write-Host "Firewall script not found. Creating basic rules..." -ForegroundColor Yellow
    $ports = @(5563, 5581, 5615)
    $cmd = "New-NetFirewallRule -DisplayName 'PC2 Essential Services' -Direction Inbound -Protocol TCP -LocalPort $($ports -join ',') -Action Allow"
    Start-Process powershell -ArgumentList "-Command `"$cmd`"" -Verb RunAs
}

# Wait a moment for firewall changes
Start-Sleep -Seconds 5

# Start each service
foreach ($service in $services) {
    Write-Host "`nStarting $($service.Name)..." -ForegroundColor Cyan
    
    if (Test-Path $service.Script) {
        Start-Process -FilePath "python" -ArgumentList $service.Script -WindowStyle Normal
        Write-Host "$($service.Name) started." -ForegroundColor Green
        
        # Give each service time to initialize
        Write-Host "Waiting for initialization..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        # Check if port is open
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        try {
            $tcpClient.Connect("localhost", $service.Port)
            Write-Host "Service is active on port $($service.Port)" -ForegroundColor Green
            $tcpClient.Close()
            
            # Check binding
            $netstat = netstat -ano | findstr "LISTENING" | findstr ":$($service.Port)"
            if ($netstat -match "0.0.0.0:$($service.Port)") {
                Write-Host "Service is correctly bound to 0.0.0.0 (all interfaces)" -ForegroundColor Green
            } else {
                Write-Host "Service may not be bound to all interfaces: $netstat" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "Service does not appear to be listening on port $($service.Port)" -ForegroundColor Red
        }
    } else {
        Write-Host "Script not found: $($service.Script)" -ForegroundColor Red
    }
}

Write-Host "`nVerifying active services:" -ForegroundColor Cyan
netstat -ano | findstr "LISTENING" | findstr -i ":5563 :5581 :5615"

Write-Host "`nAttempting to run health check:" -ForegroundColor Cyan
python pc2_health_check.py

Write-Host "`nPC2 connectivity fix complete." -ForegroundColor Green
Write-Host "DO NOT close any service windows or they will terminate!" -ForegroundColor Yellow
Write-Host "Main PC should now be able to connect to these services." -ForegroundColor Green
Write-Host ""
