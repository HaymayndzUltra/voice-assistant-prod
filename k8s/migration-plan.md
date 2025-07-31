# Kubernetes Migration Plan: Docker Compose → k3s

## Executive Summary
Migration from Docker Compose to k3s for production-grade orchestration with rolling updates, horizontal pod autoscaling (HPA), and improved resource management for RTX 4090/RTX 3060 environments.

## Migration Strategy

### Phase 1: k3s Cluster Setup (Week 1)
- **MainPC**: k3s master node with GPU node scheduling
- **PC2**: k3s worker node with RTX 3060 taints
- **Network**: Flannel CNI with cross-node service mesh
- **Storage**: Local path provisioner + NFS for shared volumes

### Phase 2: Service Translation (Week 2)
- Convert docker-compose services → Kubernetes Deployments
- Implement ConfigMaps for environment variables
- Setup Secrets for API keys and certificates
- Create Services and Ingress for external access

### Phase 3: GPU Scheduling & HPA (Week 3)
- Node affinity for GPU-bound workloads
- Custom metrics via DCGM for GPU-based autoscaling
- Resource quotas per namespace (infra, memory, gpu, etc.)
- PodDisruptionBudgets for high availability

### Phase 4: Monitoring & Observability (Week 4)
- Prometheus Operator with GPU metrics
- Grafana dashboards for multi-node visibility
- Jaeger for distributed tracing
- AlertManager for production alerts

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        k3s Cluster                         │
├─────────────────────────────────────────────────────────────┤
│ MainPC (RTX 4090) - Master + Worker                        │
│ ├─ kube-apiserver, etcd, scheduler                         │
│ ├─ nvidia-device-plugin                                    │
│ ├─ GPU Workloads: coordination, reasoning, learning        │
│ └─ Shared Services: observability, memory-stack            │
├─────────────────────────────────────────────────────────────┤
│ PC2 (RTX 3060) - Worker Node                              │
│ ├─ kubelet + nvidia-device-plugin                         │
│ ├─ GPU Workloads: vision-dream, tutoring                  │
│ └─ CPU Workloads: utility, web-interface                   │
└─────────────────────────────────────────────────────────────┘
```

## Service Mapping

| Docker Compose Group | Kubernetes Namespace | Deployment Strategy |
|---------------------|---------------------|-------------------|
| infra_core | ai-system-infra | StatefulSet (persistent storage) |
| coordination | ai-system-gpu | Deployment + GPU nodeSelector |
| memory_stack | ai-system-core | StatefulSet (database volumes) |
| speech_gpu | ai-system-gpu | Deployment + anti-affinity |
| learning_gpu | ai-system-gpu | Job/CronJob for training |
| utility_cpu | ai-system-core | Deployment + CPU nodeSelector |

## Resource Requirements

### MainPC Node
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    memory: "32Gi"
    cpu: "16"
  requests:
    nvidia.com/gpu: 1
    memory: "16Gi" 
    cpu: "8"
```

### PC2 Node
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    memory: "16Gi"
    cpu: "8"
  requests:
    nvidia.com/gpu: 1
    memory: "8Gi"
    cpu: "4"
```

## HPA Configuration

### GPU-based Autoscaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: reasoning-gpu-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reasoning-suite
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - type: Pods
    pods:
      metric:
        name: nvidia_gpu_utilization_percent
      target:
        type: AverageValue
        averageValue: "70"
```

### CPU-based Autoscaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: utility-cpu-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: utility-suite
  minReplicas: 2
  maxReplicas: 6
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

## Rolling Update Strategy

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
    maxSurge: 1
```

For GPU workloads:
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0  # No downtime for GPU services
    maxSurge: 1
```

## Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ai-system-network-policy
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/part-of: ai-system
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ai-system-core
    - namespaceSelector:
        matchLabels:
          name: ai-system-gpu
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: ai-system-core
```

## Migration Timeline

### Week 1: Infrastructure
- [ ] Install k3s on MainPC (master)
- [ ] Join PC2 as worker node
- [ ] Install NVIDIA device plugin
- [ ] Setup basic monitoring

### Week 2: Core Services
- [ ] Migrate infra_core services
- [ ] Setup persistent volumes
- [ ] Configure service discovery
- [ ] Test inter-service communication

### Week 3: GPU Workloads
- [ ] Migrate GPU-intensive services
- [ ] Configure node affinity
- [ ] Setup HPA with custom metrics
- [ ] Test rolling updates

### Week 4: Production Readiness
- [ ] Security hardening
- [ ] Backup/restore procedures
- [ ] Load testing
- [ ] Documentation and runbooks

## Risk Mitigation

1. **Service Downtime**: Blue-green deployment during migration
2. **GPU Resource Conflicts**: Careful scheduling with node taints
3. **Data Loss**: Volume snapshots before migration
4. **Network Latency**: Local cluster with high-speed interconnect

## Success Metrics

- **Zero-downtime deployments**: Rolling updates without service interruption
- **Resource Efficiency**: 20% better GPU utilization vs Docker Compose
- **Scalability**: Auto-scaling based on workload metrics
- **Observability**: Full distributed tracing across services
- **Recovery Time**: < 30 seconds for pod restarts

## Post-Migration Benefits

1. **Automated Scaling**: HPA based on GPU/CPU/memory metrics
2. **High Availability**: Multi-replica services with pod distribution
3. **Resource Optimization**: Better bin-packing of workloads
4. **GitOps Integration**: ArgoCD for declarative deployments
5. **Service Mesh**: Istio for advanced traffic management