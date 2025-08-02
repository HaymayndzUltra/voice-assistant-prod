#!/usr/bin/env bash
# Quick 5-minute performance capture for running translation services
# P1.1 completion script

set -euo pipefail

OUTPUT_DIR="performance_analysis/translation_hotspot/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "=== P1.1: Quick Translation Performance Capture ==="
echo "Output: $OUTPUT_DIR"

# Capture current translation container status
docker ps --filter "name=*translation*" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" > "$OUTPUT_DIR/translation_containers.txt"
echo "Translation containers captured"

# 5-minute performance monitoring
echo "Starting 5-minute performance monitoring..."
for i in {1..60}; do  # 60 samples at 5-second intervals = 5 minutes
  TIMESTAMP=$(date +%s)
  
  # Docker stats for translation services  
  docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}" | grep -E "(translation|nllb)" >> "$OUTPUT_DIR/translation_stats.csv" 2>/dev/null || true
  
  # GPU utilization
  nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total --format=csv,noheader >> "$OUTPUT_DIR/gpu_utilization.csv" 2>/dev/null || echo "No GPU data" >> "$OUTPUT_DIR/gpu_errors.log"
  
  # Network connections for translation ports
  ss -tn '( sport = :5582 or sport = :5584 or sport = :6582 or sport = :6584 )' > "$OUTPUT_DIR/zmq_connections_$i.txt" 2>/dev/null || true
  
  echo "Sample $i/60 at $(date)"
  sleep 5
done

echo "Performance capture completed in $OUTPUT_DIR"

# Generate summary
echo "=== Performance Capture Summary ===" > "$OUTPUT_DIR/summary.txt"
echo "Timestamp: $(date)" >> "$OUTPUT_DIR/summary.txt"
echo "Duration: 5 minutes (60 samples)" >> "$OUTPUT_DIR/summary.txt"
echo "" >> "$OUTPUT_DIR/summary.txt"

echo "Translation Containers:" >> "$OUTPUT_DIR/summary.txt"
cat "$OUTPUT_DIR/translation_containers.txt" >> "$OUTPUT_DIR/summary.txt"
echo "" >> "$OUTPUT_DIR/summary.txt"

echo "Data Collected:" >> "$OUTPUT_DIR/summary.txt"
echo "- Docker stats samples: $(wc -l < "$OUTPUT_DIR/translation_stats.csv" 2>/dev/null || echo 0)" >> "$OUTPUT_DIR/summary.txt"
echo "- GPU samples: $(wc -l < "$OUTPUT_DIR/gpu_utilization.csv" 2>/dev/null || echo 0)" >> "$OUTPUT_DIR/summary.txt"
echo "- Network snapshots: $(ls "$OUTPUT_DIR"/zmq_connections_*.txt 2>/dev/null | wc -l)" >> "$OUTPUT_DIR/summary.txt"

echo "Summary written to $OUTPUT_DIR/summary.txt"