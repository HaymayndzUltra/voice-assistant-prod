MAIN-PC CONTAINER VALIDATION PLAN
(smoke → integration → cross-group)
PREREQUISITES (once per host)
• All containers of a group are running (docker compose ps).
• Host has curl, jq, nvidia-smi.
• $DOCKER_HOST_IP points to the machine that runs the stack (often 127.0.0.1).
• For GPU groups run docker run --gpus all --rm nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi once to confirm driver-container match.

Format used below
CMD » copy-paste command
EXP » what you should see (200 OK, JSON field, etc.)
★ = required ○ = optional / nice-to-have

────────────────────────
1 infra_core (ServiceRegistry, SystemDigitalTwin)
────────────────────────
AGENT TESTS
★ CMD » curl -f http://$DOCKER_HOST_IP:8200/health
EXP » {"status":"healthy", ...}
★ CMD » curl -f http://$DOCKER_HOST_IP:8221/health # note +1 000 HTTP port
EXP » healthy JSON
○ CMD » docker exec service_registry redis-cli ping (if redis backend)
EXP » PONG

INTEGRATION
★ CMD » python scripts/health_probe.py --target SystemDigitalTwin --registry tcp://$DOCKER_HOST_IP:7200
EXP » probe returns OK

CROSS-GROUP
Used by every other agent; verify once:
★ CMD » python - <<'PY'\nimport zmq, json; s=zmq.Context().socket(zmq.REQ); s.connect('tcp://%s:7200'%'$DOCKER_HOST_IP'); s.send_json({'action':'list_agents'}); print(s.recv_json())\nPY
EXP » list contains at least ServiceRegistry & SystemDigitalTwin.

────────────────────────
2 coordination (RequestCoordinator, ModelManagerSuite, VRAMOptimizerAgent)
────────────────────────
AGENT TESTS
★ CMD » curl -f http://$DOCKER_HOST_IP:27002/health
★ CMD » curl -f http://$DOCKER_HOST_IP:8211/health
○ CMD » curl -f http://$DOCKER_HOST_IP:6572/health (VRAM Optimizer)

SMOKE NLP
★ CMD »

python - <<'PY'
import zmq, json, sys, time
ctx=zmq.Context(); s=ctx.socket(zmq.REQ); s.connect("tcp://$DOCKER_HOST_IP:26002".replace("$DOCKER_HOST_IP",sys.argv[1]))
s.send_json({"action":"generate","prompt":"Hello"}); print(s.recv_json())
PY $DOCKER_HOST_IP
EXP » JSON with engine: field (phi-2 or cloud).

INTEGRATION
★ RequestCoordinator must call ModelManagerSuite.
CMD » docker logs --tail=30 request_coordinator | grep "Forwarded to ModelManagerSuite"
EXP » at least one line.

CROSS-GROUP
★ CMD » curl -f http://$DOCKER_HOST_IP:8221/health | jq '.service'
EXP » "SystemDigitalTwin" (means coordination can see infra_core).

────────────────────────
3 observability (ObservabilityHub)
────────────────────────
★ CMD » curl -f http://$DOCKER_HOST_IP:9000/health
★ CMD » curl -f http://$DOCKER_HOST_IP:9000/metrics | head
○ CMD » curl -X POST http://$DOCKER_HOST_IP:9000/register_agent -d '{"agent_name":"dummy","port":1234}' -H "Content-Type: application/json"
EXP » {"status":"success"...}

Cross-Group
★ Observe it scraped at least one metric:
curl -s http://$DOCKER_HOST_IP:9000/health_summary | jq '.healthy_agents'
EXP » non-zero.

────────────────────────
4 memory_stack (MemoryClient, SessionMemoryAgent, KnowledgeBase)
────────────────────────
★ CMD » curl -f http://$DOCKER_HOST_IP:6713/health
★ CMD » curl -f http://$DOCKER_HOST_IP:6574/health
○ CMD » curl -f http://$DOCKER_HOST_IP:6715/health

Integration
★ MemoryClient ↔ Redis
docker logs memory_client | grep "Connected to Redis" -m1
EXP » found.
★ SessionMemoryAgent ↔ MemoryClient
curl -X POST http://$DOCKER_HOST_IP:6574/append -d '{"key":"test","value":"hello"}' -H "Content-Type: application/json"
then
curl -s http://$DOCKER_HOST_IP:6574/get/test | grep hello

────────────────────────
5 vision_gpu (FaceRecognitionAgent)
────────────────────────
Pre-condition: GPU base image present.
★ CMD » docker exec face_recognition_agent nvidia-smi (should list GPU)
★ CMD » curl -f http://$DOCKER_HOST_IP:6610/health
○ Demo inference (needs sample image face.jpg):

curl -F "file=@face.jpg" http://$DOCKER_HOST_IP:5610/recognize
EXP » JSON with bounding-box or name.

────────────────────────
6 speech_gpu (8 agents)
────────────────────────
Key endpoints (replace PORT_OFFSET):
• STT /health → 6800 • TTS /health → 6801 • StreamingInterrupt /health → 6576

Smoke
★ curl -f http://$DOCKER_HOST_IP:6800/health
★ curl -f http://$DOCKER_HOST_IP:6801/health

End-to-end streaming test (optional)
○ Run scripts/audio_pipeline_test.py (sends 5-sec wav, expects text JSON).

Integration
★ Verify WakeWordDetector publishes interrupt:
docker logs wake_word_detector | grep "WAKE_WORD_DETECTED" -m1

────────────────────────
7 learning_gpu (7 agents)
────────────────────────
Smoke
★ curl -f http://$DOCKER_HOST_IP:8212/health (LearningOrchestrationService)
★ curl -f http://$DOCKER_HOST_IP:6580/health (LearningManager)

GPU check
★ docker exec self_training_orchestrator nvidia-smi

Integration
★ After triggering orchestrator:
docker exec self_training_orchestrator python -m trigger_dummy_job
then check logs of LocalFineTunerAgent for “Training complete”.

────────────────────────
8 reasoning_gpu (3 agents)
────────────────────────
★ Health ports: 6612, 6646, 6641 → curl all.
Smoke generation
★ curl -X POST http://$DOCKER_HOST_IP:6612/chain -d '{"query":"2+2"}' -H "Content-Type: application/json"
EXP » JSON with reasoning steps.

────────────────────────
9 language_stack (11 agents)
────────────────────────
Required smoke (already mostly done):
★ curl -f http://$DOCKER_HOST_IP:6709/health (NLU)
★ curl -f http://$DOCKER_HOST_IP:6710/health (AdvCmd)
★ curl -f http://$DOCKER_HOST_IP:6706/health (EmotionSynth)

Conversation round-trip
○ python scripts/dialogue_roundtrip.py "Hello there" → expect combined NLU→Responder JSON.

────────────────────────
10 utility_cpu (6 agents)
────────────────────────
★ curl -f http://$DOCKER_HOST_IP:6650/health (CodeGenerator)
★ curl -f http://$DOCKER_HOST_IP:6606/health (Executor)
★ curl -f http://$DOCKER_HOST_IP:6595/health (TranslationService or new port 6597)

Quick compile test
○ curl -X POST http://$DOCKER_HOST_IP:6650/generate -d '{"prompt":"print(1+1)"}'

────────────────────────
11 emotion_system (6 agents)
────────────────────────
★ curl -f http://$DOCKER_HOST_IP:6590/health
★ curl -f http://$DOCKER_HOST_IP:6703/health (EmpathyAgent)

Integration
★ Post mood update
curl -X POST http://$DOCKER_HOST_IP:6704/update -d '{"mood":"happy"}'
EXP » status":"success" then EmotionEngine log shows new mood.

────────────────────────
12 translation_services (GPU adapters)
────────────────────────
★ curl -f http://$DOCKER_HOST_IP:6584/health
★ curl -f http://$DOCKER_HOST_IP:6582/health
Smoke
○ curl -X POST http://$DOCKER_HOST_IP:6584/translate -d '{"text":"Hello","target":"fr"}'
EXP » "Bonjour" in JSON.

────────────────────────
CROSS-GROUP / HYBRID ROUTING TESTS
────────────────────────
★ Local-first then fallback:

python scripts/hybrid_test.py --prompt "Summarise this text." \
      --quality-threshold 0.01      # force cloud fallback
EXP » Response JSON shows "engine":"gpt-4o"

★ Memory lookup across groups
– Insert via SessionMemoryAgent, retrieve via KnowledgeBase REST
(ensures MessageBus path).

────────────────────────
ACTION-PLAN CHECKLIST (copy-paste)
────────────────────────

Run all ★ commands.
Confirm each returns expected output / 0 restart-count.
Optional ○ commands deepen coverage.
Log any failures and re-run only the failing group’s smoke tests after fixes.