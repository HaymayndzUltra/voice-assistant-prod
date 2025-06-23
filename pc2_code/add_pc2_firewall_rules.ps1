# add_pc2_firewall_rules.ps1
# Adds firewall rules for all PC2 services to enable connectivity from Main PC

# This script must be run as Administrator on the PC2 Windows machine
# It configures the Windows firewall to allow ZMQ and other AI system traffic

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script must be run as Administrator. Please restart PowerShell as Administrator." -ForegroundColor Red
    exit 1
}

# Define the port ranges
$zmqPortRange = "5500-7200"
$httpPortRange = "8000-9000"

# Create firewall rules for ZMQ traffic (TCP)
Write-Host "Creating firewall rules for ZMQ traffic (TCP ports $zmqPortRange)..." -ForegroundColor Cyan
try {
    # Check if rule already exists
    $existingRule = Get-NetFirewallRule -DisplayName "AI System - ZMQ TCP" -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Host "Firewall rule 'AI System - ZMQ TCP' already exists. Removing and recreating..." -ForegroundColor Yellow
        Remove-NetFirewallRule -DisplayName "AI System - ZMQ TCP"
    }
    
    # Create new rule
    New-NetFirewallRule -DisplayName "AI System - ZMQ TCP" `
                        -Direction Inbound `
                        -Action Allow `
                        -Protocol TCP `
                        -LocalPort $zmqPortRange `
                        -Profile Any `
                        -Description "Allows ZMQ communication for the AI System"
    
    Write-Host "ZMQ TCP firewall rule created successfully." -ForegroundColor Green
} catch {
    Write-Host "Error creating ZMQ TCP firewall rule: $_" -ForegroundColor Red
}

# Create firewall rules for HTTP/WebSocket traffic (TCP)
Write-Host "Creating firewall rules for HTTP/WebSocket traffic (TCP ports $httpPortRange)..." -ForegroundColor Cyan
try {
    # Check if rule already exists
    $existingRule = Get-NetFirewallRule -DisplayName "AI System - HTTP/WebSocket" -ErrorAction SilentlyContinue
    if ($existingRule) {
        Write-Host "Firewall rule 'AI System - HTTP/WebSocket' already exists. Removing and recreating..." -ForegroundColor Yellow
        Remove-NetFirewallRule -DisplayName "AI System - HTTP/WebSocket"
    }
    
    # Create new rule
    New-NetFirewallRule -DisplayName "AI System - HTTP/WebSocket" `
                        -Direction Inbound `
                        -Action Allow `
                        -Protocol TCP `
                        -LocalPort $httpPortRange `
                        -Profile Any `
                        -Description "Allows HTTP and WebSocket communication for the AI System"
    
    Write-Host "HTTP/WebSocket firewall rule created successfully." -ForegroundColor Green
} catch {
    Write-Host "Error creating HTTP/WebSocket firewall rule: $_" -ForegroundColor Red
}

# Display all AI System related firewall rules
Write-Host "`nCurrent AI System firewall rules:" -ForegroundColor Cyan
Get-NetFirewallRule | Where-Object { $_.DisplayName -like "AI System*" } | 
    Select-Object DisplayName, Direction, Action, Enabled |
    Format-Table -AutoSize

Write-Host "`nFirewall configuration completed." -ForegroundColor Green
Write-Host "Note: You may need to restart the AI System services for changes to take effect." -ForegroundColor Yellow

# TCP Ports for PC2 services
$pc2Ports = @(
    5563,  # TranslatorAgent
    5581,  # NLLB Translation Adapter
    5615,  # TinyLlama Service
    5590,  # Memory Agent (Base)
    5596,  # Contextual Memory Agent
    5597,  # Digital Twin Agent
    5598,  # Jarvis Memory Agent
    5611,  # Error Pattern Memory
    7602,  # Enhanced Model Router REP
    7701,  # Enhanced Model Router PUB
    5557,  # Remote Connector Agent
    5612,  # Chain of Thought Agent
    5599,  # Learning Mode Agent
    5602,  # Enhanced Web Scraper
    5604,  # Autonomous Web Assistant
    5606,  # Filesystem Assistant Agent
    5614,  # Self-Healing Agent REP
    5616   # Self-Healing Agent PUB
)

# Create a single inbound rule for all PC2 service ports
$ruleName = "Voice Assistant PC2 Services"
$ruleDescription = "Allow all PC2 services to receive connections from Main PC"

Write-Host "Creating firewall rule for all PC2 services..."

# Delete existing rule if it exists
if (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue) {
    Remove-NetFirewallRule -DisplayName $ruleName
    Write-Host "Removed existing rule '$ruleName'"
}

# Create new rule
New-NetFirewallRule -DisplayName $ruleName `
    -Description $ruleDescription `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $pc2Ports `
    -Profile Private, Domain `
    -Enabled True | Out-Null

Write-Host "Firewall rule '$ruleName' created successfully"
Write-Host "The following ports are now open: $($pc2Ports -join ', ')"
