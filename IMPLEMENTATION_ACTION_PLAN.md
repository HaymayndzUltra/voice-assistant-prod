Workspace root = /workspace (assumed mount path)
Primary branches
main : protected, deploy-ready
refactor/<topic> : short-lived feature branches
CI = GitHub Actions (YAML in .github/workflows/)
Roles
DevOps AI : CI / scripts / infra
Refactor AI : code cleanup & design fixes
Security AI : secret scan, auth, CURVE setup
Docs AI : diagram, README updates
ML Ops AI : GPU load-balancing & quantisation
🔰 STEP-BY-STEP EXECUTION FLOW
PRE-FLIGHT (DevOps AI)
0.1 git pull origin main --rebase
0.2 python3 generate_agent_inventory.py ➜ verify agent_inventory.csv (≈298 rows).
0.3 Run python3 check_port_conflicts.py --max-count 1 — expect failures; continue to Step 2.
CI GUARDRAILS (Sprint 0.5 – P0)
1.1 Create branch refactor/ci-guardrails
1.2 Add scripts under .github/workflows/guardrails.yml (example below).
1.3 Integrate:
dependency_drift_checker.py
check_port_conflicts.py
lint_no_bare_except.py via flake8
coverage_enforcer.py --min 40 (starter threshold)
1.4 Push branch ➜ open PR ➜ merge after green checks.
Sample guardrails.yml snippet


    jobs:
      guardrails:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Set up Python
            uses: actions/setup-python@v5
            with: {python-version: '3.11'}
          - run: pip install -r pc2_code/requirements.txt -r main_pc_code/requirements.txt flake8 pytest pytest-cov
          - run: python dependency_drift_checker.py
          - run: python check_port_conflicts.py
          - run: flake8 --exit-zero --select=E900 .
          - run: python coverage_enforcer.py --min 40


PORT REGISTRY (Sprint 1 – P0)
2.1 Create config/ports.yaml listing each port, purpose, owner.
2.2 Refactor literals: search tcp://*: ➜ replace with

         from common_utils.port_registry import get_port
         port = get_port("MEMORY_AGENT")

2.3 Add runtime check inside port_registry.py to raise if two distinct agent names request same port.
2.4 Run check_port_conflicts.py again → must pass.
EXCEPTION REFACTOR (Sprint 1-2 – P1)
3.1 Create helper:

         from common_utils.error_handling import SafeExecutor
         with SafeExecutor(logger, recoverable=(ZMQError, asyncio.TimeoutError)):
              risky_call()

.2 Mechanical update:
Search except Exception: ➜ wrap logic in SafeExecutor or catch concrete error.
Search except: ➜ same.
3.3 Run flake8 --select=E900 locally until clean.
3.4 Push PR refactor/exceptions-phase1; merge when CI green.
3.5 Repeat until counter of broad catches = 0 (use script metrics).
DUPLICATE-AGENT MERGE (Sprint 2-3 – P1)
4.1 python refactor_duplicate_agents.py ➜ list duplicates.
4.2 Pick one canonical location (main_pc_code/agents/).
4.3 Diff variants → move unique logic behind feature flags (e.g., machine='PC2').
4.4 Delete backups; run create_issue_from_backup_scanner.py to ensure zero legacy files.
CIRCULAR-IMPORT BREAK (Sprint 3-4 – P1)
5.1 Introduce events/model_events.py & events/memory_events.py dataclasses.
5.2 Publish events over ZMQ PUB PORTS['EVENT_BUS'].
5.3 Replace direct calls between
memory_client ↔ session_memory_agent
model_manager_agent ↔ vram_optimizer_agent.
5.4 Unit-test via pytest‐asyncio to ensure no import loops (python -m pip install snakefood → sfood).
GPU LOAD BALANCING (Sprint 4-5 – P1)
6.1 Install bitsandbytes, transformers > 4.38 (already pinned).
6.2 Quantise NLLB model:

         from transformers import AutoModelForSeq2SeqLM, BitsAndBytesConfig
         model = AutoModelForSeq2SeqLM.from_pretrained(
             "facebook/nllb-200-distilled-600M",
             quantization_config=BitsAndBytesConfig(load_in_8bit=True)
         )

6.3 Set predictive_loading_enabled: true in startup_config.yaml for VRAMOptimizerAgent.
6.4 Deploy gpu_usage_reporter.py --gateway http://prom:9091 on both machines; Grafana dashboard.
DATABASE OPTIMISATION (Sprint 5-6 – P2)
7.1 Add asyncpg connection pool (min_size=5, max_size=20).
7.2 Replace N+1 loops with SELECT ... WHERE id = ANY($1).
7.3 Run EXPLAIN ANALYSE; create index ON logs(timestamp).
SECURITY HARDENING (Sprint 6-8 – P2)
8.1 Run bandit -r . -lll – create baseline, then clean new hits.
8.2 Switch ZMQ:


         server_secret, server_public = zmq.auth.create_certificates('certs', 'server')
         client_secret, client_public = zmq.auth.create_certificates('certs', 'client')
         socket.curve_secretkey = server_secret
         socket.curve_publickey = server_public

8.3 FastAPI admin routes:


         from fastapi import Depends
         from fastapi.security import OAuth2PasswordBearer
         token = OAuth2PasswordBearer('token')
         @app.post('/reload_model')  
         async def reload_model(req: Req, _=Depends(token)): ...


8.4 Commit .gitignore → forbid *.env, api_keys.json.
COMPLEXITY REDUCTION (Sprint 8-10 – P2)
9.1 Run radon cc -s -a main_pc_code pc2_code.
9.2 For each function ≥ A (score > 80) split into helpers.
9.3 Target drop: hottest 5 files → score < 60.
MODERNISATION (Sprint 10-12 – P3)
10.1 Add pyproject.toml using Hatch; move requirements into [project.optional-dependencies].
10.2 Introduce Dependency-Injection container (punq or wired) – agents request services via constructor.
10.3 Create communication_sdk wrapper exporting typed ZMQ client/server.
10.4 Convert legacy asyncio.get_event_loop() to asyncio.run() + TaskGroups (Py 3.12).


📦 FILE / SCRIPT DIRECTORY CHECKLIST


```
automation/
├─ generate_agent_inventory.py
├─ check_port_conflicts.py
├─ dependency_drift_checker.py
├─ extract_todos_to_issues.py
├─ create_issue_from_backup_scanner.py
├─ gpu_usage_reporter.py
├─ coverage_enforcer.py
├─ diagram_validator.py
├─ refactor_duplicate_agents.py
linters/
└─ lint_no_bare_except.py (flake8 plugin)
events/
├─ model_events.py (to be created Sprint 3)
└─ memory_events.py
common_utils/
├─ port_registry.py (to be created Sprint 1)
└─ error_handling.py (SafeExecutor class)


────────────────────────────────────────────────────────  
🔄  DAILY AUTOMATION CYCLE (CRON OR GITHUB ACTION)  
────────────────────────────────────────────────────────  
1. 06:00 UTC – **Inventory Job**  
   `python generate_agent_inventory.py && python diagram_validator.py`  
2. 06:10 UTC – **Guardrails**  
   `check_port_conflicts.py && dependency_drift_checker.py`  
3. 06:20 UTC – **Security Scan**  
   `bandit -r . -lll --quiet`  
4. 06:30 UTC – **GPU Metrics Push**  
   `gpu_usage_reporter.py --gateway $PUSHGATEWAY` (daemon)  

────────────────────────────────────────────────────────  
📌  EXTRA NOTES & TIPS  
────────────────────────────────────────────────────────  
• For any script using GitHub API set env vars:  
  `export GITHUB_TOKEN=<PAT>`  `export REPO=owner/repo`  
• Use `make ci` wrapper to run all guardrail scripts locally.  
• Maintain a **feature flag YAML** (`config/feature_flags.yaml`) so agents can fallback during refactors.  
• All new public APIs require unit tests; `coverage_enforcer.py` will raise the threshold +5 % each month.

────────────────────────────────────────────────────────  
✅  END OF PLAYBOOK – COMPLETE, EXECUTABLE, AND SELF-SUFFICIENT. Good luck!