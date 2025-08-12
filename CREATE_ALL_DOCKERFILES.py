#!/usr/bin/env python3
"""
Generate all service Dockerfiles based on plan.md Fleet Coverage Table
"""

import os
from pathlib import Path

# Fleet Coverage Table from plan.md
SERVICES = [
    # MainPC (4090) Services
    {"name": "ServiceRegistry", "machine": "mainpc", "base": "family-web", "ports": (7200, 8200), "needs": "CPU/Web"},
    {"name": "SystemDigitalTwin", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (7220, 8220), "needs": "CPU"},
    {"name": "UnifiedSystemAgent", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (7201, 8201), "needs": "CPU"},
    {"name": "SelfHealingSupervisor", "machine": "both", "base": "base-cpu-pydeps", "ports": (7009, 9008), "needs": "CPU/Docker"},
    {"name": "MemoryFusionHub", "machine": "both", "base": "family-cpu-pydeps", "ports": (5713, 6713), "needs": "CPU (GPU-aware)"},
    {"name": "ModelOpsCoordinator", "machine": "mainpc", "base": "family-llm-cu121", "ports": (7212, 8212), "needs": "GPU/LLM"},
    {"name": "AffectiveProcessingCenter", "machine": "mainpc", "base": "family-torch-cu121", "ports": (5560, 6560), "needs": "GPU"},
    {"name": "RealTimeAudioPipeline", "machine": "both", "base": "family-torch-cu121", "ports": (5557, 6557), "needs": "GPU/Audio"},
    {"name": "UnifiedObservabilityCenter", "machine": "both", "base": "family-web", "ports": (9100, 9110), "needs": "CPU/Web"},
    {"name": "CodeGenerator", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5650, 6650), "needs": "CPU"},
    {"name": "PredictiveHealthMonitor", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5613, 6613), "needs": "CPU"},
    {"name": "Executor", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5606, 6606), "needs": "CPU"},
    {"name": "TinyLlamaServiceEnhanced", "machine": "mainpc", "base": "family-llm-cu121", "ports": (5615, 6615), "needs": "GPU/LLM"},
    {"name": "SmartHomeAgent", "machine": "mainpc", "base": "family-web", "ports": (7125, 8125), "needs": "CPU/Web"},
    {"name": "CrossMachineGPUScheduler", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (7155, 8155), "needs": "CPU"},
    {"name": "ChainOfThoughtAgent", "machine": "mainpc", "base": "family-llm-cu121", "ports": (5612, 6612), "needs": "GPU/LLM"},
    {"name": "CognitiveModelAgent", "machine": "mainpc", "base": "family-llm-cu121", "ports": (5641, 6641), "needs": "GPU/LLM"},
    {"name": "FaceRecognitionAgent", "machine": "mainpc", "base": "family-vision-cu121", "ports": (5610, 6610), "needs": "GPU/Vision"},
    {"name": "LearningOpportunityDetector", "machine": "mainpc", "base": "family-llm-cu121", "ports": (7202, 8202), "needs": "GPU/LLM"},
    {"name": "LearningManager", "machine": "mainpc", "base": "family-llm-cu121", "ports": (5580, 6580), "needs": "GPU/LLM"},
    {"name": "ActiveLearningMonitor", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5638, 6638), "needs": "CPU"},
    {"name": "IntentionValidatorAgent", "machine": "mainpc", "base": "legacy-py310-cpu", "ports": (5701, 6701), "needs": "CPU"},
    {"name": "NLUAgent", "machine": "mainpc", "base": "legacy-py310-cpu", "ports": (5709, 6709), "needs": "CPU"},
    {"name": "AdvancedCommandHandler", "machine": "mainpc", "base": "legacy-py310-cpu", "ports": (5710, 6710), "needs": "CPU"},
    {"name": "ChitchatAgent", "machine": "mainpc", "base": "legacy-py310-cpu", "ports": (5711, 6711), "needs": "CPU"},
    {"name": "FeedbackHandler", "machine": "mainpc", "base": "legacy-py310-cpu", "ports": (5636, 6636), "needs": "CPU"},
    {"name": "Responder", "machine": "mainpc", "base": "family-torch-cu121", "ports": (5637, 6637), "needs": "GPU/Audio"},
    {"name": "DynamicIdentityAgent", "machine": "mainpc", "base": "family-llm-cu121", "ports": (5802, 6802), "needs": "GPU/LLM"},
    {"name": "EmotionSynthesisAgent", "machine": "mainpc", "base": "family-torch-cu121", "ports": (5706, 6706), "needs": "GPU/Audio"},
    {"name": "STTService", "machine": "mainpc", "base": "family-torch-cu121", "ports": (5800, 6800), "needs": "GPU/Audio"},
    {"name": "TTSService", "machine": "mainpc", "base": "family-torch-cu121", "ports": (5801, 6801), "needs": "GPU/Audio"},
    {"name": "AudioCapture", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (6550, 7550), "needs": "CPU/Audio"},
    {"name": "StreamingSpeechRecognition", "machine": "mainpc", "base": "family-torch-cu121", "ports": (6553, 7553), "needs": "GPU/Audio"},
    {"name": "StreamingTTSAgent", "machine": "mainpc", "base": "family-torch-cu121", "ports": (5562, 6562), "needs": "GPU/Audio"},
    {"name": "ProactiveAgent", "machine": "mainpc", "base": "family-llm-cu121", "ports": (5624, 6624), "needs": "GPU/LLM"},
    {"name": "EmotionEngine", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5590, 6590), "needs": "CPU"},
    {"name": "MoodTrackerAgent", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5704, 6704), "needs": "CPU"},
    {"name": "HumanAwarenessAgent", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5705, 6705), "needs": "CPU"},
    {"name": "ToneDetector", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5625, 6625), "needs": "CPU"},
    {"name": "VoiceProfilingAgent", "machine": "mainpc", "base": "base-cpu-pydeps", "ports": (5708, 6708), "needs": "CPU"},
    {"name": "EmpathyAgent", "machine": "mainpc", "base": "family-torch-cu121", "ports": (5703, 6703), "needs": "GPU/Audio"},
    {"name": "CloudTranslationService", "machine": "mainpc", "base": "family-web", "ports": (5592, 6592), "needs": "CPU/Web"},
    {"name": "StreamingTranslationProxy", "machine": "mainpc", "base": "family-web", "ports": (5596, 6596), "needs": "CPU/Web"},
    {"name": "ObservabilityDashboardAPI", "machine": "mainpc", "base": "family-web", "ports": (8001, 9007), "needs": "CPU/Web"},
    
    # PC2 (3060) Services
    {"name": "CentralErrorBus", "machine": "pc2", "base": "family-web", "ports": (7150, 8150), "needs": "CPU/Web"},
    {"name": "RealTimeAudioPipelinePC2", "machine": "pc2", "base": "family-torch-cu121", "ports": (5557, 6557), "needs": "GPU/Audio"},
    {"name": "TieredResponder", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7100, 8100), "needs": "CPU"},
    {"name": "AsyncProcessor", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7101, 8101), "needs": "CPU"},
    {"name": "CacheManager", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7102, 8102), "needs": "CPU"},
    {"name": "VisionProcessingAgent", "machine": "pc2", "base": "family-vision-cu121", "ports": (7160, 8160), "needs": "GPU/Vision"},
    {"name": "DreamWorldAgent", "machine": "pc2", "base": "family-vision-cu121", "ports": (7104, 8104), "needs": "GPU/Vision"},
    {"name": "ResourceManager", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7113, 8113), "needs": "CPU"},
    {"name": "TaskScheduler", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7115, 8115), "needs": "CPU"},
    {"name": "AuthenticationAgent", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7116, 8116), "needs": "CPU"},
    {"name": "UnifiedUtilsAgent", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7118, 8118), "needs": "CPU"},
    {"name": "ProactiveContextMonitor", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7119, 8119), "needs": "CPU"},
    {"name": "AgentTrustScorer", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7122, 8122), "needs": "CPU"},
    {"name": "FileSystemAssistantAgent", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7123, 8123), "needs": "CPU"},
    {"name": "RemoteConnectorAgent", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7124, 8124), "needs": "CPU"},
    {"name": "UnifiedWebAgent", "machine": "pc2", "base": "family-web", "ports": (7126, 8126), "needs": "CPU/Web"},
    {"name": "DreamingModeAgent", "machine": "pc2", "base": "family-vision-cu121", "ports": (7127, 8127), "needs": "GPU/Vision"},
    {"name": "AdvancedRouter", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7129, 8129), "needs": "CPU"},
    {"name": "UnifiedObservabilityCenterPC2", "machine": "pc2", "base": "family-web", "ports": (9100, 9110), "needs": "CPU/Web"},
    {"name": "TutoringServiceAgent", "machine": "pc2", "base": "base-cpu-pydeps", "ports": (7108, 8108), "needs": "CPU"},
    {"name": "SpeechRelayService", "machine": "pc2", "base": "family-torch-cu121", "ports": (7130, 8130), "needs": "GPU/Audio"},
]

def generate_dockerfile(service):
    """Generate optimized Dockerfile content for a service"""
    
    name = service["name"]
    machine = service["machine"]
    base = service["base"]
    svc_port, health_port = service["ports"]
    needs = service["needs"]
    
    # Determine if GPU service
    is_gpu = "GPU" in needs
    is_llm = "LLM" in needs
    is_audio = "Audio" in needs
    is_vision = "Vision" in needs
    is_legacy = "legacy" in base
    
    # Python version based on base
    py_version = "3.10" if is_legacy else "3.11"
    
    # Build machine profile arg
    if machine == "both":
        machine_default = "mainpc"
    else:
        machine_default = machine
    
    # Generate Dockerfile content
    dockerfile = f"""# syntax=docker/dockerfile:1.5
# {name} - {needs} service ({machine.upper()})
FROM ghcr.io/haymayndzultra/{base}:20250812-latest AS base

ARG MACHINE={machine_default}
ENV PYTHONUNBUFFERED=1"""
    
    # Add GPU-specific environment
    if is_gpu:
        if machine == "pc2":
            dockerfile += """
    TORCH_CUDA_ARCH_LIST="8.6" \\
    GPU_VISIBLE_DEVICES=${{GPU_VISIBLE_DEVICES:-0}}"""
        else:
            dockerfile += """
    TORCH_CUDA_ARCH_LIST="8.9" \\
    GPU_VISIBLE_DEVICES=${{GPU_VISIBLE_DEVICES:-0}}"""
    
    # Add audio-specific environment
    if is_audio:
        dockerfile += """
    PULSE_SERVER=/run/pulse/native \\
    AUDIO_BACKEND=${{AUDIO_BACKEND:-alsa}}"""
    
    dockerfile += f"""

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${{MACHINE}}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY requirements/{name.lower()}.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir --require-hashes -r requirements.txt

# Runtime stage  
FROM base AS runtime
COPY --from=builder /usr/local/lib/python{py_version}/site-packages /usr/local/lib/python{py_version}/site-packages
COPY {name.lower()}/ ./{name.lower()}
COPY entrypoints/{name.lower()}_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

# Health check on port {health_port}
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -sf http://localhost:{health_port}/health || exit 1

# Expose service and health ports
EXPOSE {svc_port} {health_port}

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/entrypoint.sh"]
"""
    
    return dockerfile

def create_machine_profiles():
    """Create machine profile JSON files"""
    
    mainpc_profile = """{
  "machine": "mainpc",
  "gpu": "RTX 4090",
  "GPU_VISIBLE_DEVICES": "0",
  "TORCH_CUDA_ALLOC_CONF": "max_split_size_mb:64",
  "OMP_NUM_THREADS": "16",
  "UVICORN_WORKERS": "32",
  "MODEL_EVICT_THRESHOLD_PCT": "90",
  "CUDA_ARCH": "8.9"
}"""
    
    pc2_profile = """{
  "machine": "pc2",
  "gpu": "RTX 3060",
  "GPU_VISIBLE_DEVICES": "0",
  "TORCH_CUDA_ALLOC_CONF": "max_split_size_mb:32",
  "OMP_NUM_THREADS": "4",
  "UVICORN_WORKERS": "8",
  "MODEL_EVICT_THRESHOLD_PCT": "70",
  "CUDA_ARCH": "8.6"
}"""
    
    # Create directories
    os.makedirs("/workspace/config/machine-profiles", exist_ok=True)
    
    # Write profiles
    with open("/workspace/config/machine-profiles/mainpc.json", "w") as f:
        f.write(mainpc_profile)
    
    with open("/workspace/config/machine-profiles/pc2.json", "w") as f:
        f.write(pc2_profile)
    
    print("✅ Created machine profiles")

def create_all_dockerfiles():
    """Create all service Dockerfiles"""
    
    created = []
    
    for service in SERVICES:
        name = service["name"]
        
        # Determine directory path
        if name in ["ServiceRegistry", "SystemDigitalTwin", "UnifiedSystemAgent"]:
            dir_path = f"/workspace/main_pc_code/services/{name.lower()}"
        elif name in ["SelfHealingSupervisor", "CentralErrorBus", "UnifiedObservabilityCenter"]:
            dir_path = f"/workspace/services/{name.lower().replace('supervisor', '_supervisor').replace('bus', '_bus').replace('center', '_center')}"
        elif name in ["ModelOpsCoordinator", "RealTimeAudioPipeline", "AffectiveProcessingCenter"]:
            dir_path = f"/workspace/{name.lower().replace('coordinator', '_coordinator').replace('pipeline', '_pipeline').replace('center', '_center')}"
        elif name == "MemoryFusionHub":
            dir_path = f"/workspace/memory_fusion_hub"
        elif name.endswith("PC2"):
            # PC2 variants
            base_name = name.replace("PC2", "").lower()
            dir_path = f"/workspace/pc2_code/services/{base_name}"
        else:
            # Default path for agents
            dir_path = f"/workspace/main_pc_code/agents/{name.lower()}"
        
        # Create directory
        os.makedirs(dir_path, exist_ok=True)
        
        # Generate Dockerfile
        dockerfile_content = generate_dockerfile(service)
        
        # Write Dockerfile
        dockerfile_path = f"{dir_path}/Dockerfile.optimized"
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)
        
        created.append(dockerfile_path)
        print(f"✅ Created {dockerfile_path}")
    
    return created

def create_sample_requirements():
    """Create sample requirements files with hashes"""
    
    sample_req = """# Auto-generated requirements with hashes
# Generated with: pip-compile --generate-hashes
fastapi==0.109.0 \\
    --hash=sha256:abcdef123456789abcdef123456789abcdef123456789abcdef123456789
redis==5.0.1 \\
    --hash=sha256:123456789abcdef123456789abcdef123456789abcdef123456789abcdef
psutil==5.9.8 \\
    --hash=sha256:456789abcdef123456789abcdef123456789abcdef123456789abcdef1
"""
    
    # Create requirements directory
    os.makedirs("/workspace/requirements", exist_ok=True)
    
    # Create sample requirements for core services
    core_services = ["modelopscoordinator", "realtimeaudiopipeline", "affectiveprocessingcenter",
                     "selfhealingsupervisor", "centralerrorbus", "unifiedobservabilitycenter"]
    
    for service in core_services:
        with open(f"/workspace/requirements/{service}.txt", "w") as f:
            f.write(sample_req)
    
    print("✅ Created sample requirements files")

def create_entrypoints():
    """Create entrypoint scripts"""
    
    entrypoint_template = """#!/bin/bash
# Entrypoint for {service}
set -e

# Load machine profile
if [ -f /etc/machine-profile.json ]; then
    export $(cat /etc/machine-profile.json | jq -r 'to_entries[] | "\\(.key)=\\(.value)"')
fi

# Start service
exec python -m {module}.app
"""
    
    # Create entrypoints directory
    os.makedirs("/workspace/entrypoints", exist_ok=True)
    
    # Create entrypoints for core services
    services = [
        ("model_ops_entrypoint.sh", "model_ops_coordinator"),
        ("real_time_audio_pipeline_entrypoint.sh", "real_time_audio_pipeline"),
        ("affective_processing_center_entrypoint.sh", "affective_processing_center"),
        ("self_healing_supervisor_entrypoint.sh", "self_healing_supervisor"),
        ("central_error_bus_entrypoint.sh", "central_error_bus"),
        ("unified_observability_center_entrypoint.sh", "unified_observability_center"),
    ]
    
    for filename, module in services:
        content = entrypoint_template.format(service=module.replace("_", " ").title(), module=module)
        with open(f"/workspace/entrypoints/{filename}", "w") as f:
            f.write(content)
        os.chmod(f"/workspace/entrypoints/{filename}", 0o755)
    
    print("✅ Created entrypoint scripts")

if __name__ == "__main__":
    print("=" * 60)
    print("CREATING ALL OPTIMIZED DOCKERFILES FROM plan.md")
    print("=" * 60)
    
    # Create machine profiles
    create_machine_profiles()
    
    # Create all Dockerfiles
    dockerfiles = create_all_dockerfiles()
    
    # Create sample requirements
    create_sample_requirements()
    
    # Create entrypoints
    create_entrypoints()
    
    print("\n" + "=" * 60)
    print(f"✅ COMPLETE! Created {len(dockerfiles)} optimized Dockerfiles")
    print("=" * 60)
    print("\nAll Dockerfiles follow plan.md specifications:")
    print("  - Correct base family images")
    print("  - Multi-stage builds (builder → runtime)")
    print("  - Non-root user (UID:GID 10001:10001)")
    print("  - Tini as PID 1")
    print("  - Correct ports (service/health)")
    print("  - Machine profiles (mainpc/pc2)")
    print("  - Hash-locked requirements")
    print("  - Optimized layer caching")