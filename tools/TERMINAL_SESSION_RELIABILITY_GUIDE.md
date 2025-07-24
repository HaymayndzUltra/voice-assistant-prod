# Terminal Session Reliability Guide

## Overview
Terminal session failures in WSL2 environments are common and frustrating. This guide provides tools and practices to prevent, detect, and recover from terminal session issues.

## ⚠️ Common Causes of Session Failures

### 1. **Resource Exhaustion**
- Python scripts consuming excessive memory/CPU
- Zombie processes from interrupted operations
- Heavy import operations (like agent testing)

### 2. **WSL2 Specific Issues**
- Connection timeouts between Windows host and WSL2
- Hyper-V subsystem instability  
- File system locks and permissions

### 3. **Command Execution Problems**
- Long-running subprocess operations
- Hanging git operations
- Deadlocked Python processes

## 🛠️ Prevention Tools

### 1. Terminal Health Monitor
Monitor system resources and session health:

```bash
# Check current session health
python3 tools/terminal_health_monitor.py --check

# Clean up zombie processes and temporary files  
python3 tools/terminal_health_monitor.py --cleanup

# Continuous monitoring
python3 tools/terminal_health_monitor.py --monitor --interval 30
```

**Example Output:**
```
🏥 Terminal Health Report
Overall Health: ✅ HEALTHY
WSL Status: ✅
Terminal Responsive: ✅
Memory Usage: 45.2%
CPU Usage: 23.1%
```

### 2. Safe Terminal Operations
Use timeout-protected commands:

```bash
# Run command with timeout protection
python3 tools/safe_terminal_ops.py "git status" --timeout 30

# Test session health before operations
python3 tools/safe_terminal_ops.py --test-health

# Attempt session recovery
python3 tools/safe_terminal_ops.py --recover
```

## 📋 Best Practices

### 1. **Before Heavy Operations**
```bash
# Always check health first
python3 tools/terminal_health_monitor.py --check

# If unhealthy, cleanup first
python3 tools/terminal_health_monitor.py --cleanup
```

### 2. **For Python Scripts**
```bash
# Use safe wrapper for agent testing
python3 tools/safe_terminal_ops.py "python3 tools/smoke_test_mainpc.py" --timeout 300

# Monitor resources during execution
python3 tools/terminal_health_monitor.py --monitor &
python3 your_script.py
```

### 3. **For Git Operations**
```bash
# Git operations with timeout protection
python3 tools/safe_terminal_ops.py "git checkout refactor/ci-guardrails" --timeout 60
python3 tools/safe_terminal_ops.py "git pull" --timeout 120
```

## 🚨 Emergency Recovery

### If Terminal Becomes Unresponsive:

#### Method 1: Automatic Recovery
```bash
python3 tools/safe_terminal_ops.py --recover
```

#### Method 2: Manual Recovery Commands
```bash
# Reset terminal state
stty sane
reset
clear

# Kill hanging processes
pkill -f python
pkill -f git
```

#### Method 3: WSL2 System Level
From Windows PowerShell (as Administrator):
```powershell
# Restart WSL subsystem
wsl --shutdown
wsl

# Or restart specific distribution
wsl -t Ubuntu
wsl -d Ubuntu
```

## 📊 Monitoring & Alerts

### Set Up Continuous Monitoring
Create a background monitoring script:

```bash
# Create monitoring service
cat > ~/.local/bin/monitor-terminal.sh << 'EOF'
#!/bin/bash
while true; do
    python3 /path/to/tools/terminal_health_monitor.py --check
    if [ $? -ne 0 ]; then
        echo "⚠️ Terminal health issue detected at $(date)"
        python3 /path/to/tools/terminal_health_monitor.py --cleanup
    fi
    sleep 300  # Check every 5 minutes
done
EOF

chmod +x ~/.local/bin/monitor-terminal.sh

# Run in background
nohup ~/.local/bin/monitor-terminal.sh > ~/terminal-monitor.log 2>&1 &
```

## 🔧 Configuration Files

### 1. WSL2 Configuration
Create/edit `%USERPROFILE%/.wslconfig`:

```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
swapfile=C:\\temp\\wsl-swap.vhdx

# Network settings
networkingMode=mirrored
firewall=true

# Performance settings
vmIdleTimeout=60000
```

### 2. Bash Profile Enhancement
Add to `~/.bashrc`:

```bash
# Terminal session reliability
export TERM_HEALTH_CHECK=1
export PYTHONUNBUFFERED=1

# Timeout settings
export TIMEOUT_CMD_DEFAULT=30
export TIMEOUT_GIT=60
export TIMEOUT_PYTHON=300

# Auto cleanup on exit
trap 'python3 ~/AI_System_Monorepo/tools/terminal_health_monitor.py --cleanup' EXIT

# Health check alias
alias health-check='python3 ~/AI_System_Monorepo/tools/terminal_health_monitor.py --check'
alias safe-run='python3 ~/AI_System_Monorepo/tools/safe_terminal_ops.py'
```

## 📈 Performance Optimization

### 1. **Prevent Resource Issues**
```bash
# Before running heavy operations
free -h  # Check memory
top -n1 | head -20  # Check CPU
df -h    # Check disk space

# Set memory limits for Python
export PYTHONMALLOC=malloc
ulimit -v 2097152  # Limit virtual memory to 2GB
```

### 2. **Optimize Python Operations**
```bash
# Use minimal imports
export PYTHONSTARTUP=""
export PYTHONPATH=""

# Disable bytecode generation for testing
export PYTHONDONTWRITEBYTECODE=1

# Use faster JSON library
pip install orjson  # Used by agents for performance
```

## 📞 Quick Reference Commands

### Health & Recovery
```bash
# Quick health check
health-check

# Emergency cleanup
python3 tools/terminal_health_monitor.py --cleanup

# Force session recovery  
python3 tools/safe_terminal_ops.py --recover

# Resource monitoring
htop       # Interactive process viewer
iotop      # I/O monitoring
nethogs    # Network monitoring
```

### Safe Operations
```bash
# Safe git operations
safe-run "git status" --timeout 30
safe-run "git pull" --timeout 120

# Safe Python scripts
safe-run "python3 script.py" --timeout 300 --retries 2

# Background operations
safe-run "long_running_command" --background --timeout 600
```

## 🎯 Success Metrics

Track these metrics to measure improvement:

1. **Session Uptime**: Target >2 hours without failure
2. **Command Success Rate**: Target >95% first-attempt success  
3. **Recovery Time**: Target <30 seconds for session recovery
4. **Resource Usage**: Keep memory <80%, CPU <70%

## 📝 Troubleshooting Log

Keep a log of session failures:

```bash
# Log session issues
echo "$(date): Session failure - $(health-check)" >> ~/session-issues.log

# Review patterns
tail -50 ~/session-issues.log
grep "UNHEALTHY" ~/session-issues.log | wc -l
```

---

## 🚀 Implementation Checklist

- [ ] Install monitoring tools
- [ ] Configure WSL2 settings  
- [ ] Set up bash profile enhancements
- [ ] Test emergency recovery procedures
- [ ] Establish monitoring routine
- [ ] Track success metrics

**Next Steps**: Implement these tools and practices systematically to eliminate terminal session reliability issues. 