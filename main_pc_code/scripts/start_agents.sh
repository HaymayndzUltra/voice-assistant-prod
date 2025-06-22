#!/bin/bash
# Start agents script for AI System
# This script will start all main agent processes with proper ZMQ timeout settings

echo "===== STARTING AI SYSTEM AGENTS ====="
echo "$(date)"
echo "====================================="

# Set working directory to the project root
cd "$(dirname "$0")/.."
BASE_DIR="$(pwd)"
echo "Working directory: $BASE_DIR"

# Function to start an agent process
start_agent() {
    agent_name="$1"
    script_path="$2"
    
    echo "Starting $agent_name..."
    
    # Check if script exists
    if [ ! -f "$script_path" ]; then
        echo "ERROR: Script not found: $script_path"
        return 1
    fi
    
    # Start the agent in the background
    python "$script_path" &
    
    # Get process ID
    pid=$!
    echo "  Started $agent_name (PID: $pid)"
    
    # Give a small delay between agent starts to prevent socket contention
    sleep 1
}

# Create logs directory if it doesn't exist
mkdir -p logs

echo "Starting core infrastructure agents..."

# Start core infrastructure agents first
start_agent "PredictiveHealthMonitor" "src/agents/predictive_health_monitor.py"
start_agent "TaskRouter" "src/core/task_router.py"
start_agent "ModelManager" "FORMAINPC/EnhancedModelRouter.py"

echo "Waiting for core infrastructure to initialize (5 seconds)..."
sleep 5

echo "Starting memory system agents..."

# Start memory system agents
start_agent "MemoryOrchestrator" "src/memory/memory_orchestrator.py"
start_agent "MemoryClient" "src/memory/memory_client.py"
start_agent "ContextSummarizer" "agents/core_memory/context_summarizer.py"
start_agent "EpisodicMemory" "agents/_referencefolderpc2/EpisodicMemoryAgent.py"

echo "Waiting for memory system to initialize (5 seconds)..."
sleep 5

echo "Starting model service agents..."

# Start language model service agents
start_agent "TinyLlamaService" "FORMAINPC/TinyLlamaServiceEnhanced.py"
start_agent "ChainOfThought" "FORMAINPC/ChainOfThoughtAgent.py"
start_agent "GOT_TOT" "FORMAINPC/GOT_TOTAgent.py"
start_agent "CognitiveModel" "FORMAINPC/CognitiveModelAgent.py"

echo "Waiting for model services to initialize (5 seconds)..."
sleep 5

echo "Starting translator agents..."

# Start translation agents
start_agent "NLLBAdapter" "FORMAINPC/NLLBAdapter.py"
start_agent "ConsolidatedTranslator" "FORMAINPC/consolidated_translator.py"
start_agent "LanguageCoordinator" "agents/language_and_translation_coordinator.py"

echo "Waiting for translators to initialize (5 seconds)..."
sleep 5

echo "Starting cognitive agents..."

# Start cognitive system agents
start_agent "GoalOrchestrator" "agents/GoalOrchestratorAgent.py"
start_agent "DynamicIdentity" "agents/DynamicIdentityAgent.py"
start_agent "MetaCognition" "agents/MetaCognitionAgent.py"
start_agent "ProactiveAgent" "agents/ProactiveAgent.py"
start_agent "EmpathyAgent" "agents/EmpathyAgent.py"
start_agent "EmotionEngine" "agents/emotion_engine.py"
start_agent "UnifiedPlanning" "agents/unified_planning_agent.py"

echo "Waiting for cognitive agents to initialize (5 seconds)..."
sleep 5

echo "Starting I/O agents..."

# Start I/O agents
start_agent "StreamingTTS" "agents/core_speech_output/streaming_tts_agent.py"
start_agent "AudioCapture" "agents/streaming_audio_capture.py"
start_agent "AdvancedCommandHandler" "agents/advanced_command_handler.py"
start_agent "NLUAgent" "agents/nlu_agent.py"
start_agent "Responder" "agents/responder.py"
start_agent "CodeGenerator" "agents/code_generator_agent.py"

echo "Waiting for I/O agents to initialize (5 seconds)..."
sleep 5

echo "Starting utility agents..."

# Start utility agents
start_agent "ActiveLearningMonitor" "agents/active_learning_monitor.py"
start_agent "SelfHealing" "agents/self_healing_agent.py"

echo "===== ALL AGENTS STARTED ====="
echo "$(date)"
echo "============================"
echo "Run 'python scripts/check_all_agents_health.py' to verify agent health" 