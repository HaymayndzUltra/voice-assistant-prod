#!/bin/bash

# Create logs directory
mkdir -p logs

# Test 1: Health Monitor
echo "Testing Health Monitor..."
python3 src/core/health_monitor.py &
HEALTH_PID=$!
sleep 5
if ps -p $HEALTH_PID > /dev/null; then
    echo "✓ Health Monitor started successfully"
    kill $HEALTH_PID
else
    echo "✗ Health Monitor failed to start"
    exit 1
fi

# Test 2: Task Router
echo "Testing Task Router..."
python3 src/core/task_router.py &
ROUTER_PID=$!
sleep 5
if ps -p $ROUTER_PID > /dev/null; then
    echo "✓ Task Router started successfully"
    kill $ROUTER_PID
else
    echo "✗ Task Router failed to start"
    exit 1
fi

# Test 3: Proactive Context Monitor
echo "Testing Proactive Context Monitor..."
python3 src/core/proactive_context_monitor.py &
MONITOR_PID=$!
sleep 5
if ps -p $MONITOR_PID > /dev/null; then
    echo "✓ Proactive Context Monitor started successfully"
    kill $MONITOR_PID
else
    echo "✗ Proactive Context Monitor failed to start"
    exit 1
fi

echo "All tests passed successfully!" 