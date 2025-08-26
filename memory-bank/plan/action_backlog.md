# Docker Blueprint v1.1 – Action-Backlog (Initial)

> This file lists all high-level remediation items extracted from `organized.md`.
> Use it as the single source of truth for tracking fixes. Mark each `- [ ]` as
> completed (`- [x]`) once the corresponding deep-dive and implementation are
> done.

| ID  | Task (Condensed) | Owner Role | Priority | Status |
|-----|------------------|-----------|----------|--------|
| C-1 | Define `PORT_OFFSET` default and wire into CI/env | DevOps | P0 | - [ ] |
| C-2 | Decommission `ObservabilityDashboardAPI`; keep UOC only | Platform Eng | P0 | - [ ] |
| C-3 | Add Dockerfiles: ServiceRegistry, SystemDigitalTwin, TieredResponder | Platform Eng | P0 | - [ ] |
| C-4 | Retag CPU-only agents to `family-cpu-pydeps` | ML Ops | P1 | - [ ] |
| C-5 | Harden legacy Py3.10 image; schedule migration to 3.11 | Eng Manager | P1 | - [ ] |
| C-6 | Replace RW docker.sock with docker-proxy sidecar | Security | P0 | - [ ] |
| C-7 | Add volumes / DB mapping for stateful agents | DevOps | P1 | - [ ] |
| C-8 | Implement ServiceRegistry discovery mechanism | Backend Lead | P0 | - [ ] |
| C-9 | Standardise /health checks & ports | SRE | P1 | - [ ] |
| C-10| Resolve port collisions (UOC duplicates) | DevOps | P1 | - [ ] |
| C-11| Assess need for `family-vision-cu121`; remove if unused | Arch Team | P2 | - [ ] |
| C-12| Break circular dependency (Streaming audio ←→ SystemDigitalTwin) | Backend Lead | P0 | - [ ] |
| C-13| Introduce secrets management (Vault / KMS) | Security | P1 | - [ ] |
| C-14| Expose CI quality gates & Trivy/SBOM workflows | CI/CD | P1 | - [ ] |
| C-15| Propagate CUDA env vars via images | ML Ops | P2 | - [ ] |
| C-16| Implement FORCE_IMAGE_TAG rollback logic in supervisors | DevOps | P2 | - [ ] |
| C-17| Pin per-service dependencies (requirements.txt hashes) | Developers | P2 | - [ ] |
| C-18| Add Prometheus metrics to all services | Observability | P2 | - [ ] |
| C-19| Document QoS/latency requirements for cross-machine audio | Arch Team | P3 | - [ ] |
| C-20| Align service names & folder paths (CrossMachineGPUScheduler) | Repo Maintainers | P2 | - [ ] |

> **Legend – Priority:** P0 = blocker, fix before deploy • P1 = high • P2 = medium • P3 = low