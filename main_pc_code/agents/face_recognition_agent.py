from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from common.utils.path_manager import PathManager
import os
import time
import json
import logging
import traceback
import threading
# from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory (commented out for PC1)
from pathlib import Path


# Import path manager for containerization-friendly paths
import os
from pathlib import Path
from common.utils.path_manager import PathManager

# Removed # Add the parent directory to sys.path to import the config module
# from main_pc_code.config.system_config import CONFIG as SYS_CONFIG
from common.env_helpers import get_env

import cv2
import numpy as np
import insightface
from common.pools.zmq_pool import get_rep_socket
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from filterpy.kalman import KalmanFilter
import torch
import onnxruntime as ort
from main_pc_code.utils.env_loader import get_env
import psutil
from main_pc_code.agents.error_publisher import ErrorPublisher

# Load configuration at module level

# Add the project's main_pc_code directory to the Python path
import os
from pathlib import Path
from common.utils.env_standardizer import get_env
MAIN_PC_CODE_DIR = PathManager.get_main_pc_code()

# Removed 
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Load configuration
try:
    with open(str(Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "face_recognition_config.json"), "r") as f:
        CONFIG = json.load(f)["face_recognition"]
except FileNotFoundError:
    # Fallback configuration if file doesn't exist
    CONFIG = {
        "model": {
            "name": "buffalo_l",
            "root": "~/.insightface",
            "providers": ["CUDAExecutionProvider", "CPUExecutionProvider"],
            "ctx_id": 0,
            "quantization": {"enabled": False}
        },
        "emotion_model": {
            "path": str(PathManager.get_models_dir() / "emotion_model.onnx")
        }
    }
    print("Warning: face_recognition_config.json not found, using defaults")

# Configure logging using canonical approach
from common.utils.log_setup import configure_logging
logger = configure_logging(__name__, log_to_file=True)

# Define ZMQ_PORT from system configuration
ZMQ_PORT = 5560  # Fallback port since SYS_CONFIG is commented out
# ZMQ_PORT = SYS_CONFIG.get("main_pc_settings", {}).get("zmq_ports", {}).get("face_recognition_port", 5560)

@dataclass
class EmotionState:
    """Represents the emotional state of a person"""
    primary_emotion: str
    secondary_emotion: Optional[str] = None
    intensity: float = 1.0
    confidence: float = 1.0
    timestamp: float = 0.0
    voice_emotion: Optional[Dict[str, float]] = None

@dataclass
class PrivacyZone:
    """Defines a privacy zone in the frame"""
    x1: int
    y1: int
    x2: int
    y2: int
    blur_level: int = 25
    enabled: bool = True

class KalmanTracker(object):
    """Kalman filter-based tracker for smooth face tracking Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    def __init__(self, measurement_noise=0.1, process_noise=0.01):
        self.kf = KalmanFilter(dim_x=4, dim_z=2)  # x, y, dx, dy
        self.kf.F = np.array([[1, 0, 1, 0],
                             [0, 1, 0, 1],
                             [0, 0, 1, 0],
                             [0, 0, 0, 1]])
        self.kf.H = np.array([[1, 0, 0, 0],
                             [0, 1, 0, 0]])
        self.kf.R *= measurement_noise
        self.kf.Q *= process_noise
        self.kf.P *= 1000
        self.kf.x = np.zeros(4)
        self.last_update = time.time()

    def update(self, bbox: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Update tracker with new bbox"""
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        self.kf.predict()
        self.kf.update(np.array([center_x, center_y]))
        self.last_update = time.time()
        return self.get_bbox(bbox[2] - bbox[0], bbox[3] - bbox[1])

    def get_bbox(self, width: int, height: int) -> Tuple[int, int, int, int]:
        """Get bbox from current state"""
        x = self.kf.x[0] - width/2
        y = self.kf.x[1] - height/2
        return (int(x), int(y), int(x + width), int(y + height))

class EmotionAnalyzer(BaseAgent):
    """Advanced emotion analysis with multi-label support and temporal tracking"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FaceRecognitionAgent")

        self.port = port

        self.running = True

        self.tracked_persons = {}

        self.known_faces = {}

        self.emotion_history = {}

        self.privacy_zones = []

        self.initialization_status = {

            "is_initialized": False,

            "error": None,

            "progress": 0.0,

            "components": {

                "zmq": False,

                "face_detector": False,

                "face_recognizer": False,

                "emotion_analyzer": False,

                "liveness_detector": False

            }

        }

        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)

        self.init_thread.start()

        logging.info("FaceRecognitionAgent basic init complete, async init started")
        self.config = config
        self.emotion_model = self._load_emotion_model()
        self.voice_model = self._load_voice_model() if config.get("voice_integration")["enabled"] else None
        self.emotion_history: Dict[int, List[EmotionState]] = {}
        self.voice_buffer = []
        self.voice_thread = None
        if self.voice_model:
            self._start_voice_processing()

    def _load_emotion_model(self) -> Any:
        """Load emotion recognition model"""
        try:
            return ort.InferenceSession(self.config.get("model_path"))
        except Exception as e:
            logging.error(f"Error loading emotion model: {e}")
            return None

    def _load_voice_model(self) -> Any:
        """Load voice emotion recognition model"""
        # TODO: Implement voice model loading
        return None

    def _start_voice_processing(self):
        """Start voice processing thread"""
        def process_voice():
            while True:
                if len(self.voice_buffer) > 0:
                    self.voice_buffer.pop(0)
                    # TODO: Process audio and update emotion state
                time.sleep(0.1)
        self.voice_thread = threading.Thread(target=process_voice, daemon=True)
        self.voice_thread.start()

    def analyze_emotion(self, face_img: np.ndarray, track_id: int) -> EmotionState:
        """Analyze emotion from face image with multi-label support"""
        if not self.emotion_model:
            return EmotionState("Unknown", confidence=0.0)

        # Prepare image
        face_img = cv2.resize(face_img, (64, 64))
        face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        face_img = np.expand_dims(face_img, axis=(0, -1))
        face_img = face_img.astype(np.float32) / 255.0

        # Get emotion predictions
        outputs = self.emotion_model.run(None, {'input': face_img})
        probs = outputs[0][0]
        
        # Get top emotions
        top_indices = np.argsort(probs)[-2:][::-1]
        primary_emotion = self.config.get("labels")[top_indices[0]]
        secondary_emotion = self.config.get("labels")[top_indices[1]] if probs[top_indices[1]] > 0.3 else None
        
        # Calculate intensity
        intensity = float(probs[top_indices[0]])
        
        # Create emotion state
        state = EmotionState(
            primary_emotion=primary_emotion,
            secondary_emotion=secondary_emotion,
            intensity=intensity,
            confidence=float(probs[top_indices[0]]),
            timestamp=time.time()
        )
        
        # Update history
        if track_id not in self.emotion_history:
            self.emotion_history[track_id] = []
        self.emotion_history[track_id].append(state)
        
        # Trim history
        if len(self.emotion_history[track_id]) > self.config.get("temporal_tracking")["history_length"]:
            self.emotion_history[track_id] = self.emotion_history[track_id][-self.config.get("temporal_tracking")["history_length"]:]
        
        return state

    def get_emotion_trend(self, track_id: int) -> Dict[str, Any]:
        """Get emotion trend analysis"""
        if track_id not in self.emotion_history:
            return {"trend": "unknown", "confidence": 0.0}
            
        history = self.emotion_history[track_id]
        if not history:
            return {"trend": "unknown", "confidence": 0.0}
            
        # Analyze trend
        primary_emotions = [state.primary_emotion for state in history]
        emotion_counts = defaultdict(int)
        for emotion in primary_emotions:
            emotion_counts[emotion] += 1
            
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])
        confidence = dominant_emotion[1] / len(history)
        
        return {
            "trend": dominant_emotion[0],
            "confidence": confidence,
            "history": [{"emotion": state.primary_emotion, "intensity": state.intensity} for state in history]
        }

class LivenessDetector(BaseAgent):
    """Advanced liveness detection with multiple methods"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FaceRecognitionAgent")
        self.config = config
        self.blink_history: Dict[int, List[bool]] = {}
        self.motion_history: Dict[int, List[float]] = {}
        self.prev_frames: Dict[int, np.ndarray] = {}

    def detect_blink(self, face_img: np.ndarray, track_id: int) -> bool:
        """Detect blink using eye aspect ratio"""
        if not self.config.get("methods")["blink"]["enabled"]:
            return True
            
        # TODO: Implement blink detection using eye landmarks
        return True

    def detect_motion(self, face_img: np.ndarray, track_id: int) -> bool:
        """Detect motion using optical flow"""
        if not self.config.get("methods")["motion"]["enabled"]:
            return True
            
        if track_id not in self.prev_frames:
            self.prev_frames[track_id] = face_img
            return True
            
        # Calculate optical flow
        prev_gray = cv2.cvtColor(self.prev_frames[track_id], cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        
        # Calculate motion magnitude
        magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
        motion_score = np.mean(magnitude)
        
        # Update history
        if track_id not in self.motion_history:
            self.motion_history[track_id] = []
        self.motion_history[track_id].append(motion_score)
        
        # Trim history
        if len(self.motion_history[track_id]) > self.config.get("methods")["motion"]["history_length"]:
            self.motion_history[track_id] = self.motion_history[track_id][-self.config.get("methods")["motion"]["history_length"]:]
        
        # Update previous frame
        self.prev_frames[track_id] = face_img
        
        return motion_score > self.config.get("methods")["motion"]["threshold"]

    def detect_anti_spoofing(self, face_img: np.ndarray) -> bool:
        """Detect anti-spoofing using texture analysis"""
        if not self.config.get("methods")["anti_spoofing"]["enabled"]:
            return True
            
        # TODO: Implement anti-spoofing detection
        return True

    def is_live(self, face_img: np.ndarray, track_id: int) -> bool:
        """Check if face is live using all enabled methods"""
        results = []
        
        if self.config.get("methods")["blink"]["enabled"]:
            results.append(self.detect_blink(face_img, track_id))
            
        if self.config.get("methods")["motion"]["enabled"]:
            results.append(self.detect_motion(face_img, track_id))
            
        if self.config.get("methods")["anti_spoofing"]["enabled"]:
            results.append(self.detect_anti_spoofing(face_img))
            
        return all(results)

class PrivacyManager(BaseAgent):
    """Enhanced privacy management with configurable zones and data minimization"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FaceRecognitionAgent")
        self.config = config
        self.privacy_zones: List[PrivacyZone] = []
        self.data_retention: Dict[str, float] = {}
        self.load_privacy_zones()

    def load_privacy_zones(self):
        """Load privacy zones from configuration"""
        for zone in self.config.get("privacy_zones")["zones"]:
            self.privacy_zones.append(PrivacyZone(**zone))

    def apply_privacy(self, frame: np.ndarray, bbox: Tuple[int, int, int, int], 
                     is_known: bool) -> np.ndarray:
        """Apply privacy measures to face region"""
        if not is_known and self.config.get("blur_unknown"):
            return self.apply_blur(frame, bbox)
            
        # Check privacy zones
        for zone in self.privacy_zones:
            if self._is_in_zone(bbox, zone):
                return self.apply_blur(frame, bbox, zone.blur_level)
                
        return frame

    def _is_in_zone(self, bbox: Tuple[int, int, int, int], zone: PrivacyZone) -> bool:
        """Check if bbox is in privacy zone"""
        return (bbox[0] >= zone.x1 and bbox[1] >= zone.y1 and
                bbox[2] <= zone.x2 and bbox[3] <= zone.y2)

    def apply_blur(self, frame: np.ndarray, bbox: Tuple[int, int, int, int], 
                  blur_level: Optional[int] = None) -> np.ndarray:
        """Apply blur to face region"""
        if blur_level is None:
            blur_level = self.config.get("blur_level")
            
        x1, y1, x2, y2 = bbox
        face_roi = frame[y1:y2, x1:x2]
        blurred = cv2.GaussianBlur(face_roi, (blur_level, blur_level), 0)
        frame[y1:y2, x1:x2] = blurred
        return frame

    def cleanup_old_data(self):
        """Clean up old data based on retention period"""
        if not self.config.get("data_minimization")["enabled"]:
            return
            
        current_time = time.time()
        retention_period = self.config.get("data_minimization")["retention_period"]
        
        # Remove old data
        self.data_retention = {
            k: v for k, v in self.data_retention.items()
            if current_time - v < retention_period
        }

class FaceRecognitionAgent(BaseAgent):
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5560)) if port is None else port
        agent_name = config.get("name", "FaceRecognitionAgent")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)

        # Centralized error publisher
        self.error_publisher = ErrorPublisher(self.__class__.__name__)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        self.start_time = time.time()
        
        # Set running flag
        self.running = True
        
        # Initialize other attributes
        self.tracked_persons = {}
        self.known_faces = {}
        self.emotion_history = {}
        self.privacy_zones = []
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "components": {
                "zmq": False,
                "face_detector": False,
                "face_recognizer": False,
                "emotion_analyzer": False,
                "liveness_detector": False
            }
        }
        
        # Start async initialization
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        
        logging.info("FaceRecognitionAgent basic init complete, async init started")

    def _perform_initialization(self):
        try:
            self._init_zmq()
            self.initialization_status["components"]["zmq"] = True
            self.initialization_status["progress"] = 0.2
            self._init_model()
            self.initialization_status["components"]["face_detector"] = True
            self.initialization_status["progress"] = 0.4
            self._init_face_recognizer()
            self.initialization_status["components"]["face_recognizer"] = True
            self.initialization_status["progress"] = 0.6
            self._init_emotion_analyzer()
            self.initialization_status["components"]["emotion_analyzer"] = True
            self.initialization_status["progress"] = 0.8
            self._init_liveness_detector()
            self.initialization_status["components"]["liveness_detector"] = True
            self.initialization_status["progress"] = 1.0
            self.initialization_status["is_initialized"] = True
            logging.info("FaceRecognitionAgent async initialization complete")
        except Exception as e:
            self.initialization_status["error"] = str(e)
            self.initialization_status["progress"] = 0.0
            logging.error(f"Async initialization failed: {e}")
            from common_utils.error_handling import SafeExecutor
            with SafeExecutor(self.logger, recoverable=(ConnectionError, AttributeError)):
                self.error_publisher.publish_error(error_type="async_init_failure", details=str(e))
            traceback.print_exc()

    def _init_zmq(self):
        """Initialize ZMQ context and sockets."""
        try:
            self.context = None  # Using pool
            self.socket = get_rep_socket(self.endpoint).socket
            self.socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
            self.socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
            self.socket.bind(f"tcp://*:{self.port}")
            
            # Initialize publisher socket for events
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.bind(f"tcp://*:{self.port + 1}")
            
            logging.info("ZMQ initialization complete")
            
        except Exception as e:
            logging.error(f"ZMQ initialization failed: {e}")
            try:
                self.error_publisher.publish_error(error_type="zmq_init_failure", details=str(e))
            except Exception:
                pass
            raise
    
    def _init_model(self):
        """Initialize face detection model."""
        try:
            # Initialize InsightFace model
            self.model = insightface.app.FaceAnalysis(
                name=CONFIG["model"]["name"],
                root=CONFIG["model"]["root"],
                providers=CONFIG["model"]["providers"]
            )
            self.model.prepare(ctx_id=CONFIG["model"]["ctx_id"])
            
            # Apply optimizations
            self._apply_gpu_optimizations()
            self._apply_quantization()
            
            logging.info("Face detection model initialized")
            
        except Exception as e:
            logging.error(f"Model initialization failed: {e}")
            try:
                self.error_publisher.publish_error(error_type="model_init_failure", details=str(e))
            except Exception:
                pass
            raise
    
    def _init_face_recognizer(self):
        """Initialize face recognition model."""
        try:
            # Load known faces
            self.load_known_faces()
            logging.info("Face recognition initialized")
            
        except Exception as e:
            logging.error(f"Face recognition initialization failed: {e}")
            try:
                self.error_publisher.publish_error(error_type="face_recognizer_init_failure", details=str(e))
            except Exception:
                pass
            raise
    
    def _init_emotion_analyzer(self):
        """Initialize emotion analysis model."""
        try:
            # Initialize emotion model
            self.emotion_model = ort.InferenceSession(CONFIG["emotion_model"]["path"])
            logging.info("Emotion analyzer initialized")
            
        except Exception as e:
            logging.error(f"Emotion analyzer initialization failed: {e}")
            raise
    
    def _init_liveness_detector(self):
        """Initialize liveness detection."""
        try:
            # Initialize liveness detection components
            self.liveness_detector = LivenessDetector()
            logging.info("Liveness detector initialized")
            
        except Exception as e:
            logging.error(f"Liveness detector initialization failed: {e}")
            raise
    
    def _apply_gpu_optimizations(self):
        """Apply GPU optimizations if available."""
        if torch.cuda.is_available():
            try:
                # Enable CUDA optimizations
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                logging.info("GPU optimizations applied")
            except Exception as e:
                logging.warning(f"GPU optimization failed: {e}")
    
    def _apply_quantization(self):
        """Apply model quantization for better performance."""
        try:
            # Apply quantization if enabled
            if CONFIG["model"]["quantization"]["enabled"]:
                self.model.quantize()
                logging.info("Model quantization applied")
        except Exception as e:
            logging.warning(f"Quantization failed: {e}")
    
    def run(self):
        logging.info("Starting FaceRecognitionAgent main loop")
        while self.running:
            try:
                # Always respond to health checks, even if not initialized
                if hasattr(self, 'socket'):
                    if self.socket.poll(timeout=100):
                        message = self.socket.recv_json()
                        if message.get("action") == "health_check":
                            self.socket.send_json({
                                "status": "ok" if self.initialization_status["is_initialized"] else "initializing",
                                "initialization_status": self.initialization_status
                            })
                            continue
                        if not self.initialization_status["is_initialized"]:
                            self.socket.send_json({
                                "status": "error",
                                "error": "Agent is still initializing",
                                "initialization_status": self.initialization_status
                            })
                            continue
                        # Normal request processing
                        response = self._handle_request(message)
                        self.socket.send_json(response)
                    else:
                        time.sleep(0.05)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                try:
                    if hasattr(self, 'socket'):
                        self.socket.send_json({
                            'status': 'error',
                            'message': str(e)
                        })
                except Exception as zmq_err:
                    logging.error(f"ZMQ error while sending error response: {zmq_err}")
                    time.sleep(1)
    
    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get("action", "")
        
        if action == "health_check":
            return {
                "status": "ok",
                "message": "FaceRecognitionAgent is running",
                "initialization_status": self.initialization_status
            }
        elif action == "process_frame":
            if not self.initialization_status["is_initialized"]:
                return {
                    "status": "error",
                    "error": "FaceRecognitionAgent is still initializing",
                    "initialization_status": self.initialization_status
                }
            return self._process_frame(request)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _process_frame(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a video frame."""
        try:
            # Extract frame data
            frame_data = request.get("frame")
            if not frame_data:
                return {"status": "error", "error": "No frame data provided"}
            
            # Convert frame data to numpy array
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            
            # Detect faces
            faces = self.model.get(frame)
            
            # Update tracked persons
            self.update_tracked_persons(faces, frame)
            
            # Return results
            return {
                "status": "ok",
                "faces_detected": len(faces),
                "tracked_persons": len(self.tracked_persons)
            }
            
        except Exception as e:
            logging.error(f"Error processing frame: {e}")
            return {"status": "error", "error": str(e)}
    
    def stop(self):
        """Stop the agent."""
        logging.info("Stopping FaceRecognitionAgent")
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'pub_socket'):
            self.pub_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
    def health_check(self):
        """Perform a health check and return status."""
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {
                    "tracked_persons": len(self.tracked_persons) if hasattr(self, 'tracked_persons') else 0,
                    "known_faces": len(self.known_faces) if hasattr(self, 'known_faces') else 0,
                    "initialization_status": self.initialization_status["is_initialized"] if hasattr(self, 'initialization_status') else False
                }
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }

    def _get_health_status(self):
        """Default health status implementation required by BaseAgent."""
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational" if self.running else "Agent is not running",
            "uptime_seconds": time.time() - self.start_time,
            "initialization_status": self.initialization_status["is_initialized"] if hasattr(self, 'initialization_status') else False
        }
        return {"status": status, "details": details}

# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        logging.info("Starting FaceRecognitionAgent...")
        agent = FaceRecognitionAgent()
        agent.run()
    except KeyboardInterrupt:
        logging.info(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        logging.error(f"An unexpected error occurred in {agent.name if agent else 'FaceRecognitionAgent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logging.info(f"Cleaning up {agent.name}...")
            agent.cleanup()
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            if hasattr(self, 'context') and self.context:
                self.context.term()
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
