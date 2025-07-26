# Container Development Guide

This document explains how to run, debug, and hot-reload individual agent groups inside Docker.

## Prerequisites
* Docker ≥ 24 with the NVIDIA container runtime (`sudo apt install nvidia-container-toolkit`)
* Python 3.11 for running host-side CLI utilities
* GNU Make (optional convenience)

## Quick Start
```bash
# 1. Build and start dev stack (hot-reload enabled)
$ docker compose -f docker/docker-compose.dev.yml up -d core_services redis

# 2. Tail logs in another terminal
$ docker compose -f docker/docker-compose.dev.yml logs -f core_services

# 3. Modify any *.py file – watchmedo auto-restart will relaunch the service.
```

## Running Tests
```bash
$ scripts/test_container_group.sh gpu_intensive
```

## Debugging Tips
* `docker top <container>` – verify CPU pinning.
* `nvidia-smi` – live VRAM usage; MIG UUIDs map to container names.
* `docker stats` – high-level CPU/RAM view.
* Add `--dry-run` to the `system_launcher` command in the compose file to validate dependencies without executing agents.

## Hot-Reload Internals
We rely on **watchdog**’s `watchmedo auto-restart`, already baked into development images via `pip install watchdog`.  It monitors for `*.py`, `*.yaml`, and restarts the Python entry-point quickly (stateful agents must persist to Redis or disk-backed DB between restarts).

## CI/CD
GitHub Actions workflow (`.github/workflows/ci.yml`) builds dev images, runs unit tests, and (on merge to main) pushes images to Docker Hub.

## Adding a New Agent
1. Edit `main_pc_code/config/startup_config.yaml` or `pc2_code/config/startup_config.yaml` and assign it to an existing group (or create a new group and update compose files).  
2. Mount-test in dev stack: `docker compose ... up -d <group>`  
3. Add unit tests under `tests/` and ensure they pass in CI.

## Gotchas
* **File permissions** – all dev containers run as user `app` (uid 1000).  Ensure host files are readable by this uid.
* **GPU contention** – only one dev container should access the 4090 at a time.  Use `docker compose stop gpu_intensive` when debugging other GPU apps.
* **Port conflicts** – the launcher expands expressions like `${PORT_OFFSET}+7200`.  In dev, export `PORT_OFFSET=10000` to avoid clashing with prod.