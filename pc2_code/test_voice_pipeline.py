import os
import json
import zmq
import wave
import numpy as np
import logging
import base64
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VoicePipelineTester")

class VoicePipelineTester:
    def __init__(self):
        self.context = zmq.Context()
        
        # Connect to Main PC's ASR service
        self.main_pc_socket = self.context.socket(zmq.REQ)
        self.main_pc_socket.connect("tcp://192.168.1.27:5570")  # Main PC's ASR port
        
        # Connect to PC2's ASR service
        self.pc2_socket = self.context.socket(zmq.REQ)
        self.pc2_socket.connect("tcp://192.168.1.2:5570")  # PC2's ASR port
        
        # Test audio samples
        self.test_samples = {
            "clean": "test_audio/clean_speech.wav",
            "noisy": "test_audio/noisy_speech.wav",
            "accent": "test_audio/accented_speech.wav",
            "silence": "test_audio/silence.wav"
        }
        
        # Create test audio directory if it doesn't exist
        os.makedirs("test_audio", exist_ok=True)
        
        # Generate test audio samples if they don't exist
        self._generate_test_audio()
    
    def _generate_test_audio(self):
        """Generate test audio samples if they don't exist"""
        if not os.path.exists(self.test_samples["clean"]):
            self._create_test_wav(self.test_samples["clean"], "This is a clean test sample.")
        
        if not os.path.exists(self.test_samples["noisy"]):
            self._create_test_wav(self.test_samples["noisy"], "This is a noisy test sample.", noise=True)
        
        if not os.path.exists(self.test_samples["accent"]):
            self._create_test_wav(self.test_samples["accent"], "This is an accented test sample.")
        
        if not os.path.exists(self.test_samples["silence"]):
            self._create_test_wav(self.test_samples["silence"], "", silence=True)
    
    def _create_test_wav(self, filename: str, text: str, noise: bool = False, silence: bool = False):
        """Create a test WAV file with the given text"""
        # Parameters
        sample_rate = 16000
        duration = 3.0  # seconds
        
        if silence:
            # Create silence
            samples = np.zeros(int(sample_rate * duration))
        else:
            # Create a simple sine wave for the text
            t = np.linspace(0, duration, int(sample_rate * duration))
            frequency = 440  # A4 note
            samples = np.sin(2 * np.pi * frequency * t)
            
            if noise:
                # Add noise
                noise_level = 0.1
                samples += np.random.normal(0, noise_level, len(samples))
        
        # Normalize
        samples = np.int16(samples * 32767)
        
        # Save as WAV
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(samples.tobytes())
    
    def test_asr(self, audio_file: str, machine: str = "main_pc") -> Dict[str, Any]:
        """Test ASR on the specified machine"""
        try:
            # Read audio file
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Base64 encode the audio data
            audio_data_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Prepare request
            request = {
                "action": "transcribe",
                "audio_data": audio_data_b64,
                "sample_rate": 16000,
                "channels": 1
            }
            
            # Send to appropriate machine
            socket = self.main_pc_socket if machine == "main_pc" else self.pc2_socket
            
            socket.send_json(request)
            if socket.poll(timeout=10000):  # 10 second timeout
                response = socket.recv_json()
                return response
            else:
                return {"status": "error", "message": "Request timed out"}
                
        except Exception as e:
            logger.error(f"ASR test failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def run_tests(self):
        """Run all voice pipeline tests"""
        results = []
        
        # Test clean speech on both machines
        logger.info("\nTesting clean speech...")
        for machine in ["main_pc", "pc2"]:
            result = self.test_asr(self.test_samples["clean"], machine)
            results.append({
                "test": "clean_speech",
                "machine": machine,
                "result": result
            })
            logger.info(f"{machine}: {json.dumps(result, indent=2)}")
        
        # Test noisy speech on both machines
        logger.info("\nTesting noisy speech...")
        for machine in ["main_pc", "pc2"]:
            result = self.test_asr(self.test_samples["noisy"], machine)
            results.append({
                "test": "noisy_speech",
                "machine": machine,
                "result": result
            })
            logger.info(f"{machine}: {json.dumps(result, indent=2)}")
        
        # Test accented speech on both machines
        logger.info("\nTesting accented speech...")
        for machine in ["main_pc", "pc2"]:
            result = self.test_asr(self.test_samples["accent"], machine)
            results.append({
                "test": "accented_speech",
                "machine": machine,
                "result": result
            })
            logger.info(f"{machine}: {json.dumps(result, indent=2)}")
        
        # Test silence on both machines
        logger.info("\nTesting silence...")
        for machine in ["main_pc", "pc2"]:
            result = self.test_asr(self.test_samples["silence"], machine)
            results.append({
                "test": "silence",
                "machine": machine,
                "result": result
            })
            logger.info(f"{machine}: {json.dumps(result, indent=2)}")
        
        # Save results
        with open("voice_pipeline_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info("\nTest results saved to voice_pipeline_test_results.json")
        
        # Clean up
        self.main_pc_socket.close()
        self.pc2_socket.close()
        self.context.term()

def main():
    tester = VoicePipelineTester()
    tester.run_tests()

if __name__ == "__main__":
    main() 