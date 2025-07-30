#!/usr/bin/env python3
"""
Start Agents Script for Windows
This script will start all main agent processes with proper ZMQ timeout settings
"""

import os
import sys
import subprocess
import time
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentStarter")

def main():
    print("===== STARTING AI SYSTEM AGENTS =====")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=====================================")
    
    # Set working directory to the project root
    base_dir = Path(__file__).parent.parent
    os.chdir(base_dir)
    print(f"Working directory: {os.getcwd()}")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Function to start an agent process
    def start_agent(agent_name, script_path):
        script_path = Path(script_path)
        print(f"Starting {agent_name}...")
        
        # Check if script exists
        if not script_path.exists():
            print(f"ERROR: Script not found: {script_path}")
            return None
        
        # Start the agent in the background
        try:
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            print(f"  Started {agent_name} (PID: {process.pid})")
            
            # Give a small delay between agent starts to prevent socket contention
            time.sleep(1)
            return process
        except Exception as e:
            print(f"  ERROR starting {agent_name}: {e}")
            return None
    
    print("Starting core infrastructure agents...")
    
    # Start core infrastructure agents first
    processes = []
    processes.append(start_agent("PredictiveHealthMonitor", "src/agents/predictive_health_monitor.py"))
    processes.append(start_agent("TaskRouter", "src/core/task_router.py"))
    processes.append(start_agent("ModelManager", "FORMAINPC/EnhancedModelRouter.py"))
    
    print("Waiting for core infrastructure to initialize (5 seconds)...")
    time.sleep(5)
    
    print("Starting memory system agents...")
    
    # Start memory system agents
    processes.append(start_agent("MemoryOrchestrator", "src/memory/memory_orchestrator.py"))
    processes.append(start_agent("MemoryClient", "src/memory/memory_client.py"))
    processes.append(start_agent("ContextSummarizer", "agents/core_memory/context_summarizer.py"))
    processes.append(start_agent("EpisodicMemory", "agents/_referencefolderpc2/EpisodicMemoryAgent.py"))
    
    print("Waiting for memory system to initialize (5 seconds)...")
    time.sleep(5)
    
    print("Starting model service agents...")
    
    # Start language model service agents
    processes.append(start_agent("TinyLlamaService", "FORMAINPC/TinyLlamaServiceEnhanced.py"))
    processes.append(start_agent("ChainOfThought", "FORMAINPC/ChainOfThoughtAgent.py"))
    processes.append(start_agent("GOT_TOT", "FORMAINPC/GOT_TOTAgent.py"))
    processes.append(start_agent("CognitiveModel", "FORMAINPC/CognitiveModelAgent.py"))
    
    print("Waiting for model services to initialize (5 seconds)...")
    time.sleep(5)
    
    print("Starting translator agents...")
    
    # Start translation agents
    processes.append(start_agent("NLLBAdapter", "FORMAINPC/NLLBAdapter.py"))
    processes.append(start_agent("ConsolidatedTranslator", "FORMAINPC/consolidated_translator.py"))
    processes.append(start_agent("LanguageCoordinator", "agents/language_and_translation_coordinator.py"))
    
    print("Waiting for translators to initialize (5 seconds)...")
    time.sleep(5)
    
    print("Starting cognitive agents...")
    
    # Start cognitive system agents
    processes.append(start_agent("GoalOrchestrator", "agents/GoalOrchestratorAgent.py"))
    processes.append(start_agent("DynamicIdentity", "agents/DynamicIdentityAgent.py"))
    processes.append(start_agent("MetaCognition", "agents/MetaCognitionAgent.py"))
    processes.append(start_agent("ProactiveAgent", "agents/ProactiveAgent.py"))
    processes.append(start_agent("EmpathyAgent", "agents/EmpathyAgent.py"))
    processes.append(start_agent("EmotionEngine", "agents/emotion_engine.py"))
    processes.append(start_agent("UnifiedPlanning", "agents/unified_planning_agent.py"))
    
    print("Waiting for cognitive agents to initialize (5 seconds)...")
    time.sleep(5)
    
    print("Starting I/O agents...")
    
    # Start I/O agents
    processes.append(start_agent("StreamingTTS", "agents/core_speech_output/streaming_tts_agent.py"))
    processes.append(start_agent("AudioCapture", "agents/streaming_audio_capture.py"))
    processes.append(start_agent("AdvancedCommandHandler", "agents/advanced_command_handler.py"))
    processes.append(start_agent("NLUAgent", "agents/nlu_agent.py"))
    processes.append(start_agent("Responder", "agents/responder.py"))
    processes.append(start_agent("CodeGenerator", "agents/code_generator_agent.py"))
    
    print("Waiting for I/O agents to initialize (5 seconds)...")
    time.sleep(5)
    
    print("Starting utility agents...")
    
    # Start utility agents
    processes.append(start_agent("ActiveLearningMonitor", "agents/active_learning_monitor.py"))
    processes.append(start_agent("SelfHealing", "agents/self_healing_agent.py"))
    
    print("===== ALL AGENTS STARTED =====")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("============================")
    print("Run 'python scripts/check_all_agents_health.py' to verify agent health")
    
    # Keep track of processes for potential cleanup
    successful = sum(1 for p in processes if p is not None)
    failed = sum(1 for p in processes if p is None)
    print(f"Started {successful} agents successfully, {failed} failed to start")
    
    return processes

if __name__ == "__main__":
    processes = main() 