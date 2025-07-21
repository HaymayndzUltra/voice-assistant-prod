Script started on 2025-07-21 17:40:38+08:00 [TERM="xterm-256color" TTY="/dev/pts/25" COLUMNS="128" LINES="22"]
[?2004h]0;haymayndz@DESKTOP-GC2ET1O: ~/AI_System_Monorepo[01;32mhaymayndz@DESKTOP-GC2ET1O[00m:[01;34m~/AI_System_Monorepo[00m$ git status
[?2004lOn branch model-management-analysis
Your branch is up to date with 'origin/model-management-analysis'.

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	[31mmy_terminal_log.txt[m

nothing added to commit but untracked files present (use "git add" to track)
[?2004h]0;haymayndz@DESKTOP-GC2ET1O: ~/AI_System_Monorepo[01;32mhaymayndz@DESKTOP-GC2ET1O[00m:[01;34m~/AI_System_Monorepo[00m$ git add .
[?2004l[?2004h]0;haymayndz@DESKTOP-GC2ET1O: ~/AI_System_Monorepo[01;32mhaymayndz@DESKTOP-GC2ET1O[00m:[01;34m~/AI_System_Monorepo[00m$ git m "[K[K[K[K[K[K[K[7m# 1. Add all changes (including automation tools)[27m
[7mgit add -A[27m

[7m# 2. Commit with descriptive message[27m
[7mgit commit -m "Background Agent: Add automation tools and healthchecks[27m

[7m- Created tools/add_healthchecks.py (socket-based health monitoring)[27m
[7m- Created tools/legacy_port_sweep.py (found 1,022 legacy port references)[27m
[7m- Created tools/compose_validate.py (validated 13 services)[27m
[7m- Added healthchecks to all Docker services[27m
[7m- Fixed NATS healthcheck (removed wget dependency)[27m
[7m- Legacy ports: 5570(346), 5575(282), 5617(234), 7222(160)"[27m

[7m# 3. Create new branch[27m
[7mgit checkout -b background-agent-automation-tools[27m

[7m# 4. Push new branch[27m
[7mgit push origin background-agent-automation-tools[27m[A[A[A[A[A[A[A[A[A[A[A[A[A[A[A[A[A# 1. Add all changes (including automation tools)
git add -A

# 2. Commit with descriptive message
git commit -m "Background Agent: Add automation tools and healthchecks

- Created tools/add_healthchecks.py (socket-based health monitoring)
- Created tools/legacy_port_sweep.py (found 1,022 legacy port references)
- Created tools/compose_validate.py (validated 13 services)
- Added healthchecks to all Docker services
- Fixed NATS healthcheck (removed wget dependency)
- Legacy ports: 5570(346), 5575(282), 5617(234), 7222(160)"

# 3. Create new branch
git checkout -b background-agent-automation-tools

# 4. Push new branch
git push origin background-agent-automation-tools
[?2004l[model-management-analysis e460774] Background Agent: Add automation tools and healthchecks
 1 file changed, 285 insertions(+)
 create mode 100644 my_terminal_log.txt
Switched to a new branch 'background-agent-automation-tools'
Enumerating objects: 4, done.
Counting objects:  25% (1/4)Counting objects:  50% (2/4)Counting objects:  75% (3/4)Counting objects: 100% (4/4)Counting objects: 100% (4/4), done.
Delta compression using up to 24 threads
Compressing objects:  33% (1/3)Compressing objects:  66% (2/3)Compressing objects: 100% (3/3)Compressing objects: 100% (3/3), done.
Writing objects:  33% (1/3)Writing objects:  66% (2/3)Writing objects: 100% (3/3)Writing objects: 100% (3/3), 6.00 KiB | 6.00 MiB/s, done.
Total 3 (delta 1), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas:   0% (0/1)[Kremote: Resolving deltas: 100% (1/1)[Kremote: Resolving deltas: 100% (1/1), completed with 1 local object.[K
remote: 
remote: Create a pull request for 'background-agent-automation-tools' on GitHub by visiting:[K
remote:      https://github.com/HaymayndzUltra/voice-assistant-prod/pull/new/background-agent-automation-tools[K
remote: 
To https://github.com/HaymayndzUltra/voice-assistant-prod.git
 * [new branch]      background-agent-automation-tools -> background-agent-automation-tools
[?2004h]0;haymayndz@DESKTOP-GC2ET1O: ~/AI_System_Monorepo[01;32mhaymayndz@DESKTOP-GC2ET1O[00m:[01;34m~/AI_System_Monorepo[00m$ git status
[?2004lOn branch background-agent-automation-tools
nothing to commit, working tree clean
[?2004h]0;haymayndz@DESKTOP-GC2E:5580->5580/tcp, 0.0.0.0:5638->5638/tcp, [::]:5638->5638/tcp, 0.0.0.0:5643->5643/tcp, [::]:5643->5643/tcp, 0.0.0.0:7202->7202/tcp, [::]:7202->7202/tcp, 0.0.0.0:7212->7212/tcp, [::]:7212->7212/tcp, 0.0.0.0:7300->7222/tcp, [::]:7300->7222/tcp                                                                                                                                         docker-learning-knowledge-1
d973afb30807   ai-system/speech-services:optimized       "python /app/main_pc…"   6 minutes ago   Up 6 minutes (unhealthy)   0.0.0.0:5800-5801->5800-5801/tcp, [::]:5800-5801->5800-5801/tcp                                                                                                                                                                                                                                                                                                                                                      docker-speech-services-1
ce8d94099bc5   ai-system/vision-processing:optimized     "python /app/main_pc…"   6 minutes ago   Up 6 minutes (unhealthy)   0.0.0.0:5610->5610/tcp, [::]:5610->5610/tcp                                                                                                                                                                                                                                                                                                                                                                          docker-vision-processing-1
31a85188ff7d   ai-system/reasoning-services:optimized    "python /app/main_pc…"   6 minutes ago   Up 6 minutes (unhealthy)   0.0.0.0:5612->5612/tcp, [::]:5612->5612/tcp, 0.0.0.0:5641->5641/tcp, [::]:5641->5641/tcp, 0.0.0.0:5646->5646/tcp, [::]:5646->5646/tcp                                                                                                                                                                                                                                                                                docker-reasoning-services-1
2819d4247cfd   ai-system/core-services:optimized         "python /app/main_pc…"   6 minutes ago   Up 6 minutes (unhealthy)   0.0.0.0:7200->7200/tcp, [::]:7200->7200/tcp, 0.0.0.0:7210-7211->7210-7211/tcp, [::]:7210-7211->7210-7211/tcp, 0.0.0.0:7220->7220/tcp, [::]:7220->7220/tcp, 0.0.0.0:7225->7225/tcp, [::]:7225->7225/tcp, 0.0.0.0:8211-8212->8211-8212/tcp, [::]:8211-8212->8211-8212/tcp, 0.0.0.0:8220->8220/tcp, [::]:8220->8220/tcp, 0.0.0.0:9000->9000/tcp, [::]:9000->9000/tcp, 0.0.0.0:26002->26002/tcp, [::]:26002->26002/tcp   docker-core-services-1
cc4ffd799689   redis:7-alpine                            "docker-entrypoint.s…"   6 minutes ago   Up 6 minutes (healthy)     6379/tcp                                                                                                                                                                                                                                                                                                                                                                                                             docker-redis-1
45284d732ba6   nats:2.10                                 "/nats-server -js -s…"   6 minutes ago   Up 6 minutes (unhealthy)   0.0.0.0:4222->4222/tcp, [::]:4222->4222/tcp, 0.0.0.0:8222->8222/tcp, [::]:8222->8222/tcp                                                                                                                                                                                                                                                                                                                             docker-nats-1
010c20f4c73f   ghcr.io/github/github-mcp-server          "/server/github-mcp-…"   3 hours ago     Up 3 hours                                                                                                                                                                                                                                                                                                                                                                                                                                      modest_fermat
681010653a7c   ai-system/mm-router:latest                "python /app/model_m…"   42 hours ago    Up 42 hours                0.0.0.0:5570->5570/tcp, [::]:5570->5570/tcp, 0.0.0.0:5575->5575/tcp, [::]:5575->5575/tcp, 0.0.0.0:5617->5617/tcp, [::]:5617->5617/tcp, 0.0.0.0:7222->7222/tcp, [::]:7222->7222/tcp                                                                                                                                                                                                                                   mm-router
feafd2e8978c   grafana/grafana                           "/run.sh"                44 hours ago    Up 44 hours                0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp                                                                                                                                                                                                                                                                                                                                                                          grafana
d6703beebcf8   prom/prometheus                           "/bin/prometheus --c…"   45 hours ago    Up 45 hours                0.0.0.0:9090->9090/tcp, [::]:9090->9090/tcp                                                                                                                                                                                                                                                                                                                                                                          prometheus
haymayndz@DESKTOP-GC2ET1O:~/AI_System_Monorepo$ docker compose -f docker/docker-compose.mainpc.yml logs --tail 20
language-processing-1  | [STARTED] MoodTrackerAgent (PID: 180) -> /app/main_pc_code/agents/mood_tracker_agent.py
language-processing-1  | [STARTED] VoiceProfilingAgent (PID: 181) -> /app/main_pc_code/agents/voice_profiling_agent.py
language-processing-1  | [STARTED] ToneDetector (PID: 182) -> /app/main_pc_code/agents/tone_detector.py
language-processing-1  | [STARTED] FixedStreamingTranslation (PID: 183) -> /app/main_pc_code/agents/fixed_streaming_translation.py
language-processing-1  | [STARTED] TinyLlamaServiceEnhanced (PID: 184) -> /app/main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
language-processing-1  | [STARTED] STTService (PID: 185) -> /app/main_pc_code/services/stt_service.py
language-processing-1  | [STARTED] LearningOrchestrationService (PID: 187) -> /app/main_pc_code/agents/learning_orchestration_service.py
language-processing-1  | [STARTED] FaceRecognitionAgent (PID: 191) -> /app/main_pc_code/agents/face_recognition_agent.py
language-processing-1  | [STARTED] SelfTrainingOrchestrator (PID: 193) -> /app/main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py
language-processing-1  | [STARTED] EmotionSynthesisAgent (PID: 195) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
language-processing-1  | [STARTED] ChainOfThoughtAgent (PID: 196) -> /app/main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
language-processing-1  | [STARTED] ModelOrchestrator (PID: 197) -> /app/main_pc_code/agents/model_orchestrator.py
language-processing-1  | [STARTED] CodeGenerator (PID: 198) -> /app/main_pc_code/agents/code_generator_agent.py
language-processing-1  | [STARTED] VRAMOptimizerAgent (PID: 222) -> /app/main_pc_code/agents/vram_optimizer_agent.py
language-processing-1  | [INFO] Waiting 10s for agents to initialize...
language-processing-1  |   [HEALTH CHECK] Attempt 1/5...
language-processing-1  |     [WAIT] Not healthy: IntentionValidatorAgent, DynamicIdentityAgent, ProactiveAgent, SessionMemoryAgent, LearningManager, KnowledgeBase, ChitchatAgent, FeedbackHandler, FusedAudioPreprocessor, HumanAwarenessAgent, MoodTrackerAgent, VoiceProfilingAgent, ToneDetector, FixedStreamingTranslation, TinyLlamaServiceEnhanced, STTService, LearningOrchestrationService, FaceRecognitionAgent, SelfTrainingOrchestrator, EmotionSynthesisAgent, ChainOfThoughtAgent, ModelOrchestrator, CodeGenerator, VRAMOptimizerAgent. Retrying in 10s...
language-processing-1  |   [HEALTH CHECK] Attempt 2/5...
language-processing-1  |     [WAIT] Not healthy: IntentionValidatorAgent, DynamicIdentityAgent, ProactiveAgent, SessionMemoryAgent, LearningManager, KnowledgeBase, ChitchatAgent, FeedbackHandler, FusedAudioPreprocessor, HumanAwarenessAgent, MoodTrackerAgent, VoiceProfilingAgent, ToneDetector, FixedStreamingTranslation, TinyLlamaServiceEnhanced, STTService, LearningOrchestrationService, FaceRecognitionAgent, SelfTrainingOrchestrator, EmotionSynthesisAgent, ChainOfThoughtAgent, ModelOrchestrator, CodeGenerator, VRAMOptimizerAgent. Retrying in 10s...
language-processing-1  |   [HEALTH CHECK] Attempt 3/5...
nats-1                 | [1] 2025/07/21 09:31:53.051580 [INF]   Version:  2.10.29
nats-1                 | [1] 2025/07/21 09:31:53.051586 [INF]   Git:      [f91ddd8]
nats-1                 | [1] 2025/07/21 09:31:53.051588 [INF]   Name:     NDBJYAKAGD7MHFXEDTWYBMNU67LN4NP75A5C5LQY5KPN5PXE2N7OJU5M
nats-1                 | [1] 2025/07/21 09:31:53.051598 [INF]   Node:     QUZD14BO
nats-1                 | [1] 2025/07/21 09:31:53.051600 [INF]   ID:       NDBJYAKAGD7MHFXEDTWYBMNU67LN4NP75A5C5LQY5KPN5PXE2N7OJU5M
nats-1                 | [1] 2025/07/21 09:31:53.065024 [INF] Starting JetStream
nats-1                 | [1] 2025/07/21 09:31:53.065153 [INF]     _ ___ _____ ___ _____ ___ ___   _   __  __
nats-1                 | [1] 2025/07/21 09:31:53.065170 [INF]  _ | | __|_   _/ __|_   _| _ \ __| /_\ |  \/  |
nats-1                 | [1] 2025/07/21 09:31:53.065173 [INF] | || | _|  | | \__ \ | | |   / _| / _ \| |\/| |
nats-1                 | [1] 2025/07/21 09:31:53.065174 [INF]  \__/|___| |_| |___/ |_| |_|_\___/_/ \_\_|  |_|
nats-1                 | [1] 2025/07/21 09:31:53.065175 [INF] 
nats-1                 | [1] 2025/07/21 09:31:53.065176 [INF]          https://docs.nats.io/jetstream
nats-1                 | [1] 2025/07/21 09:31:53.065177 [INF] 
nats-1                 | [1] 2025/07/21 09:31:53.065178 [INF] ---------------- JETSTREAM ----------------
nats-1                 | [1] 2025/07/21 09:31:53.065181 [INF]   Max Memory:      11.40 GB
nats-1                 | [1] 2025/07/21 09:31:53.065183 [INF]   Max Storage:     628.65 GB
nats-1                 | [1] 2025/07/21 09:31:53.065184 [INF]   Store Directory: "/data/jetstream"
nats-1                 | [1] 2025/07/21 09:31:53.065185 [INF] -------------------------------------------
nats-1                 | [1] 2025/07/21 09:31:53.069218 [INF] Listening for client connections on 0.0.0.0:4222
nats-1                 | [1] 2025/07/21 09:31:53.069376 [INF] Server is ready
emotion-system-1       | [STARTED] ChainOfThoughtAgent (PID: 182) -> /app/main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
emotion-system-1       | [STARTED] TinyLlamaServiceEnhanced (PID: 183) -> /app/main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
emotion-system-1       | [STARTED] CodeGenerator (PID: 185) -> /app/main_pc_code/agents/code_generator_agent.py
emotion-system-1       | [STARTED] FusedAudioPreprocessor (PID: 190) -> /app/main_pc_code/agents/fused_audio_preprocessor.py
emotion-system-1       | [STARTED] FaceRecognitionAgent (PID: 191) -> /app/main_pc_code/agents/face_recognition_agent.py
emotion-system-1       | [STARTED] ModelOrchestrator (PID: 192) -> /app/main_pc_code/agents/model_orchestrator.py
emotion-system-1       | [STARTED] EmotionSynthesisAgent (PID: 193) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
emotion-system-1       | [STARTED] VRAMOptimizerAgent (PID: 194) -> /app/main_pc_code/agents/vram_optimizer_agent.py
emotion-system-1       | [STARTED] IntentionValidatorAgent (PID: 218) -> /app/main_pc_code/agents/IntentionValidatorAgent.py
emotion-system-1       | [STARTED] ProactiveAgent (PID: 219) -> /app/main_pc_code/agents/ProactiveAgent.py
emotion-system-1       | [STARTED] DynamicIdentityAgent (PID: 220) -> /app/main_pc_code/agents/DynamicIdentityAgent.py
emotion-system-1       | [STARTED] LearningManager (PID: 221) -> /app/main_pc_code/agents/learning_manager.py
emotion-system-1       | [STARTED] KnowledgeBase (PID: 222) -> /app/main_pc_code/agents/knowledge_base.py
emotion-system-1       | [STARTED] SessionMemoryAgent (PID: 223) -> /app/main_pc_code/agents/session_memory_agent.py
emotion-system-1       | [INFO] Waiting 10s for agents to initialize...
emotion-system-1       |   [HEALTH CHECK] Attempt 1/5...
emotion-system-1       |     [WAIT] Not healthy: ChitchatAgent, FeedbackHandler, HumanAwarenessAgent, ToneDetector, MoodTrackerAgent, VoiceProfilingAgent, FixedStreamingTranslation, STTService, LearningOrchestrationService, SelfTrainingOrchestrator, ChainOfThoughtAgent, TinyLlamaServiceEnhanced, CodeGenerator, FusedAudioPreprocessor, FaceRecognitionAgent, ModelOrchestrator, EmotionSynthesisAgent, VRAMOptimizerAgent, IntentionValidatorAgent, ProactiveAgent, DynamicIdentityAgent, LearningManager, KnowledgeBase, SessionMemoryAgent. Retrying in 10s...
emotion-system-1       |   [HEALTH CHECK] Attempt 2/5...
emotion-system-1       |     [WAIT] Not healthy: ChitchatAgent, FeedbackHandler, HumanAwarenessAgent, ToneDetector, MoodTrackerAgent, VoiceProfilingAgent, FixedStreamingTranslation, STTService, LearningOrchestrationService, SelfTrainingOrchestrator, ChainOfThoughtAgent, TinyLlamaServiceEnhanced, CodeGenerator, FusedAudioPreprocessor, FaceRecognitionAgent, ModelOrchestrator, EmotionSynthesisAgent, VRAMOptimizerAgent, IntentionValidatorAgent, ProactiveAgent, DynamicIdentityAgent, LearningManager, KnowledgeBase, SessionMemoryAgent. Retrying in 10s...
emotion-system-1       |   [HEALTH CHECK] Attempt 3/5...
redis-1                | 1:C 21 Jul 2025 09:31:53.021 * oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
redis-1                | 1:C 21 Jul 2025 09:31:53.026 * Redis version=7.4.5, bits=64, commit=00000000, modified=0, pid=1, just started
redis-1                | 1:C 21 Jul 2025 09:31:53.026 # Warning: no config file specified, using the default config. In order to specify a config file use redis-server /path/to/redis.conf
redis-1                | 1:M 21 Jul 2025 09:31:53.026 * monotonic clock: POSIX clock_gettime
redis-1                | 1:M 21 Jul 2025 09:31:53.033 * Running mode=standalone, port=6379.
redis-1                | 1:M 21 Jul 2025 09:31:53.033 * Server initialized
redis-1                | 1:M 21 Jul 2025 09:31:53.046 * Loading RDB produced by version 7.4.5
redis-1                | 1:M 21 Jul 2025 09:31:53.046 * RDB age 2399 seconds
redis-1                | 1:M 21 Jul 2025 09:31:53.046 * RDB memory usage when created 0.93 Mb
redis-1                | 1:M 21 Jul 2025 09:31:53.046 * Done loading RDB, keys loaded: 0, keys expired: 0.
redis-1                | 1:M 21 Jul 2025 09:31:53.046 * DB loaded from disk: 0.013 seconds
redis-1                | 1:M 21 Jul 2025 09:31:53.046 * Ready to accept connections tcp
memory-system-1        | [STARTED] VoiceProfilingAgent (PID: 180) -> /app/main_pc_code/agents/voice_profiling_agent.py
memory-system-1        | [STARTED] MoodTrackerAgent (PID: 181) -> /app/main_pc_code/agents/mood_tracker_agent.py
memory-system-1        | [STARTED] ToneDetector (PID: 182) -> /app/main_pc_code/agents/tone_detector.py
memory-system-1        | [STARTED] LearningOrchestrationService (PID: 183) -> /app/main_pc_code/agents/learning_orchestration_service.py
memory-system-1        | [STARTED] TinyLlamaServiceEnhanced (PID: 184) -> /app/main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
memory-system-1        | [STARTED] FaceRecognitionAgent (PID: 185) -> /app/main_pc_code/agents/face_recognition_agent.py
memory-system-1        | [STARTED] VRAMOptimizerAgent (PID: 186) -> /app/main_pc_code/agents/vram_optimizer_agent.py
memory-system-1        | [STARTED] FixedStreamingTranslation (PID: 187) -> /app/main_pc_code/agents/fixed_streaming_translation.py
memory-system-1        | [STARTED] ModelOrchestrator (PID: 188) -> /app/main_pc_code/agents/model_orchestrator.py
memory-system-1        | [STARTED] ChainOfThoughtAgent (PID: 189) -> /app/main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
memory-system-1        | [STARTED] EmotionSynthesisAgent (PID: 190) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
memory-system-1        | [STARTED] SelfTrainingOrchestrator (PID: 191) -> /app/main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py
memory-system-1        | [STARTED] STTService (PID: 192) -> /app/main_pc_code/services/stt_service.py
memory-system-1        | [STARTED] CodeGenerator (PID: 198) -> /app/main_pc_code/agents/code_generator_agent.py
memory-system-1        | [INFO] Waiting 10s for agents to initialize...
memory-system-1        |   [HEALTH CHECK] Attempt 1/5...
memory-system-1        |     [WAIT] Not healthy: KnowledgeBase, DynamicIdentityAgent, LearningManager, ProactiveAgent, IntentionValidatorAgent, SessionMemoryAgent, ChitchatAgent, FeedbackHandler, FusedAudioPreprocessor, HumanAwarenessAgent, VoiceProfilingAgent, MoodTrackerAgent, ToneDetector, LearningOrchestrationService, TinyLlamaServiceEnhanced, FaceRecognitionAgent, VRAMOptimizerAgent, FixedStreamingTranslation, ModelOrchestrator, ChainOfThoughtAgent, EmotionSynthesisAgent, SelfTrainingOrchestrator, STTService, CodeGenerator. Retrying in 10s...
memory-system-1        |   [HEALTH CHECK] Attempt 2/5...
memory-system-1        |     [WAIT] Not healthy: KnowledgeBase, DynamicIdentityAgent, LearningManager, ProactiveAgent, IntentionValidatorAgent, SessionMemoryAgent, ChitchatAgent, FeedbackHandler, FusedAudioPreprocessor, HumanAwarenessAgent, VoiceProfilingAgent, MoodTrackerAgent, ToneDetector, LearningOrchestrationService, TinyLlamaServiceEnhanced, FaceRecognitionAgent, VRAMOptimizerAgent, FixedStreamingTranslation, ModelOrchestrator, ChainOfThoughtAgent, EmotionSynthesisAgent, SelfTrainingOrchestrator, STTService, CodeGenerator. Retrying in 10s...
memory-system-1        |   [HEALTH CHECK] Attempt 3/5...
reasoning-services-1   | [STARTED] VRAMOptimizerAgent (PID: 229) -> /app/main_pc_code/agents/vram_optimizer_agent.py
reasoning-services-1   | [STARTED] STTService (PID: 230) -> /app/main_pc_code/services/stt_service.py
reasoning-services-1   | [STARTED] SelfTrainingOrchestrator (PID: 231) -> /app/main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py
reasoning-services-1   | [STARTED] ChainOfThoughtAgent (PID: 232) -> /app/main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
reasoning-services-1   | [STARTED] TinyLlamaServiceEnhanced (PID: 233) -> /app/main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
reasoning-services-1   | [STARTED] CodeGenerator (PID: 234) -> /app/main_pc_code/agents/code_generator_agent.py
reasoning-services-1   | [STARTED] LearningOrchestrationService (PID: 235) -> /app/main_pc_code/agents/learning_orchestration_service.py
reasoning-services-1   | [STARTED] ModelOrchestrator (PID: 236) -> /app/main_pc_code/agents/model_orchestrator.py
reasoning-services-1   | [STARTED] FeedbackHandler (PID: 237) -> /app/main_pc_code/agents/feedback_handler.py
reasoning-services-1   | [STARTED] ChitchatAgent (PID: 238) -> /app/main_pc_code/agents/chitchat_agent.py
reasoning-services-1   | [STARTED] VoiceProfilingAgent (PID: 239) -> /app/main_pc_code/agents/voice_profiling_agent.py
reasoning-services-1   | [STARTED] HumanAwarenessAgent (PID: 244) -> /app/main_pc_code/agents/human_awareness_agent.py
reasoning-services-1   | [STARTED] MoodTrackerAgent (PID: 247) -> /app/main_pc_code/agents/mood_tracker_agent.py
reasoning-services-1   | [STARTED] ToneDetector (PID: 248) -> /app/main_pc_code/agents/tone_detector.py
reasoning-services-1   | [INFO] Waiting 10s for agents to initialize...
reasoning-services-1   |   [HEALTH CHECK] Attempt 1/5...
reasoning-services-1   |     [WAIT] Not healthy: KnowledgeBase, DynamicIdentityAgent, IntentionValidatorAgent, LearningManager, SessionMemoryAgent, ProactiveAgent, FusedAudioPreprocessor, FaceRecognitionAgent, FixedStreamingTranslation, EmotionSynthesisAgent, VRAMOptimizerAgent, STTService, SelfTrainingOrchestrator, ChainOfThoughtAgent, TinyLlamaServiceEnhanced, CodeGenerator, LearningOrchestrationService, ModelOrchestrator, FeedbackHandler, ChitchatAgent, VoiceProfilingAgent, HumanAwarenessAgent, MoodTrackerAgent, ToneDetector. Retrying in 10s...
reasoning-services-1   |   [HEALTH CHECK] Attempt 2/5...
reasoning-services-1   |     [WAIT] Not healthy: KnowledgeBase, DynamicIdentityAgent, IntentionValidatorAgent, LearningManager, SessionMemoryAgent, ProactiveAgent, FusedAudioPreprocessor, FaceRecognitionAgent, FixedStreamingTranslation, EmotionSynthesisAgent, VRAMOptimizerAgent, STTService, SelfTrainingOrchestrator, ChainOfThoughtAgent, TinyLlamaServiceEnhanced, CodeGenerator, LearningOrchestrationService, ModelOrchestrator, FeedbackHandler, ChitchatAgent, VoiceProfilingAgent, HumanAwarenessAgent, MoodTrackerAgent, ToneDetector. Retrying in 10s...
reasoning-services-1   |   [HEALTH CHECK] Attempt 3/5...
vision-processing-1    | [STARTED] KnowledgeBase (PID: 229) -> /app/main_pc_code/agents/knowledge_base.py
vision-processing-1    | [STARTED] VoiceProfilingAgent (PID: 234) -> /app/main_pc_code/agents/voice_profiling_agent.py
vision-processing-1    | [STARTED] MoodTrackerAgent (PID: 235) -> /app/main_pc_code/agents/mood_tracker_agent.py
vision-processing-1    | [STARTED] ToneDetector (PID: 236) -> /app/main_pc_code/agents/tone_detector.py
vision-processing-1    | [STARTED] HumanAwarenessAgent (PID: 237) -> /app/main_pc_code/agents/human_awareness_agent.py
vision-processing-1    | [STARTED] LearningManager (PID: 238) -> /app/main_pc_code/agents/learning_manager.py
vision-processing-1    | [STARTED] VRAMOptimizerAgent (PID: 239) -> /app/main_pc_code/agents/vram_optimizer_agent.py
vision-processing-1    | [STARTED] FaceRecognitionAgent (PID: 240) -> /app/main_pc_code/agents/face_recognition_agent.py
vision-processing-1    | [STARTED] SessionMemoryAgent (PID: 241) -> /app/main_pc_code/agents/session_memory_agent.py
vision-processing-1    | [STARTED] IntentionValidatorAgent (PID: 242) -> /app/main_pc_code/agents/IntentionValidatorAgent.py
vision-processing-1    | [STARTED] EmotionSynthesisAgent (PID: 243) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
vision-processing-1    | [STARTED] ProactiveAgent (PID: 244) -> /app/main_pc_code/agents/ProactiveAgent.py
vision-processing-1    | [STARTED] DynamicIdentityAgent (PID: 245) -> /app/main_pc_code/agents/DynamicIdentityAgent.py
vision-processing-1    | [STARTED] ModelOrchestrator (PID: 246) -> /app/main_pc_code/agents/model_orchestrator.py
vision-processing-1    | [INFO] Waiting 10s for agents to initialize...
vision-processing-1    |   [HEALTH CHECK] Attempt 1/5...
vision-processing-1    |     [WAIT] Not healthy: LearningOrchestrationService, ChainOfThoughtAgent, SelfTrainingOrchestrator, CodeGenerator, FixedStreamingTranslation, STTService, TinyLlamaServiceEnhanced, FeedbackHandler, ChitchatAgent, FusedAudioPreprocessor, KnowledgeBase, VoiceProfilingAgent, MoodTrackerAgent, ToneDetector, HumanAwarenessAgent, LearningManager, VRAMOptimizerAgent, FaceRecognitionAgent, SessionMemoryAgent, IntentionValidatorAgent, EmotionSynthesisAgent, ProactiveAgent, DynamicIdentityAgent, ModelOrchestrator. Retrying in 10s...
vision-processing-1    |   [HEALTH CHECK] Attempt 2/5...
vision-processing-1    |     [WAIT] Not healthy: LearningOrchestrationService, ChainOfThoughtAgent, SelfTrainingOrchestrator, CodeGenerator, FixedStreamingTranslation, STTService, TinyLlamaServiceEnhanced, FeedbackHandler, ChitchatAgent, FusedAudioPreprocessor, KnowledgeBase, VoiceProfilingAgent, MoodTrackerAgent, ToneDetector, HumanAwarenessAgent, LearningManager, VRAMOptimizerAgent, FaceRecognitionAgent, SessionMemoryAgent, IntentionValidatorAgent, EmotionSynthesisAgent, ProactiveAgent, DynamicIdentityAgent, ModelOrchestrator. Retrying in 10s...
vision-processing-1    |   [HEALTH CHECK] Attempt 3/5...
utility-services-1     | [STARTED] ChainOfThoughtAgent (PID: 185) -> /app/main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
utility-services-1     | [STARTED] VRAMOptimizerAgent (PID: 186) -> /app/main_pc_code/agents/vram_optimizer_agent.py
utility-services-1     | [STARTED] ModelOrchestrator (PID: 187) -> /app/main_pc_code/agents/model_orchestrator.py
utility-services-1     | [STARTED] FaceRecognitionAgent (PID: 188) -> /app/main_pc_code/agents/face_recognition_agent.py
utility-services-1     | [STARTED] SelfTrainingOrchestrator (PID: 190) -> /app/main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py
utility-services-1     | [STARTED] EmotionSynthesisAgent (PID: 191) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
utility-services-1     | [STARTED] LearningOrchestrationService (PID: 192) -> /app/main_pc_code/agents/learning_orchestration_service.py
utility-services-1     | [STARTED] CodeGenerator (PID: 193) -> /app/main_pc_code/agents/code_generator_agent.py
utility-services-1     | [STARTED] FixedStreamingTranslation (PID: 194) -> /app/main_pc_code/agents/fixed_streaming_translation.py
utility-services-1     | [STARTED] TinyLlamaServiceEnhanced (PID: 195) -> /app/main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
utility-services-1     | [STARTED] LearningManager (PID: 196) -> /app/main_pc_code/agents/learning_manager.py
utility-services-1     | [STARTED] KnowledgeBase (PID: 197) -> /app/main_pc_code/agents/knowledge_base.py
utility-services-1     | [STARTED] SessionMemoryAgent (PID: 198) -> /app/main_pc_code/agents/session_memory_agent.py
utility-services-1     | [STARTED] FusedAudioPreprocessor (PID: 199) -> /app/main_pc_code/agents/fused_audio_preprocessor.py
utility-services-1     | [INFO] Waiting 10s for agents to initialize...
utility-services-1     |   [HEALTH CHECK] Attempt 1/5...
utility-services-1     |     [WAIT] Not healthy: FeedbackHandler, ChitchatAgent, IntentionValidatorAgent, DynamicIdentityAgent, ProactiveAgent, MoodTrackerAgent, ToneDetector, VoiceProfilingAgent, HumanAwarenessAgent, STTService, ChainOfThoughtAgent, VRAMOptimizerAgent, ModelOrchestrator, FaceRecognitionAgent, SelfTrainingOrchestrator, EmotionSynthesisAgent, LearningOrchestrationService, CodeGenerator, FixedStreamingTranslation, TinyLlamaServiceEnhanced, LearningManager, KnowledgeBase, SessionMemoryAgent, FusedAudioPreprocessor. Retrying in 10s...
utility-services-1     |   [HEALTH CHECK] Attempt 2/5...
utility-services-1     |     [WAIT] Not healthy: FeedbackHandler, ChitchatAgent, IntentionValidatorAgent, DynamicIdentityAgent, ProactiveAgent, MoodTrackerAgent, ToneDetector, VoiceProfilingAgent, HumanAwarenessAgent, STTService, ChainOfThoughtAgent, VRAMOptimizerAgent, ModelOrchestrator, FaceRecognitionAgent, SelfTrainingOrchestrator, EmotionSynthesisAgent, LearningOrchestrationService, CodeGenerator, FixedStreamingTranslation, TinyLlamaServiceEnhanced, LearningManager, KnowledgeBase, SessionMemoryAgent, FusedAudioPreprocessor. Retrying in 10s...
utility-services-1     |   [HEALTH CHECK] Attempt 3/5...
gpu-infrastructure-1   | [STARTED] FaceRecognitionAgent (PID: 234) -> /app/main_pc_code/agents/face_recognition_agent.py
gpu-infrastructure-1   | [STARTED] ModelOrchestrator (PID: 235) -> /app/main_pc_code/agents/model_orchestrator.py
gpu-infrastructure-1   | [STARTED] CodeGenerator (PID: 236) -> /app/main_pc_code/agents/code_generator_agent.py
gpu-infrastructure-1   | [STARTED] FixedStreamingTranslation (PID: 238) -> /app/main_pc_code/agents/fixed_streaming_translation.py
gpu-infrastructure-1   | [STARTED] LearningOrchestrationService (PID: 239) -> /app/main_pc_code/agents/learning_orchestration_service.py
gpu-infrastructure-1   | [STARTED] VRAMOptimizerAgent (PID: 243) -> /app/main_pc_code/agents/vram_optimizer_agent.py
gpu-infrastructure-1   | [STARTED] ChainOfThoughtAgent (PID: 246) -> /app/main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
gpu-infrastructure-1   | [STARTED] KnowledgeBase (PID: 247) -> /app/main_pc_code/agents/knowledge_base.py
gpu-infrastructure-1   | [STARTED] SessionMemoryAgent (PID: 248) -> /app/main_pc_code/agents/session_memory_agent.py
gpu-infrastructure-1   | [STARTED] LearningManager (PID: 249) -> /app/main_pc_code/agents/learning_manager.py
gpu-infrastructure-1   | [STARTED] ToneDetector (PID: 250) -> /app/main_pc_code/agents/tone_detector.py
gpu-infrastructure-1   | [STARTED] HumanAwarenessAgent (PID: 251) -> /app/main_pc_code/agents/human_awareness_agent.py
gpu-infrastructure-1   | [STARTED] MoodTrackerAgent (PID: 252) -> /app/main_pc_code/agents/mood_tracker_agent.py
gpu-infrastructure-1   | [STARTED] VoiceProfilingAgent (PID: 253) -> /app/main_pc_code/agents/voice_profiling_agent.py
gpu-infrastructure-1   | [INFO] Waiting 10s for agents to initialize...
gpu-infrastructure-1   |   [HEALTH CHECK] Attempt 1/5...
gpu-infrastructure-1   |     [WAIT] Not healthy: ChitchatAgent, FeedbackHandler, FusedAudioPreprocessor, ProactiveAgent, DynamicIdentityAgent, IntentionValidatorAgent, SelfTrainingOrchestrator, EmotionSynthesisAgent, TinyLlamaServiceEnhanced, STTService, FaceRecognitionAgent, ModelOrchestrator, CodeGenerator, FixedStreamingTranslation, LearningOrchestrationService, VRAMOptimizerAgent, ChainOfThoughtAgent, KnowledgeBase, SessionMemoryAgent, LearningManager, ToneDetector, HumanAwarenessAgent, MoodTrackerAgent, VoiceProfilingAgent. Retrying in 10s...
gpu-infrastructure-1   |   [HEALTH CHECK] Attempt 2/5...
gpu-infrastructure-1   |     [WAIT] Not healthy: ChitchatAgent, FeedbackHandler, FusedAudioPreprocessor, ProactiveAgent, DynamicIdentityAgent, IntentionValidatorAgent, SelfTrainingOrchestrator, EmotionSynthesisAgent, TinyLlamaServiceEnhanced, STTService, FaceRecognitionAgent, ModelOrchestrator, CodeGenerator, FixedStreamingTranslation, LearningOrchestrationService, VRAMOptimizerAgent, ChainOfThoughtAgent, KnowledgeBase, SessionMemoryAgent, LearningManager, ToneDetector, HumanAwarenessAgent, MoodTrackerAgent, VoiceProfilingAgent. Retrying in 10s...
gpu-infrastructure-1   |   [HEALTH CHECK] Attempt 3/5...
core-services-1        | [STARTED] KnowledgeBase (PID: 232) -> /app/main_pc_code/agents/knowledge_base.py
core-services-1        | [STARTED] SessionMemoryAgent (PID: 233) -> /app/main_pc_code/agents/session_memory_agent.py
core-services-1        | [STARTED] IntentionValidatorAgent (PID: 234) -> /app/main_pc_code/agents/IntentionValidatorAgent.py
core-services-1        | [STARTED] DynamicIdentityAgent (PID: 235) -> /app/main_pc_code/agents/DynamicIdentityAgent.py
core-services-1        | [STARTED] ModelOrchestrator (PID: 236) -> /app/main_pc_code/agents/model_orchestrator.py
core-services-1        | [STARTED] EmotionSynthesisAgent (PID: 237) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
core-services-1        | [STARTED] FaceRecognitionAgent (PID: 238) -> /app/main_pc_code/agents/face_recognition_agent.py
core-services-1        | [STARTED] LearningManager (PID: 239) -> /app/main_pc_code/agents/learning_manager.py
core-services-1        | [STARTED] ProactiveAgent (PID: 240) -> /app/main_pc_code/agents/ProactiveAgent.py
core-services-1        | [STARTED] VRAMOptimizerAgent (PID: 241) -> /app/main_pc_code/agents/vram_optimizer_agent.py
core-services-1        | [STARTED] MoodTrackerAgent (PID: 242) -> /app/main_pc_code/agents/mood_tracker_agent.py
core-services-1        | [STARTED] ToneDetector (PID: 243) -> /app/main_pc_code/agents/tone_detector.py
core-services-1        | [STARTED] VoiceProfilingAgent (PID: 244) -> /app/main_pc_code/agents/voice_profiling_agent.py
core-services-1        | [STARTED] HumanAwarenessAgent (PID: 245) -> /app/main_pc_code/agents/human_awareness_agent.py
core-services-1        | [INFO] Waiting 10s for agents to initialize...
core-services-1        |   [HEALTH CHECK] Attempt 1/5...
core-services-1        |     [WAIT] Not healthy: SelfTrainingOrchestrator, LearningOrchestrationService, TinyLlamaServiceEnhanced, FixedStreamingTranslation, CodeGenerator, ChainOfThoughtAgent, STTService, FeedbackHandler, ChitchatAgent, FusedAudioPreprocessor, KnowledgeBase, SessionMemoryAgent, IntentionValidatorAgent, DynamicIdentityAgent, ModelOrchestrator, EmotionSynthesisAgent, FaceRecognitionAgent, LearningManager, ProactiveAgent, VRAMOptimizerAgent, MoodTrackerAgent, ToneDetector, VoiceProfilingAgent, HumanAwarenessAgent. Retrying in 10s...
core-services-1        |   [HEALTH CHECK] Attempt 2/5...
core-services-1        |     [WAIT] Not healthy: SelfTrainingOrchestrator, LearningOrchestrationService, TinyLlamaServiceEnhanced, FixedStreamingTranslation, CodeGenerator, ChainOfThoughtAgent, STTService, FeedbackHandler, ChitchatAgent, FusedAudioPreprocessor, KnowledgeBase, SessionMemoryAgent, IntentionValidatorAgent, DynamicIdentityAgent, ModelOrchestrator, EmotionSynthesisAgent, FaceRecognitionAgent, LearningManager, ProactiveAgent, VRAMOptimizerAgent, MoodTrackerAgent, ToneDetector, VoiceProfilingAgent, HumanAwarenessAgent. Retrying in 10s...
core-services-1        |   [HEALTH CHECK] Attempt 3/5...
learning-knowledge-1   | [STARTED] VoiceProfilingAgent (PID: 181) -> /app/main_pc_code/agents/voice_profiling_agent.py
learning-knowledge-1   | [STARTED] ToneDetector (PID: 182) -> /app/main_pc_code/agents/tone_detector.py
learning-knowledge-1   | [STARTED] HumanAwarenessAgent (PID: 183) -> /app/main_pc_code/agents/human_awareness_agent.py
learning-knowledge-1   | [STARTED] FaceRecognitionAgent (PID: 184) -> /app/main_pc_code/agents/face_recognition_agent.py
learning-knowledge-1   | [STARTED] STTService (PID: 185) -> /app/main_pc_code/services/stt_service.py
learning-knowledge-1   | [STARTED] SelfTrainingOrchestrator (PID: 186) -> /app/main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py
learning-knowledge-1   | [STARTED] LearningOrchestrationService (PID: 187) -> /app/main_pc_code/agents/learning_orchestration_service.py
learning-knowledge-1   | [STARTED] CodeGenerator (PID: 188) -> /app/main_pc_code/agents/code_generator_agent.py
learning-knowledge-1   | [STARTED] TinyLlamaServiceEnhanced (PID: 189) -> /app/main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
learning-knowledge-1   | [STARTED] FixedStreamingTranslation (PID: 194) -> /app/main_pc_code/agents/fixed_streaming_translation.py
learning-knowledge-1   | [STARTED] VRAMOptimizerAgent (PID: 198) -> /app/main_pc_code/agents/vram_optimizer_agent.py
learning-knowledge-1   | [STARTED] EmotionSynthesisAgent (PID: 199) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
learning-knowledge-1   | [STARTED] ChainOfThoughtAgent (PID: 223) -> /app/main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
learning-knowledge-1   | [STARTED] ModelOrchestrator (PID: 224) -> /app/main_pc_code/agents/model_orchestrator.py
learning-knowledge-1   | [INFO] Waiting 10s for agents to initialize...
learning-knowledge-1   |   [HEALTH CHECK] Attempt 1/5...
learning-knowledge-1   |     [WAIT] Not healthy: KnowledgeBase, FeedbackHandler, ChitchatAgent, FusedAudioPreprocessor, SessionMemoryAgent, DynamicIdentityAgent, IntentionValidatorAgent, LearningManager, ProactiveAgent, MoodTrackerAgent, VoiceProfilingAgent, ToneDetector, HumanAwarenessAgent, FaceRecognitionAgent, STTService, SelfTrainingOrchestrator, LearningOrchestrationService, CodeGenerator, TinyLlamaServiceEnhanced, FixedStreamingTranslation, VRAMOptimizerAgent, EmotionSynthesisAgent, ChainOfThoughtAgent, ModelOrchestrator. Retrying in 10s...
learning-knowledge-1   |   [HEALTH CHECK] Attempt 2/5...
learning-knowledge-1   |     [WAIT] Not healthy: KnowledgeBase, FeedbackHandler, ChitchatAgent, FusedAudioPreprocessor, SessionMemoryAgent, DynamicIdentityAgent, IntentionValidatorAgent, LearningManager, ProactiveAgent, MoodTrackerAgent, VoiceProfilingAgent, ToneDetector, HumanAwarenessAgent, FaceRecognitionAgent, STTService, SelfTrainingOrchestrator, LearningOrchestrationService, CodeGenerator, TinyLlamaServiceEnhanced, FixedStreamingTranslation, VRAMOptimizerAgent, EmotionSynthesisAgent, ChainOfThoughtAgent, ModelOrchestrator. Retrying in 10s...
learning-knowledge-1   |   [HEALTH CHECK] Attempt 3/5...
audio-interface-1      | [STARTED] HumanAwarenessAgent (PID: 182) -> /app/main_pc_code/agents/human_awareness_agent.py
audio-interface-1      | [STARTED] MoodTrackerAgent (PID: 184) -> /app/main_pc_code/agents/mood_tracker_agent.py
audio-interface-1      | [STARTED] ChitchatAgent (PID: 190) -> /app/main_pc_code/agents/chitchat_agent.py
audio-interface-1      | [STARTED] FeedbackHandler (PID: 191) -> /app/main_pc_code/agents/feedback_handler.py
audio-interface-1      | [STARTED] KnowledgeBase (PID: 192) -> /app/main_pc_code/agents/knowledge_base.py
audio-interface-1      | [STARTED] ModelOrchestrator (PID: 193) -> /app/main_pc_code/agents/model_orchestrator.py
audio-interface-1      | [STARTED] FaceRecognitionAgent (PID: 194) -> /app/main_pc_code/agents/face_recognition_agent.py
audio-interface-1      | [STARTED] IntentionValidatorAgent (PID: 195) -> /app/main_pc_code/agents/IntentionValidatorAgent.py
audio-interface-1      | [STARTED] DynamicIdentityAgent (PID: 196) -> /app/main_pc_code/agents/DynamicIdentityAgent.py
audio-interface-1      | [STARTED] SessionMemoryAgent (PID: 197) -> /app/main_pc_code/agents/session_memory_agent.py
audio-interface-1      | [STARTED] EmotionSynthesisAgent (PID: 198) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
audio-interface-1      | [STARTED] LearningManager (PID: 199) -> /app/main_pc_code/agents/learning_manager.py
audio-interface-1      | [STARTED] VRAMOptimizerAgent (PID: 200) -> /app/main_pc_code/agents/vram_optimizer_agent.py
audio-interface-1      | [STARTED] ProactiveAgent (PID: 201) -> /app/main_pc_code/agents/ProactiveAgent.py
audio-interface-1      | [INFO] Waiting 10s for agents to initialize...
audio-interface-1      |   [HEALTH CHECK] Attempt 1/5...
audio-interface-1      |     [WAIT] Not healthy: LearningOrchestrationService, STTService, CodeGenerator, TinyLlamaServiceEnhanced, FixedStreamingTranslation, SelfTrainingOrchestrator, ChainOfThoughtAgent, FusedAudioPreprocessor, ToneDetector, VoiceProfilingAgent, HumanAwarenessAgent, MoodTrackerAgent, ChitchatAgent, FeedbackHandler, KnowledgeBase, ModelOrchestrator, FaceRecognitionAgent, IntentionValidatorAgent, DynamicIdentityAgent, SessionMemoryAgent, EmotionSynthesisAgent, LearningManager, VRAMOptimizerAgent, ProactiveAgent. Retrying in 10s...
audio-interface-1      |   [HEALTH CHECK] Attempt 2/5...
audio-interface-1      |     [WAIT] Not healthy: LearningOrchestrationService, STTService, CodeGenerator, TinyLlamaServiceEnhanced, FixedStreamingTranslation, SelfTrainingOrchestrator, ChainOfThoughtAgent, FusedAudioPreprocessor, ToneDetector, VoiceProfilingAgent, HumanAwarenessAgent, MoodTrackerAgent, ChitchatAgent, FeedbackHandler, KnowledgeBase, ModelOrchestrator, FaceRecognitionAgent, IntentionValidatorAgent, DynamicIdentityAgent, SessionMemoryAgent, EmotionSynthesisAgent, LearningManager, VRAMOptimizerAgent, ProactiveAgent. Retrying in 10s...
audio-interface-1      |   [HEALTH CHECK] Attempt 3/5...
speech-services-1      | [STARTED] EmotionSynthesisAgent (PID: 180) -> /app/main_pc_code/agents/emotion_synthesis_agent.py
speech-services-1      | [STARTED] VRAMOptimizerAgent (PID: 181) -> /app/main_pc_code/agents/vram_optimizer_agent.py
speech-services-1      | [STARTED] FaceRecognitionAgent (PID: 182) -> /app/main_pc_code/agents/face_recognition_agent.py
speech-services-1      | [STARTED] LearningOrchestrationService (PID: 183) -> /app/main_pc_code/agents/learning_orchestration_service.py
speech-services-1      | [STARTED] FusedAudioPreprocessor (PID: 184) -> /app/main_pc_code/agents/fused_audio_preprocessor.py
speech-services-1      | [STARTED] ChitchatAgent (PID: 190) -> /app/main_pc_code/agents/chitchat_agent.py
speech-services-1      | [STARTED] FeedbackHandler (PID: 191) -> /app/main_pc_code/agents/feedback_handler.py
speech-services-1      | [STARTED] HumanAwarenessAgent (PID: 192) -> /app/main_pc_code/agents/human_awareness_agent.py
speech-services-1      | [STARTED] VoiceProfilingAgent (PID: 193) -> /app/main_pc_code/agents/voice_profiling_agent.py
speech-services-1      | [STARTED] ToneDetector (PID: 194) -> /app/main_pc_code/agents/tone_detector.py
speech-services-1      | [STARTED] MoodTrackerAgent (PID: 195) -> /app/main_pc_code/agents/mood_tracker_agent.py
speech-services-1      | [STARTED] KnowledgeBase (PID: 196) -> /app/main_pc_code/agents/knowledge_base.py
speech-services-1      | [STARTED] LearningManager (PID: 197) -> /app/main_pc_code/agents/learning_manager.py
speech-services-1      | [STARTED] SessionMemoryAgent (PID: 198) -> /app/main_pc_code/agents/session_memory_agent.py
speech-services-1      | [INFO] Waiting 10s for agents to initialize...
speech-services-1      |   [HEALTH CHECK] Attempt 1/5...
speech-services-1      |     [WAIT] Not healthy: ProactiveAgent, DynamicIdentityAgent, IntentionValidatorAgent, CodeGenerator, TinyLlamaServiceEnhanced, ChainOfThoughtAgent, ModelOrchestrator, STTService, FixedStreamingTranslation, SelfTrainingOrchestrator, EmotionSynthesisAgent, VRAMOptimizerAgent, FaceRecognitionAgent, LearningOrchestrationService, FusedAudioPreprocessor, ChitchatAgent, FeedbackHandler, HumanAwarenessAgent, VoiceProfilingAgent, ToneDetector, MoodTrackerAgent, KnowledgeBase, LearningManager, SessionMemoryAgent. Retrying in 10s...
speech-services-1      |   [HEALTH CHECK] Attempt 2/5...
speech-services-1      |     [WAIT] Not healthy: ProactiveAgent, DynamicIdentityAgent, IntentionValidatorAgent, CodeGenerator, TinyLlamaServiceEnhanced, ChainOfThoughtAgent, ModelOrchestrator, STTService, FixedStreamingTranslation, SelfTrainingOrchestrator, EmotionSynthesisAgent, VRAMOptimizerAgent, FaceRecognitionAgent, LearningOrchestrationService, FusedAudioPreprocessor, ChitchatAgent, FeedbackHandler, HumanAwarenessAgent, VoiceProfilingAgent, ToneDetector, MoodTrackerAgent, KnowledgeBase, LearningManager, SessionMemoryAgent. Retrying in 10s...
speech-services-1      |   [HEALTH CHECK] Attempt 3/5...
haymayndz@DESKTOP-GC2ET1O:~/AI_System_Monorepo$ docker images | grep ai-system
ai-system/core-services            optimized   f9bf70774d92   21 minutes ago   19.1GB
ai-system/reasoning-services       optimized   ce82311435ed   21 minutes ago   19.1GB
ai-system/vision-processing        optimized   ce999a872395   21 minutes ago   19.1GB
ai-system/gpu-infrastructure       optimized   088a418945bb   21 minutes ago   19.1GB
ai-system/audio-interface          optimized   a5a2a1363b08   36 minutes ago   10GB
ai-system/language-processing      optimized   7ec1a335eba4   39 minutes ago   9.33GB
ai-system/speech-services          optimized   c846891faa42   39 minutes ago   9.33GB
ai-system/learning-knowledge       optimized   dddc0168ab25   39 minutes ago   9.33GB
ai-system/utility-services         optimized   b46f7ca10ad5   39 minutes ago   9.33GB
ai-system/memory-system            optimized   94ef7e865413   39 minutes ago   9.33GB
ai-system/emotion-system           optimized   6fcdf7b844cd   39 minutes ago   9.33GB
ai-system/mm-router                latest      77aa8e4b3d3d   44 hours ago     370MB