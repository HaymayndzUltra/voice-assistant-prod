# COMPREHENSIVE MIGRATION CHECKLIST

## ✅ COMPLETE CHECKLIST - Wala Nang Nakalimutan!

### 1. CORE DEPENDENCIES (CRITICAL!)

#### Common Modules
- [ ] `/common/core/base_agent.py` → BaseAgent class (REQUIRED by ALL agents!)
- [ ] `/common/core/enhanced_base_agent.py` → Enhanced version with extra features
- [ ] `/common/config_manager.py` → get_service_ip, get_service_url, get_redis_url
- [ ] `/common/env_helpers.py` → get_env() function
- [ ] `/common/utils/env_standardizer.py` → get_mainpc_ip, get_pc2_ip, get_current_machine

#### ZMQ & Connection Pools
- [ ] `/common/pools/zmq_pool.py` → get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
- [ ] `/common/pools/redis_pool.py` → get_redis_client_sync
- [ ] `/common_utils/zmq_helper.py` → create_socket, safe_socket_send, safe_socket_recv

#### Error Handling & Logging
- [ ] `/common_utils/error_handling.py` → SafeExecutor class
- [ ] `/common/error_bus/nats_error_bus.py` → ErrorCategory, error bus implementation
- [ ] `/pc2_code/agents/error_bus_template.py` → setup_error_reporting, report_error
- [ ] `/common/utils/logger_util.py` → get_json_logger
- [ ] `/common_utils/env_loader.py` → get_env, get_ip functions

#### Path & Security Management
- [ ] `/common/utils/path_manager.py` → PathManager class (get_project_root, get_logs_dir, etc.)
- [ ] `/common/utils/secret_manager.py` → SecretManager for API keys
- [ ] `/common/utils/data_models.py` → ErrorSeverity and other data models
- [ ] `/common_utils/port_registry.py` → get_port function

### 2. AGENT FILES (77 Total)

#### MainPC Agents (54 agents)
- [ ] All files in `/main_pc_code/agents/*.py`
- [ ] All files in `/main_pc_code/services/*.py`
- [ ] All files in `/main_pc_code/FORMAINPC/*.py`
- [ ] `/main_pc_code/model_manager_suite.py` (special case)

#### PC2 Agents (23 agents)
- [ ] All files in `/pc2_code/agents/*.py`
- [ ] All files in `/pc2_code/agents/ForPC2/*.py`
- [ ] All files in `/pc2_code/agents/core_agents/*.py`
- [ ] All files in `/pc2_code/agents/utils/*.py`
- [ ] All files in `/pc2_code/agents/backups/*.py` (for reference)

#### Phase 1 Implementation
- [ ] `/phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py`

### 3. ADDITIONAL MODULES

#### Database & Security (MainPC)
- [ ] `/main_pc_code/database/*.py` → migration_system, performance_monitor, etc.
- [ ] `/main_pc_code/security/*.py` → auth_hardening, data_protection, etc.
- [ ] `/main_pc_code/complexity/*.py` → complexity_analyzer, performance_optimizer, etc.

#### Events & Configuration
- [ ] `/events/event_bus.py` → Event bus implementation
- [ ] `/pc2_code/config/*.py` → system_config, pc2_connection
- [ ] `/main_pc_code/config/*.py` → Additional configs

### 4. ENVIRONMENT VARIABLES (Must be in .env)

#### Machine Configuration
- [ ] `CURRENT_MACHINE` → unified/mainpc/pc2
- [ ] `MAINPC_IP` → IP address of MainPC
- [ ] `PC2_IP` → IP address of PC2
- [ ] `UNIFIED_HOST` → Unified system host

#### Service Endpoints
- [ ] `OBS_HUB_ENDPOINT` → ObservabilityHub URL
- [ ] `SERVICE_REGISTRY_HOST/PORT` → Service registry
- [ ] `ERROR_BUS_HOST/PORT` → Error bus endpoint
- [ ] `REDIS_HOST/PORT/URL` → Redis configuration
- [ ] `DB_HOST/PORT/NAME/USER/PASSWORD` → Database config

#### API Keys & Tokens
- [ ] `CLOUD_LLM_API_KEY` → OpenAI/Anthropic key
- [ ] `PHI_TRANSLATOR_TOKEN` → Phi translator
- [ ] `HUGGINGFACE_TOKEN` → HuggingFace access
- [ ] `JWT_SECRET_KEY` → Authentication

### 5. PYTHON DEPENDENCIES (requirements.txt)

#### Core Dependencies
- [ ] `pyyaml` → YAML parsing
- [ ] `flask` → Web framework
- [ ] `pyzmq` → ZeroMQ messaging
- [ ] `redis` → Redis client
- [ ] `psutil` → System monitoring
- [ ] `prometheus-client` → Metrics
- [ ] `aiohttp` → Async HTTP
- [ ] `click` → CLI framework

#### Additional from Common Modules
- [ ] `nats-py` → NATS messaging
- [ ] `psycopg2-binary` → PostgreSQL
- [ ] `sqlalchemy` → ORM
- [ ] `alembic` → DB migrations
- [ ] `passlib` → Password hashing
- [ ] `python-jose` → JWT tokens
- [ ] `httpx` → HTTP client
- [ ] `uvicorn` → ASGI server
- [ ] `fastapi` → API framework
- [ ] `pydantic` → Data validation

### 6. DIRECTORY STRUCTURE

```
unified-system-v1/
├── src/
│   ├── agents/
│   │   ├── mainpc/          # All MainPC agents
│   │   ├── pc2/             # All PC2 agents
│   │   └── core/            # ObservabilityHub
│   └── utils/               # Utilities
├── common/                  # Common modules (CRITICAL!)
├── common_utils/            # Common utilities
├── config/                  # All configurations
├── database/                # Database modules
├── security/                # Security modules
├── events/                  # Event system
├── complexity/              # Complexity analysis
├── models/                  # ML models
├── data/                    # Data files
├── logs/                    # Log files
├── scripts/                 # Operational scripts
├── tests/                   # Test suites
├── docs/                    # Documentation
└── monitoring/              # Prometheus/Grafana
```

### 7. IMPORT FIXES NEEDED

After copying, these imports need updating:
- [ ] `from pc2_code.agents.` → `from src.agents.pc2.`
- [ ] `from main_pc_code.agents.` → `from src.agents.mainpc.`
- [ ] `from pc2_code.agents.error_bus_template` → `from src.agents.pc2.error_bus_template`

### 8. VALIDATION STEPS

1. **Run the comprehensive migration script:**
   ```bash
   cd /workspace/unified-system-v1
   chmod +x scripts/complete_migration_v2.sh
   ./scripts/complete_migration_v2.sh
   ```

2. **Validate the structure:**
   ```bash
   python scripts/deep_scan_validator.py
   python scripts/validate_repository.py
   ```

3. **Test basic functionality:**
   ```bash
   python main.py start --profile core --dry-run
   ```

### 9. COMMON ISSUES TO CHECK

- [ ] BaseAgent not found → Copy from `/common/core/base_agent.py`
- [ ] Import errors → Check PYTHONPATH includes common/ and common_utils/
- [ ] Missing env vars → Check .env has all required variables
- [ ] Port conflicts → Check no other services using 7200-7999
- [ ] Redis connection → Ensure Redis is running
- [ ] Path issues → Verify PathManager paths are correct

### 10. FINAL VERIFICATION

```bash
# Check all agents are present
find src/agents -name "*.py" | wc -l  # Should be 77+

# Check common modules
ls -la common/core/base_agent.py  # Must exist
ls -la common/config_manager.py   # Must exist
ls -la common_utils/zmq_helper.py # Must exist

# Check environment
grep -c "=" .env  # Should have 50+ variables

# Test import
python -c "from common.core.base_agent import BaseAgent; print('✅ BaseAgent OK')"
```

---

## 🎯 SUMMARY

**Total Components to Migrate:**
- 77 agent files
- 20+ common modules
- 15+ utility modules
- 10+ configuration files
- 50+ environment variables
- 30+ Python dependencies

**Use the `complete_migration_v2.sh` script - it handles EVERYTHING!**