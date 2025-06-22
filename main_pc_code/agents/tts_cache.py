from src.core.base_agent import BaseAgent
import os
import hashlib
import pickle
import numpy as np
import sounddevice as sd
import logging
import time
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cache', 'tts')

# Ensure cache directory exists
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)

# Cache management
class TTSCache(BaseAgent):
    def __init__(self, port: int | None = None, *, max_size: int = 1000, cache_dir: str = CACHE_DIR, **kwargs):
        super().__init__(port=port, name="TtsCache")
        # Cache configuration
        self.max_size: int = max_size
        self.cache_dir: str = cache_dir
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

# Global cache instance created with CLI-provided arguments if available
# This allows external modules to import helper functions without running the agent loop.
_port_arg = getattr(_agent_args, "port", None)
_max_size_arg = getattr(_agent_args, "max_cache_size", 1000)

tts_cache = TTSCache(port=_port_arg, max_size=_max_size_arg)

# -------------------- Helper API --------------------
def get_cached_audio(text, emotion=None):
    """Get audio from cache if available"""
    return tts_cache.get_from_cache(text, emotion)
    
def add_to_cache(text, audio_data, emotion=None, sample_rate=16000):
    """Add audio to cache"""
    return tts_cache.add_to_cache(text, audio_data, emotion, sample_rate)
    
def play_cached_audio(audio_data, sample_rate=16000):
    """Play cached audio data"""
    return tts_cache.play_cached_audio(audio_data, sample_rate)
    
def clear_cache():
    """Clear the entire cache"""
    return tts_cache.clear_cache()


# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info(
        f"Starting TTSCache agent on port {tts_cache.port} (health: {tts_cache.health_check_port})"
    )
    try:
        tts_cache.run()
    except KeyboardInterrupt:
        logging.info("TTSCache agent interrupted by user")
