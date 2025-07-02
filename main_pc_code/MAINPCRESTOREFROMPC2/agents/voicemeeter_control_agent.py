from src.core.base_agent import BaseAgent
"""
VoiceMeeter Control Agent
------------------------
A ZMQ-based agent for controlling VoiceMeeter audio routing configurations.
Provides remote control of VoiceMeeter settings through a standardized interface.
"""

import os
import time
import json
import zmq
import logging
import ctypes
import subprocess
import threading
import win32gui
import win32process
import psutil
from pathlib import Path
from typing import Dict, Any, Optional

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Setup logging
LOG_PATH = os.path.join(Path(os.path.dirname(__file__)).parent, "logs", "voicemeeter_control.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("VoiceMeeterControlAgent")

# ZMQ port for this agent
VOICEMEETER_CONTROL_PORT = 5645

class VoiceMeeterControlAgent(BaseAgent):
    """ZMQ-based agent for controlling VoiceMeeter audio routing"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="VoicemeeterControlAgent")
        """Initialize the VoiceMeeter control agent"""
        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
        logger.info(f"VoiceMeeter Control Agent started on port {zmq_port}")
        
        # VoiceMeeter paths
        self.vm_path = self._find_voicemeeter_path()
        self.vm_type = self._detect_voicemeeter_type()
        
        # State tracking
        self.is_running = False
        self.current_mode = "normal"
        
        # Configuration profiles
        self.config_dir = os.path.join(os.path.expanduser("~"), "VoiceAssistant", "vm_profiles")
        os.makedirs(self.config_dir, exist_ok=True)
        self.profiles = self._load_profiles()
        
        # DLL for direct control
        self.vm_dll = None
        self.initialized = False
        
        # Ensure VoiceMeeter is running
        self._ensure_voicemeeter_running()
        
        # Initialize remote API
        self._init_remote_api()
        
        logger.info("VoiceMeeter Control Agent initialized")
    
    def _find_voicemeeter_path(self):
        """Find the VoiceMeeter installation path"""
        possible_paths = [
            "C:\\Program Files\\VB\\Voicemeeter\\voicemeeter.exe",
            "C:\\Program Files (x86)\\VB\\Voicemeeter\\voicemeeter.exe"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _detect_voicemeeter_type(self):
        """Detect which VoiceMeeter variant is installed"""
        if self.vm_path is None:
            return "unknown"
            
        if "voicemeeter8" in self.vm_path.lower():
            return "potato"
        elif "voicemeeterpro" in self.vm_path.lower() or "voicemeeterbanana" in self.vm_path.lower():
            return "banana"
        else:
            return "standard"
    
    def _load_profiles(self):
        """Load audio routing profiles from configuration files"""
        profiles = {
            "normal": self._get_default_profile("normal"),
            "recording": self._get_default_profile("recording"),
            "playback": self._get_default_profile("playback")
        }
        
        # Load custom profiles if they exist
        for profile_name in profiles.keys():
            profile_path = os.path.join(self.config_dir, f"{profile_name}.json")
            if os.path.exists(profile_path):
                try:
                    with open(profile_path, 'r') as f:
                        profiles[profile_name] = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading profile {profile_name}: {e}")
        
        return profiles
    
    def _get_default_profile(self, profile_type):
        """Get default settings for a profile type"""
        if profile_type == "normal":
            return {
                "description": "Normal Windows audio routing",
                "A1_source": "MME: Default",
                "A2_source": "None",
                "A3_source": "None",
                "B1_source": "MME: Default",
                "B2_source": "None",
                "strip[0].mute": False,
                "strip[1].mute": True,
                "strip[2].mute": True,
                "strip[3].mute": True,
                "strip[0].A1": True,
                "strip[0].B1": False,
                "strip[2].A1": False,
                "strip[2].B1": False
            }
        elif profile_type == "recording":
            return {
                "description": "Capture system audio without microphone",
                "A1_source": "MME: Default",
                "A2_source": "None",
                "A3_source": "None",
                "B1_source": "MME: Default",
                "B2_source": "VoiceMeeter Output",
                "strip[0].mute": True,
                "strip[1].mute": True,
                "strip[2].mute": False,
                "strip[3].mute": True,
                "strip[0].A1": False,
                "strip[0].B1": False,
                "strip[2].A1": True,
                "strip[2].B2": True
            }
        elif profile_type == "playback":
            return {
                "description": "Play audio to messenger without mic",
                "A1_source": "MME: Default",
                "A2_source": "None",
                "A3_source": "None",
                "B1_source": "MME: VoiceMeeter Output",
                "B2_source": "None",
                "strip[0].mute": True,
                "strip[1].mute": True,
                "strip[2].mute": False,
                "strip[3].mute": True,
                "strip[0].A1": False,
                "strip[0].B1": False,
                "strip[2].A1": True,
                "strip[2].B1": True
            }
        return {}
    
    def _ensure_voicemeeter_running(self):
        """Make sure VoiceMeeter is running"""
        if self.is_voicemeeter_running():
            self.is_running = True
            return True
            
        if self.vm_path and os.path.exists(self.vm_path):
            try:
                subprocess.Popen([self.vm_path])
                for _ in range(10):
                    time.sleep(1)
                    if self.is_voicemeeter_running():
                        self.is_running = True
                        logger.info("VoiceMeeter started successfully")
                        return True
                logger.error("Failed to start VoiceMeeter")
                return False
            except Exception as e:
                logger.error(f"Error starting VoiceMeeter: {e}")
                return False
        return False
    
    def is_voicemeeter_running(self):
        """Check if VoiceMeeter is currently running"""
        for proc in psutil.process_iter(['name']):
            if 'voicemeeter' in proc.info['name'].lower():
                return True
        return False
    
    def _init_remote_api(self):
        """Initialize the VoiceMeeter Remote API"""
        try:
            # Load the VoiceMeeter Remote DLL
            dll_path = os.path.join(os.path.dirname(self.vm_path), "VoicemeeterRemote64.dll")
            self.vm_dll = ctypes.CDLL(dll_path)
            
            # Initialize the API
            result = self.vm_dll.VBVMR_Login()
            if result == 0:
                self.initialized = True
                logger.info("VoiceMeeter Remote API initialized")
            else:
                logger.error(f"Failed to initialize VoiceMeeter Remote API: {result}")
        except Exception as e:
            logger.error(f"Error initializing VoiceMeeter Remote API: {e}")
    
    def set_parameter(self, param_name: str, value: Any) -> bool:
        """Set a VoiceMeeter parameter"""
        if not self.initialized:
            return False
            
        try:
            if isinstance(value, bool):
                result = self.vm_dll.VBVMR_SetParameterFloat(param_name.encode(), float(value))
            elif isinstance(value, (int, float)):
                result = self.vm_dll.VBVMR_SetParameterFloat(param_name.encode(), float(value))
            else:
                result = self.vm_dll.VBVMR_SetParameterString(param_name.encode(), str(value).encode())
            
            return result == 0
        except Exception as e:
            logger.error(f"Error setting parameter {param_name}: {e}")
            return False
    
    def get_parameter(self, param_name: str) -> Optional[Any]:
        """Get a VoiceMeeter parameter value"""
        if not self.initialized:
            return None
            
        try:
            value = ctypes.c_float()
            result = self.vm_dll.VBVMR_GetParameterFloat(param_name.encode(), ctypes.byref(value))
            if result == 0:
                return value.value
            return None
        except Exception as e:
            logger.error(f"Error getting parameter {param_name}: {e}")
            return None
    
    def apply_profile(self, profile_name: str) -> bool:
        """Apply a saved profile"""
        if profile_name not in self.profiles:
            logger.error(f"Profile {profile_name} not found")
            return False
            
        try:
            profile = self.profiles[profile_name]
            for param, value in profile.items():
                if param != "description":  # Skip description field
                    if not self.set_parameter(param, value):
                        logger.error(f"Failed to set parameter {param}")
                        return False
            
            self.current_mode = profile_name
            logger.info(f"Applied profile: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Error applying profile {profile_name}: {e}")
            return False
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming ZMQ requests"""
        action = request.get("action")
        
        if action == "set_profile":
            profile_name = request.get("profile_name")
            if profile_name and self.apply_profile(profile_name):
                return {"status": "success", "message": f"Applied profile: {profile_name}"}
            return {"status": "error", "message": f"Failed to apply profile: {profile_name}"}
            
        elif action == "set_parameter":
            param_name = request.get("param_name")
            value = request.get("value")
            if param_name and value is not None and self.set_parameter(param_name, value):
                return {"status": "success", "message": f"Set parameter: {param_name}"}
            return {"status": "error", "message": f"Failed to set parameter: {param_name}"}
            
        elif action == "get_parameter":
            param_name = request.get("param_name")
            if param_name:
                value = self.get_parameter(param_name)
                if value is not None:
                    return {"status": "success", "value": value}
            return {"status": "error", "message": f"Failed to get parameter: {param_name}"}
            
        elif action == "get_profiles":
            return {"status": "success", "profiles": list(self.profiles.keys())}
            
        elif action == "get_current_mode":
            return {"status": "success", "mode": self.current_mode}
            
        return {"status": "error", "message": f"Unknown action: {action}"}
    
    def run(self):
        """Main agent loop"""
        logger.info("Starting VoiceMeeter Control Agent main loop")
        
        while True:
            try:
                # Wait for request
                request_str = self.socket.recv_string()
                request = json.loads(request_str)
                
                # Process request
                response = self.handle_request(request)
                
                # Send response
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.socket.send_string(json.dumps({
                    "status": "error",
                    "message": f"Internal error: {str(e)}"
                }))
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.initialized:
                self.vm_dll.VBVMR_Logout()
            self.socket.close()
            self.context.term()
            logger.info("VoiceMeeter Control Agent cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    agent = VoiceMeeterControlAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        agent.cleanup() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise