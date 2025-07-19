# Configuration Validation Checklist – Startup System

This checklist helps ensure `startup_config.yaml` and related environment variables are valid **before** launching containers to avoid silent startup failures.

## 1. Schema Lint

```bash
pip install yamllint
yamllint main_pc_code/config/startup_config.yaml
```

Look for:
* Duplicate keys
* Incorrect indentation
* Non-YAML values (e.g., `yes` without quotes)

## 2. Structural Validation

Run the preflight script:

```bash
python -m main_pc_code.scripts.validate_startup_config main_pc_code/config/startup_config.yaml
```

The script checks:
1. `agent_groups` exists and is a mapping.
2. Every group contains at least one agent.
3. Each agent dictionary has the mandatory keys:
   * `script_path`
   * `port`
4. `dependencies` reference only agents that are defined.
5. Port & health-port pairs are unique across all agents.
6. Referenced script paths exist on disk.

(See `scripts/validate_startup_config.py` for implementation.)

## 3. Environment Variables

Minimum required variables:

| Variable        | Default | Description                      |
|-----------------|---------|----------------------------------|
| `BIND_ADDRESS`  | 0.0.0.0 | Override for 0.0.0.0 listeners   |
| `LOG_LEVEL`     | INFO    | Global log level                 |
| `DEBUG_MODE`    | false   | Enable verbose debug output      |

Export them in your `docker-compose.*.yml` files or in the host shell.

## 4. Validation in CI

Add the following to your CI pipeline:

```yaml
- name: Validate startup configuration
  run: python -m main_pc_code.scripts.validate_startup_config main_pc_code/config/startup_config.yaml
```

CI fails if any of the checks above fail.

---

Prepared: 2025-07-19