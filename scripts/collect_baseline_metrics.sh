#!/usr/bin/env bash
# scripts/collect_baseline_metrics.sh
# Collect baseline CPU/GPU/memory utilisation & ZMQ traffic for 24 h

set -euo pipefail

DURATION_SECONDS=${1:-86400}   # default 24 h
SAMPLE_INTERVAL=${SAMPLE_INTERVAL:-30}
OUTPUT_DIR=${OUTPUT_DIR:-baseline_metrics}
mkdir -p "$OUTPUT_DIR"

echo "Collecting docker stats every $SAMPLE_INTERVAL seconds for $DURATION_SECONDS s…"
END_TS=$(( $(date +%s) + DURATION_SECONDS ))

while [[ $(date +%s) -lt $END_TS ]]; do
  TIMESTAMP=$(date +%s)
  # Docker container stats (CPU %, mem, net, I/O)
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | tee -a "$OUTPUT_DIR/docker_stats_$TIMESTAMP.txt" | cat
  # GPU VRAM utilisation (NVIDIA only)
  nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits >> "$OUTPUT_DIR/gpu_stats_$TIMESTAMP.csv"
  # ZMQ connection counts (Linux only)
  ss -tn '( sport = :5570 or sport = :5575 or sport = :5617 or sport = :7222 )' >> "$OUTPUT_DIR/zmq_ss_$TIMESTAMP.txt" || true
  sleep "$SAMPLE_INTERVAL"
done

echo "Baseline collection complete. Results in $OUTPUT_DIR"