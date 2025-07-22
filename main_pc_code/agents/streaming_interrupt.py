from common.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Streaming Interrupt Detection Module
- Listens for interruption keywords in real-time while assistant is responding
- Uses Vosk (lightweight, local, supports Tagalog/English)
- Sends interrupt signal to main state machine via ZMQ
"""
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import queue
import sounddevice as sd
import vosk
try:
    import orjson
    # Use orjson for better performance
    json_loads = orjson.loads
    json_dumps = lambda obj, **kwargs: ororjson.dumps(obj).decode().decode()
except ImportError:
    import json
    json_loads = json.loads
    json_dumps = json.dumps
import threading
import time
import psutil
from datetime import datetime
from common.utils.path_env import get_main_pc_code, get_project_root

INTERRUPT_KEYWORDS = ["stop", "wait", "cancel", "pause", "change"]
ZMQ_PUB_PORT = 5562  # Custom port for interrupt signal
SAMPLE_RATE = 16000
DEVICE_INDEX = 39
MODEL_PATH = "vosk-model-small-en-ta"

class StreamingInterrupt(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingInterrupt")
        self.model = vosk.Model(MODEL_PATH)
        self.q = queue.Queue()
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.bind(f"tcp://*:{ZMQ_PUB_PORT}")
        self.running = True

    def audio_callback(self, indata, frames, time, status):
        self.q.put(bytes(indata))

    def run(self):
        rec = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize = 8000, device=DEVICE_INDEX, dtype='int16', channels=1, callback=self.audio_callback):
            print("[StreamingInterrupt] Listening for interrupt keywords...")
            while self.running:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    result = ororjson.loads(rec.Result())
                    text = result.get("text", "")
                    if any(kw in text for kw in INTERRUPT_KEYWORDS):
                        print(f"[StreamingInterrupt] Interrupt detected: {text}")
                        self.socket.send_string(ororjson.dumps({"type": "interrupt", "text": text}).decode().decode())
                        # Optional: Stop after first interrupt
                        # self.running = False


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
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    si = StreamingInterrupt()
    si.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise