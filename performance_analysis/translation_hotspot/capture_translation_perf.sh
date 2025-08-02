#!/usr/bin/env bash
# Performance capture script for translation services
# P1.1: Capture 5-min perf/flamegraph snapshot

set -euo pipefail

DURATION_SECONDS=300  # 5 minutes
SAMPLE_INTERVAL=5     # Every 5 seconds
OUTPUT_DIR="performance_analysis/translation_hotspot/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "=== P1.1: Translation Services Performance Capture ==="
echo "Duration: ${DURATION_SECONDS}s (5 min)"
echo "Interval: ${SAMPLE_INTERVAL}s"
echo "Output: $OUTPUT_DIR"
echo "========================================================"

# Start translation services in background
echo "Starting translation services..."
cd docker/translation_services/
docker-compose up -d &
COMPOSE_PID=$!

# Wait for services to stabilize
echo "Waiting 30s for services to stabilize..."
sleep 30

# Check if translation services are running
docker ps --filter "name=*translation*" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" > "$OUTPUT_DIR/translation_containers.txt"

# Performance capture loop
echo "Starting 5-minute performance capture..."
END_TS=$(( $(date +%s) + DURATION_SECONDS ))

while [[ $(date +%s) -lt $END_TS ]]; do
  TIMESTAMP=$(date +%s)
  
  # Docker container stats for translation services
  docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}" | grep -E "(translation|nllb)" >> "$OUTPUT_DIR/translation_stats.csv" || true
  
  # GPU utilization (for translation model inference)
  nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu --format=csv,noheader >> "$OUTPUT_DIR/gpu_utilization.csv" 2>/dev/null || echo "GPU monitoring failed at $TIMESTAMP" >> "$OUTPUT_DIR/errors.log"
  
  # ZMQ connection stats for translation ports (5582, 5584, etc.)
  ss -tn '( sport = :5582 or sport = :5584 or sport = :6582 or sport = :6584 )' >> "$OUTPUT_DIR/zmq_connections_$TIMESTAMP.txt" 2>/dev/null || true
  
  # CPU flamegraph data collection (if perf is available)
  if command -v perf &> /dev/null; then
    # Collect perf data for translation container processes
    docker exec fixed_streaming_translation pidof python 2>/dev/null | head -1 | xargs -I {} perf record -g -p {} -o "$OUTPUT_DIR/perf_translation_$TIMESTAMP.data" sleep 1 2>/dev/null || true
  fi
  
  # Request rate correlation - monitor ZMQ message patterns
  netstat -i > "$OUTPUT_DIR/network_interfaces_$TIMESTAMP.txt" 2>/dev/null || true
  
  echo "Captured data at $(date)"
  sleep "$SAMPLE_INTERVAL"
done

echo "Performance capture complete. Results in $OUTPUT_DIR"

# Generate summary report
echo "=== Translation Performance Summary ===" > "$OUTPUT_DIR/summary.txt"
echo "Capture Period: $(date)" >> "$OUTPUT_DIR/summary.txt"
echo "Translation Containers Found:" >> "$OUTPUT_DIR/summary.txt"
cat "$OUTPUT_DIR/translation_containers.txt" >> "$OUTPUT_DIR/summary.txt"

# Count data points
echo "Data Points Collected:" >> "$OUTPUT_DIR/summary.txt"
echo "- Docker stats samples: $(wc -l < "$OUTPUT_DIR/translation_stats.csv" 2>/dev/null || echo 0)" >> "$OUTPUT_DIR/summary.txt"
echo "- GPU utilization samples: $(wc -l < "$OUTPUT_DIR/gpu_utilization.csv" 2>/dev/null || echo 0)" >> "$OUTPUT_DIR/summary.txt"
echo "- ZMQ connection snapshots: $(ls "$OUTPUT_DIR"/zmq_connections_*.txt 2>/dev/null | wc -l)" >> "$OUTPUT_DIR/summary.txt"

echo "Capture script completed."