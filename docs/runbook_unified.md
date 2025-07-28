# Unified System Operational Runbook

## Table of Contents

1. [System Overview](#system-overview)
2. [Startup Procedures](#startup-procedures)
3. [Monitoring & Health Checks](#monitoring--health-checks)
4. [Common Operations](#common-operations)
5. [Troubleshooting](#troubleshooting)
6. [Emergency Procedures](#emergency-procedures)
7. [Maintenance](#maintenance)

## System Overview

### Architecture Summary
- **Total Agents**: 77 (24 essential + 53 optional)
- **Profiles**: core, vision, learning, tutoring, full
- **Key Services**: ObservabilityHub, LazyLoader, ModelManagerSuite
- **Port Ranges**: 5500-9199

### Critical Dependencies
1. ServiceRegistry (port 7200) - Must start first
2. ObservabilityHub (port 9000) - Central monitoring
3. SystemDigitalTwin (port 7220) - State management
4. ModelManagerSuite (port 7211) - Model coordination

## Startup Procedures

### Normal Startup

```bash
# 1. Set profile (default: core)
export PROFILE=core  # or vision, learning, tutoring, full

# 2. Launch system
python3 scripts/launch_unified_profile.py

# 3. Verify startup (wait ~60s for core profile)
curl http://localhost:9000/health  # ObservabilityHub
curl http://localhost:7200/health  # ServiceRegistry
```

### Profile-Specific Startup

#### Core Profile (Minimal)
```bash
PROFILE=core python3 scripts/launch_unified_profile.py
# Starts: 16 essential agents
# Memory: 2GB
# Time: ~60s
```

#### Vision Profile
```bash
PROFILE=vision python3 scripts/launch_unified_profile.py
# Starts: ~20 agents (includes FaceRecognitionAgent, VisionProcessingAgent)
# Memory: 4GB
# Time: ~90s
```

#### Learning Profile
```bash
PROFILE=learning python3 scripts/launch_unified_profile.py
# Starts: ~30 agents (includes learning cluster)
# Memory: 6GB
# Time: ~120s
```

#### Full Profile
```bash
PROFILE=full python3 scripts/launch_unified_profile.py
# Starts: All 77 agents available
# Memory: 8GB
# Time: ~180s
```

### Startup Verification

```bash
# Check essential agents
for port in 7200 9000 7220 7211 7201 8202; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health | grep -q "healthy" && echo "OK" || echo "FAIL"
done

# Check LazyLoader status
curl http://localhost:8202/health | jq .
```

## Monitoring & Health Checks

### ObservabilityHub Dashboard

Access: `http://localhost:9000/dashboard`

Key Metrics:
- Agent status (up/down)
- Memory usage per agent
- VRAM utilization
- Request latency
- LLM routing statistics

### Health Check Endpoints

All agents expose health endpoints:
```bash
# Format: http://localhost:{health_port}/health
# Example:
curl http://localhost:8200/health  # ServiceRegistry
curl http://localhost:9001/health  # ObservabilityHub
curl http://localhost:8202/health  # LazyLoader
```

### Prometheus Queries

```promql
# Essential agents status
up{job="unified_agents", required="true"}

# Memory usage by agent
process_resident_memory_bytes{job="unified_agents"} / 1024 / 1024

# LLM routing distribution
rate(llm_routing_decisions_total[5m])

# System health score
system_health_score
```

### Alert Response

| Alert | Severity | Action |
|-------|----------|--------|
| EssentialAgentDown | Critical | Check logs, restart agent |
| VRAMExhaustion | Critical | Free VRAM, reduce load |
| CircuitBreakerOpen | Critical | Check failing service |
| HighMemoryUsage | Warning | Monitor, consider restart |
| SlowAgentLoading | Warning | Check dependencies |

## Common Operations

### Loading Optional Agents

Optional agents load automatically on demand. To manually load:

```bash
# Send request that requires specific agent
curl -X POST http://localhost:7201/task \
  -H "Content-Type: application/json" \
  -d '{"type": "vision", "data": "..."}'

# Check LazyLoader queue
curl http://localhost:8202/health | jq .queue_size
```

### Switching Profiles

```bash
# 1. Stop current system
pkill -f launch_unified_profile.py

# 2. Change profile
export PROFILE=learning

# 3. Restart
python3 scripts/launch_unified_profile.py
```

### Manual Agent Control

```bash
# Stop specific agent
kill $(pgrep -f "agent_name.py")

# LazyLoader will auto-restart if agent is needed

# Disable auto-restart temporarily
export DISABLE_AUTO_RESTART=true
```

### Clearing Caches

```bash
# Clear model cache
curl -X POST http://localhost:7211/cache/clear

# Clear conversation memory
curl -X POST http://localhost:7220/memory/clear

# Reset LLM routing stats
curl -X POST http://localhost:7211/routing/reset
```

## Troubleshooting

### Agent Won't Start

1. Check port conflicts:
```bash
lsof -i :PORT_NUMBER
```

2. Check dependencies:
```bash
python3 scripts/validate_config.py config/unified_startup_phase2.yaml
```

3. Check logs:
```bash
tail -f logs/agents/{agent_name}.log
```

### High Memory Usage

1. Check agent memory:
```bash
curl http://localhost:9000/metrics | grep memory
```

2. Identify culprit:
```bash
ps aux | grep python | sort -k4 -nr | head -10
```

3. Restart high-memory agent:
```bash
# Agent will be restarted by LazyLoader if needed
kill $(pgrep -f "high_memory_agent.py")
```

### Slow Performance

1. Check LLM routing:
```bash
curl http://localhost:7211/routing/stats
```

2. Check circuit breakers:
```bash
curl http://localhost:9000/circuit_breakers
```

3. Review latency metrics:
```bash
curl http://localhost:9000/metrics | grep latency
```

### LazyLoader Issues

1. Check queue:
```bash
curl http://localhost:8202/health | jq .
```

2. View loading failures:
```bash
grep ERROR logs/lazy_loader.log | tail -20
```

3. Manual load attempt:
```bash
curl -X POST http://localhost:8202/load \
  -d '{"agent": "AgentName"}'
```

## Emergency Procedures

### System Hang

```bash
# 1. Capture state
curl http://localhost:9000/debug/state > system_state.json

# 2. Force stop all agents
pkill -9 -f "unified"

# 3. Clean restart with core profile
PROFILE=core python3 scripts/launch_unified_profile.py
```

### VRAM Exhaustion

```bash
# 1. Check VRAM usage
nvidia-smi

# 2. Force VRAM cleanup
curl -X POST http://localhost:5572/vram/cleanup

# 3. Reduce model loads
export VRAM_LIMIT_MB=2000
```

### Complete System Recovery

```bash
# 1. Stop everything
./scripts/emergency_stop.sh

# 2. Clear all state
rm -rf data/state/*
rm -rf logs/*

# 3. Start minimal profile
PROFILE=core LOG_LEVEL=DEBUG python3 scripts/launch_unified_profile.py
```

### Rollback Procedure

```bash
# 1. Stop current version
pkill -f launch_unified

# 2. Restore previous config
cp archive/unified_startup_backup.yaml config/unified_startup_phase2.yaml

# 3. Restart with backup
python3 scripts/launch_unified_phase2.py
```

## Maintenance

### Daily Tasks

1. **Check system health**:
```bash
curl http://localhost:9000/health/summary
```

2. **Review alerts**:
```bash
curl http://localhost:9093/api/v1/alerts | jq .
```

3. **Check disk space**:
```bash
df -h /workspace
du -sh logs/
```

### Weekly Tasks

1. **Rotate logs**:
```bash
./scripts/rotate_logs.sh
```

2. **Update metrics retention**:
```bash
curl -X POST http://localhost:9090/-/compact
```

3. **Performance review**:
```bash
python3 scripts/generate_weekly_report.py
```

### Monthly Tasks

1. **Full backup**:
```bash
./scripts/backup_system.sh
```

2. **Security updates**:
```bash
pip list --outdated
```

3. **Capacity planning**:
- Review growth trends
- Plan resource upgrades
- Update profiles if needed

### Configuration Updates

1. **Test changes**:
```bash
python3 scripts/validate_config.py new_config.yaml
```

2. **Staged rollout**:
```bash
# Test with core profile first
PROFILE=core CONFIG=new_config.yaml python3 scripts/launch_unified_profile.py
```

3. **Monitor impact**:
```bash
watch -n 5 'curl -s http://localhost:9000/metrics | grep -E "(error|latency)"'
```

## Appendix

### Port Reference

| Service | Agent Port | Health Port |
|---------|------------|-------------|
| ServiceRegistry | 7200 | 8200 |
| ObservabilityHub | 9000 | 9001 |
| LazyLoader | 7202 | 8202 |
| ModelManagerSuite | 7211 | 8211 |
| RequestCoordinator | 7201 | 8201 |

### Environment Variables

```bash
# Core settings
PROFILE=core|vision|learning|tutoring|full
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
DEBUG_MODE=true|false

# Resource limits
CPU_PERCENT=80
MEMORY_MB=4096
MAX_THREADS=8
VRAM_LIMIT_MB=4000

# Features
ENABLE_METRICS=true
ENABLE_TRACING=true
ENABLE_DATA_OPTIMIZER=true
```

### Useful Commands

```bash
# Count running agents
ps aux | grep -E "python.*agent" | wc -l

# Total memory usage
ps aux | grep python | awk '{sum+=$6} END {print sum/1024 " MB"}'

# Find agent by port
lsof -i :PORT | grep LISTEN

# Tail all agent logs
tail -f logs/agents/*.log

# Check system load
top -b -n 1 | head -5
```

---

**Last Updated**: 2025-01-27
**Version**: 1.0-unified