Hybrid LLM Migration — Three-Phase Action Plan
(snapshot branch – no impact on prod)
Phase 1 – Deep Analysis
1.1 Classification Method
Token footprint (avg. prompt + completion).
Compute profile (GPU RAM / CUDA cores / CPU).
Latency-sensitivity (streaming vs. batch).
Coupling (tight links → keep co-located).
> Rule-of-thumb:
> • >3 k tokens per call = “Heavy”
> • GPU VRAM >5 GB or training loops = “Compute-Heavy-Local”
> • Sub-second response, small tensors = “Light”
1.2 Agent-by-Agent Matrix
Agent	Old Role	New Role / Removal	Reason
ServiceRegistry	Orchestrator	Light (Local 4090)	tiny payload, mostly metadata
SystemDigitalTwin	State graph builder	Light (Local)	pointer-chasing, <0.5 k tokens
RequestCoordinator	Router	Light (Local)	control-plane logic
UnifiedSystemAgent	Macro dispatcher	Light (Local)	orchestration only
ObservabilityHub	Telemetry	Singleton (MainPC)	authoritative hub; duplicates removed
MetricsForwarder (PC2)	Metrics push	Light (PC2)	forwards Prometheus remote-write → ObservabilityHub
ModelManagerSuite	Model lifecycle	Light (Local) → now governs both local & API	extend with API registry
MemoryClient	Vector read	Light (Local)	…
SessionMemoryAgent	Session cache	Light (Local)	…
KnowledgeBase	Retrieval	Light (Local)	…
CodeGenerator	Code LLM	Heavy → Remote API (GPT-4)	>6 k tokens, high accuracy need
SelfTrainingOrchestrator	Auto-fine-tune	Heavy → Remote API fine-tuning endpoint	multi-epoch cost billed to API
PredictiveHealthMonitor	Simple stats	Light (Local)	<1 k tokens
FixedStreamingTranslation	Low-latency translator	Light (Local)	sub-1 k tokens, CPU OK
Executor	Unit-task runner	Light (Local)	Python exec; small
TinyLlamaServiceEnhanced	1.1 B LLM	Compute-Heavy-Local (4090)	VRAM OK, avoids API cost
LocalFineTunerAgent	LoRA on-device	Compute-Heavy-Local	uses 4090 GPU
NLLBAdapter	Mass translation	Heavy → Remote API (NLLB via Bedrock)	3 k+ tokens, many languages
VRAMOptimizerAgent	GPU mgr	Local (must stay)	hardware-bound
ChainOfThoughtAgent	Long CoT	Heavy → Remote API	8 k token chains
GoTToTAgent	“Game-of-Thought”	Heavy → Remote API	…
CognitiveModelAgent	Reflection loops	Heavy → Remote API	…
FaceRecognitionAgent	Vision CNN	Compute-Heavy-Local	TensorRT-optimised
LearningOrchestrationService	Curriculum	Heavy → Remote API	5 k+ tokens
LearningOpportunityDetector	Classifier	Light (Local)	small
LearningManager	Scheduler	Light (Local)	…
ActiveLearningMonitor	Metrics	Light (Local)	…
LearningAdjusterAgent	Policy edits	Heavy → Remote API	summarisation 4 k
ModelOrchestrator	Prompt router	Heavy → Remote API	dynamic prompting
GoalManager	Goal rewrite	Heavy → Remote API	long context
IntentionValidatorAgent	Classifier	Light (Local)	<512 tokens
NLUAgent	Parsing	Heavy → Remote API	deep semantic parse
AdvancedCommandHandler	Command exec	Light (Local)	rule-based
ChitchatAgent	Small-talk	Heavy → Remote API (GPT-3.5)	high frequency, >3 k total/day
FeedbackHandler	Slot-fill	Light (Local)	…
Responder	Template gen	Light (Local)	…
TranslationService	Full text	Heavy → Remote API	multi-k tokens
DynamicIdentityAgent	Persona switch	Light (Local)	<1 k
EmotionSynthesisAgent	Affect text	Light (Local)	…
STTService / TTSService	Whisper & TTS	Compute-Heavy-Local (4090)	realtime audio
AudioCapture … WakeWordDetector	Audio I/O	Light (Local)	signal level
ProactiveAgent	Long prompts	Heavy → Remote API	planning 4 k
EmotionEngine / MoodTrackerAgent / HumanAwarenessAgent / ToneDetector / VoiceProfilingAgent / EmpathyAgent	Affect loop	Mixed small calls	Light (Local)
PC2-only agents: mostly orchestration; remain Light, but can be migrated if MainPC fails.
Redundant/Consolidated
ObservabilityHub appears in both lists → keep single instance on MainPC.
ObservabilityHub is now a **singleton on MainPC**; **MetricsForwarder** replaces any secondary hubs on PC2. A standby `observability-hub-standby` container (replicas 0) can be enabled via feature flag if MainPC hub goes down.
DreamWorldAgent & DreamingModeAgent (PC2) duplicate long-context reasoning → replaced by Remote GPT; remove.
Phase 2 – Design & Allocation
2.1 Target Placement
Tier	Location	Agents
Remote API	OpenAI / Bedrock	CodeGenerator, SelfTrainingOrchestrator, ChainOfThoughtAgent, GoTToTAgent, CognitiveModelAgent, LearningOrchestrationService, LearningAdjusterAgent, ModelOrchestrator, GoalManager, NLUAgent, ChitchatAgent, TranslationService, ProactiveAgent, NLLBAdapter
Local GPU (MainPC, RTX-4090)	TinyLlamaServiceEnhanced, LocalFineTunerAgent, FaceRecognitionAgent, STTService, TTSService, VRAMOptimizerAgent	
Local CPU (MainPC)	all Light agents from Phase 1 **+ ObservabilityHub (singleton)**
Fallback GPU/CPU (PC2)	same Light set (**minus ObservabilityHub**)
			+ MetricsForwarder + TinyLlamaServiceEnhanced (quantised)
Fail-over uses docker-compose.pc2.individual.yml with ports 7100–7199 (CPU) & 8100–8199 (GPU).
### 2.2 Dependency Graph (simplified)


User
 └─► RequestCoordinator
      ├─► ModelManagerSuite
      │    ├─► RemoteApiAdapter │ ──► OpenAI/Bedrock
      │    └─► LocalModelPool  │ ──► TinyLlama, Whisper, … (4090)
      ├─► MemoryClient ──► VectorDB
      ├─► SystemDigitalTwin
      └─► ObservabilityHub (logs)
     └─► MetricsForwarder (PC2) ──► ObservabilityHub

New component: RemoteApiAdapter (language + vision endpoints) registered inside ModelManagerSuite.
### 2.3 Interface Shims 1. RemoteApiAdapter implements generate(), embed(), translate(); swaps via feature flag. 2. TinyLlamaServiceEnhanced now adheres to the same interface (AgentLLMBase) so callers stay unchanged.
### 2.4 New Docker-Compose Snippets

# docker-compose.hybrid.yml  (excerpt)
services:

  remote-api-adapter:
    image: ghcr.io/myorg/remote-api-adapter:${GIT_SHA}
    secrets:
      - openai_api_key
      - bedrock_key
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 512M

  tiny-llama:
    image: ghcr.io/myorg/tiny-llama:${GIT_SHA}
    runtime: nvidia
    environment:
      MODEL_PATH: /mnt/models/tiny-llama
    volumes:
      - model-cache:/mnt/models
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
        limits:
          memory: 8G

  metrics-forwarder:
    image: prom/remote-write:latest
    environment:
      HUB_ENDPOINT: http://observability-hub:9090
    deploy:
      resources:
        limits:
          cpus: '0.10'
          memory: 256M

  observability-hub-standby:
    image: ghcr.io/myorg/observability-hub:${GIT_SHA}
    deploy:
      replicas: 0  # disabled by default; toggle via FEATURE_ENABLE_STANDBY_HUB

secrets:
  openai_api_key:
    file: ./secrets/openai_api_key
  bedrock_key:
    file: ./secrets/bedrock_key

(docker-compose.pc2.individual.yml will mount same images but on port 8101, low-GPU mem flag --load-in-4bit) ---
## Phase 3 – Implementation Blueprint
### 3.1 Core Skeletons
remote_api_adapter/adapter.py

from typing import List
import openai, boto3

class RemoteApiAdapter:                      # unifies OpenAI & Bedrock
    def __init__(self, provider="openai"):
        self.provider = provider
        if provider == "openai":
            openai.api_key = os.getenv("OPENAI_API_KEY")
        else:
            self.bedrock = boto3.client("bedrock-runtime")

    def generate(self, prompt: str, model="gpt-4o", max_tokens=4096) -> str:
        if self.provider == "openai":
            rsp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                stream=False,
            )
            return rsp.choices[0].message.content
        else:
            body = {"prompt": prompt, "maxTokens": max_tokens}
            rsp = self.bedrock.invoke_model(body=body, modelId=model)
            return rsp["body"]["completion"]

    def embed(self, text: List[str], model="text-embedding-3-small"):
        # … similar …
        ...

    def translate(self, text: str, target_lang: str):
        # route to NLLB on Bedrock
        ...

model_manager_suite/registry.py (patch-diff)


- from local_models import LocalModelPool
+ from local_models import LocalModelPool
+ from remote_api_adapter.adapter import RemoteApiAdapter

  class ModelManagerSuite:
      def __init__(self):
          self.local = LocalModelPool()
+         self.remote = RemoteApiAdapter(provider="openai")
  
      def dispatch(self, task, *args, **kwargs):
          if self._is_heavy(task):
-             return self.local.generate(task, *args, **kwargs)
+             return self.remote.generate(*args, **kwargs)
          ...

### 3.2 Dockerfile Template (GPU-enabled example)

# syntax=docker/dockerfile:1.7
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS base
RUN apt-get update && apt-get install -y python3-pip git && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache \
    pip install -r requirements.txt
COPY . /app
WORKDIR /app
RUN python -m agent --health-check           # smoke test
ENTRYPOINT ["python", "-m", "agent"]

### 3.3 Nightly Build Matrix (GitHub Actions)


jobs:
  build-push:
    strategy:
      matrix:
        agent: [remote-api-adapter, tiny-llama, ...]
        platform: [cpu, gpu]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker buildx build \
             --push --platform linux/amd64 \
             --tag ghcr.io/myorg/${{matrix.agent}}:${{github.sha}} \
             -f docker/${{matrix.agent}}.Dockerfile .


### 3.4 Verification Steps
1. Unit tests: • Mock OpenAI & Bedrock; assert adapter fall-back logic. 2. Smoke tests (already in Dockerfile). 3. Integration: • Run docker-compose.hybrid.yml up -d; health endpoints /healthz. • Fire sample 5 k-token prompt → ensure traffic hits Remote API. 4. Fail-over drill: • Stop MainPC tiny-llama; bring up PC2 variant; latency <1.2× baseline. 5. Metrics: • ObservabilityHub dashboard shows token & cost counters.
---
## ✅ Outcome & Next Steps
1. All Heavy-token reasoning & translation workloads shift to scalable, cost-metered Remote LLMs. 2. Local RTX-4090 handles inference/training that benefits from on-prem GPU. 3. No existing Docker files touched; new blueprint cleanly co-exists. 4. Implementation can be merged behind a feature flag, rolled out per-agent.
Hand-off to DevOps for image publishing; QA can begin running the health matrix today.

### 2.6 RemoteApiAdapter Integration Notes (NEW)
```
from remote_api_adapter.adapter import RemoteApiAdapter
adapter = RemoteApiAdapter()
```
Minimal patches:
* translation_service/translator.py
```
- result = local_model.translate(text, tgt)
+ result = adapter.translate(text, tgt)
```
* nlu_agent/core.py
```
- intent = local_nlu.parse(utterance)
+ intent = adapter.generate(prompt_for_intent, model="gpt-3.5-turbo")
```
(Similar one-liners for: LearningOrchestrationService, ProactiveAgent, ModelOrchestrator, etc.)

### 2.5 Secure Secrets Handling (NEW)
```bash
# .env.example
# Place these locally, DO NOT commit real keys
OPENAI_API_KEY="sk-..."
BEDROCK_KEY="AKIA..."
```
In GitHub Actions set:
- `OPENAI_API_KEY` → `org-openai-api-key`
- `BEDROCK_KEY`    → `org-bedrock-key`

Compose now mounts them via Docker `secrets:` (see above).

### 3.4 Verification Steps (append)
- Prometheus rule (alertmanager):
```yaml
- alert: ObservabilityHubDown
  expr: up{job="observability-hub"} == 0
  for: 60s
  labels:
    severity: critical
  annotations:
    action: "kubectl scale deploy/observability-hub-standby --replicas=1"
```
- Health-check chain: MetricsForwarder ⇢ fails to ship → triggers `ObservabilityHubDown` → standby hub auto-scaled.
