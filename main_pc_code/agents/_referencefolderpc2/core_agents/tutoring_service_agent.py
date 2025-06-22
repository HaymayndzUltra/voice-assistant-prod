import zmq
import time
import json
import logging
from typing import Dict, Any
import sys
import os

# Get the absolute path of the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the parent directory to sys.path
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from tutoring_agent import AdvancedTutoringAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(current_dir, "tutoring_service_agent.log"), mode="a"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TutoringServiceAgent")

# Constants
TUTORING_PORT = 5568

class TutoringServiceAgent:
    def __init__(self):
        logger.info(f"Initializing Tutoring Service Agent on port {TUTORING_PORT}")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.socket.bind(f"tcp://*:{TUTORING_PORT}")
            logger.info(f"Successfully bound to tcp://*:{TUTORING_PORT}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to port {TUTORING_PORT}: {e}")
            logger.error("This might be due to the port being in use or other network configuration issues.")
            # Depending on desired behavior, you might want to exit or raise the exception
            raise

        self.sessions = {}  # To store AdvancedTutoringAgent instances per session_id
        self.running = True

    def _handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        action = request_data.get("action")
        session_id = request_data.get("session_id")

        if action == "health_check":
            return {"status": "success", "message": "Tutoring Service Agent is healthy", "timestamp": time.time()}
        
        elif action == "start_session":
            user_id = request_data.get("user_id")
            user_profile = request_data.get("user_profile")
            # Generate a session_id if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Check if user_profile is provided
            if not user_profile:
                return {"status": "error", "message": "user_profile is required for start_session"}
            
            try:
                logger.info(f"[PC2] Creating AdvancedTutoringAgent for session {session_id} (user_profile: {user_profile})")
                agent = AdvancedTutoringAgent(user_profile)
                self.sessions[session_id] = agent
                logger.info(f"[PC2] Started new tutoring session: {session_id} for user {user_id} (LLM integration: {getattr(agent, 'llm_available', False)})")
                return {"status": "success", "session_id": session_id, "message": "Tutoring session started (LLM integration: %s)." % getattr(agent, 'llm_available', False)}
            except Exception as e:
                logger.error(f"[PC2] Error starting session {session_id}: {e}")
                return {"status": "error", "message": f"Could not start session: {str(e)}"}
        
        # Handle other actions only if we have an active session
        if session_id and session_id in self.sessions:
            if action == "get_lesson":
                try:
                    logger.info(f"[PC2] get_lesson: Calling AdvancedTutoringAgent.get_lesson() for session {session_id}")
                    lesson_result = self.sessions[session_id].get_lesson()
                    logger.info(f"[PC2] get_lesson: Result status: {lesson_result.get('status')}")
                    if lesson_result.get('status') == 'success':
                        logger.info(f"[PC2] get_lesson: LLM-generated lesson returned for session {session_id}")
                        return {"status": "success", "lesson": lesson_result.get('lesson')}
                    else:
                        logger.warning(f"[PC2] get_lesson: Fallback/static lesson used for session {session_id} (reason: {lesson_result.get('message')})")
                        return {"status": "fallback", "lesson": lesson_result.get('lesson'), "message": lesson_result.get('message')}
                except Exception as e:
                    logger.error(f"[PC2] get_lesson: Exception generating lesson for session {session_id}: {e}")
                    return {"status": "error", "message": f"Could not generate lesson: {str(e)}"}
            
            elif action == "stop_session":
                # Remove the session
                if session_id in self.sessions:
                    del self.sessions[session_id]
                    logger.info(f"Stopped and removed tutoring session: {session_id}")
                    return {"status": "success", "message": f"Tutoring session {session_id} stopped."}
                else:
                    return {"status": "error", "message": f"Session {session_id} not found to stop."}
        
        # If we get here and session_id was provided but not found, return an error
        elif session_id and action != "start_session":
            return {"status": "error", "message": f"No active session found for session_id: {session_id}. Please start a session first."}
        
        # If we get here, it's an unknown action
        return {"status": "error", "message": f"Unknown action: {action}"}

    def run(self):
        logger.info("Tutoring Service Agent is running and listening for requests...")
        while self.running:
            try:
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                response = self._handle_request(message)
                
                self.socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except zmq.error.ContextTerminated:
                logger.info("ZMQ context terminated, shutting down agent.")
                self.running = False
            except json.JSONDecodeError:
                logger.error("Received invalid JSON message.")
                self.socket.send_json({"status": "error", "message": "Invalid JSON format"})
            except Exception as e:
                logger.error(f"An unexpected error occurred in the run loop: {e}", exc_info=True)
                # Send a generic error response if possible
                try:
                    self.socket.send_json({"status": "error", "message": f"An internal server error occurred: {str(e)}"})
                except Exception as send_e:
                    logger.error(f"Failed to send error response to client: {send_e}")

    def stop(self):
        logger.info("Stopping Tutoring Service Agent...")
        self.running = False
        # It's good practice to close sockets and terminate context explicitly
        # However, ZMQ sockets should ideally be closed from the same thread that created them.
        # If run() is in a different thread, you might need a more sophisticated shutdown.
        # For a simple single-threaded REP server, this might be okay, or rely on context termination.
        # self.socket.close() # Can cause issues if in different thread or if run() is still blocking on recv
        # self.context.term() # This will cause recv_json() to raise ContextTerminated

if __name__ == "__main__":
    agent = None
    try:
        agent = TutoringServiceAgent()
        agent.run()
    except zmq.error.ZMQError as e:
        # This handles the case where binding failed in __init__
        logger.critical(f"Could not start TutoringServiceAgent due to ZMQ error: {e}")
        # Exit or handle as appropriate for your application startup
        import sys

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
        sys.exit(1) # Indicate an error on exit
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    finally:
        if agent:
            agent.stop() # Attempt graceful shutdown
            # Explicitly terminate context if not done by stop() or if stop() is not reached
            if not agent.context.closed:
                 agent.context.term()
        logger.info("Tutoring Service Agent has been shut down.")