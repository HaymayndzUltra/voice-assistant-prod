# ModelOps Coordinator (MOC)

This service orchestrates model lifecycle, GPU/VRAM management, inference routing, and learning jobs.

## Event-Driven VRAM Optimization

MOC now embeds an event-driven `VramOptimizationModule` based on the EnhancedVRAMOptimizer design:

- Subscribes to:
  - `models.model.loaded` (model_id, model_type, vram_mb, device, ts)
  - `memory.pressure.warning` (device, usage_mb, total_mb, severity, ts)
- Default mode is dry-run; plans are logged but not applied. Enable enforcement in a later phase.
- Event bus: NATS JetStream if `NATS_URL` is set; otherwise falls back to an in-process bus.

## Migration (Dual-Write)

- `ModelManagerSuite` emits `models.model.loaded` on successful loads.
- GPU monitors should emit `memory.pressure.warning` periodically under pressure.
- Keep existing VRAM eviction safeguards during Phase 1; the VRAM module runs observe-only.

## Decommission Plan for VramOptimizerAgent

1. Phase 0-1: Dual-write events, keep legacy ZMQ calls; VRAM module dry-run only.
2. Phase 2: Enable enforcement for non-critical models on a single node; remove direct ZMQ dependencies from callers.
3. Phase 3: Full enforcement with cross-machine actions; remove `main_pc_code/agents/vram_optimizer_agent.py` and references.

## Configuration

See `config/default.yaml` for server, resources, and `vram` section.

- `NATS_URL`: optional, enables JetStream streams `MODELS` and `MEMORY`.
- `vram.budget_pct`: VRAM budget target (default 0.85).
- `vram.dry_run`: keep true until Phase 2.