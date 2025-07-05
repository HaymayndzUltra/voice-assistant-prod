#!/bin/bash
# =================================================================
# run_layer0_and_1.sh - Intelligent Layer 0 and Layer 1 Launch Script
# =================================================================
# This script launches Layer 0 agents using our improved startup script,
# then launches Layer 1 agents (those that depend only on Layer 0 agents).
# It includes proper cleanup, health checks, and path resolution.
# =================================================================

# Set up error handling, but ignore errors from cleanup_agents.py
set -e
trap 'if [[ $BASH_COMMAND != *"cleanup_agents.py"* ]]; then echo "Error on line $LINENO: $BASH_COMMAND. Exiting."; exit 1; fi' ERR

# Ensure we're in the project root
cd "$(dirname "$0")"

# Create necessary directories
mkdir -p logs
mkdir -p temp

# Set environment variables
export PYTHONPATH=$(pwd)
export ENV_TYPE=development
export NETWORK_CONFIG_PATH=$(pwd)/config/network_config.yaml
export FORCE_LOCAL_MODE=true
export PROJECT_ROOT=$(pwd)

echo "====================================================================="
echo "LAUNCHING LAYER 0 AND LAYER 1 AGENTS"
echo "====================================================================="

# Step 1: Clean up any existing processes
echo "Step 1: Cleaning up existing processes..."
python3 cleanup_agents.py --force || true
echo "Cleanup complete."
echo

# Step 2: Launch Layer 0 agents using improved startup script
echo "Step 2: Launching Layer 0 agents..."
python3 improved_layer0_startup.py --config main_pc_code/NEWMUSTFOLLOW/minimal_system_config_local.yaml
echo "Layer 0 agents launched."
echo

# Step 3: Allow Layer 0 to stabilize
echo "Step 3: Allowing Layer 0 agents to stabilize (15 seconds)..."
sleep 15
echo "Stabilization period complete."
echo

# Step 4: Launch Layer 1 agents
echo "Step 4: Launching Layer 1 agents..."

# PredictiveHealthMonitor - depends on SystemDigitalTwin
echo "  - Starting PredictiveHealthMonitor..."
python3 main_pc_code/src/agents/predictive_health_monitor.py --port 5613 --health-port 5614 &
sleep 2

# StreamingTTSAgent - depends on CoordinatorAgent, ModelManagerAgent
echo "  - Starting StreamingTTSAgent..."
python3 main_pc_code/agents/core_speech_output/streaming_tts_agent.py --port 5562 --health-port 5563 &
sleep 2

# SessionMemoryAgent - depends on CoordinatorAgent
echo "  - Starting SessionMemoryAgent..."
python3 main_pc_code/agents/session_memory_agent.py --port 5574 --health-port 5575 &
sleep 2

# TinyLlamaService - depends on ModelManagerAgent
echo "  - Starting TinyLlamaService..."
python3 main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py --port 5615 --health-port 5616 &
sleep 2

# NLLBAdapter - depends on ModelManagerAgent
echo "  - Starting NLLBAdapter..."
python3 main_pc_code/FORMAINPC/NLLBAdapter.py --port 5581 --health-port 5582 &
sleep 2

# EnhancedModelRouter - depends on ModelManagerAgent, ChainOfThoughtAgent
echo "  - Starting EnhancedModelRouter..."
python3 main_pc_code/FORMAINPC/EnhancedModelRouter.py --port 5598 --health-port 5599 &
sleep 2

# CognitiveModelAgent - depends on ChainOfThoughtAgent
echo "  - Starting CognitiveModelAgent..."
python3 main_pc_code/FORMAINPC/CognitiveModelAgent.py --port 5641 --health-port 5642 &
sleep 2

# EmotionSynthesisAgent - depends on CoordinatorAgent, ModelManagerAgent
echo "  - Starting EmotionSynthesisAgent..."
python3 main_pc_code/agents/emotion_synthesis_agent.py --port 5706 --health-port 5707 &
sleep 2

echo "All Layer 1 agents launched."
echo

# Step 5: Final stabilization period
echo "Step 5: Final stabilization period (20 seconds)..."
sleep 20
echo "Final stabilization complete."
echo

# Step 6: Full health check
echo "Step 6: Performing full health check of all agents..."
python3 check_all_agents_health.py --timeout 10

echo
echo "====================================================================="
echo "LAYER 0 AND LAYER 1 STARTUP COMPLETE"
echo "====================================================================="

# Keep the script running to maintain background processes
echo "Press Ctrl+C to terminate all agents and exit"
wait 