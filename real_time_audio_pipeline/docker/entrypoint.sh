#!/bin/bash
# RTAP Docker Entrypoint Script
# Handles audio device setup, configuration validation, and service startup

set -e

echo "=== RTAP Container Starting ==="
echo "Timestamp: $(date)"
echo "User: $(whoami)"
echo "Working Directory: $(pwd)"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check audio system availability
check_audio() {
    log "Checking audio system availability..."
    
    # Check if ALSA devices are available
    if [ -d "/proc/asound" ]; then
        log "✅ ALSA system detected"
        if ls /dev/snd/* >/dev/null 2>&1; then
            log "✅ Audio devices found: $(ls /dev/snd/)"
        else
            log "⚠️  No audio devices found in /dev/snd/"
        fi
    else
        log "⚠️  ALSA system not available"
    fi
    
    # Check PulseAudio
    if command -v pulseaudio >/dev/null 2>&1; then
        log "✅ PulseAudio available"
    else
        log "⚠️  PulseAudio not available"
    fi
    
    # Set audio environment for mock mode if no devices
    if [ ! -d "/dev/snd" ] || [ -z "$(ls -A /dev/snd 2>/dev/null)" ]; then
        log "🎯 Running in audio mock mode (no hardware devices)"
        export RTAP_AUDIO_MOCK=true
    fi
}

# Validate configuration
validate_config() {
    log "Validating configuration..."
    
    # Check if configuration files exist
    if [ ! -f "/app/config/default.yaml" ]; then
        log "❌ Default configuration not found"
        exit 1
    fi
    
    # Determine environment
    if [ -n "$RTAP_ENVIRONMENT" ]; then
        RTAP_ENV="$RTAP_ENVIRONMENT"
    elif [ -f "/app/config/main_pc.yaml" ] && [[ "$(hostname)" == *"main"* ]]; then
        RTAP_ENV="main_pc"
    elif [ -f "/app/config/pc2.yaml" ] && [[ "$(hostname)" == *"pc2"* ]]; then
        RTAP_ENV="pc2"
    else
        RTAP_ENV="default"
    fi
    
    export RTAP_ENVIRONMENT="$RTAP_ENV"
    log "✅ Using environment: $RTAP_ENV"
    
    # Validate Python environment
    if ! python3 -c "import sys; print(f'Python {sys.version}')" 2>/dev/null; then
        log "❌ Python validation failed"
        exit 1
    fi
    
    log "✅ Configuration validation passed"
}

# Setup logging
setup_logging() {
    log "Setting up logging..."
    
    # Create log directory if it doesn't exist
    mkdir -p /app/logs
    
    # Set log file based on environment
    LOG_FILE="/app/logs/rtap-$(date +%Y%m%d).log"
    export RTAP_LOG_FILE="$LOG_FILE"
    
    log "✅ Logging configured: $LOG_FILE"
}

# Check dependencies
check_dependencies() {
    log "Checking Python dependencies..."
    
    # Test critical imports
    python3 -c "
import sys
import numpy
import asyncio
import yaml
import zmq
import psutil
print('✅ Core dependencies available')
" || {
        log "❌ Dependency check failed"
        exit 1
    }
    
    # Test RTAP modules
    python3 -c "
import sys
sys.path.insert(0, '/app')
from config.loader import UnifiedConfigLoader
from core.buffers import AudioRingBuffer
from core.pipeline import AudioPipeline
print('✅ RTAP modules importable')
" || {
        log "❌ RTAP module check failed"
        exit 1
    }
    
    log "✅ Dependency check passed"
}

# Wait for dependencies (optional)
wait_for_services() {
    if [ -n "$WAIT_FOR_SERVICES" ]; then
        log "Waiting for external services..."
        
        # Parse WAIT_FOR_SERVICES (format: host:port,host:port)
        IFS=',' read -ra SERVICES <<< "$WAIT_FOR_SERVICES"
        for service in "${SERVICES[@]}"; do
            IFS=':' read -ra SERVICE_PARTS <<< "$service"
            host="${SERVICE_PARTS[0]}"
            port="${SERVICE_PARTS[1]}"
            
            log "Waiting for $host:$port..."
            while ! nc -z "$host" "$port" 2>/dev/null; do
                sleep 1
            done
            log "✅ $host:$port is available"
        done
    fi
}

# Pre-flight checks
preflight_checks() {
    log "Running pre-flight checks..."
    
    # Check memory
    available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$available_memory" -lt 512 ]; then
        log "⚠️  Low memory available: ${available_memory}MB"
    else
        log "✅ Memory check: ${available_memory}MB available"
    fi
    
    # Check disk space
    available_disk=$(df /app | awk 'NR==2{print $4}')
    if [ "$available_disk" -lt 1048576 ]; then  # 1GB in KB
        log "⚠️  Low disk space available"
    else
        log "✅ Disk space check passed"
    fi
    
    # Check network connectivity for ZMQ ports
    log "✅ Pre-flight checks completed"
}

# Signal handling for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up..."
    
    # Kill background processes
    if [ -n "$RTAP_PID" ]; then
        log "Stopping RTAP process (PID: $RTAP_PID)"
        kill -TERM "$RTAP_PID" 2>/dev/null || true
        wait "$RTAP_PID" 2>/dev/null || true
    fi
    
    log "Cleanup completed"
    exit 0
}

# Setup signal handlers
trap cleanup SIGTERM SIGINT

# Main execution
main() {
    log "Starting RTAP initialization sequence..."
    
    # Run all checks
    check_audio
    validate_config
    setup_logging
    check_dependencies
    wait_for_services
    preflight_checks
    
    log "✅ All initialization checks passed"
    log "🚀 Starting RTAP application..."
    
    # Start the application
    exec "$@" &
    RTAP_PID=$!
    
    log "RTAP started with PID: $RTAP_PID"
    
    # Wait for the application
    wait "$RTAP_PID"
}

# Execute main function
main "$@"
