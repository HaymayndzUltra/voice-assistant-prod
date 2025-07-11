# Configuration of Agents and Services

## Overview

Ang configuration ng mga agents at services sa AI System ay mahalaga para sa tamang initialization, connectivity, at behavior ng bawat component. Ang settings ay maaaring manggaling sa YAML config files, environment variables, o dynamic loading mula sa code. Ang tamang configuration ay nagtitiyak ng modularity, flexibility, at madaling maintenance.

---

## Main Configuration Sources

### 1. **YAML Configuration Files**

- **Pinakamadalas gamitin:**
  - `main_pc_code/config/startup_config.yaml` (main system config)
  - `main_pc_code/config/agent_settings.yaml` (per-agent/service overrides)
  - `main_pc_code/config/secrets.yaml` (API keys, sensitive info)
- **Nilalaman:**
  - Agent/service groupings
  - Script paths, ports, health check ports
  - Dependencies, required flags
  - Resource allocations (GPU, RAM, etc.)
- **Sample:**
  ```yaml
  agents:
    UnifiedSystemAgent:
      port: 5568
      health_check_port: 5578
      dependencies: ["RequestCoordinator", "MemoryClient"]
    StreamingSpeechRecognition:
      port: 5641
      model: "whisper-large-v2"
      language: "en"
  ```

### 2. **Environment Variables**

- **Purpose:**
  - Override config file values (e.g., for deployment)
  - Store secrets (API keys, DB URIs)
  - Control debug/logging levels
- **Common Patterns:**
  - `export AGENT_NAME=UnifiedSystemAgent`
  - `export PORT=5568`
  - `export REDIS_HOST=localhost`
- **Usage:**
  - Agents usually check `os.environ` for overrides during startup.

### 3. **Dynamic/Programmatic Loading**

- **Some agents/services** dynamically load settings at runtime:
  - From remote config servers
  - By reloading YAML files on SIGHUP
  - By merging CLI arguments, env vars, and file configs

---

## How Agents/Services Load Configuration

1. **Startup Sequence:**

   - On launch, agents/services first load YAML config files (usually via `PyYAML` or similar).
   - Next, environment variables are checked to override file-based settings.
   - Some agents accept CLI arguments for further overrides.

2. **In-Code Example:**

   ```python
   import os
   import yaml

   with open("config/startup_config.yaml") as f:
       config = yaml.safe_load(f)

   agent_port = int(os.environ.get("PORT", config["agents"]["UnifiedSystemAgent"]["port"]))
   ```

3. **Reloading/Hot-Reload:**
   - Some services support reloading config without restart (e.g., via SIGHUP or admin command).

---

## Best Practices

- **Centralized config files** for easy management.
- **Do not hardcode secrets** in code; use environment variables or secrets.yaml.
- **Document** all required config options per agent/service.
- **Validate** config at startup to catch missing/invalid settings early.

---

## Per-Agent/Service Required Config Keys

| Agent/Service              | Required Config Keys (YAML/Env)                 |
| -------------------------- | ----------------------------------------------- |
| UnifiedSystemAgent         | port, health_check_port, dependencies           |
| StreamingSpeechRecognition | port, model, language                           |
| MemoryOrchestratorService  | port, db_path, redis_host, redis_port, redis_db |
| CacheManager               | port, redis_host, redis_port, redis_db          |
| Responder                  | port, model, tts_enabled, emotion_engine        |
| AdvancedCommandHandler     | port, allowed_commands, timeout                 |
| Executor                   | port, allowed_tasks, log_path                   |
| FaceRecognitionAgent       | port, model_path, db_path                       |
| ...                        | ...                                             |

_Note: Tingnan ang bawat agent/service code para sa full list ng config keys. Lahat ng ports at credentials ay dapat unique at secure._

---

## Config File Structure & Directory Layout

```
AI_System_Monorepo/
├── main_pc_code/
│   └── config/
│       ├── startup_config.yaml
│       ├── agent_settings.yaml
│       └── secrets.yaml
├── pc2_code/
│   └── config/
│       ├── startup_config.yaml
│       └── ...
└── system_docs/
    └── configuration.md
```

- **startup_config.yaml:** Main system/agent config
- **agent_settings.yaml:** Per-agent overrides
- **secrets.yaml:** Sensitive info (API keys, passwords)

---

## Port Allocation Guidelines

- Assign a unique main `port` to every agent/service.
- Health-check port follows the convention **`health_check_port = port + 1000`**.  
  Example: `UnifiedSystemAgent` → `5568` ➔ health check on `6568`.
- Reserved Ranges:
  - **5500-5599** : Core system coordinators (e.g., `UnifiedSystemAgent`).
  - **5600-5699** : Speech & audio processing (e.g., `StreamingSpeechRecognition`).
  - **6500-6599** : Health-check ports (derived; mirrors 5500-5599 etc.).
- When introducing a new agent, update both `startup_config.yaml` and this document.

### Recent Changes (Jul 2025)

| Agent | Old Port | New Port | New Health Port | Notes |
|-------|----------|----------|-----------------|-------|
| StreamingPartialTranscripts | 5640 | 5642 | 6642 | Avoid conflict with NLU pipeline |
| FeedbackHandler | 5559 | 5569 | 6569 | Standardised +1000 rule |

---

## Graceful Shutdown Conventions

All agents now inherit the updated `BaseAgent` that:

1. Exposes a `_background_threads` list to track any thread you `start()`.
2. Implements `stop()` to:
   - set `self.running = False`,
   - `join()` every tracked thread (default timeout = 10 s),
   - close ZMQ sockets and terminate the context.

When adding a new background thread, register it like so:

```python
thread = threading.Thread(target=self._worker_loop, daemon=True)
thread.start()
self._background_threads.append(thread)
```

Failing to register a thread may result in zombie processes or ports not being freed during container shutdown.

---

## Config Validation and Error Handling

- Agents/services validate config at startup:
  - Check required fields (e.g., port, credentials)
  - Type checking (int, str, list, etc.)
  - Log errors and exit if critical config is missing/invalid
- **Example:**
  ```python
  if "port" not in config:
      logger.error("Missing required config: port")
      sys.exit(1)
  ```
- Some agents auto-generate defaults for optional settings but warn in logs.

---

## Security Practices

- **Do not hardcode secrets** in code or YAML; use environment variables or `secrets.yaml`.
- **Restrict access** to config and secrets files (chmod 600, .gitignore).
- **Audit** config files for accidental exposure before deployment.
- **Never log sensitive values** (API keys, passwords).

---

## Config Precedence/Override Order

1. **CLI Arguments** (highest)
2. **Environment Variables**
3. **YAML Config Files**
4. **In-code Defaults** (lowest)

- _Example: `python agent.py --port 5555` overrides everything else for `port`._

---

## Sample CLI Arguments

- `python agent.py --port 5568 --debug`
- `python service.py --config config/agent_settings.yaml`
- `python memory_orchestrator_service.py --db_path /tmp/mem.db --redis_host 127.0.0.1`

---

## Troubleshooting Configuration

- **Common errors:**
  - Port conflicts ("Address already in use")
  - Missing required keys ("KeyError: 'port'")
  - Invalid credentials ("Authentication failed")
- **Diagnosis:**
  - Check logs for error details
  - Use `print(config)` or logging to debug loaded values
  - Validate YAML syntax (use `yamllint`)
- **Resolution:**
  - Assign unique ports, fill all required keys, update secrets

---

## Summary Table: Configuration Sources

| Source                | Purpose/Use Case                 | Example Files/Vars                       |
| --------------------- | -------------------------------- | ---------------------------------------- |
| YAML Config Files     | Main settings, grouping, ports   | startup_config.yaml, agent_settings.yaml |
| Environment Variables | Overrides, secrets, deployment   | PORT, REDIS_HOST, API_KEY                |
| CLI Arguments         | Quick/manual override            | --port 5568, --debug                     |
| Dynamic/Remote Config | Advanced, large-scale deployment | Config server, hot-reload                |

---

Kung may gusto kang idagdag na detalye tungkol sa configuration ng specific agent/service, sabihin mo lang!
