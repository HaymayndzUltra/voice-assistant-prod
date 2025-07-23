# Containerized AI System Deployment Guide

This document provides instructions for deploying the AI system in containerized environments across MainPC and PC2.

## System Requirements

### MainPC
- NVIDIA RTX 4090 GPU (24GB VRAM)
- Ubuntu 22.04 (WSL2)
- NVIDIA Container Toolkit
- Podman or Docker
- Port range 5500-8000 available

### PC2
- NVIDIA RTX 3060 GPU (12GB VRAM)
- Ubuntu 22.04
- NVIDIA Container Toolkit
- Podman or Docker
- Port range 5500-8000 available

## Pre-Installation Steps

### 1. Install NVIDIA Container Toolkit

```bash
# On both MainPC and PC2
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
| curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add - |
| curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list |

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

### 2. Configure Podman (or Docker)

```bash
# For Podman
sudo systemctl restart podman

# For Docker
sudo systemctl restart docker
```

## Deployment Steps

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/AI_System_Monorepo.git
cd AI_System_Monorepo
```

### 2. Configure Network Settings

Edit `config/network_config.yaml` to set the correct IP addresses:

```yaml
network:
  mainpc_ip: "192.168.100.10"
  pc2_ip: "192.168.100.17"
  shared_network_name: "ai_system_network"
  use_secure_connections: true
```

### 3. Download Models

#### For MainPC

```bash
chmod +x docker/mainpc/model_setup.sh
./docker/mainpc/model_setup.sh
```

#### For PC2

Follow the instructions in `pc2_models_download_guide.txt` to download the necessary models for PC2.

### 4. Build and Start Containers

#### On MainPC

```bash
cd docker/mainpc
podman-compose build
podman-compose up -d
```

#### On PC2

```bash
cd docker/pc2
podman-compose build
podman-compose up -d
```

## Verifying Deployment

### 1. Check Container Status

```bash
# On MainPC
podman-compose ps

# On PC2
podman-compose ps
```

### 2. Check Agent Health

```bash
# On MainPC
python scripts/check_all_agents_health.py

# On PC2
python pc2_code/scripts/health_check.py
```

## Container Architecture

### MainPC Containers

1. **Core Services**
   - SystemDigitalTwin
   - RequestCoordinator
   - UnifiedSystemAgent

2. **Memory System**
   - SessionMemoryAgent
   - MemoryClient
   - KnowledgeBase

3. **Model Management**
   - ModelManagerAgent
   - VRAMOptimizerAgent
   - GGUFModelManager
   - PredictiveLoader
   - FaceRecognitionAgent

4. **Language Processing**
   - ModelOrchestrator
   - GoalManager
   - IntentionValidatorAgent
   - NLUAgent
   - AdvancedCommandHandler
   - ChitchatAgent
   - FeedbackHandler
   - Responder
   - TranslationService

5. **Audio Processing**
   - StreamingTTSAgent
   - StreamingInterruptHandler
   - StreamingSpeechRecognition
   - FusedAudioPreprocessor
   - AudioCapture
   - WakeWordDetector
   - StreamingLanguageAnalyzer

6. **Emotion System**
   - EmotionEngine
   - MoodTrackerAgent
   - HumanAwarenessAgent
   - ToneDetector
   - VoiceProfilingAgent
   - EmpathyAgent
   - EmotionSynthesisAgent

### PC2 Containers

1. **Core Services**
   - ErrorBus
   - MemoryOrchestratorService

2. **Translation Services**
   - NLLBTranslator
   - BergamotTranslator (optional)

3. **Security Services**
   - AuthenticationAgent

## Troubleshooting

### GPU Access Issues

If containers can't access the GPU:

```bash
# Check NVIDIA driver visibility
podman run --rm --gpus all nvidia/cuda:11.7.1-base-ubuntu22.04 nvidia-smi
```

### Network Communication Issues

If containers can't communicate:

```bash
# Check network configuration
podman network inspect ai_system_network

# Test connectivity
podman exec -it ai-system-mainpc-core ping 192.168.100.17
podman exec -it ai-system-pc2-core ping 192.168.100.10
```

### Container Logs

```bash
# View logs
podman logs ai-system-mainpc-core
podman logs ai-system-pc2-core
```

## Maintenance

### Update Models

To update models:

```bash
# On MainPC
./docker/mainpc/model_setup.sh

# On PC2
python -m pc2_code.scripts.update_models.py
```

### Backup Configuration

Before making changes, backup configuration:

```bash
cp -r config config_backup_$(date +%Y%m%d)
```

## Additional Resources

- [Model Configuration Guide](main_pc_code/_DOCUMENTSFINAL/implementation/models_configuration.md)
- [Error Management Documentation](documentation/error_management/error_management_config.yaml)
- [Cross-Machine Network Configuration](main_pc_code/_DOCUMENTSFINAL/implementation/cross_machine_network_config.md)