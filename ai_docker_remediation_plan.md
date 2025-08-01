# HIGH-LEVEL, END-TO-END DOCKER REMEDIATION PLAN

*Use this as the single source of truth for all deployment/ops sessions. Execute phase-by-phase. Adjust paths as needed (MainPC path = `/home/haymayndz/AI_System_Monorepo/main_pc_code`).*

---

## PHASE 0 — AUTOMATED INVENTORY & GAP SCAN

1. Launch a clean shell in the repo root (e.g. `/home/haymayndz/AI_System_Monorepo`).
2. Run:

   ```python
   import os, yaml, pathlib
   root = pathlib.Path(".").resolve()
   dockerfiles = [str(p) for p in root.rglob("Dockerfile*") if p.is_file()]
   compose_files = [str(p) for p in root.rglob("docker-compose*.yml")]
   gha = root/".github/workflows/build-and-deploy.yml"
   matrix_refs = []
   if gha.exists():
       wf=yaml.safe_load(gha.read_text())
       for inc in wf["jobs"]["build-push"]["strategy"]["matrix"]["include"]:
           matrix_refs.append(inc["dockerfile"])
   missing = [p for p in matrix_refs if not (root/p).exists()]
   print("== Dockerfiles =="); print("\n".join(dockerfiles))
   print("\n== Compose files =="); print("\n".join(compose_files))
   print("\n== Dockerfiles referenced in CI but ABSENT =="); print("\n".join(missing))
   ```
3. If missing Dockerfiles are detected, recover from VCS or switch to monolithic build.

---

## PHASE 1 — CHOOSE PACKAGING STRATEGY

* If every service has its own Dockerfile, proceed to Phase 2-A (Modular).
* If only two exist (`docker/mainpc/Dockerfile`, `docker/pc2/Dockerfile`), proceed to Phase 2-B (Monolithic).
* Document the choice in `docs/deployment_strategy.md`.

---

## PHASE 2-A — MODULAR BUILD WORKFLOW

1. Confirm all service Dockerfiles exist.
2. Create `build-images.sh`:

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   images=(
     ai_system/infra_core:main_pc_code/Dockerfile.infra_core
     ai_system/coordination:main_pc_code/Dockerfile.coordination
     ai_system/observability_hub:phase1_implementation/consolidated_agents/observability_hub/Dockerfile
     ai_system/memory_stack:main_pc_code/Dockerfile.memory_stack
     ai_system/vision_suite:main_pc_code/Dockerfile.vision_suite
     ai_system/speech_pipeline:main_pc_code/Dockerfile.speech_pipeline
     ai_system/learning_pipeline:main_pc_code/Dockerfile.learning_pipeline
     ai_system/reasoning_suite:main_pc_code/Dockerfile.reasoning_suite
     ai_system/language_stack:main_pc_code/Dockerfile.language_stack
     ai_system/utility_suite:main_pc_code/Dockerfile.utility_suite
     ai_system/emotion_system:main_pc_code/Dockerfile.emotion_system
     ai_system_pc2/infra_core:pc2_code/Dockerfile.infra_core
     ai_system_pc2/memory_stack:pc2_code/Dockerfile.memory_stack
     ai_system_pc2/async_pipeline:pc2_code/Dockerfile.async_pipeline
     ai_system_pc2/tutoring_suite:pc2_code/Dockerfile.tutoring_suite
     ai_system_pc2/vision_dream_suite:pc2_code/Dockerfile.vision_dream_suite
     ai_system_pc2/utility_suite:pc2_code/Dockerfile.utility_suite
     ai_system_pc2/web_interface:pc2_code/Dockerfile.web_interface
   )
   for spec in "${images[@]}"; do
     IFS=: read tag file <<<"$spec"
     echo "### BUILDING $tag (file $file)"
     docker buildx build --progress=plain -f "$file" -t "$tag" .
   done
   ```
3. Make it executable:

   ```bash
   chmod +x build-images.sh
   ```
4. Run the script. Fix any build errors.
5. Update Compose files to use the built images or use `build:` context blocks.

---

## PHASE 2-B — MONOLITHIC BUILD WORKFLOW

1. Build the base images:

   ```bash
   docker build -f docker/mainpc/Dockerfile -t ai_system/mainpc_stack:latest .
   docker build -f docker/pc2/Dockerfile   -t ai_system/pc2_stack:latest   .
   ```
2. In `main_pc_code/config/docker-compose.yml`, set every service’s `image:` to `ai_system/mainpc_stack:latest`
   Add service-specific `command:` entries.
3. Repeat for PC2 Compose using `ai_system/pc2_stack:latest`.

---

## PHASE 3 — REGISTRY & TAG POLICY (GHCR)

1. Set registry info:

   ```bash
   export REG=ghcr.io
   export USER=haymayndzultra
   ```
2. Login to registry:

   ```bash
   echo "$GHCR_PAT" | docker login ghcr.io -u "$USER" --password-stdin
   ```
3. Choose an immutable tag format (example: `YYYYMMDD.<git-sha>`):

   ```bash
   export VERSION_TAG=20250801.a1b2c3d4   # Palitan per build
   ```
4. Tag images:

   ```bash
   # MainPC
   docker tag ai_system/mainpc_stack:latest ghcr.io/haymayndzultra/ai_system/mainpc_stack:$VERSION_TAG
   # PC2
   docker tag ai_system/pc2_stack:latest ghcr.io/haymayndzultra/ai_system/pc2_stack:$VERSION_TAG
   # Repeat for modular images as needed
   ```
5. Push all versioned images:

   ```bash
   docker push ghcr.io/haymayndzultra/ai_system/mainpc_stack:$VERSION_TAG
   docker push ghcr.io/haymayndzultra/ai_system/pc2_stack:$VERSION_TAG
   # Add more push commands for other images if modular
   ```
6. Update all Compose files (`mainpc` and `pc2`) to use:

   ```yaml
   image: ghcr.io/haymayndzultra/ai_system/mainpc_stack:20250801.a1b2c3d4
   image: ghcr.io/haymayndzultra/ai_system/pc2_stack:20250801.a1b2c3d4
   ```

   # Use the exact tag for every service image.

---

## PHASE 4 — COMPOSE VALIDATION

1. Lint Compose files:

   ```bash
   docker compose -f main_pc_code/config/docker-compose.yml config --quiet
   docker compose -f pc2_code/config/docker-compose.yml    config --quiet
   ```
2. Dry-run Swarm conversion:

   ```bash
   docker stack deploy --compose-file main_pc_code/config/docker-compose.yml dummy --dry-run
   ```
3. Security scan:

   ```bash
   docker scan $(docker images -q)  # Or use trivy if available
   ```

---

## PHASE 5 — DEPLOY, HEALTH & MONITORING

1. Launch Compose stacks:

   ```bash
   docker compose -f main_pc_code/config/docker-compose.yml up -d
   docker compose -f pc2_code/config/docker-compose.yml up -d
   ```
2. Confirm Prometheus scrape targets are active (MainPC: 9000, PC2: 9100).
3. Confirm GPU/VRAM allocation is correct (see VRAMOptimizerAgent config).
4. Run health probes on all agents. If fail, retry with timeout and confirm GPU warmup.

---

## PHASE 6 — LOAD TESTING & SMOKE TESTS

1. Run synthetic load tests:

   ```bash
   python3 /home/haymayndz/AI_System_Monorepo/main_pc_code/tests/load/generate_requests.py --duration 300 --qps 25
   ```
2. Monitor GPU usage during test:

   ```bash
   watch -n3 nvidia-smi
   ```
3. Run all smoke tests:

   ```bash
   python3 /home/haymayndz/AI_System_Monorepo/main_pc_code/scripts/smoke_test_agents.py --target pc2
   # Should output "ALL TESTS PASSED"
   ```

---

## PHASE 7 — SECURITY HARDENING

1. Enable Docker Content Trust:

   ```bash
   export DOCKER_CONTENT_TRUST=1
   ```
2. Scan all running containers:

   ```bash
   docker scan $(docker ps -q)
   ```
3. Enable automatic system security updates:

   ```bash
   sudo apt-get install -y unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```
4. Check non-root user in containers:

   ```bash
   docker inspect ghcr.io/haymayndzultra/ai_system/infra_core:$VERSION_TAG --format '{{json .Config.User}}'
   # Output should be "ai" (or your user)
   ```

---

## PHASE 8 — BACKUP & DISASTER RECOVERY

1. Create backup script for data volumes:

   ```bash
   cat > /home/haymayndz/AI_System_Monorepo/scripts/volume_backup.sh <<'EOS'
   #!/usr/bin/env bash
   set -e
   TS=$(date +%Y%m%d_%H%M)
   docker run --rm --volumes-from mainpc_ai_stack_infra_core_1 \
     -v /backups:/backup alpine \
     tar czf /backup/infra_core_${TS}.tgz /app/data
   EOS
   chmod +x /home/haymayndz/AI_System_Monorepo/scripts/volume_backup.sh
   ```
2. Schedule daily cron job for the backup script.
3. Test restore path using tar:

   ```bash
   mkdir /tmp/restore && tar xzf /backups/infra_core_<timestamp>.tgz -C /tmp/restore
   ```

---

## PHASE 9 — MAINTENANCE OPERATIONS

1. For rolling updates (example for infra\_core):

   ```bash
   docker build -f /home/haymayndz/AI_System_Monorepo/main_pc_code/Dockerfile.infra_core -t ghcr.io/haymayndzultra/ai_system/infra_core:$VERSION_TAG .
   docker push ghcr.io/haymayndzultra/ai_system/infra_core:$VERSION_TAG
   docker compose -f /home/haymayndz/AI_System_Monorepo/main_pc_code/config/docker-compose.yml pull infra_core
   docker compose -f /home/haymayndz/AI_System_Monorepo/main_pc_code/config/docker-compose.yml up -d infra_core
   ```
2. Validate health after update:

   ```bash
   python3 /home/haymayndz/AI_System_Monorepo/main_pc_code/scripts/health_probe.py --host 127.0.0.1
   ```
3. Monthly cleanup:

   ```bash
   docker system prune -af --volumes
   ```

---

## PHASE 10 — DOCUMENT & ARCHIVE

1. Log all deployments:

   ```bash
   mkdir -p /home/haymayndz/AI_System_Monorepo/deployment_logs
   docker compose logs --no-color > /home/haymayndz/AI_System_Monorepo/deployment_logs/$(date +%Y%m%d_%H%M)_mainpc.log
   ```
2. Update docs (deployment date, image tags, GPU allocation, backup schedule, etc).
3. Commit & push documentation:

   ```bash
   git add docs/production_deployment_overview.md deployment_logs/*
   git commit -m "Update deployment docs and logs"
   git push
   ```

---

## VALIDATION & NEXT SESSION

* Re-run Phase 0 audit.
* Ensure no missing Dockerfiles and config lint passes.
* If not, return to Phase 1 decisions.
* Continue backup, monitoring, testing, and periodic updates as part of standard ops cycle.

---

**Implement all phases sequentially. Stop only on explicit errors, correct, then resume. Save this file for every deployment iteration.**
