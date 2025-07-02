#!/bin/bash

# Exit on error
set -e

echo "Starting AI System..."

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory if it doesn't exist
mkdir -p logs

# Kill any zombie Python processes
echo "Killing any existing Python processes..."
pkill -f python || true

# Set PYTHONPATH to include project root and key directories
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/../:$PYTHONPATH"
echo "PYTHONPATH set to: $PYTHONPATH"

# Create symlinks for backward compatibility
echo "Creating symlinks for backward compatibility..."
ln -sf "$SCRIPT_DIR/utils" ../utils 2>/dev/null || true
ln -sf "$SCRIPT_DIR/src" ../src 2>/dev/null || true
ln -sf "$SCRIPT_DIR/config" ../config 2>/dev/null || true

# Install required packages if missing
echo "Checking for required packages..."
pip3 install zmq pyyaml psutil 2>/dev/null || true

# Fix syntax error in unified_planning_agent.py if it exists
if grep -q "f\"tcp://{_agent_args.host}:\"){" agents/unified_planning_agent.py 2>/dev/null; then
    echo "Fixing syntax error in unified_planning_agent.py..."
    sed -i 's/f"tcp:\/\/{_agent_args.host}:"){/f"tcp:\/\/{_agent_args.host}:{/' agents/unified_planning_agent.py
fi

# Run the fixed startup script
echo "Running fixed startup script..."
python3 fixed_start_ai_system.py

echo "AI System startup complete!" 