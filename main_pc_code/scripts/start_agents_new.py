import subprocess
import sys
import time
import socket
import os
import logging
from typing import List, Dict, Tuple, Optional
import urllib.request
import urllib.error
from common.utils.log_setup import configure_logging
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager

# Configure logging
LOGS_DIR = PathManager.join_path("logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logger = configure_logging(__name__)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, str(PathManager.get_logs_dir() / "startup.log"))),
        logging.StreamHandler()
    ]
)

# --- USER CONFIGURATION: PLEASE POPULATE THIS SECTION ---

# This list defines the agents to be launched, their script paths, and their health check ports.
# The script path should be relative to the `main_pc_code` directory.
# The health check port is the port the agent's health probe listens on.
#
# Agents are launched in batches. The script will wait for all agents in a batch
# to be healthy before starting the next batch.

AGENT_BATCHES: List[List[Dict[str, str | int]]] = [
    # Batch 1: Core services with no dependencies
    [
        {"name": "ChainOfThoughtAgent", "script": "FORMAINPC/ChainOfThoughtAgent.py", "port": 5612},
        {"name": "GOT_TOTAgent", "script": "FORMAINPC/GOT_TOTAgent.py", "port": 5646},
        {"name": "ModelManagerAgent", "script": "agents/model_manager_agent.py", "port": 5570},
        {"name": "CoordinatorAgent", "script": "agents/coordinator_agent.py", "port": 26002},
        {"name": "EnhancedModelRouter", "script": "FORMAINPC/EnhancedModelRouter.py", "port": 5598},
        {"name": "TinyLlamaService", "script": "FORMAINPC/TinyLlamaServiceEnhanced.py", "port": 5615},
        {"name": "NLLBAdapter", "script": "FORMAINPC/NLLBAdapter.py", "port": 5581},
        {"name": "LearningAdjusterAgent", "script": "FORMAINPC/LearningAdjusterAgent.py", "port": 5643},
        {"name": "LocalFineTunerAgent", "script": "FORMAINPC/LocalFineTunerAgent.py", "port": 5645},
        {"name": "SelfTrainingOrchestrator", "script": "FORMAINPC/SelfTrainingOrchestrator.py", "port": 5644},
        {"name": "CognitiveModelAgent", "script": "FORMAINPC/CognitiveModelAgent.py", "port": 5641},
        {"name": "ConsolidatedTranslator", "script": "FORMAINPC/consolidated_translator.py", "port": 5563},
        {"name": "EmotionEngine", "script": "agents/emotion_engine.py", "port": 5590},
        {"name": "MemoryOrchestrator", "script": "src/memory/memory_orchestrator.py", "port": 5576},
        {"name": "MemoryClient", "script": "src/memory/memory_client.py", "port": 5577},
        {"name": "TTSCache", "script": "agents/tts_cache.py", "port": 5628},
        {"name": "Executor", "script": "agents/executor.py", "port": 5606},
        {"name": "AudioCapture", "script": "agents/streaming_audio_capture.py", "port": 6575},
        {"name": "VisionCaptureAgent", "script": "src/vision/vision_capture_agent.py", "port": 5592},
        {"name": "PredictiveHealthMonitor", "script": "agents/predictive_health_monitor.py", "port": 5613}
    ],
    # Batch 2: Services dependent on Batch 1
    [
        {"name": "TaskRouter", "script": "src/core/task_router.py", "port": 8571},
        {"name": "GoalOrchestratorAgent", "script": "agents/GoalOrchestratorAgent.py", "port": 7001},
        {"name": "IntentionValidatorAgent", "script": "agents/IntentionValidatorAgent.py", "port": 5701},
        {"name": "DynamicIdentityAgent", "script": "agents/DynamicIdentityAgent.py", "port": 5802},
        {"name": "EmpathyAgent", "script": "agents/EmpathyAgent.py", "port": 5703},
        {"name": "ProactiveAgent", "script": "agents/ProactiveAgent.py", "port": 5624},
        {"name": "PredictiveLoader", "script": "agents/predictive_loader.py", "port": 5617},
        {"name": "MoodTrackerAgent", "script": "agents/mood_tracker_agent.py", "port": 5704},
        {"name": "HumanAwarenessAgent", "script": "agents/human_awareness_agent.py", "port": 5705},
        {"name": "EmotionSynthesisAgent", "script": "agents/emotion_synthesis_agent.py", "port": 5706},
        {"name": "ToneDetector", "script": "agents/tone_detector.py", "port": 5625},
        {"name": "VoiceProfiler", "script": "agents/voice_profiling_agent.py", "port": 5708},
        {"name": "SessionMemoryAgent", "script": "agents/session_memory_agent.py", "port": 5572},
        {"name": "UnifiedMemoryReasoningAgent", "script": "agents/_referencefolderpc2/UnifiedMemoryReasoningAgent.py", "port": 5596},
        {"name": "CodeGenerator", "script": "agents/code_generator_agent.py", "port": 5604},
        {"name": "TTSConnector", "script": "agents/tts_connector.py", "port": 5582},
        {"name": "StreamingTTSAgent", "script": "agents/streaming_tts_agent.py", "port": 5562},
        {"name": "FusedAudioPreprocessor", "script": "src/audio/fused_audio_preprocessor.py", "port": 6578},
        {"name": "LanguageAndTranslationCoordinator", "script": "agents/language_and_translation_coordinator.py", "port": 6581},
        {"name": "FaceRecognitionAgent", "script": "agents/face_recognition_agent.py", "port": 5610},
        {"name": "StreamingSpeechRecognition", "script": "agents/streaming_speech_recognition.py", "port": 6580}
    ],
    # Batch 3: Services dependent on Batch 2
    [
        {"name": "MemoryClient", "script": "agents/memory_client.py", "port": 5713},
        {"name": "EpisodicMemoryAgent", "script": "agents/_referencefolderpc2/EpisodicMemoryAgent.py", "port": 5597},
        {"name": "WakeWordDetector", "script": "agents/wake_word_detector.py", "port": 6577},
        {"name": "NLUAgent", "script": "agents/nlu_agent.py", "port": 5709}
    ],
    # Batch 4: Services dependent on Batch 3
    [
        {"name": "LearningManager", "script": "agents/learning_manager.py", "port": 5579},
        {"name": "KnowledgeBase", "script": "agents/knowledge_base.py", "port": 5578},
        {"name": "AdvancedCommandHandler", "script": "agents/advanced_command_handler.py", "port": 5710},
        {"name": "ChitchatAgent", "script": "agents/chitchat_agent.py", "port": 5711},
        {"name": "FeedbackHandler", "script": "agents/feedback_handler.py", "port": 5636},
        {"name": "Responder", "script": "agents/responder.py", "port": 5637}
    ],
    # Batch 5: Services dependent on Batch 4
    [
        {"name": "MetaCognitionAgent", "script": "agents/MetaCognitionAgent.py", "port": 5630},
        {"name": "ActiveLearningMonitor", "script": "agents/active_learning_monitor.py", "port": 5638},
        {"name": "UnifiedPlanningAgent", "script": "agents/unified_planning_agent.py", "port": 5634}
    ],
    # Batch 6: Services dependent on Batch 5
    [
        {"name": "MultiAgentSwarmManager", "script": "agents/MultiAgentSwarmManager.py", "port": 5639},
        {"name": "UnifiedSystemAgent", "script": "agents/unified_system_agent.py", "port": 5640}
    ]
]

# --- END OF USER CONFIGURATION ---


def check_agent_health(host: str, port: int, timeout: int = 5) -> bool:
    """Checks the health of an agent by connecting to its health probe port."""
    # Special case for TaskRouter which uses an HTTP health check
    if port == 8571:
        try:
            # We assume the health endpoint is at the root path '/'
            with urllib.request.urlopen(f"http://{host}:{port}/", timeout=timeout) as response:
                if response.status == 200:
                    logging.info(f"Health check PASSED for HTTP agent at {host}:{port}.")
                    return True
                else:
                    logging.warning(
                        f"Health check for HTTP agent at {host}:{port} returned status {response.status}."
                    )
                    return False
        except (urllib.error.URLError, socket.timeout) as e:
            logging.warning(f"Health check FAILED for HTTP agent at {host}:{port}. Reason: {e}")
            return False

    # Default TCP check for all other agents
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            response = sock.recv(1024)
            if response == b"OK":
                logging.info(f"Health check PASSED for agent at {host}:{port}.")
                return True
            else:
                decoded_response = response.decode(errors='ignore')
                logging.warning(
                    f"Health check for {host}:{port} returned non-OK response. "
                    f"Raw: {response!r}, Decoded: '{decoded_response}'. Agent might be initializing."
                )
                return False
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        logging.warning(f"Health check FAILED for agent at {host}:{port}. Reason: {e}")
        return False


def start_agent(agent_name: str, script_path: str) -> Optional[subprocess.Popen]:
    """Starts an agent script as a subprocess and logs its output."""
    log_file_path = os.path.join(LOGS_DIR, fstr(PathManager.get_logs_dir() / "{agent_name}.log"))
    
    # Use absolute path for the script
    abs_script_path = os.path.join(get_main_pc_code(), script_path)

    if not os.path.exists(abs_script_path):
        logging.error(f"Agent script not found at: {abs_script_path}. Cannot start {agent_name}.")
        return None

    logging.info(f"Starting agent: {agent_name}. Logging to {log_file_path}")
    
    with open(log_file_path, 'wb') as log_file:
        process = subprocess.Popen(
            ['python', '-u', abs_script_path],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
    return process


def wait_for_agent(host: str, port: int, overall_timeout: int = 120, check_interval: int = 3):
    """Waits for a single agent to become healthy."""
    start_time = time.time()
    while time.time() - start_time < overall_timeout:
        if check_agent_health(host, port):
            logging.info(f"Agent at {host}:{port} is ready.")
            return True
        logging.info(f"Waiting for agent at {host}:{port} to be ready... retrying in {check_interval}s")
        time.sleep(check_interval)
    logging.error(f"Timeout! Agent at {host}:{port} did not become ready within {overall_timeout} seconds.")
    return False


def main():
    """
    Main function to start all agents in batches.
    """
    logging.info("--- Starting AI System Agents ---")
    launched_processes: Dict[str, subprocess.Popen] = {}

    for i, batch in enumerate(AGENT_BATCHES):
        logging.info(f"--- Starting Batch {i+1}/{len(AGENT_BATCHES)} ---")
        
        batch_to_check: List[Tuple[str, int]] = []

        for agent_config in batch:
            name = str(agent_config["name"])
            script = str(agent_config["script"])
            port = int(agent_config["port"])

            process = start_agent(name, script)
            if process:
                launched_processes[name] = process
                batch_to_check.append(("localhost", port))
            else:
                logging.error(f"Failed to start {name}. Aborting startup.")
                # Terminate already launched processes if a critical one fails
                for proc in launched_processes.values():
                    proc.terminate()
                return

        logging.info(f"--- Waiting for Batch {i+1} to become healthy ---")
        all_healthy = True
        for host, port in batch_to_check:
            if not wait_for_agent(host, port):
                logging.error(f"Agent at {host}:{port} failed to become healthy. Aborting startup.")
                all_healthy = False
                break
        
        if not all_healthy:
            # Terminate all launched processes if a batch fails health checks
            for proc in launched_processes.values():
                proc.terminate()
            logging.critical("Agent startup aborted due to health check failures.")
            return
            
        logging.info(f"--- Batch {i+1} is healthy ---")

    logging.info("--- All agents started successfully! ---")
    
    # Keep the script running to monitor processes, or just exit
    # For now, we exit, assuming agents run independently.
    # To keep this script alive as a monitor, you could add:
    # while True: time.sleep(10)


if __name__ == "__main__":
    main() 