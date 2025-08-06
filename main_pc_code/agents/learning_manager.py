"""
Learning Manager Agent
------------------
Responsible for:
- Managing the learning process of the AI system
- Tracking learning progress and performance
- Adjusting learning parameters based on feedback
- Coordinating with other agents for continuous learning
"""
from common.utils.path_manager import PathManager

# Add the project's main_pc_code directory to the Python path
import sys
import os
# Removed 
import zmq
import time
import logging
import threading
import os
import sys
from datetime import datetime
from typing import Dict, Any

from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from common.utils.env_standardizer import get_env
from main_pc_code.agents.error_publisher import ErrorPublisher

# Parse command line arguments
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Configure logging using canonical approach
from common.utils.log_setup import configure_logging
logger = configure_logging(__name__, log_to_file=True)

# Constants
ZMQ_LEARNING_PORT = 5588  # Port for learning requests
ZMQ_HEALTH_PORT = 6588  # Health status port
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Learning settings
MAX_LEARNING_SESSIONS = 10
LEARNING_TIMEOUT = 3600  # 1 hour timeout for learning sessions
DEFAULT_LEARNING_RATE = 0.01

class LearningManager(BaseAgent):
    """Agent for managing the learning process of the AI system. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self):
        """Initialize the learning manager."""
        # Load configuration once
        self.config = config
        agent_name = self.config.get('name', 'LearningManager')
        agent_port = self.config.get('port', ZMQ_LEARNING_PORT)
        super().__init__(name=agent_name, port=agent_port)
        
        # Initialize state
        self.start_time = time.time()
        self.health_port = ZMQ_HEALTH_PORT
        self.running = True
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "components": {"core": False}
        }
        
        # Learning state
        self.learning_sessions = {}
        self.learning_history = []
        self.current_learning_rate = self.config.get('learning_rate', DEFAULT_LEARNING_RATE)
        self.processed_items = 0
        self.sessions_managed = 0
        
        # Initialize threads
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        logger.info("LearningManager basic init complete, async init started")
        
        self.health_thread = None

        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler

    def _perform_initialization(self):
        try:
            self._init_components()
            self.initialization_status["components"]["core"] = True
            self.initialization_status["progress"] = 1.0
            self.initialization_status["is_initialized"] = True
            logger.info("LearningManager initialization complete")
        except Exception as e:
            self.initialization_status["error"] = str(e)
            self.initialization_status["progress"] = 0.0
            logger.error(f"Initialization error: {e}")

    def _init_components(self):
        """Initialize core runtime components (runs in background thread)."""
        self._setup_sockets()
        self.health_thread = threading.Thread(target=self.health_broadcast_loop, daemon=True)
        self.health_thread.start()
        logger.info("LearningManager health broadcast loop started")
        
        # Initialize learning models and resources
        self._init_learning_resources()
    
    def _setup_sockets(self):
        """Set up ZMQ sockets."""
        try:
            if not hasattr(self, 'health_pub_socket'):
                self.health_pub_socket = self.context.socket(zmq.PUB)
                self.health_pub_socket.bind(f"tcp://*:{self.health_port}")
                logger.info(f"LearningManager health PUB bound on port {self.health_port}")
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {str(e)}")
            raise
    
    def _init_learning_resources(self):
        """Initialize learning models and resources."""
        try:
            # Initialize learning resources
            logger.info("Initializing learning resources")
            
            # Example: Load learning parameters
            self.learning_parameters = {
                "learning_rate": self.current_learning_rate,
                "batch_size": self.config.get('batch_size', 32),
                "epochs": self.config.get('epochs', 10),
                "optimizer": self.config.get('optimizer', 'adam')
            }
            
            # Example: Initialize model registry
            self.model_registry = {}
            
            logger.info("Learning resources initialized")
        except Exception as e:
            logger.error(f"Error initializing learning resources: {str(e)}")
            raise
    
    def _create_learning_session(self, session_id, model_id, parameters=None):
        """Create a new learning session."""
        try:
            now = datetime.now().isoformat()
            
            if len(self.learning_sessions) >= MAX_LEARNING_SESSIONS:
                # Remove oldest session
                oldest_session = min(self.learning_sessions.items(), key=lambda x: x[1]["created_at"])
                del self.learning_sessions[oldest_session[0]]
            
            self.learning_sessions[session_id] = {
                "model_id": model_id,
                "created_at": now,
                "last_active": now,
                "parameters": parameters or {},
                "status": "initialized",
                "progress": 0.0,
                "metrics": {},
                "history": []
            }
            
            self.sessions_managed += 1
            logger.info(f"Created new learning session {session_id} for model {model_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating learning session: {str(e)}")
            return None
    
    def _update_learning_session(self, session_id, status=None, progress=None, metrics=None):
        """Update a learning session."""
        try:
            if session_id not in self.learning_sessions:
                return False
            
            now = datetime.now().isoformat()
            self.learning_sessions[session_id]["last_active"] = now
            
            if status:
                self.learning_sessions[session_id]["status"] = status
            
            if progress is not None:
                self.learning_sessions[session_id]["progress"] = progress
            
            if metrics:
                self.learning_sessions[session_id]["metrics"].update(metrics)
                self.learning_sessions[session_id]["history"].append({
                    "timestamp": now,
                    "metrics": metrics
                })
            
            logger.info(f"Updated learning session {session_id}: status={status}, progress={progress}")
            return True
        except Exception as e:
            logger.error(f"Error updating learning session: {str(e)}")
            return False
    
    def _get_learning_session(self, session_id):
        """Get a learning session by ID."""
        if session_id in self.learning_sessions:
            now = datetime.now().isoformat()
            self.learning_sessions[session_id]["last_active"] = now
            return self.learning_sessions[session_id]
        return None
    
    def _delete_learning_session(self, session_id):
        """Delete a learning session."""
        if session_id in self.learning_sessions:
            # Archive session data
            self.learning_history.append({
                "session_id": session_id,
                "model_id": self.learning_sessions[session_id]["model_id"],
                "created_at": self.learning_sessions[session_id]["created_at"],
                "ended_at": datetime.now().isoformat(),
                "final_status": self.learning_sessions[session_id]["status"],
                "final_metrics": self.learning_sessions[session_id]["metrics"]
            })
            
            del self.learning_sessions[session_id]
            logger.info(f"Deleted learning session {session_id}")
            return True
        return False
    
    def _adjust_learning_rate(self, metrics):
        """Adjust learning rate based on performance metrics."""
        try:
            # Example: Simple learning rate adjustment based on loss
            if "loss" in metrics:
                loss = metrics["loss"]
                
                # If loss is decreasing, keep the learning rate
                # If loss is increasing, decrease the learning rate
                if len(self.learning_history) > 0:
                    last_metrics = self.learning_history[-1].get("final_metrics", {})
                    if "loss" in last_metrics and loss > last_metrics["loss"]:
                        self.current_learning_rate *= 0.9
                        logger.info(f"Decreased learning rate to {self.current_learning_rate}")
            
            return self.current_learning_rate
        except Exception as e:
            logger.error(f"Error adjusting learning rate: {str(e)}")
            return self.current_learning_rate
    
    def handle_request(self, request):
        """Handle a request from the coordinator."""
        try:
            action = request.get("action", "")
            
            if action == "create_session":
                session_id = request.get("session_id", str(time.time()))
                model_id = request.get("model_id")
                parameters = request.get("parameters", {})
                
                if not model_id:
                    return {
                        "status": "error",
                        "message": "Missing model_id",
                        "request_id": request.get("request_id", "")
                    }
                
                result = self._create_learning_session(session_id, model_id, parameters)
                
                return {
                    "status": "success" if result else "error",
                    "session_id": result,
                    "request_id": request.get("request_id", "")
                }
            
            elif action == "update_session":
                session_id = request.get("session_id")
                status = request.get("status")
                progress = request.get("progress")
                metrics = request.get("metrics", {})
                
                if not session_id:
                    return {
                        "status": "error",
                        "message": "Missing session_id",
                        "request_id": request.get("request_id", "")
                    }
                
                result = self._update_learning_session(session_id, status, progress, metrics)
                
                if result and metrics:
                    new_learning_rate = self._adjust_learning_rate(metrics)
                    
                    return {
                        "status": "success",
                        "learning_rate": new_learning_rate,
                        "request_id": request.get("request_id", "")
                    }
                
                return {
                    "status": "success" if result else "error",
                    "request_id": request.get("request_id", "")
                }
            
            elif action == "get_session":
                session_id = request.get("session_id")
                
                if not session_id:
                    return {
                        "status": "error",
                        "message": "Missing session_id",
                        "request_id": request.get("request_id", "")
                    }
                
                session = self._get_learning_session(session_id)
                
                return {
                    "status": "success" if session else "error",
                    "session": session,
                    "request_id": request.get("request_id", "")
                }
            
            elif action == "delete_session":
                session_id = request.get("session_id")
                
                if not session_id:
                    return {
                        "status": "error",
                        "message": "Missing session_id",
                        "request_id": request.get("request_id", "")
                    }
                
                result = self._delete_learning_session(session_id)
                
                return {
                    "status": "success" if result else "error",
                    "request_id": request.get("request_id", "")
                }
            
            elif action == "get_learning_rate":
                model_id = request.get("model_id")
                
                # For now, we use a global learning rate
                # In the future, we could have model-specific learning rates
                
                return {
                    "status": "success",
                    "learning_rate": self.current_learning_rate,
                    "request_id": request.get("request_id", "")
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "request_id": request.get("request_id", "")
                }
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
                "request_id": request.get("request_id", "")
            }
    
    def health_broadcast_loop(self):
        """Loop for broadcasting health status."""
        while self.running:
            try:
                status = {
                    "component": "learning_manager",
                    "status": "running",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "active_sessions": len(self.learning_sessions),
                        "learning_rate": self.current_learning_rate
                    }
                }
                
                self.health_pub_socket.send_json(status)
                
            except Exception as e:
                logger.error(f"Error broadcasting health status: {str(e)}")
            
            time.sleep(5)
    
    def run(self):
        """Run the learning manager."""
        logger.info("Starting LearningManager main loop")
        
        # Call parent's run method to ensure health check thread works
        super().run()
        
        while self.running:
            try:
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
                        response = self.handle_request(message)
                        self.socket.send_json(response)
                    else:
                        time.sleep(0.05)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                try:
                    if hasattr(self, 'socket'):
                        self.socket.send_json({'status': 'error','message': str(e)})
                except Exception as zmq_err:
                    logger.error(f"ZMQ error while sending error response: {zmq_err}")
                    time.sleep(1)
    
    def stop(self):
        """Stop the learning manager."""
        logger.info("Stopping learning manager")
        self.running = False
        
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'health_pub_socket'):
            self.health_pub_
        if self.health_thread:
            self.health_thread.join(timeout=1.0)
        
        logger.info("Learning manager stopped")

    def _get_health_status(self) -> Dict[str, Any]:
        """Overrides the base method to add agent-specific health metrics."""
        return {
            'status': 'ok',
            'ready': True,
            'initialized': True,
            'service': 'learning_manager',
            'components': {
                'health_broadcast': self.health_thread is not None and self.health_thread.is_alive() if self.health_thread else False
            },
            'status_detail': 'active',
            'processed_items': self.processed_items,
            'sessions_managed': self.sessions_managed,
            'active_sessions': len(self.learning_sessions),
            'learning_rate': self.current_learning_rate,
            'uptime': time.time() - self.start_time
        }

    def cleanup(self):
        """Gracefully shutdown the agent"""
        logger.info("Cleaning up LearningManager")
        self.running = False
        
        # Close sockets
        if hasattr(self, 'socket'):
            pass  # Cleanup handled by BaseAgent
        if hasattr(self, 'health_pub_socket'):
            self.health_pub_
        # Wait for threads to finish
        if self.health_thread:
            self.health_thread.join(timeout=1.0)
            
        # Call parent cleanup
        super().cleanup()
        logger.info("LearningManager cleanup complete")

# Example usage
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = LearningManager()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()