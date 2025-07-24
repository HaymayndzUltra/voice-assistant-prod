#!/usr/bin/env python3
"""
🔥 RTX 4090 MODEL DOWNLOADER
Download all premium models for the AI system

MODELS TO DOWNLOAD:
1. Meta-Llama-3-8B-Instruct (Premium LLM)
2. Mistral-7B-Instruct-v0.2 (Quality LLM)  
3. microsoft/phi-3-mini-4k-instruct (Fast LLM)
4. microsoft/phi-3-mini-128k-instruct (Long context)
5. openai/whisper-large-v3 (Premium STT)
6. coqui/XTTS-v2 (Premium TTS)
"""

import os
from pathlib import Path
from huggingface_hub import snapshot_download, login
import time

class ModelDownloader:
    """Download and cache all required models"""
    
    def __init__(self, cache_dir="models_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
                 # Model configuration matching our config file
        self.models = {
            # LLM Models
            "llama-3-8b-instruct": {
                "repo_id": "meta-llama/Meta-Llama-3-8B-Instruct",
                "size_gb": 16,  # Full model size
                "priority": 1,  # High priority
                "description": "🔥 Premium 8B LLM for reasoning tasks"
            },
            "phi-3-medium": {
                "repo_id": "microsoft/Phi-3-medium-4k-instruct", 
                "size_gb": 14,
                "priority": 2,
                "description": "💻 14B LLM optimized for coding tasks"
            },
            
            # STT Models - GPU ACCELERATED
            "whisper-large-v3": {
                "repo_id": "openai/whisper-large-v3",
                "size_gb": 6,
                "priority": 3,
                "description": "🎤 GPU-accelerated STT for best Tagalog accuracy"
            },
            
            # TTS Models  
            "xtts-v2": {
                "repo_id": "coqui/XTTS-v2",
                "size_gb": 5,
                "priority": 4,
                "description": "🔊 Premium TTS for natural speech"
            }
        }
        
    def check_hf_token(self):
        """Check if Hugging Face token is available"""
        token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
        if token:
            print(f"✅ Hugging Face token found")
            try:
                login(token=token)
                return True
            except Exception as e:
                print(f"⚠️ Token login failed: {e}")
                return False
        else:
            print(f"⚠️ No HF_TOKEN found. Some models may not download.")
            print(f"   For Llama models, get token from: https://huggingface.co/settings/tokens")
            return False
    
    def estimate_download_time(self, size_gb, speed_mbps=50):
        """Estimate download time based on file size and connection speed"""
        size_mb = size_gb * 1024
        time_seconds = (size_mb * 8) / speed_mbps
        time_minutes = time_seconds / 60
        return time_minutes
    
    def download_model(self, model_name, model_info):
        """Download a single model"""
        repo_id = model_info["repo_id"]
        size_gb = model_info["size_gb"]
        description = model_info["description"]
        
        print(f"\n🔽 DOWNLOADING: {model_name}")
        print(f"   📦 Repository: {repo_id}")
        print(f"   💾 Size: ~{size_gb}GB")
        print(f"   📝 {description}")
        
        # Estimate download time
        est_time = self.estimate_download_time(size_gb)
        print(f"   ⏱️ Estimated time: {est_time:.1f} minutes")
        
        try:
            start_time = time.time()
            
            # Download model to cache
            model_path = snapshot_download(
                repo_id=repo_id,
                cache_dir=str(self.cache_dir),
                resume_download=True,
                local_files_only=False
            )
            
            elapsed_time = time.time() - start_time
            elapsed_minutes = elapsed_time / 60
            
            print(f"   ✅ Downloaded to: {model_path}")
            print(f"   ⏱️ Actual time: {elapsed_minutes:.1f} minutes")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Download failed: {e}")
            
            # Special handling for Llama models (may need approval)
            if "llama" in repo_id.lower():
                print(f"   💡 Llama models may require:")
                print(f"      1. Accept license at: https://huggingface.co/{repo_id}")
                print(f"      2. Valid HF_TOKEN with access")
                
            return False
    
    def download_all_models(self):
        """Download all models in priority order"""
        print("🚀 RTX 4090 MODEL DOWNLOAD STARTED")
        print("=" * 50)
        
        # Check HF token
        has_token = self.check_hf_token()
        
        # Calculate total download size
        total_size = sum(model["size_gb"] for model in self.models.values())
        total_time_est = sum(self.estimate_download_time(model["size_gb"]) for model in self.models.values())
        
        print(f"\n📊 DOWNLOAD SUMMARY:")
        print(f"   🎯 Models to download: {len(self.models)}")
        print(f"   💾 Total size: ~{total_size}GB")
        print(f"   ⏱️ Estimated total time: {total_time_est:.1f} minutes")
        print(f"   💿 Cache directory: {self.cache_dir.absolute()}")
        
        # Sort by priority
        sorted_models = sorted(
            self.models.items(), 
            key=lambda x: x[1]["priority"]
        )
        
        success_count = 0
        failed_models = []
        
        for model_name, model_info in sorted_models:
            if self.download_model(model_name, model_info):
                success_count += 1
            else:
                failed_models.append(model_name)
        
        # Final summary
        print(f"\n🎉 DOWNLOAD COMPLETE!")
        print(f"   ✅ Successfully downloaded: {success_count}/{len(self.models)}")
        
        if failed_models:
            print(f"   ❌ Failed downloads: {failed_models}")
            print(f"   💡 Check internet connection and HF_TOKEN")
        else:
            print(f"   🎯 ALL MODELS READY FOR RTX 4090!")
            
        print(f"\n📂 Models cached in: {self.cache_dir.absolute()}")
        
    def list_downloaded_models(self):
        """List all currently downloaded models"""
        print("\n📋 DOWNLOADED MODELS:")
        
        if not self.cache_dir.exists():
            print("   ❌ No models downloaded yet")
            return
            
        model_dirs = [d for d in self.cache_dir.iterdir() if d.is_dir()]
        
        if not model_dirs:
            print("   ❌ No models found in cache")
            return
            
        for model_dir in sorted(model_dirs):
            size_mb = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file()) / (1024**2)
            print(f"   ✅ {model_dir.name} ({size_mb:.1f}MB)")

def main():
    """Main execution"""
    print("🔥 RTX 4090 MODEL DOWNLOADER")
    print("Downloading premium models for maximum AI performance")
    print("=" * 60)
    
    # Create downloader
    downloader = ModelDownloader()
    
    # Show current status
    downloader.list_downloaded_models()
    
    # Ask for confirmation
    print(f"\n⚠️ WARNING: This will download ~{sum(model['size_gb'] for model in downloader.models.values())}GB of models!")
    print(f"📡 Make sure you have good internet connection")
    print(f"💾 Make sure you have enough disk space")
    
    response = input(f"\n🤔 Continue with download? (y/N): ").lower().strip()
    
    if response in ['y', 'yes']:
        # Start download
        downloader.download_all_models()
    else:
        print(f"❌ Download cancelled")
        print(f"💡 Run this script again when ready")

if __name__ == "__main__":
    main() 