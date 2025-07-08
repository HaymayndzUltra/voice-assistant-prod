#!/bin/bash

# Memory Monitor Script for Docker Containers
# This script controls memory usage in containers to prevent excessive memory consumption

# Configuration
MAX_MEM_PERCENT=80       # Maximum memory percentage before cleanup
CHECK_INTERVAL=60        # Check every 60 seconds
PYTORCH_CACHE_DIR="/tmp/torch_cache"
TRANSFORMERS_CACHE_DIR="/tmp/transformers_cache"

echo "Starting container memory monitor..."
echo "Container memory limit: $MEMORY_LIMIT bytes"
echo "Max memory usage before cleanup: ${MAX_MEM_PERCENT}%"

# Create cache directories
mkdir -p $PYTORCH_CACHE_DIR
mkdir -p $TRANSFORMERS_CACHE_DIR

# Set cache directories
export PYTORCH_HOME=$PYTORCH_CACHE_DIR
export TRANSFORMERS_CACHE=$TRANSFORMERS_CACHE_DIR
export HF_HOME=$TRANSFORMERS_CACHE_DIR

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to clean memory
clean_memory() {
    log_message "Cleaning memory..."
    
    # Python memory cleanup
    if pgrep python > /dev/null; then
        log_message "Sending trim signals to Python processes"
        for pid in $(pgrep python); do
            kill -USR1 $pid 2>/dev/null || true
        done
    fi
    
    # Clear system cache
    log_message "Clearing system caches"
    sync
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    
    # Run garbage collection on Python processes
    if [ -f "/app/pc2_code/scripts/gc_collect.py" ]; then
        log_message "Running Python garbage collection"
        python /app/pc2_code/scripts/gc_collect.py
    fi
    
    # Clear PyTorch cache
    if [ -d "$PYTORCH_CACHE_DIR" ]; then
        log_message "Clearing PyTorch cache"
        find $PYTORCH_CACHE_DIR -type f -name "*.bin" -size +100M -delete
    fi
    
    # Clear Transformers cache
    if [ -d "$TRANSFORMERS_CACHE_DIR" ]; then
        log_message "Clearing Transformers cache"
        find $TRANSFORMERS_CACHE_DIR -type f -name "*.bin" -size +100M -delete
    fi
    
    # Try to compress memory
    log_message "Compressing memory"
    malloc_trim 0 2>/dev/null || true
}

# Create the garbage collection script if it doesn't exist
if [ ! -f "/app/pc2_code/scripts/gc_collect.py" ]; then
    cat > /app/pc2_code/scripts/gc_collect.py << 'EOF'
#!/usr/bin/env python3
import gc
import os
import psutil
import torch
import sys

# Force garbage collection
gc.collect()

# Clear PyTorch cache if torch is available
try:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        print("PyTorch CUDA cache cleared")
except:
    print("Failed to clear PyTorch cache")

# Get memory info
process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f"Memory usage: {memory_info.rss / (1024 * 1024):.2f} MB")

# Exit with success
sys.exit(0)
EOF
    chmod +x /app/pc2_code/scripts/gc_collect.py
fi

# Start memory monitoring in the background
(
    while true; do
        # Get current memory usage
        MEM_USED_PERCENT=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
        
        # Log memory status
        log_message "Memory usage: ${MEM_USED_PERCENT:.2f}%"
        
        # Check if memory usage exceeds threshold
        if (( $(echo "$MEM_USED_PERCENT > $MAX_MEM_PERCENT" | bc -l) )); then
            log_message "WARNING: Memory usage exceeded ${MAX_MEM_PERCENT}%"
            clean_memory
        fi
        
        # Sleep before next check
        sleep $CHECK_INTERVAL
    done
) &

# Start the main command
echo "Starting main container process..."
if [ $# -gt 0 ]; then
    exec "$@"
else
    echo "Container started. Please provide a command to run specific agents."
    tail -f /dev/null
fi 