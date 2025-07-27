# GABAY SA PAGLIPAT SA BAGONG UNIFIED SYSTEM REPOSITORY

## MGA HAKBANG SA PAGLIPAT (Step-by-Step Migration)

### HAKBANG 1: Kopyahin ang Agents

**IMPORTANTE**: Oo, kailangan mong kopyahin LAHAT ng agent files mula sa main_pc_code at pc2_code!

```bash
# 1. Pumunta sa unified-system-v1 directory
cd /workspace/unified-system-v1

# 2. Kopyahin LAHAT ng MainPC agents
cp -r /workspace/main_pc_code/agents/* src/agents/mainpc/
cp -r /workspace/main_pc_code/services/* src/agents/mainpc/services/
cp -r /workspace/main_pc_code/FORMAINPC/* src/agents/mainpc/formainpc/

# 3. Kopyahin ang model_manager_suite.py (special case)
cp /workspace/main_pc_code/model_manager_suite.py src/agents/mainpc/

# 4. Kopyahin LAHAT ng PC2 agents  
cp -r /workspace/pc2_code/agents/* src/agents/pc2/
cp -r /workspace/pc2_code/agents/ForPC2/* src/agents/pc2/forpc2/

# 5. Kopyahin ang ObservabilityHub
cp -r /workspace/phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/* src/agents/core/
```

### HAKBANG 2: I-create ang mga directories kung wala pa

```bash
# Siguruhing may mga directories
mkdir -p src/agents/mainpc/services
mkdir -p src/agents/mainpc/formainpc
mkdir -p src/agents/pc2/forpc2
mkdir -p src/agents/core
```

### HAKBANG 3: I-update ang script paths sa configuration

```bash
# I-edit ang config/startup_config.yaml
# Palitan lahat ng paths from:
#   script_path: main_pc_code/agents/xxx.py
# To:
#   script_path: src/agents/mainpc/xxx.py

# At from:
#   script_path: pc2_code/agents/xxx.py  
# To:
#   script_path: src/agents/pc2/xxx.py
```

### HAKBANG 4: Kopyahin ang ibang dependencies

```bash
# Kopyahin ang shared utilities kung meron
cp -r /workspace/main_pc_code/utils/* src/utils/
cp -r /workspace/pc2_code/utils/* src/utils/

# Kopyahin ang models directory kung meron
cp -r /workspace/main_pc_code/models models/
cp -r /workspace/pc2_code/models models/
```

### HAKBANG 5: I-setup ang environment

```bash
# 1. Gumawa ng virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# O sa Windows: venv\Scripts\activate

# 2. I-install ang dependencies
pip install -r requirements.txt

# 3. Kopyahin at i-setup ang .env file
cp .env.example .env
# I-edit ang .env at ilagay ang tamang values
nano .env  # o kung anong editor gusto mo
```

### HAKBANG 6: I-test ang configuration

```bash
# 1. I-validate ang configuration
python scripts/maintenance/validate_config.py config/startup_config.yaml

# 2. Subukan ang dry-run
python main.py start --profile core --dry-run

# 3. Kung ok na, i-start ang system
python main.py start --profile core
```

## MGA AGENT NA KAILANGAN MONG KOPYAHIN

### Mula sa MainPC (54 agents):
- service_registry_agent.py
- system_digital_twin.py
- request_coordinator.py
- model_manager_suite.py
- vram_optimizer_agent.py
- memory_client.py
- knowledge_base.py
- session_memory_agent.py
- streaming_audio_capture.py
- fused_audio_preprocessor.py
- streaming_speech_recognition.py
- streaming_tts_agent.py
- chain_of_thought_agent.py
- vision_agent.py
- emotion_agent.py
- nlu_agent.py
- at marami pang iba...

### Mula sa PC2 (23 agents):
- memory_orchestrator_service.py
- resource_manager.py
- async_processor.py
- context_manager.py
- unified_memory_reasoning_agent.py
- task_scheduler.py
- tiered_responder.py
- vision_processing_agent.py
- DreamWorldAgent.py
- tutor_agent.py
- at iba pa...

### Mula sa Phase1 Implementation:
- observability_hub.py

## CHECKLIST BAGO MAG-DEPLOY

- [ ] Nakopya na lahat ng agent files
- [ ] Na-update na ang script paths sa config
- [ ] Nakopya na ang utilities at models
- [ ] Na-setup na ang .env file
- [ ] Na-install na ang dependencies
- [ ] Na-test na ang configuration
- [ ] Gumagana na ang basic startup

## MGA COMMON ISSUES AT SOLUTIONS

### 1. "Module not found" error
```bash
# Siguruhing nasa PYTHONPATH ang src directory
export PYTHONPATH=$PYTHONPATH:/path/to/unified-system-v1/src
```

### 2. Port conflicts
```bash
# Tignan kung may gumagamit ng ports
lsof -i :7200-7299
# Kill kung kailangan
kill -9 <PID>
```

### 3. Missing dependencies
```bash
# I-check ang imports sa agent files
grep -r "import" src/agents/ | grep -v "from \." | sort | uniq
# Idagdag sa requirements.txt kung may kulang
```

## FINAL VERIFICATION

```bash
# 1. I-run ang repository validator
python scripts/validate_repository.py

# 2. I-test ang lahat ng profiles
for profile in core vision learning tutoring full; do
    echo "Testing $profile profile..."
    python main.py start --profile $profile --dry-run
done

# 3. I-run ang integration tests
python tests/integration/test_phase2_integration.py
```

---

**PAALALA**: Importante na i-backup mo muna ang original files bago ka mag-migrate!

```bash
# Backup muna
tar -czf unified-system-backup-$(date +%Y%m%d).tar.gz /workspace/main_pc_code /workspace/pc2_code
```