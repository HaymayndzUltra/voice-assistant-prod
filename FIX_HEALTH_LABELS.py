#!/usr/bin/env python3
"""
Add health_check_port LABEL to all optimized Dockerfiles
"""

import os
import re

# Service to health port mapping from plan.md
HEALTH_PORTS = {
    "ModelOpsCoordinator": 8212,
    "RealTimeAudioPipeline": 6557,
    "AffectiveProcessingCenter": 6560,
    "UnifiedObservabilityCenter": 9110,
    "MemoryFusionHub": 6713,
    "SelfHealingSupervisor": 9008,
    "CentralErrorBus": 8150,
}

def add_health_label(dockerfile_path, health_port):
    """Add LABEL health_check_port to Dockerfile"""
    
    with open(dockerfile_path, 'r') as f:
        content = f.read()
    
    # Check if label already exists
    if 'LABEL health_check_port=' in content:
        print(f"  ⚠️  Label already exists in {dockerfile_path}")
        return
    
    # Find where to insert label (after USER appuser)
    pattern = r'(USER appuser\n)'
    replacement = f'\\1\n# Label for validation script\nLABEL health_check_port="{health_port}"\n'
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        with open(dockerfile_path, 'w') as f:
            f.write(new_content)
        print(f"  ✅ Added health_check_port={health_port} to {dockerfile_path}")
    else:
        print(f"  ❌ Could not add label to {dockerfile_path}")

def main():
    print("=" * 60)
    print("ADDING HEALTH PORT LABELS TO DOCKERFILES")
    print("=" * 60)
    
    # Core services
    dockerfiles = [
        ("/workspace/model_ops_coordinator/Dockerfile.optimized", 8212),
        ("/workspace/real_time_audio_pipeline/Dockerfile.optimized", 6557),
        ("/workspace/affective_processing_center/Dockerfile.optimized", 6560),
        ("/workspace/unified_observability_center/Dockerfile.optimized", 9110),
        ("/workspace/memory_fusion_hub/Dockerfile.optimized", 6713),
        ("/workspace/services/self_healing_supervisor/Dockerfile.optimized", 9008),
        ("/workspace/services/central_error_bus/Dockerfile.optimized", 8150),
    ]
    
    for path, port in dockerfiles:
        if os.path.exists(path):
            add_health_label(path, port)
        else:
            print(f"  ❌ File not found: {path}")
    
    print("\n" + "=" * 60)
    print("✅ HEALTH LABELS ADDED!")
    print("=" * 60)
    
    # Also update machine profiles with correct workers
    print("\nUpdating machine profiles with optimized worker counts...")
    
    mainpc_profile = """{
  "machine": "mainpc",
  "gpu": "RTX 4090",
  "GPU_VISIBLE_DEVICES": "0",
  "TORCH_CUDA_ALLOC_CONF": "max_split_size_mb:64",
  "OMP_NUM_THREADS": "16",
  "UVICORN_WORKERS": "8",
  "UVICORN_WORKERS_GPU": "4",
  "MODEL_EVICT_THRESHOLD_PCT": "90",
  "CUDA_ARCH": "8.9"
}"""
    
    pc2_profile = """{
  "machine": "pc2",
  "gpu": "RTX 3060",
  "GPU_VISIBLE_DEVICES": "0",
  "TORCH_CUDA_ALLOC_CONF": "max_split_size_mb:32",
  "OMP_NUM_THREADS": "4",
  "UVICORN_WORKERS": "4",
  "UVICORN_WORKERS_GPU": "2",
  "MODEL_EVICT_THRESHOLD_PCT": "70",
  "CUDA_ARCH": "8.6"
}"""
    
    with open("/workspace/config/machine-profiles/mainpc.json", "w") as f:
        f.write(mainpc_profile)
    print("  ✅ Updated mainpc.json with optimized worker counts")
    
    with open("/workspace/config/machine-profiles/pc2.json", "w") as f:
        f.write(pc2_profile)
    print("  ✅ Updated pc2.json with optimized worker counts")

if __name__ == "__main__":
    main()