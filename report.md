COMPREHENSIVE DEEP-SCAN REPORT
(Repository: AI_System_Monorepo – scanned docker-compose files, core config utilities, and representative agent code)
1. Cross-Machine Docker Network Misconfiguration
Evidence
docker/mainpc/docker-compose.mainpc.yml (lines 252-269) creates a local bridge network ai_system_network with subnet 172.20.0.0/16.
docker/pc2/docker-compose.pc2.yml (bottom) declares the same network name but marks it external: true and supplies no subnet.
Bridge networks are host-local; identically-named bridges on two hosts do NOT interconnect.
Impact
Containers resolve service names only on the same host → cross-machine traffic silently falls back to the public host IPs or stalls.
Recommendation
Switch to Docker Swarm/Kubernetes overlay network or WireGuard-backed bridge that spans both hosts.
If Compose must stay, expose required services via host network and use explicit environment variables (MAINPC_IP, PC2_IP).
Confidence Score: 85% – confirmed by direct inspection of both compose files and Docker networking rules.
2. GPU Resource Allocation Conflicts
Evidence
MainPC: every agent-group container reserves driver: nvidia, count: 1 (Compose lines 66-84, 113-134, 156-178, 199-221).
All groups will address GPU 0 of the lone RTX 4090 concurrently.
PC2 compose files have no GPU reservation, yet several PC2 agents call .to("cuda") – e.g.
pc2_code/nllb_adapter.py line 97, agents/*translation_adapter.py lines 156 & 378.
Impact
MainPC: VRAM exhaustion & context switching slow-downs.
PC2: Agents crash at start-up when CUDA unavailable → contributes to the current 33.3 % failure rate on PC2.
Recommendation
Introduce NVIDIA_VISIBLE_DEVICES per container (e.g. "0" for MainPC group A, "0" with GPU_MEM_FRACTION=0.30 for group B…) or enable MIG on the 4090.
Add identical deploy.resources.reservations.devices stanza to PC2 compose with capabilities: [gpu] count: 1 and verify nvidia-container-toolkit on PC2.
Refactor agent code to read CUDA_DEVICE env var instead of hard-coding .to("cuda").
Confidence Score: 80% – multiple confirming code paths; runtime crashes already observed.
3. Hard-Coded IP Fallbacks Causing Config Drift
Evidence
common/config_manager.py (lines 118-132) defaults to "192.168.100.16" / "192.168.100.17" when env vars missing.
Numerous scripts (e.g. remote_connector_agent.py, validate-setup.py) embed literal 192.168.100.16.
Impact
Network changes (DHCP, VPN, second NIC) break inter-agent calls without warning; manual override required in dozens of places.
Recommendation
Finish running migrate_hardcoded_ips.py across all directories; commit resulting env-based placeholders.
Centralise host discovery in Service-Registry agent and inject via it or via Consul/etcd.
Confidence Score: 75% – direct matches across six files; pattern likely broader.
4. Missing Resource Limits (CPU / Memory / GPU)
Evidence
No deploy.resources.limits stanza in either compose file.
Impact
Agents may spike CPU/VRAM → trigger OOM-killer or throttle other containers; root cause of “gradual performance degradation”.
Recommendation
Define per-service limits (cpus: "2.0", memory: 4g, reservations:…) based on current profiling (system_health_report.md).
Confidence Score: 80% – explicit absence verified in compose files.
5. Agent Start-Up Race Conditions on PC2
Evidence
docker-compose.pc2.yml groups have no depends_on except implicit network; e.g. ai-reasoning-group uses CacheManager but doesn’t wait for memory-services-group.
Impact
First-boot failure cascades; observed 33 % agent failure rate aligns with this.
Recommendation
Add health-checked depends_on or orchestrate via system-digital-twin ordering hooks.
Confidence Score: 70% – deduction from compose structure; full dependency graph needs manual confirmation.
6. GPU-Absent Agents Executing CUDA Code on PC2
Evidence
PC2 agent code paths in pc2_code/nllb_adapter.py, llm_translation_adapter.py call .to("cuda") unconditionally.
Impact
Immediate torch.cuda.CudaError → silent crash if caught and logged as non-fatal.
Recommendation
Wrap device selection:

       device = "cuda" if torch.cuda.is_available() else "cpu"
       model.to(device)

and surface warnings to Observability Hub.
Confidence Score: 78% – reproducible in static analysis.
7. Observability Hub Port Duplication Across Machines
Evidence
Both hosts expose 9000/9100. Not a collision per host, but remote scripts (e.g. validate-setup.py) assume MainPC IP for both.
Impact
Health-check tooling may ignore PC2 metrics → blind-spot in monitoring.
Recommendation
Use distinct ports (e.g. 9001 on PC2) or route via NGINX reverse proxy on MainPC.
Confidence Score: 50% – issue affects tooling rather than runtime; requires ops-level decision.
8. Silent Failure Detection Gaps
Evidence
Health-check decorators exist (common/utils/health.py) but many agents lack periodic metric pushes (confirmed via absence in 20 random agents).
Impact
Silent VRAM leaks & queue stalls go unreported.
Recommendation
Enforce interface: every BaseAgent must call report_metric("heartbeat", 1) every N seconds.
Extend System-Digital-Twin to mark missing heartbeats as CRITICAL.
Confidence Score: 65% – sampling indicates coverage gaps; full audit needed.
UNABLE TO VERIFY (Manual Review Needed)
Port collisions inside agents’ ZMQ bindings (requires runtime inspection).
Actual memory-leak hotspots (needs long-running profiler traces).
Docker volume permission issues (depends on host FS ACLs).
NEXT-STEP AUTOMATED REMEDIATIONS (High-Level)
1 . scripts/deploy_system.py – integrate docker network create --driver overlay ai_system_network --subnet 172.30.0.0/16 and switch both compose files to external: true.
2. Patch GPU device env-vars in all Dockerfiles:

   ENV CUDA_VISIBLE_DEVICES=${CUDA_DEVICE:-0}

3. Append to every compose service:
   deploy:
     resources:
       limits:
         memory: 6g
         cpus: "2.0"

4. Generate dependency map via create_system_diagram.py and feed into compose depends_on automatically.
5. Run python migrate_hardcoded_ips.py --apply as pre-commit hook.
SYSTEM HEALTH DASHBOARD SNAPSHOT (derived from last reports)
MainPC agents active: 12/54 (23 %)
PC2 agents active: 18/27 (67 %)
Redis latency MainPC → PC2: 68 ms (target < 50 ms)
VRAM utilisation MainPC GPU0: 89 % peak at 09:42 UTC
CPU throttling events inside memory-system-group: 17 in last 6 h
OPTIMIZATION ROADMAP (Priority-Ordered)
Fix overlay network (blocks most cross-machine errors).
GPU allocation overhaul (MIG & env-var device selection).
Add resource limits + monitoring hooks.
Remove IP literals; move to service discovery.
Introduce orchestrated start-up sequencing for PC2.
