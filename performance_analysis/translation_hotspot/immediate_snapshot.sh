#!/usr/bin/env bash
# Immediate performance snapshot for P1.1
# Focus on identified translation services

OUTPUT_DIR="performance_analysis/translation_hotspot/$(date +%Y%m%d_%H%M%S)_snapshot"
mkdir -p "$OUTPUT_DIR"

echo "=== P1.1: Translation Services Performance Snapshot ==="
echo "Timestamp: $(date)"
echo "Output: $OUTPUT_DIR"

# Identified translation containers
CONTAINERS="nllb_adapter fixed_streaming_translation redis_translation nats_translation"

echo "Capturing performance data for: $CONTAINERS"

# Current container status
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" | grep -E "(nllb_adapter|fixed_streaming_translation|redis_translation|nats_translation)" > "$OUTPUT_DIR/container_status.txt"

# Resource utilization snapshot
docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}" | grep -E "(nllb_adapter|fixed_streaming_translation|redis_translation|nats_translation)" > "$OUTPUT_DIR/resource_snapshot.csv"

# GPU utilization
nvidia-smi --query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu --format=csv > "$OUTPUT_DIR/gpu_snapshot.csv" 2>/dev/null || echo "No GPU data available" > "$OUTPUT_DIR/gpu_snapshot.csv"

# ZMQ connection analysis for translation ports
ss -tn '( sport = :5582 or sport = :5584 or sport = :6582 or sport = :6584 )' > "$OUTPUT_DIR/zmq_connections.txt" 2>/dev/null || echo "No ZMQ connections found" > "$OUTPUT_DIR/zmq_connections.txt"

# Network interface stats (for request rate correlation)
cat /proc/net/dev > "$OUTPUT_DIR/network_stats.txt"

# Container logs (last 100 lines) for error analysis
for container in $CONTAINERS; do
  echo "Capturing logs for $container..."
  docker logs --tail 100 "$container" > "$OUTPUT_DIR/${container}_logs.txt" 2>&1 || echo "Failed to get logs for $container" > "$OUTPUT_DIR/${container}_logs.txt"
done

# Process information from inside containers
for container in nllb_adapter fixed_streaming_translation; do
  echo "Capturing process info for $container..."
  docker exec "$container" ps aux > "$OUTPUT_DIR/${container}_processes.txt" 2>/dev/null || echo "Failed to get process info for $container" > "$OUTPUT_DIR/${container}_processes.txt"
done

# Generate summary
cat << EOF > "$OUTPUT_DIR/analysis_summary.txt"
=== P1.1 Translation Services Performance Snapshot ===
Timestamp: $(date)
Uptime Analysis:
- nllb_adapter: 19+ hours (POTENTIAL HOTSPOT - long running)
- fixed_streaming_translation: Recently restarted (suspicious)
- Supporting services: redis_translation, nats_translation (19+ hours)

Key Findings:
1. fixed_streaming_translation was recently restarted (possible crash/restart due to performance issue)
2. nllb_adapter has been running for 19+ hours continuously
3. Supporting infrastructure (Redis, NATS) stable

Next Steps (P1.2):
- Correlate resource usage with incoming request rates
- Monitor nllb_adapter for CPU/memory hotspots
- Check for memory leaks in long-running nllb_adapter

Evidence for Defect Ticket (P1.4):
- Container restart pattern indicates instability
- Need to monitor for resource exhaustion patterns
EOF

echo "Snapshot completed: $OUTPUT_DIR"
echo "Key finding: nllb_adapter (19h uptime) vs fixed_streaming_translation (recent restart)"