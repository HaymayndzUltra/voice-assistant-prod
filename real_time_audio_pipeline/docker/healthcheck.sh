#!/bin/bash
# RTAP Health Check Script
# Validates service health for Docker HEALTHCHECK and monitoring

set -e

# Configuration
HEALTH_TIMEOUT=5
ZMQ_EVENTS_PORT=6552
ZMQ_TRANSCRIPTS_PORT=6553
WEBSOCKET_PORT=5802

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: $1"
}

# Check if ports are listening
check_ports() {
    local failed_ports=()
    
    # Check ZMQ Events port
    if ! nc -z localhost $ZMQ_EVENTS_PORT 2>/dev/null; then
        failed_ports+=("$ZMQ_EVENTS_PORT (ZMQ Events)")
    fi
    
    # Check ZMQ Transcripts port
    if ! nc -z localhost $ZMQ_TRANSCRIPTS_PORT 2>/dev/null; then
        failed_ports+=("$ZMQ_TRANSCRIPTS_PORT (ZMQ Transcripts)")
    fi
    
    # Check WebSocket port
    if ! nc -z localhost $WEBSOCKET_PORT 2>/dev/null; then
        failed_ports+=("$WEBSOCKET_PORT (WebSocket)")
    fi
    
    if [ ${#failed_ports[@]} -eq 0 ]; then
        log "✅ All ports listening"
        return 0
    else
        log "❌ Failed ports: ${failed_ports[*]}"
        return 1
    fi
}

# Check process health
check_process() {
    # Look for RTAP Python process
    if pgrep -f "python.*app.py" >/dev/null; then
        log "✅ RTAP process running"
        return 0
    else
        log "❌ RTAP process not found"
        return 1
    fi
}

# Check memory usage
check_memory() {
    local memory_usage
    memory_usage=$(ps -o pid,ppid,pmem,pcpu,comm -p $(pgrep -f "python.*app.py") 2>/dev/null | tail -1 | awk '{print $3}')
    
    if [ -n "$memory_usage" ]; then
        # Check if memory usage is reasonable (< 50%)
        if (( $(echo "$memory_usage < 50.0" | bc -l) )); then
            log "✅ Memory usage: ${memory_usage}%"
            return 0
        else
            log "⚠️  High memory usage: ${memory_usage}%"
            return 1
        fi
    else
        log "❌ Cannot determine memory usage"
        return 1
    fi
}

# Check log for recent activity
check_logs() {
    local log_file="/app/logs/rtap-$(date +%Y%m%d).log"
    
    if [ -f "$log_file" ]; then
        # Check if log has been updated in the last 60 seconds
        if [ $(find "$log_file" -mmin -1 | wc -l) -gt 0 ]; then
            log "✅ Recent log activity detected"
            return 0
        else
            log "⚠️  No recent log activity"
            return 0  # Not critical for health
        fi
    else
        log "⚠️  Log file not found: $log_file"
        return 0  # Not critical for health
    fi
}

# Check configuration
check_config() {
    if [ -f "/app/config/default.yaml" ]; then
        log "✅ Configuration file present"
        return 0
    else
        log "❌ Configuration file missing"
        return 1
    fi
}

# Simple application health check via Python
check_app_health() {
    timeout $HEALTH_TIMEOUT python3 -c "
import sys
sys.path.insert(0, '/app')

try:
    # Test basic imports
    from config.loader import UnifiedConfigLoader
    from core.buffers import AudioRingBuffer
    
    # Quick configuration test
    loader = UnifiedConfigLoader()
    config = loader.load_config()
    
    # Test buffer creation
    buffer = AudioRingBuffer(16000, 1000, 1, 20)
    
    print('HEALTH: ✅ Application modules healthy')
except Exception as e:
    print(f'HEALTH: ❌ Application health check failed: {e}')
    sys.exit(1)
" 2>/dev/null
    
    return $?
}

# Main health check
main() {
    log "Starting health check..."
    
    local checks_passed=0
    local total_checks=6
    
    # Run all health checks
    if check_process; then
        ((checks_passed++))
    fi
    
    if check_ports; then
        ((checks_passed++))
    fi
    
    if check_memory; then
        ((checks_passed++))
    fi
    
    if check_logs; then
        ((checks_passed++))
    fi
    
    if check_config; then
        ((checks_passed++))
    fi
    
    if check_app_health; then
        ((checks_passed++))
    fi
    
    # Determine overall health
    if [ $checks_passed -eq $total_checks ]; then
        log "🎉 Health check PASSED ($checks_passed/$total_checks)"
        exit 0
    elif [ $checks_passed -ge $((total_checks * 2 / 3)) ]; then
        log "⚠️  Health check DEGRADED ($checks_passed/$total_checks)"
        exit 0  # Still considered healthy for Docker
    else
        log "❌ Health check FAILED ($checks_passed/$total_checks)"
        exit 1
    fi
}

# Execute health check
main "$@"
