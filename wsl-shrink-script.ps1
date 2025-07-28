# WSL2 ext4.vhdx Shrink Script
# Run this from Windows PowerShell as Administrator after Docker cleanup

Write-Host "🔧 WSL2 Disk Shrinking Process" -ForegroundColor Green

# Get current ext4.vhdx file size
$vhdxPath = "C:\Users\haymayndz\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu22.04LTS_79rhkp1fndgsc\LocalState\ext4.vhdx"

if (Test-Path $vhdxPath) {
    $beforeSize = (Get-Item $vhdxPath).Length
    Write-Host "Current ext4.vhdx size: $(($beforeSize / 1GB).ToString('F2')) GB" -ForegroundColor Yellow
    
    Write-Host "Shutting down WSL..." -ForegroundColor Blue
    wsl --shutdown
    Start-Sleep -Seconds 5
    
    Write-Host "Compacting ext4.vhdx file..." -ForegroundColor Blue
    diskpart /s @"
select vdisk file="$vhdxPath"
attach vdisk readonly
compact vdisk
detach vdisk
"@ | Out-Host
    
    $afterSize = (Get-Item $vhdxPath).Length
    $saved = ($beforeSize - $afterSize) / 1GB
    
    Write-Host "✅ Compaction completed!" -ForegroundColor Green
    Write-Host "New size: $(($afterSize / 1GB).ToString('F2')) GB" -ForegroundColor Green
    Write-Host "Space saved: $($saved.ToString('F2')) GB" -ForegroundColor Green
    
    Write-Host "Starting WSL..." -ForegroundColor Blue
    wsl -d Ubuntu-22.04
} else {
    Write-Host "❌ ext4.vhdx file not found at: $vhdxPath" -ForegroundColor Red
} 