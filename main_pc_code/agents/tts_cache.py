from common.core.base_agent import BaseAgent
import os
import hashlib
import pickle
import numpy as np
import sounddevice as sd
import logging
import time
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.env_loader import get_env
import psutil
from datetime import datetime

# Load configuration at module level

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

config = load_config()

# Cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache', 'tts')

# Ensure cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)

# Cache management
class TTSCache(BaseAgent):
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5704)) if port is None else port
        agent_name = config.get("name", "TTSCache")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        self.start_time = time.time()
        self.running = True
        
        # Cache configuration
        self.max_size = int(config.get("max_cache_size", 1000))
        self.cache_dir = CACHE_DIR
        self.cache_index = {}
        self.load_cache_index()
        
    def load_cache_index(self):
        """Load the cache index from disk"""
        index_path = os.path.join(self.cache_dir, 'cache_index.pkl')
        if os.path.exists(index_path):
            try:
                with open(index_path, 'rb') as f:
                    self.cache_index = pickle.load(f)
                logging.info(f"[TTS Cache] Loaded {len(self.cache_index)} entries from cache index")
            except Exception as e:
                logging.error(f"[TTS Cache] Error loading cache index: {e}")
                self.cache_index = {}
        else:
            self.cache_index = {}
            
    def save_cache_index(self):
        """Save the cache index to disk"""
        index_path = os.path.join(self.cache_dir, 'cache_index.pkl')
        try:
            with open(index_path, 'wb') as f:
                pickle.dump(self.cache_index, f)
        except Exception as e:
            logging.error(f"[TTS Cache] Error saving cache index: {e}")
            
    def get_cache_key(self, text, emotion=None):
        """Generate a unique cache key for a text and emotion"""
        key_str = f"{text}_{emotion}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
        
    def get_from_cache(self, text, emotion=None):
        """Get audio from cache if available"""
        cache_key = self.get_cache_key(text, emotion)
        
        if cache_key in self.cache_index:
            cache_path = os.path.join(self.cache_dir, f"{cache_key}.npy")
            if os.path.exists(cache_path):
                try:
                    # Update access time
                    self.cache_index[cache_key]['last_accessed'] = time.time()
                    self.save_cache_index()
                    
                    # Load and return audio data
                    audio_data = np.load(cache_path)
                    return audio_data
                except Exception as e:
                    logging.error(f"[TTS Cache] Error loading cached audio: {e}")
                    
        return None
        
    def add_to_cache(self, text, audio_data, emotion=None, sample_rate=16000):
        """Add audio to cache"""
        cache_key = self.get_cache_key(text, emotion)
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.npy")
        
        try:
            # Save audio data
            np.save(cache_path, audio_data)
            
            # Update cache index
            self.cache_index[cache_key] = {
                'text': text,
                'emotion': emotion,
                'sample_rate': sample_rate,
                'created': time.time(),
                'last_accessed': time.time(),
                'file_path': cache_path
            }
            
            # Prune cache if necessary
            self._prune_cache_if_needed()
            
            # Save updated index
            self.save_cache_index()
            return True
        except Exception as e:
            logging.error(f"[TTS Cache] Error adding to cache: {e}")
            return False
            
    def _prune_cache_if_needed(self):
        """Remove oldest entries if cache exceeds max size"""
        if len(self.cache_index) <= self.max_size:
            return
            
        # Sort by last accessed time
        sorted_entries = sorted(
            self.cache_index.items(), 
            key=lambda x: x[1]['last_accessed']
        )
        
        # Remove oldest entries
        entries_to_remove = len(self.cache_index) - self.max_size
        for i in range(entries_to_remove):
            key, entry = sorted_entries[i]
            try:
                # Remove file
                if os.path.exists(entry['file_path']):
                    os.remove(entry['file_path'])
                # Remove from index
                del self.cache_index[key]
            except Exception as e:
                logging.error(f"[TTS Cache] Error pruning cache: {e}")
                
    def play_cached_audio(self, audio_data, sample_rate=16000):
        """Play cached audio data"""
        try:
            sd.play(audio_data, sample_rate)
            sd.wait()
            return True
        except Exception as e:
            logging.error(f"[TTS Cache] Error playing cached audio: {e}")
            return False
            
    def clear_cache(self):
        """Clear the entire cache"""
        try:
            for key, entry in self.cache_index.items():
                if os.path.exists(entry['file_path']):
                    os.remove(entry['file_path'])
            self.cache_index = {}
            self.save_cache_index()
            logging.info("[TTS Cache] Cache cleared")
            return True
        except Exception as e:
            logging.error(f"[TTS Cache] Error clearing cache: {e}")
            return False

    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

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
                    "cache_size": len(self.cache_index),
                    "max_cache_size": self.max_size
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
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time,
            "cache_entries": len(self.cache_index)
        }
        return {"status": status, "details": details}

# Global cache instance created with CLI-provided arguments if available
# This allows external modules to import helper functions without running the agent loop.
tts_cache = None

# -------------------- Helper API --------------------
def get_cached_audio(text, emotion=None):
    """Get audio from cache if available"""
    global tts_cache
    if tts_cache is None:
        tts_cache = TTSCache()
    return tts_cache.get_from_cache(text, emotion)
    
def add_to_cache(text, audio_data, emotion=None, sample_rate=16000):
    """Add audio to cache"""
    global tts_cache
    if tts_cache is None:
        tts_cache = TTSCache()
    return tts_cache.add_to_cache(text, audio_data, emotion, sample_rate)
    
def play_cached_audio(audio_data, sample_rate=16000):
    """Play cached audio data"""
    global tts_cache
    if tts_cache is None:
        tts_cache = TTSCache()
    return tts_cache.play_cached_audio(audio_data, sample_rate)
    
def clear_cache():
    """Clear the entire cache"""
    global tts_cache
    if tts_cache is None:
        tts_cache = TTSCache()
    return tts_cache.clear_cache()


# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Standardized main execution block
    agent = None
    try:
        agent = TTSCache()
        logging.info(f"Starting TTSCache agent on port {agent.port}")
        agent.run()
    except KeyboardInterrupt:
        logging.info("TTSCache agent interrupted by user")
    except Exception as e:
        import traceback
        logging.error(f"An unexpected error occurred in TTSCache: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logging.info("Cleaning up TTSCache agent...")
            agent.cleanup()