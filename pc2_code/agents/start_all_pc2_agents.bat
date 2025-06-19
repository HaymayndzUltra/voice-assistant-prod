@echo off
setlocal enabledelayedexpansion

REM Set environment variables for host and port configuration
set ENHANCED_MODEL_ROUTER_HOST=0.0.0.0
set ENHANCED_MODEL_ROUTER_PORT=5601
set DREAM_WORLD_HOST=0.0.0.0
set DREAM_WORLD_PORT=5599
set COGNITIVE_MODEL_HOST=0.0.0.0
set COGNITIVE_MODEL_PORT=5600
set UNIFIED_MEMORY_HOST=0.0.0.0
set UNIFIED_MEMORY_PORT=5602
set TUTOR_HOST=0.0.0.0
set TUTOR_PORT=5603
set TUTORING_SERVICE_HOST=0.0.0.0
set TUTORING_SERVICE_PORT=5604

REM Start Enhanced Model Router
start "Enhanced Model Router" python enhanced_model_router.py
echo Started Enhanced Model Router

REM Start Dream World Agent
start "Dream World Agent" python DreamWorldAgent.py
echo Started Dream World Agent

REM Start Cognitive Model Agent
start "Cognitive Model Agent" python CognitiveModelAgent.py
echo Started Cognitive Model Agent

REM Start Unified Memory Reasoning Agent
start "Unified Memory Reasoning Agent" python UnifiedMemoryReasoningAgent.py
echo Started Unified Memory Reasoning Agent

REM Start Tutor Agent
start "Tutor Agent" python tutor_agent.py
echo Started Tutor Agent

REM Start Tutoring Service Agent
start "Tutoring Service Agent" python tutoring_service_agent.py
echo Started Tutoring Service Agent

echo All PC2 agents started successfully
