#!/bin/bash
echo "=== DOCKER DEPLOYMENT STATUS ==="
echo ""
echo "📦 Running Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || echo "Docker not accessible"
echo ""
echo "📊 Container Count: $(docker ps -q 2>/dev/null | wc -l)"
echo ""
echo "🔍 Consolidated Hubs Status:"
for hub in unified_observability_center real_time_audio_pipeline model_ops_coordinator memory_fusion_hub affective_processing_center; do
    if docker ps | grep -q $hub 2>/dev/null; then
        echo "✅ $hub - RUNNING"
    else
        echo "❌ $hub - NOT FOUND"
    fi
done
echo ""
echo "📋 Individual Agents Still Running:"
docker ps --format "{{.Names}}" 2>/dev/null | grep -i agent | grep -v -E "observability|pipeline|coordinator|fusion|affective" || echo "None or Docker not accessible"
