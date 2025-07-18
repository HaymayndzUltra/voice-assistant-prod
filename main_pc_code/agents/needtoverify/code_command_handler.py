from common.core.base_agent import BaseAgent
"""
Code Command Handler for Voice Assistant
This script handles voice commands related to auto code generation, debugging, and self-healing
"""

import os
import sys
import json
import time
import zmq
import threading
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'code_command_handler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CodeCommandHandler")

# Check if running in virtual environment
def is_venv_active():
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

class CodeCommandHandler(BaseAgent):
    """Handler for code-related voice commands including auto-fixing and self-healing"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="CodeCommandHandler")
        """Initialize the code command handler"""
        # Setup ZMQ connection to listener agent
        self.context = zmq.Context()
        self.listener_socket = self.context.socket(zmq.SUB)
        self.listener_socket.connect("tcp://localhost:5561")  # Listener ZMQ port
        self.listener_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Setup ZMQ connection to TTS agent
        self.tts_context = zmq.Context()
        self.tts_socket = self.tts_context.socket(zmq.REQ)  # Changed from PUSH to REQ
        self.tts_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.tts_socket.connect("tcp://localhost:5562")  # TTS ZMQ port
        self.tts_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # Setup ZMQ connection to auto-fixer agent
        self.auto_fixer_context = zmq.Context()
        self.auto_fixer_socket = self.auto_fixer_context.socket(zmq.REQ)
        self.auto_fixer_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.auto_fixer_socket.connect("tcp://localhost:5609")  # Auto-fixer ZMQ port
        
        # Setup ZMQ connection to self-healing agent
        self.self_healing_context = zmq.Context()
        self.self_healing_socket = self.self_healing_context.socket(zmq.REQ)
        self.self_healing_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.self_healing_socket.connect("tcp://localhost:5611")  # Self-healing ZMQ port
        
        # Setup ZMQ connection to code generator agent
        self.code_gen_context = zmq.Context()
        self.code_gen_socket = self.code_gen_context.socket(zmq.REQ)
        self.code_gen_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.code_gen_socket.connect("tcp://localhost:5604")  # Code generator ZMQ port
        
        # Setup ZMQ connection to executor agent
        self.executor_context = zmq.Context()
        self.executor_socket = self.executor_context.socket(zmq.REQ)
        self.executor_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.executor_socket.connect("tcp://localhost:5613")  # Executor ZMQ port
        
        # Command patterns for voice recognition
        self.command_patterns = {
            "generate_code": [
                r"generate (python|javascript|java|c\+\+|c#|html|css) code (for|that) (.+)",
                r"create (python|javascript|java|c\+\+|c#|html|css) (code|script|program) (for|that) (.+)",
                r"write (python|javascript|java|c\+\+|c#|html|css) (code|script|program) (for|that) (.+)",
                r"code (a|an) (python|javascript|java|c\+\+|c#|html|css) (.+)",
                r"gumawa ng (python|javascript|java|c\+\+|c#|html|css) code (para sa|na) (.+)"
            ],
            "auto_fix": [
                r"(auto fix|auto debug|fix|debug) (the|my) (code|script|program)",
                r"(auto fix|auto debug|fix|debug) (the|my) (.+) (code|script|program)",
                r"(ayusin|i-debug) (ang|yung) (code|script|program)",
                r"(ayusin|i-debug) (ang|yung) (.+) (code|script|program)"
            ],
            "health_check": [
                r"(check|show|display) (agent|system) (health|status)",
                r"(check|show|display) (health|status) (of|for) (all|the) agents",
                r"(tingnan|ipakita) (ang|yung) (health|status) (ng|ng mga) (agent|system)"
            ],
            "restart_agent": [
                r"restart (the|) (.+) agent",
                r"restart (all|) agents",
                r"i-restart (ang|yung) (.+) agent",
                r"i-restart (lahat ng|) agents"
            ]
        }
        
        self.running = False
        self.command_thread = None
    
    def speak(self, text):
        """Send text to the TTS agent to be spoken"""
        try:
            # Create request payload
            tts_command = {
                "command": "speak",
                "text": text,
                "voice": "jarvis"  # Use JARVIS voice
            }
            
            # Send request to TTS agent
            self.tts_socket.send_json(tts_command)
            logger.info(f"Sent to TTS: {text}")
            
            # Wait for response with timeout (already set in __init__)
            try:
                response = self.tts_socket.recv_json()
                
                if response.get('status') == 'ok':
                    logger.info(f"TTS successfully processed: '{text[:30]}...'")
                    return True
                else:
                    logger.warning(f"TTS agent returned error: {response}")
                    return False
            except zmq.error.Again:
                # Timeout occurred
                logger.warning("TTS request timed out")
                return False
                
        except zmq.ZMQError as e:
            logger.error(f"ZMQ error sending to TTS: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending to TTS: {e}")
            return False
    
    def matches_pattern(self, command, patterns):
        """Check if command matches any of the patterns"""
        for pattern in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                return match
        return None
    
    def generate_code(self, language, description):
        """Generate code using the code generator agent"""
        try:
            self.speak(f"Generating {language} code for {description}")
            
            # Send request to code generator
            self.code_gen_socket.send_string(json.dumps({
                "request_type": "generate",
                "description": description,
                "language": language,
                "save_to_file": True
            }))
            
            # Get response with timeout
            poller = zmq.Poller()
            poller.register(self.code_gen_socket, zmq.POLLIN)
            
            if poller.poll(10000):  # 10 second timeout
                response = json.loads(self.code_gen_socket.recv_string())
                
                if response.get("status") == "success":
                    code = response.get("code", "")
                    filename = response.get("filename", "")
                    
                    if filename:
                        self.speak(f"Code generated and saved to {filename}")
                    else:
                        self.speak("Code generated successfully")
                    
                    return True
                else:
                    error = response.get("error", "Unknown error")
                    self.speak(f"Failed to generate code: {error}")
            else:
                self.speak("Code generation timed out. Please try again.")
            
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            self.speak(f"Error generating code: {str(e)}")
        
        return False
    
    def auto_fix_code(self, description=None):
        """Auto-fix code using the auto-fixer agent"""
        try:
            if description:
                self.speak(f"Auto-fixing code for {description}")
            else:
                self.speak("Auto-fixing code")
            
            # TODO: Auto-fixer agent is archived. This feature is disabled.
            # # Send request to auto-fixer
            # request = {
            #     "description": description or "Fix the most recent code"
            # }
            # 
            # self.auto_fixer_socket.send_string(json.dumps(request))
            # 
            # # Get response with timeout
            # poller = zmq.Poller()
            # poller.register(self.auto_fixer_socket, zmq.POLLIN)
            # 
            # if poller.poll(30000):  # 30 second timeout
            #     response = json.loads(self.auto_fixer_socket.recv_string())
            #     
            #     if response.get("status") == "success":
            #         attempts = response.get("attempts", 0)
            #         result = response.get("result", {})
            #         
            #         self.speak(f"Code fixed successfully after {attempts} attempts")
            #         return True
            #     else:
            #         error = response.get("error", "Unknown error")
            #         attempts = response.get("attempts", 0)
            #         self.speak(f"Failed to fix code after {attempts} attempts. Error: {error}")
            # else:
            #     self.speak("Auto-fix operation timed out. Please try again.")
            
            self.speak("Auto-fix feature is currently disabled. Please use code generator instead.")
            return False
            
        except Exception as e:
            logger.error(f"Error auto-fixing code: {e}")
            self.speak(f"Error auto-fixing code: {str(e)}")
        
        return False
    
    def check_agent_health(self):
        """Check health status of all agents using the self-healing agent"""
        try:
            self.speak("Checking agent health status")
            
            # Send request to self-healing agent
            self.self_healing_socket.send_string(json.dumps({
                "request_type": "status"
            }))
            
            # Get response with timeout
            poller = zmq.Poller()
            poller.register(self.self_healing_socket, zmq.POLLIN)
            
            if poller.poll(5000):  # 5 second timeout
                response = json.loads(self.self_healing_socket.recv_string())
                
                if response.get("status") == "ok":
                    report = response.get("report", {})
                    
                    # Extract key information
                    healthy_agents = report.get("healthy_agents", [])
                    unhealthy_agents = report.get("unhealthy_agents", [])
                    resource_alerts = report.get("resource_alerts", [])
                    
                    # Prepare speech response
                    if unhealthy_agents:
                        self.speak(f"Warning: {len(unhealthy_agents)} agents are unhealthy: {', '.join(unhealthy_agents)}")
                    else:
                        self.speak(f"All {len(healthy_agents)} agents are healthy")
                    
                    if resource_alerts:
                        self.speak(f"Resource alerts: {len(resource_alerts)}")
                        for alert in resource_alerts[:2]:  # Only speak the first 2 alerts
                            self.speak(f"{alert.get('resource')}: {alert.get('message')}")
                    
                    return True
                else:
                    error = response.get("error", "Unknown error")
                    self.speak(f"Failed to get health status: {error}")
            else:
                self.speak("Health check timed out. Self-healing agent may be unavailable.")
            
        except Exception as e:
            logger.error(f"Error checking agent health: {e}")
            self.speak(f"Error checking agent health: {str(e)}")
        
        return False
    
    def restart_agent(self, agent_name=None):
        """Restart an agent or all agents using the self-healing agent"""
        try:
            if agent_name and agent_name.lower() != "all":
                self.speak(f"Restarting {agent_name} agent")
                target = agent_name
            else:
                self.speak("Restarting all agents")
                target = "all"
            
            # Send request to self-healing agent
            self.self_healing_socket.send_string(json.dumps({
                "request_type": "restart",
                "target": target
            }))
            
            # Get response with timeout
            poller = zmq.Poller()
            poller.register(self.self_healing_socket, zmq.POLLIN)
            
            if poller.poll(10000):  # 10 second timeout
                response = json.loads(self.self_healing_socket.recv_string())
                
                if response.get("status") == "ok":
                    result = response.get("result", {})
                    success = result.get("success", False)
                    
                    if success:
                        self.speak(f"Successfully restarted {target}")
                    else:
                        error = result.get("error", "Unknown error")
                        self.speak(f"Failed to restart {target}: {error}")
                    
                    return success
                else:
                    error = response.get("error", "Unknown error")
                    self.speak(f"Failed to restart {target}: {error}")
            else:
                self.speak("Restart operation timed out. Self-healing agent may be unavailable.")
            
        except Exception as e:
            logger.error(f"Error restarting agent: {e}")
            self.speak(f"Error restarting agent: {str(e)}")
        
        return False
    
    def process_voice_command(self, command):
        """Process a voice command related to code generation, auto-fixing, or self-healing"""
        command = command.lower()
        logger.info(f"Processing command: {command}")
        
        # Command: Generate code
        match = self.matches_pattern(command, self.command_patterns["generate_code"])
        if match:
            groups = match.groups()
            if len(groups) >= 3:
                language = groups[0]
                description = groups[-1]
                return self.generate_code(language, description)
        
        # Command: Auto-fix code
        match = self.matches_pattern(command, self.command_patterns["auto_fix"])
        if match:
            groups = match.groups()
            description = None
            if len(groups) >= 3:
                description = groups[-2] if groups[-1] in ["code", "script", "program"] else None
            return self.auto_fix_code(description)
        
        # Command: Check agent health
        match = self.matches_pattern(command, self.command_patterns["health_check"])
        if match:
            return self.check_agent_health()
        
        # Command: Restart agent
        match = self.matches_pattern(command, self.command_patterns["restart_agent"])
        if match:
            groups = match.groups()
            agent_name = groups[1] if len(groups) >= 2 else "all"
            return self.restart_agent(agent_name)
        
        return False
    
    def command_listener(self):
        """Listen for voice commands"""
        logger.info("Code command handler listening for voice commands...")
        
        while self.running:
            try:
                message_str = self.listener_socket.recv_string(flags=zmq.NOBLOCK)
                message = json.loads(message_str)
                
                # Check if this is a transcription message
                if "text" in message:
                    command = message.get("text", "")
                    
                    if command:
                        # Check if it's a code-related command
                        if self.process_voice_command(command):
                            logger.info(f"Processed code command: {command}")
                        else:
                            logger.debug(f"Not a code command: {command}")
            
            except zmq.Again:
                # No message available yet
                time.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Error in command listener: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the code command handler"""
        if self.running:
            logger.info("Code command handler is already running.")
            return
        
        self.running = True
        self.command_thread = threading.Thread(target=self.command_listener)
        self.command_thread.daemon = True
        self.command_thread.start()
        
        logger.info("Code command handler started.")
        self.speak("Code command handler is now active. You can use voice commands for code generation, auto-fixing, and agent health monitoring.")
    
    def stop(self):
        """Stop the code command handler"""
        self.running = False
        
        # Close all ZMQ sockets
        for socket_name in ["listener_socket", "tts_socket", "auto_fixer_socket", 
                           "self_healing_socket", "code_gen_socket", "executor_socket"]:
            socket = getattr(self, socket_name, None)
            if socket:
                socket.close()
        
        # Terminate all ZMQ contexts
        for context_name in ["context", "tts_context", "auto_fixer_context", 
                            "self_healing_context", "code_gen_context", "executor_context"]:
            context = getattr(self, context_name, None)
            if context:
                context.term()
        
        logger.info("Code command handler stopped.")
        self.speak("Code command handler stopped.")

def main():
    """Main function to run the code command handler"""
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    if not is_venv_active():
        print("WARNING: Virtual environment is not activated. It's recommended to run in a virtual environment.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting. Please activate your virtual environment and try again.")
            sys.exit(1)
    
    handler = CodeCommandHandler()
    
    try:
        handler.start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("Stopping code command handler...")
    
    finally:
        handler.stop()

if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise