#!/usr/bin/env bash
# P1.2 & P1.3: Immediate Translation Hotspot Mitigation
# CRITICAL: fixed_streaming_translation at 121.29% CPU

set -euo pipefail

echo "=== P1.2 & P1.3: EMERGENCY TRANSLATION HOTSPOT MITIGATION ==="
echo "CRITICAL ISSUE: fixed_streaming_translation consuming 121.29% CPU"
echo "Timestamp: $(date)"

# P1.2: Correlate with incoming request rate
echo "--- P1.2: Request Rate Correlation ---"

# Monitor ZMQ message rates on translation ports
echo "Monitoring request rates on translation ports..."
for i in {1..6}; do
  echo "Sample $i/6:"
  ss -tn '( sport = :5582 or sport = :5584 or sport = :6582 or sport = :6584 )' | wc -l
  netstat -i | grep -E "(eth0|docker0)" || true
  sleep 10
done > performance_analysis/translation_hotspot/request_rate_correlation.txt

# Check container resource usage pattern
echo "Monitoring CPU pattern..."
for i in {1..5}; do
  echo "$(date): $(docker stats --no-stream --format '{{.Name}},{{.CPUPerc}}' fixed_streaming_translation)"
  sleep 5
done > performance_analysis/translation_hotspot/cpu_pattern.txt

# P1.3: Apply immediate throttle
echo "--- P1.3: Applying Immediate CPU Throttling ---"

# Method 1: Docker CPU limit (immediate safeguard)
echo "Applying CPU quota limit to fixed_streaming_translation..."
docker update --cpus="1.0" fixed_streaming_translation
echo "✅ CPU limit applied: 1.0 core max"

# Method 2: Check if autoscaling is available
echo "Checking for Docker Swarm/Kubernetes autoscaling..."
docker service ls 2>/dev/null && echo "Docker Swarm detected" || echo "No Docker Swarm"
kubectl get nodes 2>/dev/null && echo "Kubernetes detected" || echo "No Kubernetes"

# Method 3: Apply memory limit as additional safeguard  
echo "Applying memory limit as additional safeguard..."
docker update --memory="512m" fixed_streaming_translation
echo "✅ Memory limit applied: 512MB max"

# Verify throttling applied
echo "--- Verification ---"
docker inspect fixed_streaming_translation | grep -A 5 -B 5 "Cpu\|Memory" || true

# Monitor immediate effect
echo "Monitoring throttling effect..."
sleep 10
NEW_CPU=$(docker stats --no-stream --format '{{.CPUPerc}}' fixed_streaming_translation)
echo "CPU usage after throttling: $NEW_CPU"

# Create immediate alert/monitoring
echo "--- P1.3: Creating Prometheus-style Alert ---"
cat << 'EOF' > performance_analysis/translation_hotspot/prometheus_alert.yml
# Immediate monitoring alert for translation_services CPU
groups:
  - name: translation_hotspot_alerts
    rules:
      - alert: TranslationServiceHighCPU
        expr: container_cpu_usage_rate{container_name="fixed_streaming_translation"} > 0.9
        for: 5m
        labels:
          severity: critical
          service: translation_services
        annotations:
          summary: "Translation service CPU usage is critically high"
          description: "fixed_streaming_translation CPU usage is {{ $value }}% for more than 5 minutes"
          
      - alert: TranslationServiceMemoryLeak
        expr: container_memory_usage_bytes{container_name="fixed_streaming_translation"} > 500000000
        for: 10m
        labels:
          severity: warning
          service: translation_services
        annotations:
          summary: "Possible memory leak in translation service"
          description: "Memory usage trending upward: {{ $value }} bytes"
EOF

echo "✅ P1.2 & P1.3 COMPLETED"
echo "   - Request rate correlation data captured"
echo "   - CPU throttling applied (1 core limit)"
echo "   - Memory limit applied (512MB)"
echo "   - Monitoring alert created"
echo ""
echo "NEXT: P1.4 - Create defect ticket with evidence"