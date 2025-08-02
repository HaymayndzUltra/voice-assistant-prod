Executable Diagnostics (run these in the-test stack before reading the explanation)
# 0. Shell helper – capture container IDs
SDT_ID=$(docker ps -qf "name=system_digital_twin")
RC_ID=$(docker ps -qf "name=request_coordinator")

# 1. Is SystemDigitalTwin actually up?
docker inspect -f '{{.State.Status}}' $SDT_ID  # expect "running"

# 2. Port reachability from host
nc -zv $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $SDT_ID) 7220

# 3. Health probe (5 s timeout)
curl -m 5 http://$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $SDT_ID):7220/healthz

# 4. Internal reachability from RequestCoordinator
docker exec $RC_ID curl -m 5 http://system_digital_twin:7220/healthz

# 5. Recent logs
docker logs --since 2m $SDT_ID | tail -50
docker logs --since 2m $RC_ID | tail -50

If any of the commands above fail or return non-200, proceed through the remediation playbook below.
Root-Cause Analysis & Remediation Playbook
Container-level Issues
docker inspect $SDT_ID --format '{{.State.RestartCount}}'
>3 restarts → crash-loop.
Action: docker logs $SDT_ID | head -50 to capture the stack-trace.
Memory / OOM
docker stats --no-stream $SDT_ID – RSS near limit?
Action: bump mem_limit in compose / Kubernetes spec or optimise JVM/heap.
Port Exposure & Networking
Incorrect host-port mapping
docker port $SDT_ID should show 0.0.0.0:7220 → 7220/tcp.
If absent → recreate container with -p 7220:7220.
DNS or overlay-network
Inside request_coordinator, run ping -c1 system_digital_twin.
If fails → add both containers to the same docker network,
e.g. docker network connect core_net $SDT_ID.
Application-level Timeout
Health endpoint cold-start >5 s
Increase readinessProbe.timeoutSeconds (K8s) or RC client timeout (RC_SDT_TIMEOUT_MS).
Blocking startup tasks (DB migration, model load)
Check logs for “migrating …”, “loading weights …”.
Action: move heavy tasks to background thread or pre-warm image.
Service-Registry Mismatch
service_registry may hold stale IP.
curl http://service_registry:7000/services | jq '.SystemDigitalTwin'
If IP ≠ container IP → curl -XDELETE …/SystemDigitalTwin then container will re-register.
TLS / mTLS Handshake
If logs show SSLHandshakeException, ensure certificates under
/etc/certs/system_digital_twin/* are updated and env-vars
SDT_CERT_PATH, SDT_KEY_PATH are correct.
Regenerate certs with:


      docker exec $SDT_ID ./scripts/gen_self_signed.sh
      docker restart $SDT_ID

Resource Orchestrator (VRAM Optimiser) Interference
If GPU memory pressure causes SDT to hang during model sync,
verify with docker exec vram_optimizer nvidia-smi.
Action: pin SDT container to CPU-only node (--gpus '"device=none"').
Rollback / Redeploy
If new image tag introduced bug → roll back:


      docker pull system_digital_twin:<previous_tag>
      docker stop $SDT_ID && docker rm $SDT_ID
      docker run -d --name system_digital_twin -p 7220:7220 system_digital_twin:<previous_tag>

Verify RC now receives 200 OK:

      curl -m 3 http://$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $RC_ID):26002/_health

Post-Fix Validation (automated)
# One-shot functional test
docker exec $RC_ID curl -f -s \
  -H 'Content-Type: application/json' \
  -d '{"input":"ping"}' \
  http://localhost:26002/api/v1/process | jq '.status=="ok"'

# Synthetic monitoring (every 30 s)
watch -n30 curl -m2 -f http://system_digital_twin:7220/healthz

Edge-Case Considerations
Network partitions on overlay networks (Flannel/Cilium) – run traceroute.
Clock skew causing TLS expiry – verify date inside containers.
File descriptor exhaustion – cat /proc/$(pidof sdt)/limits | grep open.
Performance Implications
Increasing timeouts masks latency; root cause should still be addressed.
Frequent restarts lead to registry churn; add exponential back-off.
Failure Modes
SDT unavailable → cascading 502/504 in RC.
Registry holds phantom entry → health checks keep hitting dead IP.
Authoritative References
Docker networking: docs.docker.com/network/overlay/
Kubernetes readiness probes: kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
System design fault-tolerance: “Designing Data-Intensive Applications”, M. Kleppmann, ch. 11.
