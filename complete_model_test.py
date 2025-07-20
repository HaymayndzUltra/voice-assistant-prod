#!/usr/bin/env python3
"""
🚀 COMPLETE MODEL TESTING SUITE
Tests LLM (Phi-3-Mini) + TTS (XTTS-v2) + GGUF support
Optimized for RTX 4090 testing setup

FEATURES:
- Phi-3-Mini LLM testing (HuggingFace + GGUF)
- XTTS-v2 TTS testing 
- Voice pipeline testing (Text → TTS)
- Performance benchmarking
- Memory optimization
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import psutil
import gc
import os
from pathlib import Path
import soundfile as sf
import numpy as np

# Try importing TTS libraries
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("⚠️ TTS library not installed. Run: pip install TTS")

# Try importing GGUF support
try:
    from llama_cpp import Llama
    GGUF_AVAILABLE = True
except ImportError:
    GGUF_AVAILABLE = False
    print("⚠️ llama-cpp-python not installed. Run: pip install llama-cpp-python")

class CompleteModelTester:
    """Complete model testing suite for RTX 4090"""
    
    def __init__(self):
        self.llm_model = None
        self.llm_tokenizer = None
        self.tts_model = None
        self.gguf_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Model paths
        self.models_dir = Path("models")
        self.gguf_dir = self.models_dir / "gguf"
        self.audio_dir = Path("audio_output")
        
        # Create directories
        self.models_dir.mkdir(exist_ok=True)
        self.gguf_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(exist_ok=True)
        
        print(f"🎯 Device: {self.device}")
        if self.device == "cuda":
            print(f"🔥 GPU: {torch.cuda.get_device_name()}")
            print(f"💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
        
    def download_gguf_models(self):
        """Download GGUF models for testing"""
        print(f"\n📦 DOWNLOADING GGUF MODELS...")
        
        gguf_models = {
            "phi-3-mini-4k-instruct-q4_K_M.gguf": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
            "mistral-7b-instruct-v0.2-q4_K_M.gguf": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        }
        
        for filename, url in gguf_models.items():
            filepath = self.gguf_dir / filename
            if not filepath.exists():
                print(f"🔽 Downloading {filename}...")
                print(f"   URL: {url}")
                print(f"   Use: wget -O {filepath} {url}")
            else:
                print(f"✅ {filename} already exists")
        
        return list(gguf_models.keys())
    
    def load_huggingface_llm(self):
        """Load Phi-3-Mini from HuggingFace"""
        print(f"\n🔽 LOADING PHI-3-MINI (HUGGINGFACE)...")
        
        try:
            start_time = time.time()
            
            # Load tokenizer
            print("📝 Loading tokenizer...")
            self.llm_tokenizer = AutoTokenizer.from_pretrained(
                "microsoft/Phi-3-mini-4k-instruct",
                trust_remote_code=True
            )
            
            # Load model
            print("🧠 Loading model...")
            self.llm_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Phi-3-mini-4k-instruct",
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            load_time = time.time() - start_time
            
            # Check VRAM usage
            if torch.cuda.is_available():
                vram_used = torch.cuda.memory_allocated() / 1e9
                print(f"💾 VRAM Used: {vram_used:.2f}GB")
            
            print(f"✅ HuggingFace LLM loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            print(f"❌ HuggingFace LLM loading failed: {e}")
            return False
    
    def load_gguf_llm(self, model_path=None):
        """Load GGUF model for testing"""
        if not GGUF_AVAILABLE:
            print("❌ GGUF support not available")
            return False
            
        print(f"\n🔽 LOADING GGUF MODEL...")
        
        if not model_path:
            # Try to find a GGUF model
            gguf_files = list(self.gguf_dir.glob("*.gguf"))
            if not gguf_files:
                print("❌ No GGUF models found. Download first!")
                return False
            model_path = gguf_files[0]
        
        try:
            start_time = time.time()
            
            print(f"📂 Loading: {model_path}")
            self.gguf_model = Llama(
                model_path=str(model_path),
                n_gpu_layers=-1,  # Use all GPU layers
                n_ctx=4096,       # Context length
                verbose=False
            )
            
            load_time = time.time() - start_time
            print(f"✅ GGUF model loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            print(f"❌ GGUF loading failed: {e}")
            return False
    
    def load_tts_model(self):
        """Load XTTS-v2 for TTS testing"""
        if not TTS_AVAILABLE:
            print("❌ TTS library not available")
            return False
            
        print(f"\n🔽 LOADING XTTS-V2...")
        
        try:
            start_time = time.time()
            
            # Initialize TTS with XTTS-v2
            self.tts_model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=True,
                gpu=torch.cuda.is_available()
            )
            
            load_time = time.time() - start_time
            
            # Check VRAM after TTS loading
            if torch.cuda.is_available():
                vram_used = torch.cuda.memory_allocated() / 1e9
                print(f"💾 Total VRAM Used: {vram_used:.2f}GB")
            
            print(f"✅ XTTS-v2 loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            print(f"❌ TTS loading failed: {e}")
            return False
    
    def test_huggingface_inference(self, prompt="Hello, how are you?"):
        """Test HuggingFace model inference"""
        if not self.llm_model or not self.llm_tokenizer:
            print("❌ HuggingFace model not loaded!")
            return None
            
        print(f"\n🎯 TESTING HUGGINGFACE INFERENCE:")
        print(f"📝 Prompt: '{prompt}'")
        
        try:
            start_time = time.time()
            
            # Tokenize and generate
            inputs = self.llm_tokenizer(prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.llm_model.generate(
                    **inputs,
                    max_new_tokens=100,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=self.llm_tokenizer.eos_token_id
                )
            
            response = self.llm_tokenizer.decode(outputs[0], skip_special_tokens=True)
            generated_text = response[len(prompt):].strip()
            
            inference_time = time.time() - start_time
            tokens_generated = len(outputs[0]) - len(inputs['input_ids'][0])
            tokens_per_second = tokens_generated / inference_time
            
            print(f"🤖 Response: '{generated_text}'")
            print(f"⏱️ Time: {inference_time:.2f}s")
            print(f"🚀 Speed: {tokens_per_second:.1f} tokens/sec")
            
            return {
                "text": generated_text,
                "inference_time": inference_time,
                "tokens_per_second": tokens_per_second,
                "model_type": "huggingface"
            }
            
        except Exception as e:
            print(f"❌ HuggingFace inference failed: {e}")
            return None
    
    def test_gguf_inference(self, prompt="Hello, how are you?"):
        """Test GGUF model inference"""
        if not self.gguf_model:
            print("❌ GGUF model not loaded!")
            return None
            
        print(f"\n🎯 TESTING GGUF INFERENCE:")
        print(f"📝 Prompt: '{prompt}'")
        
        try:
            start_time = time.time()
            
            # Generate with GGUF model
            response = self.gguf_model(
                prompt,
                max_tokens=100,
                temperature=0.7,
                stop=["</s>"],
                echo=False
            )
            
            generated_text = response['choices'][0]['text'].strip()
            inference_time = time.time() - start_time
            
            # Estimate tokens (rough)
            tokens_generated = len(generated_text.split())
            tokens_per_second = tokens_generated / inference_time
            
            print(f"🤖 Response: '{generated_text}'")
            print(f"⏱️ Time: {inference_time:.2f}s")
            print(f"🚀 Speed: {tokens_per_second:.1f} tokens/sec")
            
            return {
                "text": generated_text,
                "inference_time": inference_time,
                "tokens_per_second": tokens_per_second,
                "model_type": "gguf"
            }
            
        except Exception as e:
            print(f"❌ GGUF inference failed: {e}")
            return None
    
    def test_tts_synthesis(self, text="Hello, this is a test of text to speech synthesis."):
        """Test TTS synthesis"""
        if not self.tts_model:
            print("❌ TTS model not loaded!")
            return None
            
        print(f"\n🔊 TESTING TTS SYNTHESIS:")
        print(f"📝 Text: '{text}'")
        
        try:
            start_time = time.time()
            
            # Generate speech
            output_path = self.audio_dir / f"tts_test_{int(time.time())}.wav"
            
            # For XTTS-v2, we need a reference speaker (can use built-in)
            self.tts_model.tts_to_file(
                text=text,
                file_path=str(output_path),
                speaker_wav=None,  # Use default speaker
                language="en"      # English
            )
            
            synthesis_time = time.time() - start_time
            
            # Check file size
            if output_path.exists():
                file_size = output_path.stat().st_size / 1024  # KB
                print(f"🎵 Audio saved: {output_path}")
                print(f"📊 File size: {file_size:.1f}KB")
                print(f"⏱️ Synthesis time: {synthesis_time:.2f}s")
                
                return {
                    "output_path": str(output_path),
                    "synthesis_time": synthesis_time,
                    "file_size_kb": file_size,
                    "success": True
                }
            else:
                print("❌ Audio file not created")
                return None
                
        except Exception as e:
            print(f"❌ TTS synthesis failed: {e}")
            return None
    
    def test_complete_pipeline(self, prompt="Explain what artificial intelligence is in simple terms."):
        """Test complete LLM → TTS pipeline"""
        print(f"\n🚀 TESTING COMPLETE PIPELINE:")
        print(f"📝 Prompt: '{prompt}'")
        
        # Step 1: LLM inference
        llm_result = None
        if self.llm_model:
            llm_result = self.test_huggingface_inference(prompt)
        elif self.gguf_model:
            llm_result = self.test_gguf_inference(prompt)
        
        if not llm_result:
            print("❌ LLM inference failed, cannot continue pipeline")
            return None
        
        # Step 2: TTS synthesis
        generated_text = llm_result["text"]
        tts_result = self.test_tts_synthesis(generated_text)
        
        if not tts_result:
            print("❌ TTS synthesis failed")
            return None
        
        # Pipeline summary
        total_time = llm_result["inference_time"] + tts_result["synthesis_time"]
        
        print(f"\n🎯 PIPELINE COMPLETE:")
        print(f"   📝 LLM Time: {llm_result['inference_time']:.2f}s")
        print(f"   🔊 TTS Time: {tts_result['synthesis_time']:.2f}s")
        print(f"   ⏱️ Total Time: {total_time:.2f}s")
        print(f"   🎵 Audio: {tts_result['output_path']}")
        
        return {
            "llm_result": llm_result,
            "tts_result": tts_result,
            "total_time": total_time
        }
    
    def cleanup(self):
        """Clean up all models and free memory"""
        print(f"\n🧹 CLEANING UP...")
        
        # Clean up HuggingFace models
        if self.llm_model:
            del self.llm_model
            self.llm_model = None
        if self.llm_tokenizer:
            del self.llm_tokenizer
            self.llm_tokenizer = None
            
        # Clean up GGUF model
        if self.gguf_model:
            del self.gguf_model
            self.gguf_model = None
            
        # Clean up TTS model
        if self.tts_model:
            del self.tts_model
            self.tts_model = None
            
        # Force cleanup
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            vram_used = torch.cuda.memory_allocated() / 1e9
            print(f"💾 VRAM after cleanup: {vram_used:.2f}GB")
        
        print("✅ Cleanup complete")

def main():
    """Main testing function"""
    print("🚀 COMPLETE MODEL TESTING SUITE")
    print("Testing LLM + TTS + GGUF support")
    print("=" * 60)
    
    # System info
    print(f"🖥️ CPU: {psutil.cpu_count()} cores")
    print(f"💾 RAM: {psutil.virtual_memory().total / 1e9:.1f}GB")
    print(f"🔧 TTS Available: {TTS_AVAILABLE}")
    print(f"🔧 GGUF Available: {GGUF_AVAILABLE}")
    
    tester = CompleteModelTester()
    
    try:
        # Show GGUF download instructions
        print(f"\n📦 GGUF MODEL SETUP:")
        gguf_models = tester.download_gguf_models()
        
        # Load models (try different options)
        models_loaded = []
        
        # Try HuggingFace LLM
        if tester.load_huggingface_llm():
            models_loaded.append("huggingface_llm")
        
        # Try GGUF LLM
        if tester.load_gguf_llm():
            models_loaded.append("gguf_llm")
        
        # Try TTS
        if tester.load_tts_model():
            models_loaded.append("tts")
        
        print(f"\n✅ Models loaded: {models_loaded}")
        
        if not models_loaded:
            print("❌ No models loaded successfully!")
            return
        
        # Test individual components
        test_prompts = [
            "Hello, how are you today?",
            "Explain machine learning in simple terms.",
            "Write a Python function to add two numbers."
        ]
        
        for prompt in test_prompts:
            if "huggingface_llm" in models_loaded:
                tester.test_huggingface_inference(prompt)
            if "gguf_llm" in models_loaded:
                tester.test_gguf_inference(prompt)
        
        # Test TTS
        if "tts" in models_loaded:
            tester.test_tts_synthesis("This is a test of the text to speech system.")
        
        # Test complete pipeline
        if len(models_loaded) >= 2:  # Need LLM + TTS
            tester.test_complete_pipeline("What is the weather like today?")
        
    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main() 