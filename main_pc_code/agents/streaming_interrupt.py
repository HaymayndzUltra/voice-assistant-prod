from src.core.base_agent import BaseAgent
"""
Streaming Interrupt Detection Module
- Listens for interruption keywords in real-time while assistant is responding
- Uses Vosk (lightweight, local, supports Tagalog/English)
- Sends interrupt signal to main state machine via ZMQ
"""
import zmq
import queue
import sounddevice as sd
import vosk
import json
import threading

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
                    result = json.loads(rec.Result())
                    text = result.get("text", "")
                    if any(kw in text for kw in INTERRUPT_KEYWORDS):
                        print(f"[StreamingInterrupt] Interrupt detected: {text}")
                        self.socket.send_string(json.dumps({"type": "interrupt", "text": text}))
                        # Optional: Stop after first interrupt
                        # self.running = False

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
