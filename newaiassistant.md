A. ROOT-CAUSE ANALYSIS OF COMPLEXITY
1. Excessive Agent Count
MainPC : 54 agents, many “required: true” by default
PC2 : 23 agents, several redundant monitoring / utility agents
Several agents overlap in purpose (e.g., ObservabilityHub now replaces 3 legacy monitors that are still referenced).
Deep, Chain-Like Dependencies
8-to-10-layer dependency chains on MainPC (e.g., AudioCapture → FusedAudioPreprocessor → StreamingSpeechRecognition → StreamingLanguageAnalyzer …).
Circular-risk edges now commented-out but still present in YAML (e.g., PerformanceMonitor ↔ PerformanceLoggerAgent).
“Required” Flag Mis-used
Nearly every MainPC agent is flagged required – masking true business-critical path and inflating mandatory start-up time.
Mixed Infrastructure Concerns
GPU/VRAM management, learning, reasoning, speech, vision, emotion, code-gen, etc. all launch together, regardless of session needs.
Hybrid / cross-machine monitoring partially modernised but legacy shards remain.
B. ESSENTIAL vs. OPTIONAL AGENTS
Legend
■ = keep (core) □ = optional / postpone ⊗ = remove / deprecated
MAIN PC (keep 15 / 54)
Core Platform
■ ServiceRegistry
■ SystemDigitalTwin
■ ObservabilityHub (single monitoring endpoint)
Scheduling / Coordination
■ RequestCoordinator
■ ModelManagerSuite (model loading / VRAM gatekeeper)
■ VRAMOptimizerAgent
Memory Stack
■ MemoryClient
■ SessionMemoryAgent
■ KnowledgeBase
Speech I/O (minimum conversational loop)
■ AudioCapture
■ FusedAudioPreprocessor
■ StreamingSpeechRecognition
■ StreamingTTSAgent
■ STTService
■ TTSService
OPTIONAL CLUSTERS
□ Reasoning (ChainOfThoughtAgent, etc.)
□ Learning & Self-training suite
□ Vision, Emotion, Proactive agents
□ CodeGenerator, Executor, TranslationService, Tiny Llama, etc.
PC-2 (keep 8 / 23)
Core Platform
■ ObservabilityHub (pc2 scope)
■ MemoryOrchestratorService
■ ResourceManager
■ AsyncProcessor
Knowledge / Context
■ ContextManager
■ UnifiedMemoryReasoningAgent
Application-specific
■ TieredResponder (primary response service)
■ TaskScheduler
OPTIONAL CLUSTERS
□ DreamWorldAgent, DreamingModeAgent
□ VisionProcessingAgent (only if PC-2 camera required)
□ Tutor / Tutoring agents, UnifiedWebAgent, etc.
⊗ Duplicated / deprecated monitors (PerformanceMonitor, HealthMonitor, etc.)
C. OPTIMAL START-UP SEQUENCE
Dependencies resolved left→right.
Infrastructure & Registry
1.1 ServiceRegistry → 1.2 ObservabilityHub → 1.3 SystemDigitalTwin
Coordination / Resource Control
2.1 ModelManagerSuite → 2.2 VRAMOptimizerAgent → 2.3 RequestCoordinator
Memory Foundation
3.1 MemoryClient → 3.2 KnowledgeBase → 3.3 SessionMemoryAgent
Speech I/O Loop
4.1 AudioCapture → 4.2 FusedAudioPreprocessor → 4.3 STTService
4.4 StreamingSpeechRecognition → 4.5 TTSService → 4.6 StreamingTTSAgent
(PC-2)
5.1 ObservabilityHub-PC2 → 5.2 MemoryOrchestratorService → 5.3 ResourceManager
5.4 AsyncProcessor → 5.5 ContextManager → 5.6 UnifiedMemoryReasoningAgent
5.7 TaskScheduler → 5.8 TieredResponder
⟶ All remaining optional agents load on-demand via dynamic launcher once core is healthy.
D. HYBRID LLM ROUTING STRATEGY
• Heavy compute: delegate to cloud LLM (large-context reasoning, code-gen, training).
Triggered by RequestCoordinator when task.complexity > threshold
Lightweight tasks: use on-premise local LLM (NLU, short replies) via StreamingTTS/ STT pair.
ObservabilityHub records per-task latency → feedback to ModelManagerSuite to refine routing threshold.
Fail-over: if cloud LLM unreachable, fallback to local; if VRAM exhausted, gracefully degrade to smaller quantised model (TinyLlama/TinyMix).
E. SYSTEM IMPROVEMENT RECOMMENDATIONS
1. Explicit required flags: mark only “■” agents true; others false or conditional.
Consolidate monitoring: ensure all agents reference ObservabilityHub; purge legacy monitors.
Introduce lazy loader: orchestrator that spawns optional clusters when first requested.
Health-check back-pressure: VRAMOptimizerAgent can instruct RequestCoordinator to queue jobs.
Configuration-as-code: generate derived minimal YAML per deployment profile (speech-only, vision-enabled, tutoring, etc.).
F. STEP-BY-STEP ACTION PLAN
Phase 0 – Preparation
0.1 Backup both YAMLs to version control branch optimize/startup_reduction.
0.2 Create profiles/ folder for variant configs.
Phase 1 – Define Core Profile
1.1 Copy current MainPC YAML → profiles/mainpc_core.yaml.
1.2 Remove / comment out all □ & ⊗ agents.
1.3 Ensure “required: true” only for the 15 core agents listed above.
1.4 Repeat for PC-2 → profiles/pc2_core.yaml with 8 core agents.
Phase 2 – Bootstrap Script Update
2.1 Update loader to parse env var PROFILE=core|full|custom to select YAML.
2.2 Add dependency-topological sort (or re-use existing) to enforce sequence table (Section C).
Phase 3 – Hybrid LLM Routing
3.1 Extend ModelManagerSuite with select_back_end(task_metadata) hook.
3.2 Integrate ObservabilityHub metrics for latency & GPU-usage to that hook.
Phase 4 – Observability Consolidation
4.1 Remove PerformanceMonitor, HealthMonitor, SystemHealthManager, PerformanceLoggerAgent from repo; update references to ObservabilityHub.
4.2 Validate Prometheus scrape targets aggregated across machines.
Phase 5 – Automated Tests
5.1 Write start-up smoke test launching only core profile on CI (both machines).
5.2 Verify all health-checks pass within 120 s; VRAM within 80 %.
Phase 6 – Gradual Roll-out
6.1 Deploy core profile to staging cluster; monitor for 48 h.
6.2 Incrementally enable optional clusters behind feature flags.
Phase 7 – Documentation & Handover
7.1 Produce updated architecture diagram and README.
7.2 Schedule knowledge-transfer session with ops team.
Expected Outcomes
Start-up time ↓ ~65 %
Peak GPU / CPU utilisation ↓ 40-50 % under idle conversational load
Observability unified; failure domains isolated
Flexible, profile-based deployment enabling faster iteration
