#!/bin/bash
# Run script for Layer 1 agents (those that depend only on Layer 0 agents)

# Set environment variables
export PYTHONPATH=$(pwd)
export ENV_TYPE=development
export NETWORK_CONFIG_PATH=$(pwd)/config/network_config.yaml
export FORCE_LOCAL_MODE=true

# Create log directories if they don't exist
mkdir -p logs

echo "Launching Layer 1 agents..."

# Launch each Layer 1 agent in the background
echo "Starting PredictiveHealthMonitor..."
python3 main_pc_code/src/agents/predictive_health_monitor.py --port 5613 &

echo "Starting StreamingTTSAgent..."
python3 main_pc_code/agents/core_speech_output/streaming_tts_agent.py --port 5562 &

echo "Starting SessionMemoryAgent..."
python3 main_pc_code/agents/session_memory_agent.py --port 5574 &

echo "Starting TinyLlamaService..."
python3 main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py --port 5615 &

echo "Starting NLLBAdapter..."
python3 main_pc_code/FORMAINPC/NLLBAdapter.py --port 5581 &

echo "Starting EnhancedModelRouter..."
python3 main_pc_code/FORMAINPC/EnhancedModelRouter.py --port 5598 &

echo "Starting CognitiveModelAgent..."
python3 main_pc_code/FORMAINPC/CognitiveModelAgent.py --port 5641 &

echo "Starting EmotionSynthesisAgent..."
python3 main_pc_code/agents/emotion_synthesis_agent.py --port 5706 &

echo "Starting CodeGenerator..."
python3 main_pc_code/agents/code_generator_agent.py --port 5604 &

echo "Starting VisionCaptureAgent..."
python3 main_pc_code/src/vision/vision_capture_agent.py --port 5592 &

echo "All Layer 1 agents launched. Waiting for them to initialize..."
sleep 20

echo "Layer 1 agents should now be initialized."