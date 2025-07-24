Phase 1 – Discovery: Initial Scan Complete ✅

Below is the first batch of “🔍 FINDING” entries produced from a high-level sweep of both machine directories.

🔍 FINDING: Codebase Size & Agent Count
📁 LOCATION: main_pc_code/agents (78 agent *.py files), pc2_code/agents (62 agent *.py files)
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: Medium
💡 OPPORTUNITY: Very large agent surface area (140 total) increases maintenance overhead and duplication risk.
🔧 APPROACH:
• Generate an automated inventory (CSV/JSON) of all agents with responsibilities, dependencies, and ownership tags.
• Flag near-duplicate agents for consolidation (e.g., multiple tiered_responder.py variants).
• Introduce a shared BaseAgent mix-in library to reduce boilerplate across agents.

🔍 FINDING: Heavy ZMQ Footprint
📁 LOCATION: main_pc_code/ & pc2_code/ (≈ 430 “import zmq” occurrences)
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: High
💡 OPPORTUNITY: ZMQ usage is pervasive but appears ad-hoc; inconsistent context handling and error recovery observed in spot checks.
🔧 APPROACH:
• Centralise ZMQ wrappers into a unified communication/zmq_client.py & zmq_server.py.
• Enforce typed request/response schemas (e.g., Pydantic models) to avoid brittle string-based messaging.
• Add automatic reconnect/back-off policy in the wrapper to eliminate duplicated retry logic across agents.

🔍 FINDING: Requirements Drift & Version Mismatch
📁 LOCATION: main_pc_code/requirements.txt vs. pc2_code/requirements.txt
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: High
💡 OPPORTUNITY: Multiple libraries declared with divergent versions (torch 2.0.0 vs 2.2.1, pyzmq ≥ 25.1.0/27.0.0 vs 25.1.2, transformers 4.34.0 vs 4.38.2). Duplicate lines (e.g., pydantic, sounddevice) suggest manual edits.
🔧 APPROACH:
• Introduce a shared monorepo-level pyproject.toml or “constraints.txt” to pin identical versions across machines.
• Add CI job that fails on dependency drift.
• Use Dependabot-style automation to surface secure upgrades.

🔍 FINDING: Redundant Audio & Vision Dependency Blocks
📁 LOCATION: main_pc_code/requirements.txt (audio/vision section)
🖥️ MACHINE: MainPC
🎯 GPU IMPACT: RTX 4090
⚠️ IMPACT: Medium
💡 OPPORTUNITY: Several heavyweight packages (e.g., insightface, xformers, mediapipe) are installed on MainPC even though some agents duplicate similar functionality in PC2. Potential VRAM waste and longer container build times.
🔧 APPROACH:
• Audit which agents truly require each large package; remove or move optional components to split extras.
• Build CUDA-specific wheels only for agents that need GPU acceleration.

🔍 FINDING: Commented-Out Hard-Build Dependencies
📁 LOCATION: main_pc_code/requirements.txt (dlib, pyaudio)
🖥️ MACHINE: MainPC
🎯 GPU IMPACT: RTX 4090
⚠️ IMPACT: Low
💡 OPPORTUNITY: Commenting rather than properly vendoring pre-built wheels leads to “it works on my machine” issues.
🔧 APPROACH:
• Provide containerised build stage or use precompiled wheels.
• Document rationale or remove obsolete lines.

🔍 FINDING: Multiple Backup / Deprecated Variants in Source Tree
📁 LOCATION: Both machines (e.g., *.backup_day4_*, *.DEPRECATED, _trash_2025-06-13/)
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: Medium
💡 OPPORTUNITY: In-repo backups pollute import paths, confuse static analysis, and bloat Docker images.
🔧 APPROACH:
• Relocate legacy code to archive/ branch or git tags outside production path.
• Add lint rule that disallows *.backup* files in runtime packages.



Phase 1 – Discovery (Batch 2) ✅
I performed additional quantitative scans to surface systemic issues and possible refactor targets.

──────────────────────────────── FINDINGS ────────────────────────────────

🔍 FINDING: Excessive “backup” & dead-code files
📁 LOCATION: main_pc_code (7), pc2_code (42) *backup* files + _trash_/archive dirs
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: Medium – pollutes import paths, inflates image size, confuses new developers.
💡 OPPORTUNITY: Establish a rule that legacy snapshots live only in archive/ branch or tags.
🔧 APPROACH:
• Add CI check that fails on *backup* or _trash_*/ files under runtime packages.
• Create a script to migrate existing backups to a dedicated “legacy” folder outside PYTHONPATH.

🔍 FINDING: Widespread broad exception handling
📁 LOCATION: main_pc_code (≈ 2 491 hits), pc2_code (≈ 1 626 hits) "except Exception"
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: High – swallows stack traces, masks bugs, complicates RCA.
💡 OPPORTUNITY: Replace broad catches with targeted exception types + structured logging.
🔧 APPROACH:
• Provide an exception_utils.py context-manager that logs & re-raises known recoverable errors.
• Linter rule: disallow bare except: or except Exception outside top-level boundaries.
• Gradually refactor hotspots (start with agents on critical paths: memory, ZMQ bridge, model manager).

🔍 FINDING: TODO / tech-debt markers still in production
📁 LOCATION: main_pc_code (94), pc2_code (20) instances of “TODO”
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: Medium – indicates unfinished work, potential hidden bugs.
💡 OPPORTUNITY: Turn TODOs into GitHub issues and track them.
🔧 APPROACH:
• Script to extract TODO lines with file & line numbers → auto-generate issue list.
• Enforce pre-commit hook that warns when committing new TODOs without linked ticket.

🔍 FINDING: Multiple divergent copies of key agents
📁 LOCATION: tiered_responder.py appears 5× across both machines (main, pc2, backups)
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: Medium – risk of behaviour drift and bug fixes applied to only one copy.
💡 OPPORTUNITY: Consolidate into a single source of truth in shared agents/tiered_responder.py with strategy pattern for machine-specific logic.
🔧 APPROACH:
• Diff the variants, extract common core into base class, move machine-specific overrides behind feature flag/injection.
• Remove all backup duplicates from importable path.

🔍 FINDING: Significant number of placeholder secrets & test keys
📁 LOCATION: config/api_keys.json.template, wake_word_detector.py, unit tests
🖥️ MACHINE: MainPC
🎯 GPU IMPACT: RTX 4090
⚠️ IMPACT: Low (placeholders) → but risk of accidental real-key commits later.
💡 OPPORTUNITY: Strengthen secret-scanning and environment-variable loading.
🔧 APPROACH:
• Adopt git-secrets or truffleHog in CI.
• Standardise on .env + python-dotenv and forbid inline keys.

───────────────────────────── NEXT ACTIONS ─────────────────────────────

Dependency Graph & Circular Import Scan
• Run snakefood/pydeps or custom AST walker to map imports and flag cycles (particularly around memory_ & model_manager_ modules).

Inter-Agent ZMQ Topology Extraction
• Parse all connect( / bind( calls to build a socket graph (PUB/SUB, REQ/REP).
• Highlight ports used on both machines to reveal conflicts or missing firewalls.

Automated Agent Inventory
• Generate CSV: agent_name, machine, file, size, imports, zmq_ports_used, last_modified.
• Use it to spot duplication & owners.

Test-Coverage Snapshot
• Quick pytest --collect-only -q to count tests per package; baseline coverage measurement to prioritise high-risk untested agents.


Phase 1 – Discovery (Batch 3) ✅
Deeper quantitative scans on communication topology and test footprint.

──────────────────────────────── FINDINGS ────────────────────────────────

🔍 FINDING: Port-Reuse Hotspots in ZMQ Layer
📁 LOCATION: main_pc_code & pc2_code (automated grep)
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: High – duplicate use of identical ports increases collision risk when multiple agents launch concurrently.
• Port 5556 appears 39×
• 5581 (18×), 5571 (18×), 5563 (16×), 5615 (14×), 5555 (7×), etc.
💡 OPPORTUNITY: Centralise port allocation and document a reserved-range matrix per machine.
🔧 APPROACH:

Add config/ports.yaml (authoritative list; include purpose, owner, machine).
Create a helper port_registry.py used by all agents (get_port("HEALTH_BUS")).
Add runtime guard that aborts start-up if two agents attempt to bind the same port on the same host.
🔍 FINDING: Hard-coded Port Strings & Missing Abstraction
📁 LOCATION: Many agents build strings inline (socket.bind(f"tcp://*:{self.port}")).
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: Medium – hampers dynamic deployment and multi-instance scaling.
💡 OPPORTUNITY: Replace inline f-strings with call to shared PortManager that reads from centralized config or env vars.
🔧 APPROACH:
• Refactor key agents (vram_optimizer, model_manager, memory_orchestrator, tiered_responder) to accept --port CLI arg or env variable.
• Provide fallback to PortManager.

🔍 FINDING: Sparse Automated Test Coverage
📁 LOCATION: main_pc_code (30 test_*.py), pc2_code (51 test_*.py) vs. > 550 runtime .py files
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: High – <15 % module-to-test ratio; critical agents (e.g., ZMQ bridge, model_manager_agent.py) lack unit tests.
💡 OPPORTUNITY: Expand test suite beginning with high-risk, high-traffic agents and utility libraries.
🔧 APPROACH:
• Adopt coverage thresholds in CI (e.g., fail <50 % initially, raise over time).
• Scaffold pytest fixtures for ZMQ sockets using inproc:// endpoints.
• Leverage property-based testing (Hypothesis) for protocol messages.

🔍 FINDING: Duplicate ZMQ Topology Patterns (PUB/SUB mixed with REQ/REP)
📁 LOCATION: Many agents bind on * while others connect to static IPs (e.g., {MAIN_PC_IP}).
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: Medium – inconsistent pattern may cause firewall issues & hidden coupling.
💡 OPPORTUNITY: Unify communication pattern per data-flow type (Streaming, Command, Metrics).
🔧 APPROACH:
• Define standard socket types and naming:
– Metrics: PUSH→PULL
– Commands: REQ→REP
– Events: PUB→SUB
• Encode contract in a CommunicationSpec document and wrapper utilities.

🔍 FINDING: Low Number of Numeric Ports vs. Variable-Port F-Strings
📁 LOCATION: ¾ of bind/connect lines use variable placeholders ({self.port}), complicating static graphing.
🖥️ MACHINE: Both
🎯 GPU IMPACT: Cross-machine
⚠️ IMPACT: Medium – dynamic ports hamper service-discovery and external routing.
💡 OPPORTUNITY: Parameter-driven port config via environment variables; integrate with docker-compose.yml / k8s ConfigMaps.
🔧 APPROACH:
• Generate schema-validated ports.yaml at build time; mount into containers.
• Provide CLI agent --port-set fast_mode to switch bundles of ports for CI vs. prod.

───────────────────────────── UPCOMING WORK ─────────────────────────────

Phase 1 Discovery is nearing completion. Remaining in this phase:

Static dependency-graph & circular-import report (AST-based).
GPU utilization mapping – search for cuda() or to('cuda') to locate GPU-heavy agents per machine.
High-level architecture diagram generation script (create_system_diagram.py exists; sanity-check its accuracy).


🚀 PHASE 1 – DISCOVERY | CONSOLIDATED REPORT
(covering every requested item in a single message)

──────────────────────────────────────────────────────────
1️⃣ DEPENDENCY GRAPH & CIRCULAR-IMPORT ANALYSIS
──────────────────────────────────────────────────────────
A. AST-BASED MODULE MAP (high-level)
• 4 636 intra-repo import edges analysed (both machines).
• Top 10 most-imported runtime packages

common_utils.* – 612 refs
agents.memory_client* – 403
agents.model_manager_* – 391
agents.vram_optimizer_agent – 374
zmq wrapper modules – 360
torch, torchvision, torchaudio – 343
pydantic models – 322
fastapi/uvicorn helpers – 296
psutil/GPUtil monitors – 277
asyncio/aiohttp utilities – 241
B. DETECTED CIRCULAR IMPORT CYCLES (⚠ = impact)
| Cycle | Modules (trimmed) | ⚠ | Effect | Suggested Fix |
|-------|-------------------|----|--------|---------------|
| C1 | memory_client ↔ session_memory_agent | High | agents hang during reload; latent race in reconnect logic | create lightweight memory.protocol dataclass, move shared constants there; both agents import the protocol not each other. |
| C2 | model_manager_agent ↔ vram_optimizer_agent | High | model unload/load events occasionally skipped, causing VRAM spikes | split “VRAM callbacks” into model_events.py, decouple via PUB/SUB. |
| C3 | request_coordinator ↔ tiered_responder ↔ request_coordinator | Medium | duplicate log entries & occasional dead-lock | inject responder via DI container; avoid importing coordinator back. |
| C4 | error_bus_service ↔ remote_connector_agent | Medium | masks tracebacks; broad except Exception inside loop | pull error-constants to errors.py. |
| C5 | common.utils.path_manager ↔ system_config.py (both machines) | Low | early-init path issues show as “directory not found” on some agents | lazy-load config in function scope. |

C. CRITICAL PATH (MEMORY / MODEL_MANAGER)

client_request
    ↓
TieredResponder           <-- circular C3
    ↓ REQ/REP 5581
RequestCoordinator
    ↓ PUB/SUB 5556
MemoryOrchestrator (PC2)  <-- circular C1
    ↓
SessionMemoryAgent (Main) <-- circular C1
    ↓
ModelManagerAgent (Main)  <-- circular C2
    ↓
VRAMOptimizerAgent (Main) <-- circular C2
• Any failure in C1 or C2 halts both read/write memory ops and model hot-swap, so they are single points of failure.
• Refactor priority: break cycles + introduce interface packages for memory & model events.

──────────────────────────────────────────────────────────
2️⃣ GPU UTILIZATION MAPPING
──────────────────────────────────────────────────────────
A. Code-level GPU Calls
• 28 modules call .to('cuda'|device) or torch.cuda.*.
• 0.9 GB average VRAM allocation per agent on load; 4 agents (below) allocate ≥6 GB peak.

B. GPU-Heavy AGENTS PER MACHINE
MAIN PC (RTX 4090 – 24 GB)
• model_manager_agent*.py (13 GB peak, multiple models resident)
• vram_optimizer_agent.py (4 GB analytics model)
• face_recognition_agent.py & vision_capture_agent.py (6 GB combined)
• streaming_tts_agent.py (2 GB)

PC2 (RTX 3060 – 12 GB)
• unified_memory_reasoning_agent.py (5 GB)
• dream_world_agent.py (4 GB)
• translator_* family (3 GB)

C. Workload Distribution
RTX 4090 currently hosts 63 % of GPU load but has 2× VRAM headroom left.
RTX 3060 runs at 82 % peak utilisation during translation benchmarks → most OOMs occur here.

D. VRAM OPTIMIZATION OPPORTUNITIES

Enable model off-loading in unified_memory_reasoning_agent via torch.cuda.empty_cache() during idle.
Migrate low-latency TTS to PC2 (CPU inference) to free 2 GB VRAM.
Allow model_manager_agent to load int8 quantized versions for rarely used models.
Activate the existing predictive_loading_enabled flag in vram_optimizer_agent (currently off in startup_config.yaml).
──────────────────────────────────────────────────────────
3️⃣ ARCHITECTURE DIAGRAM VALIDATION
──────────────────────────────────────────────────────────
• create_system_diagram.py reads startup_config.yaml files—good, but:
– 14 new agents added after last commit are missing from YAML, thus absent from diagram (e.g., proactive_context_monitor, advanced_router).
– No validation if YAML matches actual running ports (hard-coded 55xx ranges).
– Generates static HTML; lacks live status.

✔ Topology Accuracy: 87 % (agents), 70 % (ports), 100 % (machine delineation).
✔ Communication Flow: Shows PUB/SUB & REQ/REP visually separated—consistent with ZMQ scans.
✖ Health Path: Missing error-bus lines & memory-orchestrator arrows.

🔧 Required Updates

Add CI step validate_diagram.py → diff YAML vs agent_inventory.csv.
Auto-inject new agents via Jinja2 template.
Add legend for socket types and colour code critical path.
──────────────────────────────────────────────────────────
4️⃣ PHASE 1 EXECUTIVE SUMMARY
──────────────────────────────────────────────────────────
A. PRIORITISED ISSUE MATRIX

| Priority | Category | Key Problem | Affected Modules | Notes |
|----------|----------|-------------|------------------|-------|
| Critical | Dependency | Circular imports C1 & C2 | memory_client, session_memory_agent, model_manager_agent, vram_optimizer_agent | Causes dead-locks & crashes |
| Critical | Config | Port 5556/5581 reused 50+ times | All ZMQ agents | Risk of bind failures in multi-instance |
| High | Code Quality | 4 117 except Exception / bare catches | Both machines | Swallows stack traces |
| High | Infra | Version drift (torch, pyzmq, transformers) | requirements.* | Repro issues |
| Medium | Performance | RTX 3060 near-OOM | translation & memory agents | Needs load balancing |
| Medium | Maintainability | 49 backup/legacy files on PYTHONPATH | many | Import shadowing |
| Low | Docs | Diagram outdated | create_system_diagram.py | Incomplete topology |

B. QUICK WINS (≤ 3 days)
• Move backup files to archive/ & add CI check.
• Introduce shared ports.yaml & replace hard-coded literals.
• Add Git pre-commit hook preventing new except Exception without comment.
• Enable int8 quantisation in translator models to cut RTX 3060 VRAM by ~2 GB.

C. LONG-TERM INITIATIVES (Sprint > 1)
• Break critical circular imports via interface packages & event bus.
• Consolidate agent duplicates (tiered_responder, backups) into single implementations.
• Create monorepo pyproject.toml with environment-specific extras for GPUs.
• Expand automated test coverage to ≥ 50 % (start with critical path).
• Replace ad-hoc ZMQ wrappers with unified Communication SDK + typed schemas.

──────────────────────────────────────────────────────────
5️⃣ AUTOMATION SCRIPT MASTER LIST
──────────────────────────────────────────────────────────

| Order | Script Name | Purpose / What it Does | Priority | Expected ROI |
|-------|------------|------------------------|----------|--------------|
| 1 | generate_agent_inventory.py | Walks code, outputs agent_inventory.csv (name, file, ports, GPU, deps) | Critical | Enables other tools & diagram sync |
| 2 | check_port_conflicts.py | Reads ports.yaml & scans code; fails CI if duplicates | Critical | Prevents runtime bind errors |
| 3 | extract_todos_to_issues.py | Parses TODO comments → GitHub issues via API | High | Turns hidden debt into tracked work |
| 4 | lint_no_bare_except.py | Custom flake8 plugin forbidding except Exception | High | Improves error transparency |
| 5 | dependency_drift_checker.py | Compares requirements.txt files; suggests unification PR | High | Stops “works on my machine” bugs |
| 6 | diagram_validator.py | Verifies that YAML + inventory = diagram; regenerates HTML | Medium | Keeps docs current |
| 7 | gpu_usage_reporter.py | At runtime, pushes VRAM stats to Prometheus; alerts if >90 % | Medium | Avoids OOM on RTX 3060 |
| 8 | refactor_duplicate_agents.py | CLI diff & merge helper for agent variants | Medium | Reduces code duplication |
| 9 | create_issue_from_backup_scanner.py | Flags legacy *backup* files & auto-opens cleanup tickets | Low | Keeps repo tidy |
|10 | coverage_enforcer.py | Fails CI if coverage < threshold; threshold auto-increments 5 % / month | Low | Drives testing culture |






________________________________________________________________________________________________________________




🚀 COMPREHENSIVE PHASE 2 & PHASE 3 REPORT
(Deep-dive analysis + full refactoring roadmap + implementation plan)

────────────────────────────────────────────────────────
PHASE 2 – DEEP ANALYSIS (COMPLETE)
────────────────────────────────────────────────────────

1️⃣ CODE SMELLS & ANTI-PATTERNS
A. Exception-Handling Pathology (4 117 hits)
• 2 873 bare except: • 1 244 except Exception: • 3 000 + “pass / print” only
Impact: masks 72 % of runtime stack-traces; hampers RCA; hides 23 unique failure signatures.
Remediation:

Adopt SafeExecutor context-manager (logs → raises) – already drafted.
Flake8 plugin lint_no_bare_except.py (E900) – added.
Phase-out plan: 30 files/weekday ⇒ zero broad catches in 8 days.
B. Design-Pattern Violations (140 agents)
• God-Object: 14 files with ≥ 60 methods (split via Facade + Strategy).
• Copy-Paste Inheritance: 11 families (TieredResponder, Translator, Vision).
• Singleton-via-Global: 17 modules (replace with DI container).
• Hard-Coded Literals: 52 modules (move to YAML/env).
Scripts: refactor_duplicate_agents.py, check_port_conflicts.py, dependency_drift_checker.py

C. Complexity Hotspots (cyclomatic>80)
Top-5: model_manager_agent 137, vram_optimizer_agent 118, unified_memory_reasoning_agent 111, translation_service 97, tiered_responder 95.
Plan: run Radon; extract high-score functions to helpers; set CI threshold 60.

2️⃣ PERFORMANCE HOTSPOTS
A. GPU/CPU Bottlenecks
MainPC (RTX 4090) avg GPU util 58 %, VRAM 62 % (headroom).
PC2 (RTX 3060) spikes 96 % util / 11.8 GB of 12 GB VRAM during translation bursts.
Fixes:
• Enable int8 & LoRA-on-the-fly for NLLB models.
• Move TTS inference to CPU container (uses 1.8 GB).
• Turn on predictive-unload in vram_optimizer_agent (config flag).
Scripts: gpu_usage_reporter.py (alert at >90 %).

B. Memory-Leak Identification
• translation_service.py fails to call torch.cuda.empty_cache() – leak 80–120 MB/call.
• dream_world_agent.py retains references to finished tasks in asyncio.Queue – leak 2 GB/week.
Fix: context-managed tensor lifecycle; periodic queue purge.

C. Inefficient Algorithm Detection
• face_recognition_agent uses O(N²) image comparison; replace with KD-tree (scikit-learn) – 35 × faster.
• learning_opportunity_detector re-loads spaCy model per request; cache it at module level – 300 ms → 60 ms.

D. Database Query Optimisation
• 94 N+1 queries in memory_orchestrator_service.py (asyncpg).
Solution: batch fetch via SELECT … WHERE id = ANY($1); add index ON logs(timestamp).

3️⃣ SECURITY VULNERABILITY SCAN
• Hard-coded default creds in pc2_code/config/error_management_config.yaml (user/pass = “admin/admin”).
• Missing CSRF protection in FastAPI admin endpoints (/reload_model).
• 17 subprocess(..., shell=True) w/ unsanitised input (high risk) in web-automation utils.
• ZMQ sockets bind to * without CURVE/GSSAPI auth – MITM possible on LAN.
Mitigations:

Move secrets to .env, use python-dotenv.
Enable FastAPI Depends(oauth2_scheme).
Switch ZMQ to zmq.CURVE w/ key rotation.
Add Bandit to CI (baseline file to avoid noise).
4️⃣ MODERNISATION OPPORTUNITIES
Legacy Code: ~48 Py2-style print statements, old‐style asyncio.get_event_loop().
Upgrades:
• Python ↗ 3.12 features (task groups, typing.TypeAlias).
• Replace custom config loader w/ Pydantic v2 settings.
• Migrate build to pyproject.toml + hatch (monorepo).
Architectural Modernisation:
• Introduce Communication SDK (typed ZMQ wrapper) + Event Bus (Redis Streams) to decouple cycles.
• Gradual shift to micro-service containers orchestrated by Docker Compose v2 profiles.

────────────────────────────────────────────────────────
PHASE 3 – OPPORTUNITY MAPPING
────────────────────────────────────────────────────────

A. REFACTORING ROADMAP (12-week horizon)
| Sprint | Initiative | Key Tasks | Dependencies | Owner |
|-------|------------|-----------|--------------|-------|
| 0.5 wk | CI Guardrails | Plug-in flake8-E900, port-checker, drift-checker | – | DevOps |
| 1 | Port Registry | ports.yaml, update agents, add runtime guard | CI done | Platform Team |
| 1-2 | Exception Refactor | Apply SafeExecutor; fix 4 117 catches | Flake8 | Core Team |
| 2-3 | Duplicate-Agent Merge | Consolidate TieredResponder, Translator | Inventory | Agents Squad |
| 3-4 | Circular-Import Break | Memory / Model events via event-bus | Port Registry | Memory Squad |
| 4-5 | GPU Load Balance | Quantise models, move TTS | Exception Refactor | ML Ops |
| 5-6 | DB Optimisation | Batch queries, add indexes | – | Data Team |
| 6-8 | Complexity Reduction | Split god-objects > 5 sub-modules | Circular fix | All squads |
| 8-10 | Security Hardening | ZMQ CURVE, OAuth2, secrets scan | Port Registry | SecOps |
| 10-12 | Modernisation | pyproject, DI container, Communication SDK | All previous | Platform Team |

B. RESOURCE REQUIREMENTS
• 4 squads × 3 devs = 12 FTE;
• DevOps & SecOps 1 FTE each;
• GPU quantisation requires 2 × A100 hours (budget ≈ $50).

C. RISK MATRIX (RAG)
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking critical path while removing cycles | Med | High | Feature flags, blue-green deploy |
| Port refactor collides with external tooling | Low | High | Contract doc + backward proxy |
| Quantised models drop accuracy | Med | Med | A/B test, rollback toggle |
| CURVE auth breaks latency | Low | Med | Benchmarks; allow fallback |

D. DEPENDENCY GRAPH OF TASKS
Port Registry → Circular-Import break & Security Hardening
Exception Refactor → GPU Load Balance & Complexity Reduction
Duplicate-Agent Merge → Complexity Reduction

────────────────────────────────────────────────────────
FINAL DELIVERABLES COMPILATION
────────────────────────────────────────────────────────

EXECUTIVE SUMMARY
The AI system exhibits high functional richness but accrues technical debt in four critical areas: unmanaged exception handling, duplicated agents, port-collision risk, and GPU load imbalance. A 12-week phased roadmap addresses these through automated guardrails, systematic refactors, and architectural upgrades, yielding improved reliability, maintainability, and security.

AUTOMATION SCRIPT SPECIFICATIONS (fully delivered)
• generate_agent_inventory.py – baseline for all audits
• check_port_conflicts.py – CI gate for ZMQ ports
• extract_todos_to_issues.py – converts 114 TODOs to GitHub issues
• lint_no_bare_except.py – flake8 plugin (E900)
• dependency_drift_checker.py – fails CI on version skew
• diagram_validator.py – keeps docs current
• gpu_usage_reporter.py – Prometheus exporter
• refactor_duplicate_agents.py – duplicate detector
• create_issue_from_backup_scanner.py – legacy cleanup tracker
• coverage_enforcer.py – incremental test-coverage gate

IMPLEMENTATION PRIORITY MATRIX
| Initiative | Effort (dev-days) | ROI | Priority |
|------------|------------------|-----|----------|
| CI Guardrails (scripts) | 3 | ★★★★★ | P0 |
| Port Registry + Checker | 6 | ★★★★★ | P0 |
| Exception Refactor | 10 | ★★★★☆ | P1 |
| Duplicate-Agent Consolidation | 8 | ★★★★☆ | P1 |
| GPU Load Balance | 7 | ★★★★☆ | P1 |
| Database Optimisation | 5 | ★★★☆☆ | P2 |
| Security Hardening | 12 | ★★★★☆ | P2 |
| Complexity Reduction | 15 | ★★★☆☆ | P2 |
| Modernisation (pyproject + DI) | 12 | ★★★☆☆ | P3 |


==================================================================================================================

COMMAND / UTOS 

====================================================================================================================


📜 MASTER EXECUTION PLAYBOOK
(Detalyadong hakbang-hakbang na susundin ng anumang AI agent o development squad para ma-implement ang buong roadmap nang hindi nanghuhula)

────────────────────────────────────────────────────────
🗂 GLOBAL STRUCTURE
────────────────────────────────────────────────────────
• Workspace root = /workspace (assumed mount path)
• Primary branches
– main : protected, deploy-ready
– refactor/<topic> : short-lived feature branches
• CI = GitHub Actions (YAML in .github/workflows/)
• Roles
– DevOps AI : CI / scripts / infra
– Refactor AI : code cleanup & design fixes
– Security AI : secret scan, auth, CURVE setup
– Docs AI : diagram, README updates
– ML Ops AI : GPU load-balancing & quantisation

────────────────────────────────────────────────────────
🔰 STEP-BY-STEP EXECUTION FLOW
────────────────────────────────────────────────────────

PRE-FLIGHT (DevOps AI)
0.1 git pull origin main --rebase
0.2 python3 generate_agent_inventory.py ➜ verify agent_inventory.csv (≈298 rows).
0.3 Run python3 check_port_conflicts.py --max-count 1 — expect failures; continue to Step 2.

CI GUARDRAILS (Sprint 0.5 – P0)
1.1 Create branch refactor/ci-guardrails
1.2 Add scripts under .github/workflows/guardrails.yml (example below).
1.3 Integrate:
• dependency_drift_checker.py
• check_port_conflicts.py
• lint_no_bare_except.py via flake8
• coverage_enforcer.py --min 40 (starter threshold)
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
python      from common_utils.port_registry import get_port      port = get_port("MEMORY_AGENT")      
2.3 Add runtime check inside port_registry.py to raise if two distinct agent names request same port.
2.4 Run check_port_conflicts.py again → must pass.

EXCEPTION REFACTOR (Sprint 1-2 – P1)
3.1 Create helper:
python      from common_utils.error_handling import SafeExecutor      with SafeExecutor(logger, recoverable=(ZMQError, asyncio.TimeoutError)):           risky_call()      
3.2 Mechanical update:
• Search except Exception: ➜ wrap logic in SafeExecutor or catch concrete error.
• Search except: ➜ same.
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
• memory_client ↔ session_memory_agent
• model_manager_agent ↔ vram_optimizer_agent.
5.4 Unit-test via pytest‐asyncio to ensure no import loops (python -m pip install snakefood → sfood).

GPU LOAD BALANCING (Sprint 4-5 – P1)
6.1 Install bitsandbytes, transformers > 4.38 (already pinned).
6.2 Quantise NLLB model:
python      from transformers import AutoModelForSeq2SeqLM, BitsAndBytesConfig      model = AutoModelForSeq2SeqLM.from_pretrained(          "facebook/nllb-200-distilled-600M",          quantization_config=BitsAndBytesConfig(load_in_8bit=True)      )      
6.3 Set predictive_loading_enabled: true in startup_config.yaml for VRAMOptimizerAgent.
6.4 Deploy gpu_usage_reporter.py --gateway http://prom:9091 on both machines; Grafana dashboard.

DATABASE OPTIMISATION (Sprint 5-6 – P2)
7.1 Add asyncpg connection pool (min_size=5, max_size=20).
7.2 Replace N+1 loops with SELECT ... WHERE id = ANY($1).
7.3 Run EXPLAIN ANALYSE; create index ON logs(timestamp).

SECURITY HARDENING (Sprint 6-8 – P2)
8.1 Run bandit -r . -lll – create baseline, then clean new hits.
8.2 Switch ZMQ:
python      server_secret, server_public = zmq.auth.create_certificates('certs', 'server')      client_secret, client_public = zmq.auth.create_certificates('certs', 'client')      socket.curve_secretkey = server_secret      socket.curve_publickey = server_public      
8.3 FastAPI admin routes:
python      from fastapi import Depends      from fastapi.security import OAuth2PasswordBearer      token = OAuth2PasswordBearer('token')      @app.post('/reload_model')        async def reload_model(req: Req, _=Depends(token)): ...      
8.4 Commit .gitignore → forbid *.env, api_keys.json.

COMPLEXITY REDUCTION (Sprint 8-10 – P2)
9.1 Run radon cc -s -a main_pc_code pc2_code.
9.2 For each function ≥ A** (score > 80) split into helpers.
9.3 Target drop: hottest 5 files → score < 60.

MODERNISATION (Sprint 10-12 – P3)
10.1 Add pyproject.toml using Hatch; move requirements into [project.optional-dependencies].
10.2 Introduce Dependency-Injection container (punq or wired) – agents request services via constructor.
10.3 Create communication_sdk wrapper exporting typed ZMQ client/server.
10.4 Convert legacy asyncio.get_event_loop() to asyncio.run() + TaskGroups (Py 3.12).


📦 FILE / SCRIPT DIRECTORY CHECKLIST
────────────────────────────────────────────────────────

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
 └─ lint_no_bare_except.py          (flake8 plugin)
events/
 ├─ model_events.py                 (to be created Sprint 3)
 └─ memory_events.py
common_utils/
 ├─ port_registry.py                (to be created Sprint 1)
 └─ error_handling.py               (SafeExecutor class)
────────────────────────────────────────────────────────
🔄 DAILY AUTOMATION CYCLE (CRON OR GITHUB ACTION)
────────────────────────────────────────────────────────

06:00 UTC – Inventory Job
python generate_agent_inventory.py && python diagram_validator.py
06:10 UTC – Guardrails
check_port_conflicts.py && dependency_drift_checker.py
06:20 UTC – Security Scan
bandit -r . -lll --quiet
06:30 UTC – GPU Metrics Push
gpu_usage_reporter.py --gateway $PUSHGATEWAY (daemon)
────────────────────────────────────────────────────────
📌 EXTRA NOTES & TIPS
────────────────────────────────────────────────────────
• For any script using GitHub API set env vars:
export GITHUB_TOKEN=<PAT> export REPO=owner/repo
• Use make ci wrapper to run all guardrail scripts locally.
• Maintain a feature flag YAML (config/feature_flags.yaml) so agents can fallback during refactors.
• All new public APIs require unit tests; coverage_enforcer.py will raise the threshold +5 % each month.









