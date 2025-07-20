#!/usr/bin/env python3
"""
🚀 PHI-3-MINI TESTING SCRIPT
Optimized for RTX 4090 testing setup

FEATURES:
- Proper GPU allocation
- Memory optimization  
- Error handling
- Performance monitoring
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import psutil
import gc

class Phi3MiniTester:
    """Test Phi-3-Mini model with RTX 4090 optimization"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"🎯 Device: {self.device}")
        if self.device == "cuda":
            print(f"🔥 GPU: {torch.cuda.get_device_name()}")
            print(f"💾 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
        
    def load_model(self):
        """Load Phi-3-Mini with RTX 4090 optimization"""
        print(f"\n🔽 LOADING PHI-3-MINI...")
        
        try:
            start_time = time.time()
            
            # Load tokenizer first (smaller, faster)
            print("📝 Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                "microsoft/Phi-3-mini-4k-instruct",
                trust_remote_code=True
            )
            
            # Load model with optimizations
            print("🧠 Loading model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Phi-3-mini-4k-instruct",
                torch_dtype=torch.float16,          # ✅ Half precision for speed
                device_map="auto",                  # ✅ Auto GPU allocation
                trust_remote_code=True,
                attn_implementation="flash_attention_2" if hasattr(torch.nn, 'flash_attention_2') else "eager"
            )
            
            load_time = time.time() - start_time
            
            # Check VRAM usage
            if torch.cuda.is_available():
                vram_used = torch.cuda.memory_allocated() / 1e9
                vram_cached = torch.cuda.memory_reserved() / 1e9
                print(f"💾 VRAM Used: {vram_used:.2f}GB")
                print(f"📦 VRAM Cached: {vram_cached:.2f}GB")
            
            print(f"✅ Model loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            print(f"❌ Loading failed: {e}")
            return False
    
    def test_inference(self, prompt="Hello, how are you?"):
        """Test model inference"""
        if not self.model or not self.tokenizer:
            print("❌ Model not loaded!")
            return None
            
        print(f"\n🎯 TESTING INFERENCE:")
        print(f"📝 Prompt: '{prompt}'")
        
        try:
            start_time = time.time()
            
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            inference_time = time.time() - start_time
            
            # Extract only the generated part
            generated_text = response[len(prompt):].strip()
            
            print(f"🤖 Response: '{generated_text}'")
            print(f"⏱️ Inference time: {inference_time:.2f}s")
            
            # Performance metrics
            tokens_generated = len(outputs[0]) - len(inputs['input_ids'][0])
            tokens_per_second = tokens_generated / inference_time
            print(f"🚀 Speed: {tokens_per_second:.1f} tokens/sec")
            
            return {
                "prompt": prompt,
                "response": generated_text,
                "inference_time": inference_time,
                "tokens_per_second": tokens_per_second
            }
            
        except Exception as e:
            print(f"❌ Inference failed: {e}")
            return None
    
    def test_tagalog_prompt(self):
        """Test with Tagalog/English prompt"""
        tagalog_prompt = "Kumusta ka? Paano mo ako matutulungan?"
        
        print(f"\n🇵🇭 TESTING TAGALOG PROMPT:")
        return self.test_inference(tagalog_prompt)
    
    def test_coding_prompt(self):
        """Test with coding prompt"""
        coding_prompt = "Write a Python function to calculate fibonacci numbers:"
        
        print(f"\n💻 TESTING CODING PROMPT:")
        return self.test_inference(coding_prompt)
    
    def benchmark_performance(self):
        """Run performance benchmark"""
        print(f"\n⚡ PERFORMANCE BENCHMARK:")
        
        test_prompts = [
            "What is artificial intelligence?",
            "Explain machine learning in simple terms.",
            "Write a hello world program in Python.",
            "Ano ang AI? Ipaliwanag mo sa simple na paraan.",
            "Create a function to sort a list."
        ]
        
        results = []
        total_time = 0
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n📊 Test {i}/{len(test_prompts)}")
            result = self.test_inference(prompt)
            if result:
                results.append(result)
                total_time += result["inference_time"]
        
        if results:
            avg_time = total_time / len(results)
            avg_tokens_per_sec = sum(r["tokens_per_second"] for r in results) / len(results)
            
            print(f"\n🎯 BENCHMARK RESULTS:")
            print(f"   ✅ Successful tests: {len(results)}/{len(test_prompts)}")
            print(f"   ⏱️ Average time: {avg_time:.2f}s")
            print(f"   🚀 Average speed: {avg_tokens_per_sec:.1f} tokens/sec")
            
            # VRAM usage after benchmark
            if torch.cuda.is_available():
                vram_used = torch.cuda.memory_allocated() / 1e9
                print(f"   💾 Final VRAM: {vram_used:.2f}GB")
    
    def cleanup(self):
        """Clean up model and free memory"""
        print(f"\n🧹 CLEANING UP...")
        
        if self.model:
            del self.model
            self.model = None
            
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
            
        # Force garbage collection
        gc.collect()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            vram_used = torch.cuda.memory_allocated() / 1e9
            print(f"💾 VRAM after cleanup: {vram_used:.2f}GB")
        
        print("✅ Cleanup complete")

def main():
    """Main testing function"""
    print("🚀 PHI-3-MINI RTX 4090 TESTING")
    print("=" * 50)
    
    # Check system info
    print(f"🖥️ CPU: {psutil.cpu_count()} cores")
    print(f"💾 RAM: {psutil.virtual_memory().total / 1e9:.1f}GB")
    
    # Create tester
    tester = Phi3MiniTester()
    
    try:
        # Load model
        if not tester.load_model():
            print("❌ Model loading failed, exiting...")
            return
        
        # Basic test
        tester.test_inference("Hello, how are you today?")
        
        # Tagalog test
        tester.test_tagalog_prompt()
        
        # Coding test
        tester.test_coding_prompt()
        
        # Full benchmark
        tester.benchmark_performance()
        
    except KeyboardInterrupt:
        print("\n⏹️ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        # Always cleanup
        tester.cleanup()

if __name__ == "__main__":
    main() 