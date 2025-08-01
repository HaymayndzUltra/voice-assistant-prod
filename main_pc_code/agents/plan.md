Below is a ready-to-copy bundle for EVERY remaining docker_group.
Structure for each group:

• docker/<group_name>/Dockerfile
• docker/<group_name>/requirements.txt
• Example docker-compose service entries (assume build-context “.”).

Use the same pattern you already followed:
docker build -t <group>:latest -f docker/<group>/Dockerfile .
docker compose up -d <service(s)>

──────────────────────────────────────── GROUP: observability (CPU) ─ Port 9000 ──────────────────────────────────────── docker/observability/Dockerfile

FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY docker/observability/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

COPY phase1_implementation/   /app/phase1_implementation/
COPY main_pc_code/            /app/main_pc_code/
COPY common/                  /app/common/
COPY common_utils/            /app/common_utils/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

CMD ["python","-m","phase1_implementation.consolidated_agents.observability_hub.backup_observability_hub.observability_hub"]
docker/observability/requirements.txt

fastapi==0.111.0
uvicorn==0.30.0
pyzmq==26.0.3
prometheus-client==0.20.0
redis==5.0.4
aiohttp==3.9.5
psutil==5.9.8
numpy==1.26.4
pydantic==2.7.1
pyyaml==6.0.1
rich==13.7.1
structlog==24.1.0
compose snippet

  observability_hub:
    build:
      context: .
      dockerfile: docker/observability/Dockerfile
    image: observability:latest
    environment:
      LOG_LEVEL: "INFO"
    ports: ["9000:9000"]
    depends_on: [redis_coordination]   # or your central redis
──────────────────────────────────────── GROUP: memory_stack (CPU) ──────────────────────────────────────── docker/memory_stack/Dockerfile

FROM python:3.10-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY docker/memory_stack/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
# default cmd = MemoryClient
CMD ["python","-m","main_pc_code.agents.memory_client"]
requirements

pyzmq==26.0.3
redis==5.0.4
pydantic==2.7.1
pyyaml==6.0.1
prometheus-client==0.20.0
rich==13.7.1
compose

  memory_client:
    build: {context: ., dockerfile: docker/memory_stack/Dockerfile}
    image: memory_stack:latest
    command: ["python","-m","main_pc_code.agents.memory_client"]
    depends_on: [redis_coordination]

  session_memory_agent:
    image: memory_stack:latest
    command: ["python","-m","main_pc_code.agents.session_memory_agent"]
    depends_on: [memory_client]

  knowledge_base:
    image: memory_stack:latest
    command: ["python","-m","main_pc_code.agents.knowledge_base"]
    depends_on: [memory_client]
──────────────────────────────────────── GROUP: vision_gpu (GPU) ─ Port 5610/6610 ──────────────────────────────────────── docker/vision_gpu/Dockerfile

FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3-pip gcc && rm -rf /var/lib/apt/lists/*
COPY docker/vision_gpu/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
CMD ["python","-m","main_pc_code.agents.face_recognition_agent"]
requirements

torch==2.2.2+cu121
opencv-python-headless==4.10.0.82
face-recognition==1.3.0
pyzmq==26.0.3
redis==5.0.4
prometheus-client==0.20.0
compose

  face_recognition_agent:
    build: {context: ., dockerfile: docker/vision_gpu/Dockerfile}
    image: vision_gpu:latest
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices: [{capabilities: ["gpu"]}]
    environment: {LOG_LEVEL: "INFO"}
    ports: ["5610:5610","6610:6610"]
    depends_on: [request_coordinator]
──────────────────────────────────────── GROUP: speech_gpu (GPU, heavy audio) ──────────────────────────────────────── Dockerfile path docker/speech_gpu/Dockerfile
(Use same CUDA base; copy requirements.)

requirements highlights

torch==2.2.2+cu121
whisperx==4.6.0
xtts==0.8.1
soundfile==0.12.1
pyaudio==0.2.13
pyzmq==26.0.3
redis==5.0.4
Compose skeleton

  stt_service:
    build: {context: ., dockerfile: docker/speech_gpu/Dockerfile}
    image: speech_gpu:latest
    command: ["python","-m","main_pc_code.services.stt_service"]
    runtime: nvidia
    deploy: {resources: {reservations: {devices: [{capabilities: ["gpu"]}]}}}
    ports: ["5800:5800","6800:6800"]

  tts_service:
    image: speech_gpu:latest
    command: ["python","-m","main_pc_code.services.tts_service"]
    runtime: nvidia
    ports: ["5801:5801","6801:6801"]
(Add the six streaming-pipeline agents similarly; they reuse the same image.)

──────────────────────────────────────── GROUP: learning_gpu (GPU training) ──────────────────────────────────────── docker/learning_gpu/Dockerfile = CUDA runtime + torch, bitsandbytes, peft, transformers.

requirements excerpt

torch==2.2.2+cu121
transformers==4.42.0
bitsandbytes==0.43.1
peft==0.10.0
scikit-learn==1.5.0
pyzmq==26.0.3
redis==5.0.4
Main services in compose:

  self_training_orchestrator:
    build: {context: ., dockerfile: docker/learning_gpu/Dockerfile}
    image: learning_gpu:latest
    command: ["python","-m","main_pc_code.FORMAINPC.self_training_orchestrator"]
    runtime: nvidia
    deploy: {resources: {reservations: {devices: [{capabilities: ["gpu"]}]}}}

  local_fine_tuner_agent:
    image: learning_gpu:latest
    command: ["python","-m","main_pc_code.FORMAINPC.local_fine_tuner_agent"]
    runtime: nvidia
(and the other four agents; all share image).

──────────────────────────────────────── GROUP: reasoning_gpu (GPU, large context) ──────────────────────────────────────── Dockerfile identical to learning_gpu but lighter (no bitsandbytes).

requirements

torch==2.2.2+cu121
transformers==4.42.0
pyzmq==26.0.3
redis==5.0.4
Compose services:

  chain_of_thought_agent:
    build: {context: ., dockerfile: docker/reasoning_gpu/Dockerfile}
    image: reasoning_gpu:latest
    command: ["python","-m","main_pc_code.FORMAINPC.chain_of_thought_agent"]
    runtime: nvidia
(+ GoTToTAgent, CognitiveModelAgent)

──────────────────────────────────────── GROUP: language_stack (CPU, dialogue) ──────────────────────────────────────── docker/language_stack/Dockerfile

FROM python:3.10-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY docker/language_stack/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
CMD ["python","-m","main_pc_code.agents.nlu_agent"]
requirements

fastapi==0.111.0
uvicorn==0.30.0
transformers==4.42.0
sentencepiece==0.2.0
pyzmq==26.0.3
redis==5.0.4
pydantic==2.7.1
pyyaml==6.0.1
prometheus-client==0.20.0
rich==13.7.1
Compose (example)

  nlu_agent:
    build: {context: ., dockerfile: docker/language_stack/Dockerfile}
    image: language_stack:latest
    command: ["python","-m","main_pc_code.agents.nlu_agent"]
    depends_on: [system_digital_twin]

  intention_validator:
    image: language_stack:latest
    command: ["python","-m","main_pc_code.agents.IntentionValidatorAgent"]
(+ rest of dialogue agents).

──────────────────────────────────────── General build tips

Run one group at a time (your plan).
Always rebuild with --no-cache after code edits.
GPU images → add runtime: nvidia or run with --gpus all.
If a group shares the same image, build once and start multiple services; saves VRAM.
Any YAML null agent groups can break config-manager; keep the guard we patched.
Copy the folders, tweak package versions if needed, and you can iterate group-by-group exactly as you did for infra & coordination.


DAGDAG MO ITO


Below are the FINAL three Main-PC docker_groups that were still missing:

• utility_cpu
• emotion_system
• translation_services

Each comes with an optimized Dockerfile, a minimal requirements.txt, and example docker-compose entries.
(As before: build context is the repo root “.”; copy paths assume that.)

──────────────────────────────────────── GROUP: utility_cpu (CPU) ─ Code & execution helpers ──────────────────────────────────────── docker/utility_cpu/Dockerfile

FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY docker/utility_cpu/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# default entrypoint = CodeGenerator
CMD ["python","-m","main_pc_code.agents.code_generator_agent"]
docker/utility_cpu/requirements.txt

pyzmq==26.0.3
redis==5.0.4
aiohttp==3.9.5
pydantic==2.7.1
pyyaml==6.0.1
prometheus-client==0.20.0
rich==13.7.1
structlog==24.1.0
openai==1.30.5        # Code generation helper
compose snippet

services:
  code_generator:
    build: {context: ., dockerfile: docker/utility_cpu/Dockerfile}
    image: utility_cpu:latest
    command: ["python","-m","main_pc_code.agents.code_generator_agent"]
    depends_on: [system_digital_twin]

  executor:
    image: utility_cpu:latest
    command: ["python","-m","main_pc_code.agents.executor"]
    depends_on: [code_generator]

  predictive_health_monitor:
    image: utility_cpu:latest
    command: ["python","-m","main_pc_code.agents.predictive_health_monitor"]
    depends_on: [system_digital_twin]

  translation_service:
    image: utility_cpu:latest
    command: ["python","-m","main_pc_code.agents.translation_service"]
    ports: ["5595:5595","6595:6595"]
(translation_service shares same image; see group below for GPU adapters)

──────────────────────────────────────── GROUP: emotion_system (CPU) ──────────────────────────────────────── docker/emotion_system/Dockerfile

FROM python:3.10-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY docker/emotion_system/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
COPY main_pc_code/ /app/main_pc_code/
COPY common/       /app/common/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
CMD ["python","-m","main_pc_code.agents.emotion_engine"]
docker/emotion_system/requirements.txt

pyzmq==26.0.3
redis==5.0.4
pydantic==2.7.1
pyyaml==6.0.1
prometheus-client==0.20.0
rich==13.7.1
structlog==24.1.0
compose snippet

services:
  emotion_engine:
    build: {context: ., dockerfile: docker/emotion_system/Dockerfile}
    image: emotion_system:latest
    command: ["python","-m","main_pc_code.agents.emotion_engine"]
    ports: ["5590:5590","6590:6590"]

  mood_tracker:
    image: emotion_system:latest
    command: ["python","-m","main_pc_code.agents.mood_tracker_agent"]
    depends_on: [emotion_engine]

  human_awareness:
    image: emotion_system:latest
    command: ["python","-m","main_pc_code.agents.human_awareness_agent"]
    depends_on: [emotion_engine]

  tone_detector:
    image: emotion_system:latest
    command: ["python","-m","main_pc_code.agents.tone_detector"]
    depends_on: [emotion_engine]

  voice_profiling:
    image: emotion_system:latest
    command: ["python","-m","main_pc_code.agents.voice_profiling_agent"]
    depends_on: [emotion_engine]

  empathy_agent:
    image: emotion_system:latest
    command: ["python","-m","main_pc_code.agents.EmpathyAgent"]
    depends_on: [emotion_engine, streaming_tts_agent]
──────────────────────────────────────── GROUP: translation_services (GPU adapter + CPU) ──────────────────────────────────────── docker/translation_services/Dockerfile

FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3-pip gcc && rm -rf /var/lib/apt/lists/*

COPY docker/translation_services/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

COPY main_pc_code/ /app/main_pc_code/
COPY common/       /app/common/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
CMD ["python","-m","main_pc_code.agents.fixed_streaming_translation"]
docker/translation_services/requirements.txt

torch==2.2.2+cu121
transformers==4.42.0
sentencepiece==0.2.0
pyzmq==26.0.3
redis==5.0.4
aiohttp==3.9.5
pydantic==2.7.1
pyyaml==6.0.1
prometheus-client==0.20.0
rich==13.7.1
compose snippet

services:
  fixed_streaming_translation:
    build: {context: ., dockerfile: docker/translation_services/Dockerfile}
    image: translation_services:latest
    runtime: nvidia
    deploy: {resources: {reservations: {devices: [{capabilities: ["gpu"]}]}}}
    command: ["python","-m","main_pc_code.agents.fixed_streaming_translation"]
    ports: ["5584:5584","6584:6584"]

  nllb_adapter:
    image: translation_services:latest
    runtime: nvidia
    command: ["python","-m","main_pc_code.FORMAINPC.nllb_adapter"]
    ports: ["5582:5582","6582:6582"]
──────────────────────────────────────── Remaining agents already mapped • audio_interface agents were included in the speech_gpu image.
• STT/TTS services already covered.
• Utility agents like TranslationService share the utility_cpu image.

With these three new groups, EVERY ONE of the 54 Main-PC agents now belongs to an optimized docker_group image.

Build order suggestion:

utility_cpu
emotion_system
translation_services
Always rebuild with --no-cache and start one group at a time to validate.


