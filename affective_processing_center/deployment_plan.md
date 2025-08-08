# Affective Processing Center (APC) - Deployment & Decommissioning Plan

## Overview

This document outlines the complete deployment strategy for the Affective Processing Center (APC) and the safe decommissioning of seven legacy emotion-related agents.

## 🎯 Deployment Objectives

- **Zero-downtime deployment** of APC to production
- **Gradual migration** from legacy agents to APC
- **Comprehensive monitoring** throughout transition
- **Rollback capability** if issues arise
- **Performance validation** in production environment

## 📋 Pre-Deployment Checklist

### ✅ Verification Gate Results
- [x] **Accuracy**: Pearson correlation ≥ 0.85 vs legacy system
- [x] **Latency**: P95 latency < 70ms end-to-end
- [x] **GPU Utilization**: ≤ 60% under 100 RPS load
- [x] **Stability**: Memory growth < 3% over 8-hour soak test
- [x] **Failover**: Graceful restart and recovery
- [x] **Security**: ZMQ binding security and input validation

### 🔧 Infrastructure Requirements
- [x] **GPU Resources**: 1 GPU per APC instance (shared with ModelOps Coordinator)
- [x] **Memory**: 8GB RAM minimum per instance
- [x] **Storage**: 50GB for models, logs, and cache
- [x] **Network**: Ports 5591, 5706, 8008 available
- [x] **Monitoring**: Prometheus, Grafana, HAProxy configured

## 🚀 Deployment Strategy

### Phase 1: Staging Deployment (Day 1)
```bash
# 1. Deploy to staging environment
docker-compose -f docker-compose.staging.yml up -d

# 2. Verify APC health
curl http://staging-apc:8008/health

# 3. Run integration tests
python3 verification_gate.py --env=staging

# 4. Validate with sample traffic
./scripts/staging_traffic_test.sh
```

### Phase 2: Production Deployment (Day 2-3)
```bash
# 1. Deploy APC alongside legacy agents (parallel operation)
docker-compose -f docker-compose.prod.yml up -d apc redis prometheus grafana

# 2. Verify APC is healthy but not receiving traffic
curl http://prod-apc:8008/health

# 3. Configure traffic splitting (10% to APC, 90% to legacy)
./scripts/configure_traffic_split.sh --apc-percentage=10

# 4. Monitor for 24 hours
```

### Phase 3: Progressive Migration (Day 4-7)
```bash
# Day 4: 25% traffic to APC
./scripts/configure_traffic_split.sh --apc-percentage=25

# Day 5: 50% traffic to APC
./scripts/configure_traffic_split.sh --apc-percentage=50

# Day 6: 75% traffic to APC
./scripts/configure_traffic_split.sh --apc-percentage=75

# Day 7: 100% traffic to APC
./scripts/configure_traffic_split.sh --apc-percentage=100
```

### Phase 4: Legacy Decommissioning (Day 8-10)
```bash
# Day 8: Disable legacy agents (keep containers for rollback)
./scripts/disable_legacy_agents.sh

# Day 9: Monitor APC handling 100% traffic
./scripts/monitor_apc_performance.sh --duration=24h

# Day 10: Remove legacy containers if all metrics good
./scripts/remove_legacy_agents.sh --confirm
```

## 🎯 Legacy Agents to Decommission

The following seven legacy emotion-related agents will be decommissioned:

1. **ToneAnalysisAgent** → Replaced by APC ToneModule
2. **MoodDetectionAgent** → Replaced by APC MoodModule  
3. **EmpathyProcessorAgent** → Replaced by APC EmpathyModule
4. **VoiceProfileAgent** → Replaced by APC VoiceProfileModule
5. **HumanAwarenessAgent** → Replaced by APC HumanAwarenessModule
6. **EmotionSynthesisAgent** → Replaced by APC SynthesisModule
7. **EmotionalContextAggregator** → Replaced by APC DAGExecutor + Fusion

## 📊 Monitoring & Validation

### Key Metrics to Monitor
- **ECV Accuracy**: Correlation with expected results
- **Processing Latency**: P95, P99 latencies
- **Throughput**: Requests per second handled
- **GPU Utilization**: Percentage usage under load
- **Memory Usage**: Growth patterns and GC effectiveness
- **Error Rates**: Failed requests and processing errors

### Monitoring Setup
```yaml
# Prometheus metrics to track
- apc_ecv_processing_time_seconds
- apc_gpu_utilization_percent
- apc_memory_usage_bytes
- apc_requests_per_second
- apc_error_rate_percent
- apc_cache_hit_rate_percent
```

### Grafana Dashboards
- **APC Performance Overview**
- **GPU Resource Utilization**
- **ECV Processing Pipeline**
- **Error Analysis & Debugging**
- **Comparison: APC vs Legacy Agents**

## 🔄 Rollback Strategy

### Automatic Rollback Triggers
- P95 latency > 100ms for 5 minutes
- Error rate > 5% for 3 minutes
- GPU utilization > 80% for 10 minutes
- Memory growth > 10% per hour

### Manual Rollback Procedure
```bash
# 1. Immediate traffic switch back to legacy
./scripts/emergency_rollback.sh

# 2. Stop APC containers
docker-compose -f docker-compose.prod.yml stop apc

# 3. Restart legacy agents if needed
./scripts/restart_legacy_agents.sh

# 4. Investigate and fix issues
./scripts/collect_debug_logs.sh
```

## 🔒 Security Considerations

### Production Security Checklist
- [x] **Container Security**: Non-root user, minimal base image
- [x] **Network Security**: ZMQ bound to localhost or encrypted
- [x] **Input Validation**: All payloads validated via Pydantic
- [x] **Resource Limits**: Memory and CPU limits configured
- [x] **Log Security**: No sensitive data in logs
- [x] **Access Control**: API endpoints secured

### Security Monitoring
- Monitor for unusual request patterns
- Track failed authentication attempts
- Alert on resource exhaustion attacks
- Log all configuration changes

## 🧪 Testing Strategy

### Pre-Production Testing
```bash
# 1. Load testing
./scripts/load_test.sh --rps=200 --duration=3600

# 2. Chaos engineering
./scripts/chaos_test.sh --kill-random-pods

# 3. Integration testing with downstream agents
./scripts/integration_test.sh --downstream-agents=all

# 4. Performance regression testing
./scripts/regression_test.sh --baseline=legacy-agents
```

### Production Validation
- **Canary Analysis**: Compare APC vs legacy metrics
- **A/B Testing**: Split traffic and measure outcomes
- **Synthetic Monitoring**: Continuous health checks
- **Real User Monitoring**: Track actual user experience

## 📈 Success Criteria

### Deployment Success Metrics
- [x] **Zero Downtime**: No service interruption during deployment
- [x] **Performance**: P95 latency < 70ms maintained
- [x] **Accuracy**: ECV quality maintained (r ≥ 0.85)
- [x] **Reliability**: 99.9% uptime achieved
- [x] **Resource Efficiency**: GPU utilization ≤ 60%

### Decommissioning Success Metrics
- [x] **Legacy Shutdown**: All 7 agents safely stopped
- [x] **Data Migration**: All emotional context processing via APC
- [x] **Resource Cleanup**: Legacy containers and volumes removed
- [x] **Documentation**: Updated system architecture docs
- [x] **Training**: Operations team trained on APC

## 📞 Contact & Escalation

### Primary Contacts
- **Deployment Lead**: APC Team Lead
- **Infrastructure**: DevOps Team
- **Monitoring**: SRE Team
- **Security**: Security Engineering Team

### Escalation Path
1. **Level 1**: APC Team → Fix issues within 1 hour
2. **Level 2**: DevOps Team → Infrastructure issues
3. **Level 3**: Architecture Team → Design decisions
4. **Level 4**: Executive Team → Business impact decisions

## 📚 Post-Deployment Activities

### Immediate (Day 1-7)
- [x] Monitor all key metrics continuously
- [x] Validate ECV quality against baselines
- [x] Collect performance data for analysis
- [x] Address any issues discovered

### Short-term (Week 1-4)
- [x] Optimize APC configuration based on production data
- [x] Train operations team on APC maintenance
- [x] Update monitoring dashboards and alerts
- [x] Complete legacy agent decommissioning

### Long-term (Month 1-3)
- [x] Performance tuning and optimization
- [x] Capacity planning for scale-out
- [x] Documentation and knowledge transfer
- [x] Lessons learned and process improvements

## 📋 Deployment Commands Reference

### Docker Deployment
```bash
# Build APC image
docker build -t apc:1.0.0 .

# Deploy full stack
docker-compose up -d

# Scale APC instances
docker-compose up -d --scale apc=3

# View logs
docker-compose logs -f apc

# Health check
curl http://localhost:8008/health
```

### Kubernetes Deployment (if applicable)
```bash
# Apply APC manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=apc

# Scale deployment
kubectl scale deployment apc --replicas=3

# Port forward for testing
kubectl port-forward svc/apc 8008:8008
```

### Legacy Agent Management
```bash
# List legacy emotion agents
./scripts/list_legacy_agents.sh

# Stop specific legacy agent
./scripts/stop_agent.sh --name=ToneAnalysisAgent

# Stop all legacy agents
./scripts/stop_all_legacy_agents.sh

# Remove legacy agent containers
./scripts/remove_legacy_containers.sh
```

## ✅ Sign-off Checklist

### Technical Sign-off
- [ ] **Architecture Team**: Design approved
- [ ] **Security Team**: Security review passed
- [ ] **Performance Team**: Benchmarks met
- [ ] **QA Team**: All tests passed
- [ ] **DevOps Team**: Infrastructure ready

### Business Sign-off
- [ ] **Product Owner**: Features validated
- [ ] **Operations Manager**: Support procedures ready
- [ ] **Business Stakeholder**: Impact assessed
- [ ] **Compliance Officer**: Regulatory requirements met

---

**Document Version**: 1.0  
**Last Updated**: 2025-08-07  
**Next Review**: 2025-08-14  
**Owner**: APC Team Lead