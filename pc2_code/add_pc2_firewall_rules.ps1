# add_pc2_firewall_rules.ps1
# Adds firewall rules for all PC2 services to enable connectivity from Main PC

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
