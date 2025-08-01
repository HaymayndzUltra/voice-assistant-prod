version: "3.9"
name: mainpc_sot

# -----------------------------------------------------------------------------
# GLOBALS / VOLUMES / NETWORKS
# -----------------------------------------------------------------------------

volumes:
  redis_data:
  data:
  models:
  logs:

networks:
  backplane:
    driver: bridge

services:
  # ---------------------------------------------------------------------------
  # 1. INFRASTRUCTURE – Redis (shared in-memory registry)
  # ---------------------------------------------------------------------------
  redis:
    image: redis:7-alpine
    container_name: mainpc-redis
    command: ["redis-server", "--appendonly", "yes"]
    networks: [backplane]
    ports:
      - "6380:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ---------------------------------------------------------------------------
  # 2. FOUNDATION_SERVICES – Core orchestration & monitoring (4 agents)
  # ---------------------------------------------------------------------------
  foundation_services:
    build:
      context: .
      dockerfile: docker/mainpc/Dockerfile
    image: mainpc/foundation_services:latest
    container_name: mainpc-foundation-services
    command: >-
      python -m main_pc_code.system_launcher_containerized \
      --groups foundation_services
    environment:
      PYTHONPATH: /app
      MACHINE_TYPE: mainpc
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6380/0
      PORT_OFFSET: 0
    depends_on:
      redis:
        condition: service_healthy
    networks: [backplane]
    ports:
      - "7200:7200"   # ServiceRegistry
      - "7220:7220"   # SystemDigitalTwin
      - "26002:26002" # RequestCoordinator
      - "7211:7211"   # ModelManagerSuite
      - "5572:5572"   # VRAMOptimizerAgent
      - "7201:7201"   # UnifiedSystemAgent
      - "9000:9000"   # ObservabilityHub
    volumes:
      - logs:/app/logs
      - data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9000/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

  # ---------------------------------------------------------------------------
  # 3. MODEL_MANAGEMENT – Heavy GPU services (currently empty)
  # ---------------------------------------------------------------------------
  # model_management service removed - no agents in gpu_infrastructure group
  # GPU resources are handled by foundation_services (ModelManagerSuite, VRAMOptimizerAgent)

  # ---------------------------------------------------------------------------
  # 4. LANGUAGE_PIPELINE – Core NLP stack (language_processing group)
  # ---------------------------------------------------------------------------
  language_pipeline:
    build:
      context: .
      dockerfile: docker/mainpc/Dockerfile
    image: mainpc/language_pipeline:latest
    container_name: mainpc-language-pipeline
    command: >-
      python -m main_pc_code.system_launcher_containerized \
      --groups language_processing
    environment:
      PYTHONPATH: /app
      MACHINE_TYPE: mainpc
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6380/0
    depends_on:
      foundation_services:
        condition: service_started
    networks: [backplane]
    ports:
      - "5709:5709"  # NLUAgent
      - "5710:5710"  # AdvancedCommandHandler
      - "5711:5711"  # ChitchatAgent
      - "5637:5637"  # Responder
      - "5701:5701"  # IntentionValidatorAgent
    volumes:
      - data:/app/data:ro
      - logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:5709/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  # ---------------------------------------------------------------------------
  # 5. TRANSLATION_SERVICES – Dedicated translation agents
  # ---------------------------------------------------------------------------
  translation_services:
    build:
      context: .
      dockerfile: docker/mainpc/Dockerfile
    image: mainpc/translation_services:latest
    container_name: mainpc-translation-services
    command: >-
      python -m main_pc_code.system_launcher_containerized \
      --groups translation_services
    environment:
      PYTHONPATH: /app
      MACHINE_TYPE: mainpc
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6380/0
    depends_on:
      foundation_services:
        condition: service_started
    networks: [backplane]
    ports:
      - "5595:5595"  # TranslationService
      - "5584:5584"  # FixedStreamingTranslation
      - "5581:5581"  # NLLBAdapter
    volumes:
      - data:/app/data:ro
      - logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:5595/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  # ---------------------------------------------------------------------------
  # 6. AUDIO_SPEECH – Full streaming audio pipeline (speech_services + audio_interface)
  # ---------------------------------------------------------------------------
  audio_speech:
    build:
      context: .
      dockerfile: docker/mainpc/Dockerfile
    image: mainpc/audio_speech:latest
    container_name: mainpc-audio-speech
    command: >-
      python -m main_pc_code.system_launcher_containerized \
      --groups speech_services,audio_interface
    environment:
      PYTHONPATH: /app
      MACHINE_TYPE: mainpc
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6380/0
    depends_on:
      foundation_services:
        condition: service_started
    networks: [backplane]
    ports:
      - "5800:5800"  # STTService
      - "5801:5801"  # TTSService
      - "6553:6553"  # StreamingSpeechRecognition
      - "5562:5562"  # StreamingTTSAgent
      - "5579:5579"  # StreamingLanguageAnalyzer
      - "6552:6552"  # WakeWordDetector
      - "6550:6550"  # AudioCapture
      - "6551:6551"  # FusedAudioPreprocessor
      - "5576:5576"  # StreamingInterruptHandler
    volumes:
      - data:/app/data:ro
      - logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:5800/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  # ---------------------------------------------------------------------------
  # 7. VISION_PROCESSING – Face/vision agents
  # ---------------------------------------------------------------------------
  vision_processing:
    build:
      context: .
      dockerfile: docker/mainpc/Dockerfile
    image: mainpc/vision_processing:latest
    container_name: mainpc-vision-processing
    command: >-
      python -m main_pc_code.system_launcher_containerized \
      --groups vision_processing
    environment:
      PYTHONPATH: /app
      MACHINE_TYPE: mainpc
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6380/0
    depends_on:
      foundation_services:
        condition: service_started
    networks: [backplane]
    ports:
      - "5610:5610"  # FaceRecognitionAgent
    volumes:
      - data:/app/data:ro
      - logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:5610/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  # ---------------------------------------------------------------------------
  # 8. MEMORY_SYSTEM – Memory-related agents
  # ---------------------------------------------------------------------------
  memory_system:
    build:
      context: .
      dockerfile: docker/mainpc/Dockerfile
    image: mainpc/memory_system:latest
    container_name: mainpc-memory-system
    command: >-
      python -m main_pc_code.system_launcher_containerized \
      --groups memory_system
    environment:
      PYTHONPATH: /app
      MACHINE_TYPE: mainpc
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6380/0
    depends_on:
      foundation_services:
        condition: service_started
    networks: [backplane]
    ports:
      - "5713:5713"  # MemoryClient
      - "5574:5574"  # SessionMemoryAgent
      - "5715:5715"  # KnowledgeBase
    volumes:
      - data:/app/data
      - logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:5713/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  # ---------------------------------------------------------------------------
  # 9. EMOTION_SYSTEM – Emotion-related agents
  # ---------------------------------------------------------------------------
  emotion_system:
    build:
      context: .
      dockerfile: docker/mainpc/Dockerfile
    image: mainpc/emotion_system:latest
    container_name: mainpc-emotion-system
    command: >-
      python -m main_pc_code.system_launcher_containerized \
      --groups emotion_system
    environment:
      PYTHONPATH: /app
      MACHINE_TYPE: mainpc
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6380/0
    depends_on:
      foundation_services:
        condition: service_started
      audio_speech:
        condition: service_started
    networks: [backplane]
    ports:
      - "5590:5590"  # EmotionEngine
      - "5704:5704"  # MoodTrackerAgent
      - "5705:5705"  # HumanAwarenessAgent
      - "5625:5625"  # ToneDetector
      - "5708:5708"  # VoiceProfilingAgent
      - "5703:5703"  # EmpathyAgent
    volumes:
      - logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:5590/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  # ---------------------------------------------------------------------------
  # 10. LEARNING_SERVICES – Learning & training agents
  # ---------------------------------------------------------------------------
  learning_services:
    build:
      context: .
      dockerfile: docker/mainpc/Dockerfile
    image: mainpc/learning_services:latest
    container_name: mainpc-learning-services
    command: >-
      python -m main_pc_code.system_launcher_containerized \
      --groups learning_knowledge,utility_services,reasoning_services
    environment:
      PYTHONPATH: /app
      MACHINE_TYPE: mainpc
      LOG_LEVEL: INFO
      REDIS_URL: redis://redis:6380/0
      NVIDIA_VISIBLE_DEVICES: 0
    depends_on:
      foundation_services:
        condition: service_started
    networks: [backplane]
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
        limits:
          cpus: "4"
          memory: 8G
    ports:
      - "7210:7210"  # LearningOrchestrationService
      - "7202:7202"  # LearningOpportunityDetector
      - "5580:5580"  # LearningManager
      - "5638:5638"  # ActiveLearningMonitor
      - "5643:5643"  # LearningAdjusterAgent
      - "5660:5660"  # SelfTrainingOrchestrator
      - "5642:5642"  # LocalFineTunerAgent
      - "5612:5612"  # ChainOfThoughtAgent
      - "5646:5646"  # GoTToTAgent
      - "5641:5641"  # CognitiveModelAgent
    volumes:
      - models:/app/models:ro
      - data:/app/data:ro
      - logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:7210/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s



📊 UPDATED STRUCTURE:
Service	Agents	Dependencies
1. redis	1	None
2. foundation_services	7	redis
3. language_pipeline	5	foundation_services
4. translation_services	3	foundation_services
5. audio_speech	9	foundation_services
6. vision_processing	1	foundation_services
7. memory_system	3	foundation_services
8. emotion_system	6	foundation_services, audio_speech
9. learning_services	10	foundation_services
�� BENEFITS:
✅ No more invalid health checks
✅ Cleaner dependency chain
✅ GPU resources handled by foundation_services
✅ 9 services instead of 10 (more efficient)
Ready to deploy now! 🚀


