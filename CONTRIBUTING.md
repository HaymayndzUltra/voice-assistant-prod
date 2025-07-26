# Contributing Guide

## Quick Smoke Tests

Every pull-request must pass the quick smoke workflow that ensures the system
configuration is still sane.

Run it locally before pushing:

```bash
pip install -r requirements.base.txt
python main_pc_code/system_launcher.py --dry-run --config main_pc_code/config/startup_config.yaml
```

This command validates:

* All ports are unique once `${PORT_OFFSET}` is expanded.
* The dependency graph is acyclic.
* Each agent exposes a health-check implementation.

The CI equivalent lives in `.github/workflows/quick-smoke.yml` and will block
merges if any of the above fail.

## Docker build pattern

All Dockerfiles now follow a two-layer requirements install to maximise layer
caching:

1. `requirements.base.txt` – common, rarely changing dependencies.
2. Image-specific `requirements*.txt` – small delta per group.

When adding a new image make sure to replicate the pattern:

```dockerfile
COPY requirements.base.txt /app/requirements.base.txt
COPY docker/your_group/requirements.extra.txt /app/requirements.txt
RUN pip install -r requirements.base.txt && \
    pip install -r requirements.txt
```

## Configuration overrides

Machine or environment specific tweaks go under `config/overrides/`.
Use `MACHINE_TYPE=mainpc|pc2` or `CONFIG_OVERRIDE=docker|production` to pick a
file at runtime.  The `UnifiedConfigLoader` merges base → machine → env vars.