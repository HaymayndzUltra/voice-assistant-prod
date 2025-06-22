# PC2 Architecture Cleanup Script
# Based on confirmed architectural decisions - May 31, 2025
# Created by Cascade

# Display header
Write-Host "PC2 ARCHITECTURE CLEANUP" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

# Create deprecated folder if it doesn't exist
$deprecatedFolder = "D:\DISKARTE\Voice Assistant\deprecated_agents"
if (-not (Test-Path $deprecatedFolder)) {
    Write-Host "Creating deprecated_agents folder..." -ForegroundColor Yellow
    New-Item -Path $deprecatedFolder -ItemType Directory -Force | Out-Null
    Write-Host "Folder created at $deprecatedFolder" -ForegroundColor Green
}

# Define deprecated services to stop and move
$deprecatedServices = @(
    @{
        Name = "Model Manager Agent";
        Port = 5605;
        Script = "agents\model_manager_agent.py";
        Reason = "DEPRECATED: Main PC MMA is now the only central orchestrator";
    },
    @{
        Name = "Code Generator Agent";
        Port = 5602;
        Script = "agents\code_generator_agent.py";
        Reason = "DEPRECATED: All code generation handled by Main PC CodeGeneratorAgent";
    },
    @{
        Name = "Executor Agent";
        Port = 5603;
        Script = "agents\executor_agent.py";
        Reason = "DEPRECATED: Code execution handled by Main PC Executor Agent";
    },
    @{
        Name = "Progressive Code Generator";
        Port = 5604;
        Script = "agents\progressive_code_generator.py";
        Reason = "DEPRECATED: Not needed with Main PC handling code generation";
    },
    @{
        Name = "Web Scraper Agent";
        Port = 5601;
        Script = "agents\web_scraper_agent.py";
        Reason = "DEPRECATED: Functionality assessment pending, moved as precaution";
    }
)

# Essential services to keep running
$essentialServices = @(
    @{
        Name = "Translator Agent";
        Port = 5563;
        Script = "quick_translator_fix.py";
    },
    @{
        Name = "NLLB Translation Adapter";
        Port = 5581;
        Script = "agents\nllb_translation_adapter.py";
    },
    @{
        Name = "TinyLlama Service";
        Port = 5615;
        Script = "agents\tinyllama_service_enhanced.py";
    },
    @{
        Name = "Memory Agent";
        Port = 5590;
        Script = "agents\memory.py";
    },
    @{
        Name = "Contextual Memory Agent";
        Port = 5596;
        Script = "agents\contextual_memory_agent.py";
    },
    @{
        Name = "Digital Twin Agent";
        Port = 5597;
        Script = "agents\digital_twin_agent.py";
    },
    @{
        Name = "Jarvis Memory Agent";
        Port = 5598;
        Script = "agents\jarvis_memory_agent.py";
    },
    @{
        Name = "Context Summarizer Agent";
        Port = 5610;
        Script = "agents\context_summarizer_agent.py";
    },
    @{
        Name = "Error Pattern Memory";
        Port = 5611;
        Script = "agents\error_pattern_memory.py";
    },
    @{
        Name = "Chain of Thought Agent";
        Port = 5612;
        Script = "agents\chain_of_thought_agent.py";
    }
)

# Function to kill process using a specific port
function Kill-ProcessOnPort($port) {
    try {
        # Find and kill process on the specified port
        $processInfo = netstat -ano | findstr ":$port" | findstr "LISTENING"
        if ($processInfo) {
            $processId = ($processInfo -split ' ')[-1]
            Write-Host "Found process $processId on port $port, terminating..." -ForegroundColor Yellow
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            return $true
        } else {
            Write-Host "No process found on port $port" -ForegroundColor Gray
            return $false
        }
    } catch {
        Write-Host "Error killing process on port $port: $_" -ForegroundColor Red
        return $false
    }
}

# Step 1: Stop all deprecated services
Write-Host "`nSTEP 1: STOPPING DEPRECATED SERVICES" -ForegroundColor Magenta
foreach ($service in $deprecatedServices) {
    Write-Host "`nProcessing $($service.Name) on port $($service.Port)..." -ForegroundColor Yellow
    Write-Host "Reason: $($service.Reason)" -ForegroundColor Gray
    
    # Kill the process if it's running
    $killed = Kill-ProcessOnPort $service.Port
    if ($killed) {
        Write-Host "$($service.Name) process terminated successfully" -ForegroundColor Green
    }
}

# Step 2: Move deprecated scripts to deprecated folder
Write-Host "`nSTEP 2: MOVING DEPRECATED SCRIPTS TO ARCHIVE" -ForegroundColor Magenta
foreach ($service in $deprecatedServices) {
    $sourcePath = "D:\DISKARTE\Voice Assistant\$($service.Script)"
    $fileName = Split-Path $service.Script -Leaf
    $destinationPath = "$deprecatedFolder\$fileName"
    
    if (Test-Path $sourcePath) {
        # Create a copy in the deprecated folder
        Write-Host "Moving $fileName to deprecated_agents folder..." -ForegroundColor Yellow
        Copy-Item -Path $sourcePath -Destination $destinationPath -Force
        Write-Host "Backup created at $destinationPath" -ForegroundColor Green
    } else {
        Write-Host "Script file not found: $sourcePath" -ForegroundColor Red
    }
}

# Step 3: Verify essential services are running and properly bound
Write-Host "`nSTEP 3: VERIFYING ESSENTIAL SERVICES" -ForegroundColor Magenta
$runningServices = @()
$notRunningServices = @()

foreach ($service in $essentialServices) {
    $port = $service.Port
    $serviceRunning = $false
    
    # Check if service is running on the port
    $processInfo = netstat -ano | findstr ":$port" | findstr "LISTENING"
    if ($processInfo) {
        # Check if bound to 0.0.0.0
        if ($processInfo -match "0.0.0.0:$port") {
            Write-Host "$($service.Name) is RUNNING and PROPERLY BOUND to 0.0.0.0" -ForegroundColor Green
            $serviceRunning = $true
            $runningServices += $service.Name
        } else {
            Write-Host "$($service.Name) is running but NOT BOUND to 0.0.0.0" -ForegroundColor Yellow
            $notRunningServices += "$($service.Name) (improper binding)"
        }
    } else {
        Write-Host "$($service.Name) is NOT RUNNING" -ForegroundColor Red
        $notRunningServices += $service.Name
    }
}

# Final summary
Write-Host "`nPC2 ARCHITECTURE CLEANUP SUMMARY" -ForegroundColor Cyan
Write-Host "--------------------------------" -ForegroundColor Cyan
Write-Host "`nDeprecated Services (Terminated and Archived):" -ForegroundColor Yellow
foreach ($service in $deprecatedServices) {
    Write-Host "- $($service.Name) (Port $($service.Port))" -ForegroundColor Gray
}

Write-Host "`nEssential Services Running Correctly:" -ForegroundColor Green
foreach ($service in $runningServices) {
    Write-Host "- $service" -ForegroundColor Green
}

if ($notRunningServices.Count -gt 0) {
    Write-Host "`nServices Needing Attention:" -ForegroundColor Red
    foreach ($service in $notRunningServices) {
        Write-Host "- $service" -ForegroundColor Red
    }
    
    Write-Host "`nRecommendation: Run 'start_essential_pc2_services.bat' to restart missing essential services" -ForegroundColor Yellow
} else {
    Write-Host "`nAll essential services are running correctly with proper binding!" -ForegroundColor Green
}

Write-Host "`nPC2 architecture cleanup complete." -ForegroundColor Cyan
