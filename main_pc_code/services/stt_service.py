"""
STT (Speech-to-Text) Micro-service
Purpose: Lightweight wrapper to receive audio data and request transcription from ModelManagerAgent
Features: Audio preprocessing, format conversion, language detection, batch processing
"""

import zmq
import numpy as np
import time
import logging
import json
import threading
import traceback
from datetime import datetime
import uuid
import sys
from typing import List, Dict, Any

# Add the project's main_pc_code directory to the Python path
from common.utils.path_manager import PathManager
from common.utils.path_manager import PathManager
from common.utils.log_setup import configure_logging
MAIN_PC_CODE_DIR = PathManager.get_project_root()
if str(MAIN_PC_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))

from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.service_discovery_client import register_service
from main_pc_code.utils import model_client

# Load configuration
config = load_config()

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("STTService")

# Audio Settings
SAMPLE_RATE = int(config.get("sample_rate", 16000))  # Whisper expects 16kHz
DEFAULT_LANGUAGE = config.get("default_language", "en")
SUPPORTED_LANGUAGES = config.get("supported_languages", ["en", "tl", "fil"])  # English, Tagalog, Filipino

# Batch Processing Settings
MAX_BATCH_SIZE = int(config.get("max_batch_size", 8))  # Maximum number of audio segments in a batch
MIN_BATCH_SIZE = int(config.get("min_batch_size", 2))  # Minimum number of audio segments to use batching
MAX_BATCH_WAIT_MS = int(config.get("max_batch_wait_ms", 100))  # Maximum time to wait for batch completion

class STTService(BaseAgent):
    def __init__(self, port=None):
        """Initialize the STT service."""
        # Get configuration values with fallbacks
        agent_port = int(config.get("stt_service_port", 5800)) if port is None else port
        agent_name = config.get("stt_service_name", "STTService")
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Initialize state variables
        self.running = True
        self.start_time = time.time()
        self.request_count = 0
        self.current_language = DEFAULT_LANGUAGE
        
        # Batch processing state
        self.batch_queue = []
        self.batch_lock = threading.Lock()
        self.batch_event = threading.Event()
        self.batch_thread = threading.Thread(target=self._batch_processing_loop, daemon=True)
        self.batch_thread.start()
        
        # Performance metrics
        self.total_processing_time = 0
        self.total_audio_seconds = 0
        self.batch_count = 0
        self.single_request_count = 0
        

        
        # Register with service discovery
        self._register_service()
        
        logger.info(f"{self.name} initialized on port {self.port}")

    def _register_service(self):
        """Register this service with the service discovery system."""
        try:
            register_result = register_service(
                name=self.name,
                port=self.port,
                additional_info={
                    "capabilities": ["stt", "transcription", "multilingual", "batch_processing"],
                    "status": "online"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")

    def transcribe(self, audio_data, language=None):
        """
        Transcribe audio data using the ModelManagerAgent.
        
        Args:
            audio_data (numpy.ndarray): Audio data as a numpy array
            language (str, optional): Language code. Defaults to None (auto-detect).
            
        Returns:
            dict: Transcription result with text, confidence, and language
        """
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # Ensure audio is in the correct format (float32, 16kHz, mono)
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data)
            
            # Normalize audio
            audio_data = audio_data / (np.max(np.abs(audio_data)) + 1e-8)
            
            # Use model_client to request transcription from ModelManagerAgent
            request_id = str(uuid.uuid4())
            
            # Prepare request parameters
            params = {
                "audio_data": audio_data.tolist(),  # Convert to list for JSON serialization
                "sample_rate": SAMPLE_RATE,
                "request_id": request_id,
                "model_type": "stt"
            }
            
            # ✅ NEW: Use Whisper-Large-v3 model specifically
            request_params = {
                "action": "generate_text",
                "model_id": "whisper-large-v3",  # Use downloaded model
                "audio_data": audio_data.tolist() if isinstance(audio_data, np.ndarray) else audio_data,
                "sample_rate": SAMPLE_RATE,
                "task": "transcribe",
                "language": language or "auto",
                "request_id": request_id,
                "precision": "float16",  # Best quality for RTX 4090
                "device": "cuda",  # GPU precision setting
                "return_timestamps": True,
                "return_confidence": True
            }

            # Add language if specified
            if language:
                params["language"] = language
                
            # ✅ UPDATED: Send request to ModelManagerSuite using Whisper-Large-v3
            response = model_client.request_inference(request_params)
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"PERF_METRIC: [STTService] - [Transcription] - Duration: {duration_ms:.2f}ms")
            
            # Update metrics
            self.single_request_count += 1
            self.total_processing_time += (time.time() - start_time)
            self.total_audio_seconds += len(audio_data) / SAMPLE_RATE
            
            if response.get("status") == "success":
                result = response.get("result", {})
                transcript = {
                    "text": result.get("text", "").strip(),
                    "confidence": result.get("confidence", 0.0),
                    "language": result.get("language", language or self.current_language),
                    "timestamp": datetime.now().isoformat()
                }
                return transcript
            else:
                error_message = response.get("message", "Unknown error")
                logger.error(f"Transcription failed: {error_message}")
                self.report_error("TranscriptionError", f"Failed to transcribe audio: {error_message}")
                return {
                    "status": "error",
                    "message": error_message
                }
                
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            logger.error(traceback.format_exc())
            self.report_error("TranscriptionError", f"Exception during transcription: {str(e)}")
            return self._transcribe_fallback(audio_data, language)

    def _transcribe_fallback(self, audio_data, language=None):
        """Fallback to CPU whisper.cpp model"""
        try:
            fallback_params = {
                "action": "generate_text", 
                "model_id": "whisper-cpp-medium",  # CPU fallback
                "audio_data": audio_data.tolist() if isinstance(audio_data, np.ndarray) else audio_data,
                "task": "transcribe",
                "language": language or "auto"
            }
            
            response = model_client.request_inference(fallback_params)
            
            if response and response.get("success"):
                return {
                    "text": response.get("text", ""),
                    "confidence": response.get("confidence", 0.8),  # Default confidence
                    "language": response.get("detected_language", language or "unknown"),
                    "model_used": "whisper-cpp-medium",
                    "fallback": True
                }
        except Exception as e:
            logger.error(f"Fallback STT failed: {e}")
            
        return {
            "text": "",
            "confidence": 0.0,
            "language": "unknown",
            "error": "STT failed",
            "model_used": "none"
        }

    def batch_transcribe(self, audio_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transcribe multiple audio segments in a single batch request.
        
        Args:
            audio_batch (List[Dict]): List of dictionaries containing audio data and metadata
                Each dict should have:
                - audio_data: numpy array or list of audio samples
                - language: (optional) language code
                - request_id: (optional) unique identifier for the request
                
        Returns:
            List[Dict]: List of transcription results, one per input audio segment
        """
        if not audio_batch:
            return []
            
        try:
            # Start timing for performance metrics
            start_time = time.time()
            
            # Process and normalize each audio segment
            processed_batch = []
            for item in audio_batch:
                audio_data = item.get("audio_data")
                if audio_data is None:
                    continue
                    
                # Convert to numpy array if needed
                if not isinstance(audio_data, np.ndarray):
                    audio_data = np.array(audio_data)
                
                # Normalize audio
                audio_data = audio_data / (np.max(np.abs(audio_data)) + 1e-8)
                
                # Create processed item
                processed_item = {
                    "audio_data": audio_data.tolist(),  # Convert to list for JSON serialization
                    "sample_rate": SAMPLE_RATE,
                    "request_id": item.get("request_id", str(uuid.uuid4())),
                    "language": item.get("language")
                }
                processed_batch.append(processed_item)
            
            # Skip if no valid audio segments
            if not processed_batch:
                return []
                
            # Prepare batch request parameters
            batch_request = {
                "batch_data": processed_batch,
                "model_type": "stt",
                "batch_size": len(processed_batch)
            }
                
            # Send batch request to ModelManagerAgent via model_client
            response = model_client.generate(
                prompt="Batch transcribe audio to text",
                quality="quality",  # Use high quality for transcription
                batch_mode=True,
                **batch_request
            )
            
            # Calculate and log the duration
            duration_ms = (time.time() - start_time) * 1000
            batch_size = len(processed_batch)
            logger.info(f"PERF_METRIC: [STTService] - [BatchTranscription] - Size: {batch_size}, Duration: {duration_ms:.2f}ms, Avg: {duration_ms/batch_size:.2f}ms per item")
            
            # Update metrics
            self.batch_count += 1
            self.total_processing_time += (time.time() - start_time)
            total_audio_len = sum(len(item.get("audio_data", [])) for item in audio_batch) / SAMPLE_RATE
            self.total_audio_seconds += total_audio_len
            
            # Process response
            if response.get("status") == "success":
                results = response.get("results", [])
                
                # Format results
                transcripts = []
                for i, result in enumerate(results):
                    item = audio_batch[i] if i < len(audio_batch) else {}
                    language = item.get("language") or self.current_language
                    
                    transcript = {
                        "text": result.get("text", "").strip(),
                        "confidence": result.get("confidence", 0.0),
                        "language": result.get("language", language),
                        "request_id": item.get("request_id", "unknown"),
                        "timestamp": datetime.now().isoformat()
                    }
                    transcripts.append(transcript)
                
                return transcripts
            else:
                error_message = response.get("message", "Unknown error")
                logger.error(f"Batch transcription failed: {error_message}")
                self.report_error("BatchTranscriptionError", f"Failed to transcribe audio batch: {error_message}")
                
                # Return error for each item in the batch
                return [
                    {
                        "status": "error",
                        "message": error_message,
                        "request_id": item.get("request_id", "unknown")
                    }
                    for item in audio_batch
                ]
                
        except Exception as e:
            logger.error(f"Error in batch transcription: {str(e)}")
            logger.error(traceback.format_exc())
            self.report_error("BatchTranscriptionError", f"Exception during batch transcription: {str(e)}")
            
            # Return error for each item in the batch
            return [
                {
                    "status": "error",
                    "message": str(e),
                    "request_id": item.get("request_id", "unknown")
                }
                for item in audio_batch
            ]

    def queue_for_batch(self, audio_data, language=None, request_id=None, callback=None):
        """
        Queue an audio segment for batch processing.
        
        Args:
            audio_data: Audio data as numpy array or list
            language: Optional language code
            request_id: Optional request ID
            callback: Optional callback function to call with the result
            
        Returns:
            str: Request ID for tracking
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
            
        # Create batch item
        batch_item = {
            "audio_data": audio_data,
            "language": language,
            "request_id": request_id,
            "timestamp": time.time(),
            "callback": callback
        }
        
        # Add to batch queue
        with self.batch_lock:
            self.batch_queue.append(batch_item)
            
            # Signal batch thread if we've reached minimum batch size
            if len(self.batch_queue) >= MIN_BATCH_SIZE:
                self.batch_event.set()
        
        return request_id

    def _batch_processing_loop(self):
        """Background thread for processing batched transcription requests."""
        logger.info("Starting batch processing thread")
        
        while self.running:
            try:
                # Wait for batch event or timeout
                wait_time = float(MAX_BATCH_WAIT_MS) / 1000.0
                self.batch_event.wait(wait_time)
                self.batch_event.clear()
                
                # Check if we have items to process
                with self.batch_lock:
                    if not self.batch_queue:
                        continue
                        
                    # Take up to MAX_BATCH_SIZE items
                    batch_items = self.batch_queue[:MAX_BATCH_SIZE]
                    self.batch_queue = self.batch_queue[MAX_BATCH_SIZE:]
                
                # Skip if batch is empty
                if not batch_items:
                    continue
                    
                # Process batch
                logger.info(f"Processing batch of {len(batch_items)} audio segments")
                results = self.batch_transcribe(batch_items)
                
                # Handle results
                for i, result in enumerate(results):
                    if i < len(batch_items):
                        # Get callback if available
                        callback = batch_items[i].get("callback")
                        if callback and callable(callback):
                            try:
                                callback(result)
                            except Exception as e:
                                logger.error(f"Error in batch result callback: {e}")
            
            except Exception as e:
                logger.error(f"Error in batch processing loop: {e}")
                logger.error(traceback.format_exc())
                time.sleep(1)  # Avoid tight loop on error

    def report_error(self, error_type, message, severity="WARNING", context=None):
        """Report an error to the error bus."""
        try:
            error_data = {
                "agent": self.name,
                "error_type": error_type,
                "severity": severity,
                "message": message,
                "context": context or {}
            }
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"Reported error: {message}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")

    def handle_request(self, request):
        """Handle incoming requests."""
        try:
            self.request_count += 1
            
            # Ensure request is a dictionary
            if not isinstance(request, dict):
                return {"status": "error", "message": "Request must be a dictionary"}
                
            action = request.get("action", "")
            
            if action == "transcribe":
                audio_data = request.get("audio_data")
                language = request.get("language")
                
                if audio_data is None:
                    return {"status": "error", "message": "Missing audio_data parameter"}
                
                result = self.transcribe(audio_data, language)
                return result
                
            elif action == "batch_transcribe":
                audio_batch = request.get("audio_batch")
                
                if not audio_batch:
                    return {"status": "error", "message": "Missing or empty audio_batch parameter"}
                
                results = self.batch_transcribe(audio_batch)
                return {"status": "success", "results": results}
                
            elif action == "queue_for_batch":
                audio_data = request.get("audio_data")
                language = request.get("language")
                request_id = request.get("request_id")
                
                if audio_data is None:
                    return {"status": "error", "message": "Missing audio_data parameter"}
                
                request_id = self.queue_for_batch(audio_data, language, request_id)
                return {"status": "queued", "request_id": request_id}
                
            elif action == "health_check":
                return self._get_health_status()
                
            elif action == "performance_metrics":
                return self._get_performance_metrics()
                
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}

    def _get_health_status(self):
        """Get the health status of the service."""
        return {
            "status": "ok",
            "service": self.name,
            "uptime_seconds": int(time.time() - self.start_time),
            "request_count": self.request_count,
            "batch_queue_size": len(self.batch_queue),
            "batch_count": self.batch_count,
            "single_request_count": self.single_request_count
        }
        
    def _get_performance_metrics(self):
        """Get performance metrics for the service."""
        total_requests = self.batch_count + self.single_request_count
        
        if total_requests == 0:
            return {
                "status": "ok",
                "message": "No transcription requests processed yet"
            }
            
        avg_processing_time = self.total_processing_time / total_requests if total_requests > 0 else 0
        realtime_factor = self.total_processing_time / self.total_audio_seconds if self.total_audio_seconds > 0 else 0
        
        return {
            "status": "ok",
            "metrics": {
                "total_requests": total_requests,
                "batch_count": self.batch_count,
                "single_request_count": self.single_request_count,
                "total_processing_time_seconds": round(self.total_processing_time, 2),
                "total_audio_seconds": round(self.total_audio_seconds, 2),
                "average_processing_time_seconds": round(avg_processing_time, 3),
                "realtime_factor": round(realtime_factor, 2),
                "batch_queue_current_size": len(self.batch_queue)
            }
        }

    def run(self):
        """Main run loop."""
        logger.info(f"Starting {self.name}...")
        
        while self.running:
            try:
                # Wait for a request with timeout
                if self.socket.poll(1000) == 0:  # 1 second timeout
                    continue
                    
                # Receive and process request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process the request
                response = self.handle_request(message)
                
                # Send the response
                self.socket.send_json(response)
                
            except zmq.error.Again:
                # Timeout, continue loop
                continue
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                logger.error(traceback.format_exc())
                try:
                    self.socket.send_json({"status": "error", "message": str(e)})
                except:
                    pass

    def cleanup(self):
        """Clean up resources before shutting down."""
        logger.info(f"Cleaning up {self.name}...")
        self.running = False
        self.batch_event.set()  # Signal batch thread to exit
        
        # Wait for batch thread to exit
        if self.batch_thread.is_alive():
            self.batch_thread.join(timeout=2.0)
            
        # Close ZMQ sockets
        try:
            self.error_bus_pub.close()
        except:
            pass
            
        # Call parent cleanup
        super().cleanup()


# Entry point for running as a standalone service
if __name__ == "__main__":
    service = STTService()
    try:
        service.run()
    except KeyboardInterrupt:
        print("Shutting down STT service...")
    finally:
        service.cleanup() 