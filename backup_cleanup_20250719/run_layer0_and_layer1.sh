#!/bin/bash
# Master script to launch Layer 0 and Layer 1 agents

echo "===== STARTING LAYER 0 AND LAYER 1 AGENT LAUNCH PROCESS ====="

# Step 1: Ensure a clean environment by terminating any lingering agent processes
echo "Terminating any existing agent processes..."
pkill -f "python.*agent.py" || true
sleep 2

# Step 2: Launch Layer 0 agents
echo "Launching Layer 0 agents..."
./run_layer0.sh
echo "Waiting for Layer 0 agents to stabilize..."
sleep 10

# Step 3: Launch Layer 1 agents
echo "Launching Layer 1 agents..."
chmod +x run_layer1.sh
./run_layer1.sh
echo "Waiting for Layer 1 agents to stabilize..."
sleep 20

# Step 4: Verify health of all agents
echo "Verifying health of all agents..."
python3 main_pc_code/NEWMUSTFOLLOW/check_mvs_health.py

echo "===== LAYER 0 AND LAYER 1 AGENT LAUNCH PROCESS COMPLETE =====" 