# Distributed AI System Architecture

> **Hosts**  
> • **MainPC** – NVIDIA RTX 4090  
> • **PC2** – NVIDIA RTX 3060

---

## 1  High-Level Architecture Diagram

```mermaid
graph TD
  %%==================== MainPC ====================%%
  subgraph MAINPC [MainPC (RTX 4090)]
    direction TB
    %% Core Services
    subgraph Core_Services
      ServiceRegistry[ServiceRegistry\n7200 / 8200]
      SystemDigitalTwin[SystemDigitalTwin\n7220 / 8220]
      RequestCoordinator[RequestCoordinator\n26002 / 27002]
      UnifiedSystemAgent[UnifiedSystemAgent\n7225 / 8225]
      ObservabilityHub_MP[ObservabilityHub\n9000 / 9100]
      ModelManagerSuite[ModelManagerSuite*\n7211 / 8211]
      ServiceRegistry --> SystemDigitalTwin
      SystemDigitalTwin --> RequestCoordinator
      SystemDigitalTwin --> UnifiedSystemAgent
      SystemDigitalTwin -. metrics .-> ObservabilityHub_MP
      ModelManagerSuite -->|GPU| VRAMOptimizerAgent
    end

    %% GPU Infrastructure
    subgraph GPU_Infrastructure
      VRAMOptimizerAgent[VRAMOptimizerAgent*\n5572 / 6572]
    end

    %% Vision Processing (sample)
    subgraph Vision_Processing
      FaceRecognitionAgent[FaceRecognitionAgent*\n5610 / 6610]
    end
  end

  %%==================== PC2 ====================%%
  subgraph PC2 [PC2 (RTX 3060)]
    direction TB
    MemoryOrchestratorService[MemoryOrchestratorService\n7140 / 8140]
    TieredResponder[TieredResponder\n7100 / 8100]
    AsyncProcessor[AsyncProcessor\n7101 / 8101]
    CacheManager[CacheManager\n7102 / 8102]
    VisionProcessingAgent_PC2[VisionProcessingAgent*\n7150 / 8150]
    ObservabilityHub_PC2[ObservabilityHub\n9000 / 9100]
    MemoryOrchestratorService --> TieredResponder
    MemoryOrchestratorService --> CacheManager
    TieredResponder --> AsyncProcessor
    CacheManager --> VisionProcessingAgent_PC2
  end

  %%==================== Cross-Host Links ====================%%
  ObservabilityHub_PC2 --"cross-machine sync"--> ObservabilityHub_MP
  MemoryOrchestratorService -. data .-> SystemDigitalTwin
```
Note: Nodes marked with an asterisk (*) utilise GPU resources.

---

## 2  System Overview
The system is a distributed set of AI services running across two physical hosts:

• **MainPC** (Linux, NVIDIA RTX 4090) – runs core reasoning, language, memory, GPU-heavy LLM and vision components.  
• **PC2** (Linux, NVIDIA RTX 3060) – offloads memory orchestration, specialised tutoring/vision agents, and auxiliary services.  

Services communicate primarily over ZeroMQ and HTTP on a shared bridge network `ai_system_network` (subnet 172.20.0.0/16). Consolidated monitoring is provided by `ObservabilityHub`, which synchronises metrics between hosts.

---

## 3  System-Wide Settings
| Setting                                  | MainPC | PC2 |
|------------------------------------------|:------:|:---:|
| CPU limit                                | 80 %   | 80 % |
| RAM limit                                | 2048 MB| 4096 MB |
| Max threads per agent                    | 4      | 8 |
| Health-check interval / timeout / retries| 30 s / 10 s / 3 | 30 s / 10 s / 3 |
| Network bridge & subnet                  | `ai_system_network` 172.20.0.0/16 | same bridge |
| Volumes mounted                          | `./logs`, `./models`, `./data`, `./config` | n/a (handled per-agent) |

---

## 4  Agent / Service Catalogue

### Legend
• **Req.** – service marked `required: true` in config  
• **GPU** – service performs GPU inference or optimisation (RTX model shown)  
• **Deps** – direct runtime dependencies  

### 4.1  MainPC Agents (RTX 4090)

#### Core Services
| Name | Port / HC | Script Path | Req. | Deps | Notes |
|------|-----------|-------------|:----:|------|-------|
| ServiceRegistry | 7200 / 8200 | `main_pc_code/agents/service_registry_agent.py` | ✅ | – | In-memory registry (Redis optional) |
| SystemDigitalTwin | 7220 / 8220 | `main_pc_code/agents/system_digital_twin.py` | ✅ | ServiceRegistry | Central state DB, shared with PC2 agents |
| RequestCoordinator | 26002 / 27002 | `main_pc_code/agents/request_coordinator.py` | ✅ | SystemDigitalTwin | Orchestrates request routing |
| UnifiedSystemAgent | 7225 / 8225 | `main_pc_code/agents/unified_system_agent.py` | ✅ | SystemDigitalTwin | High-level orchestrator |
| ObservabilityHub | 9000 / 9100 | `phase1_implementation/.../observability_hub.py` | ✅ | SystemDigitalTwin | Consolidated monitoring; syncs with PC2 |
| ModelManagerSuite | 7211 / 8211 | `main_pc_code/model_manager_suite.py` | ✅ | SystemDigitalTwin | GPU model loading / VRAM budget (GPU-RTX 4090) |

... etc (tables for each group)

#### GPU Infrastructure
| Name | Port / HC | Path | Req. | Deps | GPU | Notes |
|------|-----------|------|:----:|------|-----|-------|
| VRAMOptimizerAgent | 5572 / 6572 | `main_pc_code/agents/vram_optimizer_agent.py` | ✅ | ModelManagerSuite, RequestCoordinator, SystemDigitalTwin | RTX 4090 | Dynamically frees/reserves VRAM |

#### Vision Processing
| Name | Port / HC | Path | Req. | Deps | GPU | Notes |
|------|-----------|------|:----:|------|-----|-------|
| FaceRecognitionAgent | 5610 / 6610 | `main_pc_code/agents/face_recognition_agent.py` | ✅ | ReqCoord, ModelManagerSuite, SystemDigitalTwin | RTX 4090 | Uses vision encoder on GPU |

*(Continue with other MainPC agent groups following the same table format — memory_system, utility_services, reasoning_services, language_processing, speech_services, audio_interface, emotion_system, etc.)*

### 4.2  PC2 Agents (RTX 3060)

| Name | Port / HC | Script Path | Req. | Deps | GPU | Notes |
|------|-----------|-------------|:----:|------|-----|-------|
| MemoryOrchestratorService | 7140 / 8140 | `pc2_code/agents/memory_orchestrator_service.py` | ✅ | – | – | Manages distributed memory shards |
| TieredResponder | 7100 / 8100 | `pc2_code/agents/tiered_responder.py` | ✅ | ResourceManager | – | Multi-tier response logic |
| AsyncProcessor | 7101 / 8101 | `pc2_code/agents/async_processor.py` | ✅ | ResourceManager | – | Background task executor |
| CacheManager | 7102 / 8102 | `pc2_code/agents/cache_manager.py` | ✅ | MemoryOrchestratorService | – | LRU / KV cache |
| VisionProcessingAgent | 7150 / 8150 | `pc2_code/agents/VisionProcessingAgent.py` | ✅ | CacheManager | RTX 3060 | GPU-accelerated inference |
| DreamWorldAgent | 7104 / 8104 | `pc2_code/agents/DreamWorldAgent.py` | ✅ | MemoryOrchestratorService | RTX 3060 | Generative dreaming mode |
| UnifiedMemoryReasoningAgent | 7105 / 8105 | `pc2_code/agents/unified_memory_reasoning_agent.py` | ✅ | MemoryOrchestratorService | – | Complex queries across memory shards |
| ObservabilityHub (PC2) | 9000 / 9100 | same as MainPC path | ✅ | — | – | `scope: pc2_agents`, syncs to MainPC hub |
| ... | ... | ... | ... | ... | ... | ... |

*(Continue for remaining PC2 agents.)*

---

## 5  Cross-Host Relationships & Data Flows
1. **ObservabilityHub ↔ Cross-Machine Sync** – PC2 hub pushes metrics to MainPC hub endpoint `http://192.168.100.16:9000`.
2. **MemoryOrchestratorService → SystemDigitalTwin** – distributed memory updates.
3. **VisionProcessingAgent (PC2) → FaceRecognitionAgent (MainPC)** – optional raw/processed vision frames.
4. **UnifiedWebAgent (PC2) → RequestCoordinator (MainPC)** – web-derived actions.

---

## 6  Update & Extension Guidelines
• Each new agent must declare: unique port + health port, dependencies, and whether it requires GPU.  
• Update the Mermaid diagram blocks (subgraphs) accordingly.  
• Keep cross-host links explicit for easier troubleshooting.

---

*Document generated automatically from `main_pc_code/config/startup_config.yaml` and `pc2_code/config/startup_config.yaml` — **{date}**.*