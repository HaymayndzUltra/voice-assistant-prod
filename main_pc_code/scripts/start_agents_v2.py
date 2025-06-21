import os
import sys
import time
import logging
import socket
import subprocess
import zmq
import json
import urllib.request
from pathlib import Path
from typing import List, Dict, Union, Optional, Tuple

# Configure logging
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# List of ports that use ZMQ protocol for health checks
ZMQ_PORTS = [5612, 5646, 5641, 5643, 5644, 5645, 5598, 5615, 5581, 5709, 26002]

# Define request timeout for ZMQ and other connections
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds in milliseconds

# Delay between agent launches within a batch for stability
AGENT_LAUNCH_DELAY_SECONDS = 1.0  # Configurable delay between agent launches

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'startup_v2.log')),
        logging.StreamHandler()
    ]
)

# This list defines the agents to be launched, their script paths, and their health check ports.
# Agents are launched in batches. The script will wait for all agents in a batch
# to be healthy before starting the next batch.

# Define a phased approach for agent startup
# Phase 1: Core ZMQ agents that provide basic functionality
PHASE1_AGENTS: List[Dict[str, Union[str, int]]] = [
    {"name": "CoordinatorAgent", "script": "agents/coordinator_agent.py", "port": 26002},
    {"name": "ChainOfThoughtAgent", "script": "FORMAINPC/ChainOfThoughtAgent.py", "port": 5612},
    {"name": "TinyLlamaService", "script": "FORMAINPC/TinyLlamaServiceEnhanced.py", "port": 5615},
]

# Phase 2: Add more ZMQ agents that require models
PHASE2_AGENTS: List[Dict[str, Union[str, int]]] = [
    {"name": "GOT_TOTAgent", "script": "FORMAINPC/GOT_TOTAgent.py", "port": 5646},
    {"name": "ModelManagerAgent", "script": "agents/model_manager_agent.py", "port": 5570},
]

# Phase 3: Add core services with no dependencies
PHASE3_AGENTS: List[Dict[str, Union[str, int]]] = [
    {"name": "EnhancedModelRouter", "script": "FORMAINPC/EnhancedModelRouter.py", "port": 5598},
    {"name": "NLLBAdapter", "script": "FORMAINPC/NLLBAdapter.py", "port": 5581},
]

# Phase 4: Add learning and cognitive agents
PHASE4_AGENTS: List[Dict[str, Union[str, int]]] = [
    {"name": "LearningAdjusterAgent", "script": "FORMAINPC/LearningAdjusterAgent.py", "port": 5643},
    {"name": "LocalFineTunerAgent", "script": "FORMAINPC/LocalFineTunerAgent.py", "port": 5645},
    {"name": "SelfTrainingOrchestrator", "script": "FORMAINPC/SelfTrainingOrchestrator.py", "port": 5644},
    {"name": "CognitiveModelAgent", "script": "FORMAINPC/CognitiveModelAgent.py", "port": 5641},
]

# FULL SYSTEM CONFIGURATION: All agents in batches
AGENT_BATCHES: List[List[Dict[str, str | int]]] = [
    # Batch 1: Core services with no dependencies (EnhancedModelRouter, ConsolidatedTranslator, etc. - dependencies of TaskRouter)
    [
        {"name": "CoordinatorAgent", "script": "agents/coordinator_agent.py", "port": 26002},
        {"name": "ChainOfThoughtAgent", "script": "FORMAINPC/ChainOfThoughtAgent.py", "port": 5612},
        {"name": "GOT_TOTAgent", "script": "FORMAINPC/GOT_TOTAgent.py", "port": 5646},
        {"name": "ModelManagerAgent", "script": "agents/model_manager_agent.py", "port": 5570},
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

        {"name": "TTSCache", "script": "agents/tts_cache.py", "port": 5628},
        {"name": "Executor", "script": "agents/executor.py",  "port": 5606},
        {"name": "AudioCapture", "script": "agents/streaming_audio_capture.py", "port": 6575},
        {"name": "VisionCaptureAgent", "script": "src/vision/vision_capture_agent.py", "port": 5587},
        {"name": "PredictiveHealthMonitor", "script": "agents/predictive_health_monitor.py", "port": 5613}
    ],
    # Batch 2: Services dependent on Batch 1 (TaskRouter is here)
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
        {"name": "MemoryManager", "script": "agents/memory_manager.py", "port": 5712},
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

# -------------------- TEMPORARY TEST OVERRIDE --------------------
# Launch ONLY the five Batch-1 agents we need to verify.
AGENT_BATCHES_TEST_DISABLED = [
    [
        {"name": "SelfTrainingOrchestrator", "script": "FORMAINPC/SelfTrainingOrchestrator.py", "port": 5644},
        {"name": "CognitiveModelAgent", "script": "FORMAINPC/CognitiveModelAgent.py", "port": 5641},
        {"name": "ConsolidatedTranslator", "script": "FORMAINPC/consolidated_translator.py", "port": 5563},
        {"name": "MemoryOrchestrator", "script": "src/memory/memory_orchestrator.py", "port": 5576},
        {"name": "TTSCache", "script": "agents/tts_cache.py", "port": 5628},
    ]
]
# ---------------------------------------------------------------
print('DEBUG LAUNCHER os.getcwd():', os.getcwd())
print('DEBUG LAUNCHER os.environ:', dict(os.environ))

def check_agent_health(host: str, port: int, timeout: int = 5) -> bool:
    """Checks the health of an agent by connecting to its health probe port."""
    import socket  # Explicitly import here to guarantee scope
    logging.info(f"Checking health for port {port} (type: {type(port)})")  # DEBUGGING

    # --- Custom health-check overrides for verified Batch-1 agents ---
    BASE_AGENT_MAIN_PORTS = {5570, 5590, 5628, 5606, 5598}
    SPECIAL_VISION_PORT = 5587

    def _check_zmq_custom(target_port: int, request_payload: dict) -> bool:
        """Internal helper to perform a ZMQ health request and return True/False."""
        context = zmq.Context()
        sock = context.socket(zmq.REQ)
        sock.setsockopt(zmq.LINGER, 0)
        sock.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        sock.setsockopt(zmq.SNDTIMEO, timeout * 1000)
        try:
            sock.connect(f"tcp://{host}:{target_port}")
            sock.send_json(request_payload)
            response = sock.recv_json()
            logging.debug(f"ZMQ custom health response from {host}:{target_port}: {response}")
            return response.get("status") == "ok"
        except zmq.error.Again:
            logging.warning(f"Health check TIMEOUT for ZMQ agent at {host}:{target_port}")
            return False
        except Exception as e:
            logging.warning(f"Health check ERROR for ZMQ agent at {host}:{target_port}: {e}")
            return False
        finally:
            sock.close()
            context.term()

    def _check_zmq_router(target_port: int, request_payload: dict) -> bool:
        """Internal helper to perform a ZMQ health request against a ROUTER socket (e.g. CognitiveModelAgent)."""
        context = zmq.Context()
        sock = context.socket(zmq.DEALER)
        identity = f"health_probe_{int(time.time() * 1000)}".encode()
        sock.setsockopt(zmq.IDENTITY, identity)
        sock.setsockopt(zmq.LINGER, 0)
        sock.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        sock.setsockopt(zmq.SNDTIMEO, timeout * 1000)
        try:
            sock.connect(f"tcp://{host}:{target_port}")
            payload = json.dumps(request_payload).encode()
            # Dealer -> Router pattern: include empty delimiter frame before payload
            sock.send_multipart([b'', payload])
            frames = sock.recv_multipart()
            if not frames:
                return False
            try:
                response = json.loads(frames[-1].decode())
                logging.debug(f"ZMQ ROUTER health response from {host}:{target_port}: {response}")
                return response.get("status") == "ok"
            except Exception as parse_err:
                logging.warning(f"Failed to parse health response from {host}:{target_port}: {parse_err}")
                return False
        except zmq.error.Again:
            logging.warning(f"Health check TIMEOUT for ZMQ ROUTER agent at {host}:{target_port}")
            return False
        except Exception as e:
            logging.warning(f"Health check ERROR for ZMQ ROUTER agent at {host}:{target_port}: {e}")
            return False
        finally:
            sock.close()
            context.term()

    def _check_zmq_sub(target_port: int) -> bool:
        """Subscribe to a PUB socket and wait for a health_status message."""
        context = zmq.Context()
        sock = context.socket(zmq.SUB)
        sock.setsockopt_string(zmq.SUBSCRIBE, "")
        sock.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        sock.setsockopt(zmq.LINGER, 0)
        try:
            sock.connect(f"tcp://{host}:{target_port}")
            message = sock.recv_json()
            logging.debug(f"ZMQ SUB health message from {host}:{target_port}: {message}")
            return message.get("status") in ("running", "ok")
        except zmq.error.Again:
            logging.warning(f"Health check TIMEOUT for ZMQ SUB agent at {host}:{target_port}")
            return False
        except Exception as e:
            logging.warning(f"Health check ERROR for ZMQ SUB agent at {host}:{target_port}: {e}")
            return False
        finally:
            sock.close()
            context.term()
        """Internal helper to perform a ZMQ health request against a ROUTER socket (e.g. CognitiveModelAgent)."""
        context = zmq.Context()
        sock = context.socket(zmq.DEALER)
        identity = f"health_probe_{int(time.time() * 1000)}".encode()
        sock.setsockopt(zmq.IDENTITY, identity)
        sock.setsockopt(zmq.LINGER, 0)
        sock.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        sock.setsockopt(zmq.SNDTIMEO, timeout * 1000)
        try:
            sock.connect(f"tcp://{host}:{target_port}")
            payload = json.dumps(request_payload).encode()
            # Dealer -> Router pattern: include empty delimiter frame before payload
            sock.send_multipart([b'', payload])
            frames = sock.recv_multipart()
            if not frames:
                return False
            try:
                response = json.loads(frames[-1].decode())
                logging.debug(f"ZMQ ROUTER health response from {host}:{target_port}: {response}")
                return response.get("status") == "ok"
            except Exception as parse_err:
                logging.warning(f"Failed to parse health response from {host}:{target_port}: {parse_err}")
                return False
        except zmq.error.Again:
            logging.warning(f"Health check TIMEOUT for ZMQ ROUTER agent at {host}:{target_port}")
            return False
        except Exception as e:
            logging.warning(f"Health check ERROR for ZMQ ROUTER agent at {host}:{target_port}: {e}")
            return False
        finally:
            sock.close()
            context.term()

    # VisionCaptureAgent exposes health on its main port (5587)
    if port == SPECIAL_VISION_PORT:
        return _check_zmq_custom(SPECIAL_VISION_PORT, {"action": "health_check"})

    # BaseAgent-derived agents expose health on main_port + 1
    # EnhancedModelRouter expects a different payload ("type": "health_check") on its health port (main+1)
    elif port == 5598:
        return _check_zmq_custom(port + 1, {"type": "health_check"})
    # NLLBAdapter exposes health on its main ZMQ port (5581) and expects an "health_check" action.
    elif port == 5581:
        return _check_zmq_custom(port, {"action": "health_check"})
    # LearningAdjusterAgent and LocalFineTunerAgent expose health on their main ZMQ ports (5643, 5645)
    # and expect an "health_check" action.
    elif port in (5643, 5645):
        return _check_zmq_custom(port, {"action": "health_check"})
    # ConsolidatedTranslator exposes health on a dedicated port (main_port + 1) and expects an "health_check" action.
    elif port == 5563:
        return _check_zmq_custom(port + 1, {"action": "health_check"})
    # SelfTrainingOrchestrator uses ZMQ REQ on main port
    elif port == 5644:
        return _check_zmq_custom(port, {"action": "health_check"})
    # CognitiveModelAgent uses ZMQ ROUTER socket on main port
    elif port == 5641:
        return _check_zmq_router(port, {"action": "health_check"})
    # MemoryOrchestrator uses ZMQ REP on main port
    elif port == 5576:
        return _check_zmq_custom(port, {"action": "health_check"})
    # LearningAdjusterAgent expects explicit "health_check" action on main port
    elif port == 5643:
        return _check_zmq_custom(port, {"action": "health_check"})
    # WakeWordDetector publishes health on 6579 (PUB); subscribe and wait
    elif port == 6577:
        return _check_zmq_sub(6579)
    # NLUAgent responds on its main port to 'health_check'
    elif port == 5709:
        return _check_zmq_custom(port, {"action": "health_check"})
    # TTSCache inherits BaseAgent; health check on main+1
    elif port == 5628:
        return _check_zmq_custom(port + 1, {"action": "health_check"})
    elif port in BASE_AGENT_MAIN_PORTS:
        return _check_zmq_custom(port + 1, {"action": "health"})
    
    # ZMQ Check for agents using ZMQ
    if port in ZMQ_PORTS:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)  # in milliseconds
        socket.setsockopt(zmq.SNDTIMEO, timeout * 1000)  # in milliseconds
        
        try:
            socket.connect(f"tcp://{host}:{port}")
            logging.debug(f"Sending ZMQ health check to {host}:{port}")
            
            # Special case for CoordinatorAgent which uses a different health check action
            if port == 26002:  # CoordinatorAgent port
                logging.info(f"Using 'ping' action for CoordinatorAgent health check on port {port}")
                socket.send_json({"action": "ping"})
            else:
                socket.send_json({"action": "health"})
                
            try:
                response = socket.recv_json()
                logging.debug(f"ZMQ health response from {host}:{port}: {response}")
                if response.get("status") == "ok":
                    logging.info(f"Health Check SUCCESS for ZMQ agent at {host}:{port}.")
                    return True
                else:
                    logging.warning(f"Health check for ZMQ agent at {host}:{port} returned non-OK status: {response}")
                    return False
            except zmq.error.Again:
                logging.warning(f"Health check FAILED for ZMQ agent at {host}:{port}. Reason: Response timeout. Agent may be initializing.")
                return False
            except Exception as e:
                logging.warning(f"Health check FAILED for ZMQ agent at {host}:{port}. Reason: {str(e)}")
                return False
        except Exception as e:
            logging.warning(f"Health check FAILED for ZMQ agent at {host}:{port}. Reason: {str(e)}")
            return False
        finally:
            socket.close()
            context.term()

    # HTTP health check for agents using HTTP
    elif port >= 8000 and port < 9000:
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=timeout) as response:
                if response.getcode() == 200:
                    logging.info(f"Health Check SUCCESS for HTTP agent at {host}:{port}.")
                    return True
                else:
                    logging.warning(f"Health check FAILED for HTTP agent at {host}:{port}. Status code: {response.getcode()}")
                    return False
        except (urllib.error.URLError, socket.timeout) as e:
            logging.warning(f"Health check FAILED for HTTP agent at {host}:{port}. Reason: {e}")
            return False

    # Default TCP check for all other agents
    else:
        s = None
        try:
            s = socket.create_connection((host, port), timeout=timeout)
            s.settimeout(timeout)
            response = s.recv(1024)
            if response == b"OK":
                logging.info(f"Health Check SUCCESS for agent at {host}:{port}.")
                return True
            else:
                decoded_response = response.decode(errors='ignore')
                logging.warning(f"Health check for {host}:{port} returned non-OK response. Raw: {response}, Decoded: '{decoded_response}'")
                return False
        except Exception as e:
            logging.warning(f"Health check FAILED for agent at {host}:{port}. Reason: {str(e)}")
            return False
        finally:
            if s:
                s.close()

def wait_for_agent(host: str, port: int, overall_timeout: int = 120, check_interval: int = 3, max_retries: int = 3) -> Tuple[bool, str]:
    """Waits for a single agent to become healthy with retry mechanism."""
    # Use longer timeout for specific agents that need more time to initialize
    if port in [5646, 5641, 5643, 5644, 5645, 5615, 5581, 5612, 5598, 5640, 26002]:  # These agents load ML models
        overall_timeout = 300  # 5 minutes for model-loading agents
        
    start_time = time.time()
    retries = 0
    last_error = ""
    
    while time.time() - start_time < overall_timeout:
        try:
            if check_agent_health(host, port):
                logging.info(f"Health Check SUCCESS for agent at {host}:{port}.")
                return True, "Healthy"
            
            if retries < max_retries:
                retries += 1
                logging.info(f"Health check failed for agent at {host}:{port}. Retry {retries}/{max_retries}... retrying in {check_interval}s")
                time.sleep(check_interval)
            else:
                reason = f"Max retries ({max_retries}) reached for agent at {host}:{port}"
                logging.warning(reason)
                return False, reason
                
        except Exception as e:
            logging.error(f"Error during health check for agent at {host}:{port}: {str(e)}")
            if retries < max_retries:
                retries += 1
                logging.info(f"Error occurred. Retry {retries}/{max_retries}... retrying in {check_interval}s")
                time.sleep(check_interval)
            else:
                reason = f"Max retries ({max_retries}) reached with errors for agent at {host}:{port}. Last error: {last_error}"
                logging.error(reason)
                return False, reason
    
    reason = f"Timeout waiting for agent at {host}:{port} to become healthy."
    logging.error(reason)
    return False, reason

def wait_for_batch(batch: List[Dict[str, Union[str, int]]], host: str = "localhost", timeout: int = 180, check_interval: int = 3):
    """Waits for all agents in a batch to become healthy."""
    logging.info(f"--- Waiting for Batch to become healthy ---")
    start_time = time.time()
    
    # Check health of each agent
    for agent in batch:
        port = int(agent["port"])
        
        # Individual agent health check timeout is capped at the remaining batch timeout
        remaining_timeout = max(10, int(timeout - (time.time() - start_time)))
        agent_ready = wait_for_agent(host, port, overall_timeout=remaining_timeout, check_interval=check_interval)
        
        if not agent_ready:
            logging.error(f"Agent {agent['name']} did not become healthy within timeout.")
            return False
    
    logging.info(f"All agents in batch are healthy.")
    return True

def _is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """Return True if the TCP port is already bound on the given host."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return False  # bind succeeded – port free
        except OSError:
            return True  # bind failed – port in use


def start_agent(agent_info: dict, base_dir: str) -> Optional[subprocess.Popen]:
    """Starts an agent script as a subprocess and logs its output."""
    try:
        agent_name = agent_info["name"]
        agent_port = agent_info.get("port")

        # Skip launch if port is already in use (prevents duplicate instances)
        if agent_port is not None and _is_port_in_use(agent_port):
            logging.warning(f"Port {agent_port} already in use, skipping launch of {agent_name}.")
            return None
        # Compute the project root
        project_root = os.path.abspath(os.path.join(base_dir, '..'))
        script_path = os.path.join(base_dir, agent_info["script"])
        log_dir = os.path.join(base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"{agent_name}.log")
        env = os.environ.copy()
        # Set PYTHONPATH to the project root
        env['PYTHONPATH'] = base_dir + os.pathsep + project_root + os.pathsep + env.get('PYTHONPATH', '')
        logging.info(f"PYTHONPATH for {agent_name}: {env['PYTHONPATH']}")
        logging.info(f"Script path for {agent_name}: {script_path}")
        # Convert script path to module path for -m
        rel_script = os.path.relpath(script_path, project_root)
        module_path = rel_script.replace('/', '.').replace('\\', '.').replace('.py', '')
        logging.info(f"Module path for {agent_name}: {module_path}")
        process = subprocess.Popen(
            ['python3', script_path, '--port', str(agent_info["port"])],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=project_root
        )
        logging.info(f"Starting agent: {agent_name} from directory {project_root}")
        logging.info(f"Logging to {log_file}")
        return process
    except Exception as e:
        logging.error(f"Failed to start agent {agent_info['name']}: {str(e)}")
        return None

def main():
    """Main function to start agents in batches and report all failures."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    os.chdir(base_dir)

    logging.info("--- Starting Full System Diagnostic Run ---")
    failed_agents_report: List[Dict[str, Any]] = []
    active_processes: Dict[str, subprocess.Popen] = {}

    for i, batch in enumerate(AGENT_BATCHES):
        logging.info(f"--- Processing Batch {i+1}/{len(AGENT_BATCHES)} ---")
        batch_to_check: List[Tuple[str, int, str]] = []

        # Launch agents in the batch
        for agent_config in batch:
            name = agent_config['name']
            script = agent_config['script']
            port = agent_config['port']
            
            process = start_agent(agent_config, base_dir)
            if process:
                active_processes[name] = process
                host = "localhost"
                batch_to_check.append((host, port, name))
                logging.info(f"Agent {name} launched. Waiting {AGENT_LAUNCH_DELAY_SECONDS}s...")
                time.sleep(AGENT_LAUNCH_DELAY_SECONDS)
            else:
                if _is_port_in_use(port):
                    logging.warning(f"Port {port} already in use. Skipped launching {name}.")
                    # Skipped agents are not considered failures for this diagnostic run
                    continue
                logging.error(f"Failed to launch agent {name}. Recording failure.")
                failed_agents_report.append({
                    "name": name,
                    "port": port,
                    "status": "Failed to Launch",
                    "reason": "Process returned None on start."
                })

        # Health check agents that were successfully launched in this batch
        logging.info(f"--- Health Checking Batch {i+1}/{len(AGENT_BATCHES)} ---")
        for host, port, agent_name_for_health_check in batch_to_check:
            healthy, reason = wait_for_agent(host, port)
            if not healthy:
                logging.error(f"Agent {agent_name_for_health_check} on port {port} failed health check. Reason: {reason}")
                failed_agents_report.append({
                    "name": agent_name_for_health_check,
                    "port": port,
                    "status": "Health Check Failed",
                    "reason": reason
                })
            else:
                logging.info(f"Health Check SUCCESS for {agent_name_for_health_check} (Port {port}).")

    # After processing all batches, print the summary report
    logging.info("--- Full System Diagnostic Run Finished ---")
    if failed_agents_report:
        logging.warning("--- COMPREHENSIVE SYSTEM HEALTH REPORT ---")
        logging.warning(f"Found {len(failed_agents_report)} failures:")
        # Using a basic print here for clean, copy-friendly output
        print("\n--- FAILED AGENTS SUMMARY ---")
        for report in failed_agents_report:
            print(f"- Agent: {report['name']}")
            print(f"  Port: {report['port']}")
            print(f"  Status: {report['status']}")
            print(f"  Reason: {report['reason']}")
            print("-" * 20)
        print("--- END OF SUMMARY ---\n")
        logging.warning("System startup completed with failures. Check individual logs for details.")
        # We don't terminate running agents to allow for inspection
        return 1 # Indicate that errors occurred
    else:
        logging.info("--- All agents started and passed health checks successfully. ---")
        return 0
    return 0

if __name__ == "__main__":
    sys.exit(main()) 