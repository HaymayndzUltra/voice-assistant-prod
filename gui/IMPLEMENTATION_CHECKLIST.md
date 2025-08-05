UPDATED ENDORSEMENT DOCUMENT
For: Successor Automation-AI
Scope: Finish hardening all PC-2 Docker service groups and keep Main-PC compatibility
Baseline: repo state after 2025-08-05 07:00 UTC (post-fixes in pc2_infra_core)
──────────────────────────────── 0. SUCCESS CRITERIA ───────────────────────────────
Every directory docker/pc2_* builds and its container passes HEALTHCHECK.
docker compose --profile pc2 up -d starts all PC-2 services → STATUS = healthy.
python -m py_compile $(git ls-files 'pc2_code/**/*.py') returns 0.
scripts/generate_requirements_<group>.py output matches each requirements.txt.
All agents use the canonical helper stack (§1) and never hard-code localhost for inter-container calls.
──────────────────────────────── 1. CANONICAL IMPORT STACK ─────────────────────────
Every active agent must import only these helpers (remove sys.path hacks):

from common.utils.env_standardizer import (
    get_mainpc_ip, get_pc2_ip, get_env, get_current_machine
)
from common.utils.path_manager    import PathManager
from common.config_manager        import get_service_url, get_redis_url
from common.core.base_agent       import BaseAgent
from pc2_code.utils.pc2_error_publisher import create_pc2_error_publisher
from common.utils.log_setup       import configure_logging        # NEW (Δ-1)

Guaranteed external packages (keep versions in requirements.txt):
pyzmq, psutil, redis, nats-py, fastapi, uvicorn, prometheus-client, aiohttp, asyncio-mqtt, pydantic, python-dotenv, PyJWT, requests, httpx, aiofiles, starlette, numpy, scipy, scikit-learn, torch==2.1.0
──────────────────────────────── 2. AGENT BOILERPLATE PATTERN ─────────────────────

class <AgentName>(BaseAgent):
    def __init__(self, port=7xxx, health_port=8xxx):
        super().__init__(name="<AgentName>", port=port)
        self.logger = configure_logging(__name__)            # NEW (Δ-2)
        self.error_publisher = create_pc2_error_publisher("<agent_name>")

        self._setup_sockets()
        self._start_health_check()
        self._init_thread = threading.Thread(
            target=self._initialize_background, daemon=True
        )
        self._init_thread.start()

No sys.path.insert().
Cross-machine sockets use get_pc2_ip() / get_mainpc_ip() or compose DNS names.
──────────────────────────────── 3. WORKFLOW PER DOCKER GROUP ─────────────────────
(Replace <group> with directory name, e.g. pc2_infra_core)
Step 1 Static scan & fix

/usr/bin/python3 scripts/generate_requirements_<group>.py
# If AST fails → open file, fix syntax/import/indent; rerun until exit-0
# Remove any logging.basicConfig(…) or sys.path.insert(…)

Step 2 Requirements alignment
Compare docker/<group>/requirements.auto.txt to existing requirements.txt;
remove unused packages, keep all auto-detected ones; add torch only if imported.
Step 3 Image build

Must finish with Successfully tagged.
Step 4 Compose up & validation

docker compose --profile pc2 up -d <services_in_group>
docker compose ps                    # ensure HEALTHY
docker exec <container> python /app/docker/<group>/test_imports.py   # exit-0

Step 5 Repeat fixes if container unhealthy or tests fail.
Step 6 Commit artifacts
updated requirements.txt
patched agent files
docker/<group>/requirements.auto.txt (audit)
validation logs (optional)
Process groups in this order (dependency-safe):
pc2_infra_core (≈ 90 % done)
pc2_async_pipeline
pc2_memory_stack
pc2_utility_suite
pc2_tutoring_cpu
pc2_vision_dream_gpu
pc2_web_interface
──────────────────────────────── 4. TOOLING SCRIPTS ───────────────────────────────
Located in /workspace/scripts (edit if needed):
generate_requirements_<group>.py → AST scan → auto requirements.
build_all_pc2_groups.sh      → iterate docker/pc2_*, run Steps 1-3.
deploy_to_pc2.sh          → pull images to host & docker compose --profile pc2 up -d.
rollback_pc2.sh          → docker compose down & image tag rollback.
──────────────────────────────── 5. LOGGING, ERROR, HEALTH ─────────────────────────
Use configure_logging(__name__); remove stray logging.basicConfig(...).
Errors go through pc2_error_publisher only.
Every Dockerfile ends with
HEALTHCHECK CMD curl -f http://localhost:${HEALTH_PORT}/health || exit 1
──────────────────────────────── 6. MAIN-PC COMPATIBILITY ─────────────────────────
Do not touch code under docker/<main_pc_group> during this pass.
Compose must export:

MAINPC_IP=mainpc-service
PC2_IP=pc2-service

(or matching DNS names).
──────────────────────────────── 7. ACCEPTANCE CHECKLIST ──────────────────────────
☐ python -m py_compile $(git ls-files 'pc2_code/**/*.py') passes.
☐ grep -R "sys.path.insert" pc2_code/agents | wc -l == 0 (Δ-3)
☐ grep -R "logging.basicConfig" pc2_code/agents | wc -l == 0 (Δ-3)
☐ docker compose --profile pc2 ps shows all HEALTHY.
☐ No localhost: literals in PC-2 agents except loopback health endpoints.
☐ requirements.txt sorted, unique, matches auto list.
☐ Build & deploy scripts run without manual edits.
Follow these steps verbatim; defer architectural overhauls (Poetry, PEP-420 namespaces) until after production hardening is complete.

