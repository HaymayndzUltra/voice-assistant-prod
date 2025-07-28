# 🚀 Docker + WSL2 Disk Space Management Guide

## 🎯 Problem Summary
WSL2 `ext4.vhdx` file grows to 100GB+ due to Docker cache buildup but never shrinks automatically.

## ✅ Quick Fix Results
- **Before**: ext4.vhdx = 249GB, Docker = 178GB  
- **After**: ext4.vhdx = ~127GB, Docker = 56GB
- **Saved**: ~122GB of disk space

## 🔧 Root Causes Found

### 1. BuildX Cache (90GB) 
- `buildx_buildkit_exciting_jang0_state` volume
- Build cache accumulates but never auto-cleans

### 2. Docker Build Cache (25GB)
- Legacy builder cache objects  
- Intermediate layers from failed builds

### 3. WSL2 ext4.vhdx Never Shrinks
- Grows automatically but requires manual compaction
- Windows doesn't auto-compact VHDX files

## 🛠️ Solutions Implemented

### 1. Immediate Cleanup
```bash
# Run the provided cleanup script
./docker-cleanup-script.sh
```

### 2. WSL2 VHDX Compaction
```powershell
# Run from Windows PowerShell as Administrator
.\wsl-shrink-script.ps1
```

### 3. Docker Daemon Config (Prevention)
```bash
# Copy daemon config to proper location
sudo cp docker-daemon-config.json /etc/docker/daemon.json
sudo systemctl restart docker
```

## 📋 Weekly Maintenance Tasks

### WSL Linux Side:
```bash
# 1. Clean Docker cache
./docker-cleanup-script.sh

# 2. Check disk usage
df -h
sudo du -sh /var/lib/docker/

# 3. Remove old images (be careful!)
docker image prune -a --filter "until=168h"
```

### Windows Side:
```powershell
# 1. Check ext4.vhdx size
Get-Item 'C:\Users\haymayndz\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu22.04LTS_79rhkp1fndgsc\LocalState\ext4.vhdx' | Select-Object Length, LastWriteTime

# 2. Compact if needed (>50GB)
.\wsl-shrink-script.ps1
```

## 🚨 Prevention Strategies

### 1. Docker Context Management
```bash
# Always know which context you're using
docker context ls
docker context use default  # For WSL Docker
docker context use desktop-linux  # For Docker Desktop
```

### 2. BuildX Management
```bash
# List builders
docker buildx ls

# Remove large builders when done
docker buildx rm builder-name

# Use default builder for small projects
docker buildx use default
```

### 3. Volume Management
```bash
# Regular volume cleanup
docker volume prune -f

# Check volume sizes
docker system df -v
```

## 📊 Monitoring Commands

### Check Docker Disk Usage:
```bash
sudo du -sh /var/lib/docker/
docker system df -v
```

### Check WSL2 Usage:
```bash
df -h
```

### Check ext4.vhdx Size (Windows):
```powershell
Get-Item 'C:\Users\haymayndz\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu22.04LTS_79rhkp1fndgsc\LocalState\ext4.vhdx' | Select-Object Length, LastWriteTime
```

## 🔄 Automated Setup

### Crontab for Weekly Cleanup:
```bash
# Add to crontab (crontab -e)
0 2 * * 0 /home/haymayndz/AI_System_Monorepo/docker-cleanup-script.sh >> /tmp/docker-cleanup.log 2>&1
```

### Windows Task Scheduler:
- Create task to run `wsl-shrink-script.ps1` monthly
- Trigger: When ext4.vhdx > 50GB

## ⚠️ Important Notes

1. **Backup Important Data** before major cleanups
2. **Check Running Containers** before volume pruning
3. **Docker Desktop vs WSL Docker** - they're separate!
4. **BuildX Cache** grows fastest during development
5. **ext4.vhdx** needs manual compaction on Windows

## 🎯 Best Practices

1. **Use Multi-stage Builds** to reduce image sizes
2. **Clean up after development sessions**
3. **Monitor disk usage weekly**
4. **Use .dockerignore** to avoid copying unnecessary files
5. **Remove test containers/images regularly**

## 📞 Quick Commands Reference

```bash
# Emergency cleanup (removes everything unused)
docker system prune -a --volumes -f

# Check what's using space
sudo du -sh /var/lib/docker/*

# Remove specific large image
docker rmi IMAGE_ID

# Remove all stopped containers
docker container prune -f

# Remove buildx cache
docker buildx prune -a -f
``` 