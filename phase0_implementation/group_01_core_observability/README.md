# PHASE 0 - GROUP 1: CORE & OBSERVABILITY
**Consolidation Group: Core & Observability (5 agents → 2)**

## 🎯 TARGET SERVICES

### CoreOrchestrator (Port 7000, MainPC)
**Source Agents:**
- ServiceRegistry
- SystemDigitalTwin  
- RequestCoordinator
- UnifiedSystemAgent

**Notes:**
- SystemDigitalTwin kept as internal module inside CoreOrchestrator
- Everything bootstraps from CoreOrchestrator

### ObservabilityHub (Port 9000, PC2)
**Source Agents:**
- PredictiveHealthMonitor
- PerformanceMonitor
- HealthMonitor
- PerformanceLoggerAgent
- SystemHealthManager

**Notes:**
- Health endpoints become /metrics
- Data sent to Prometheus + Grafana

## ⚠️ RISKS & MITIGATIONS
- **Risk:** Merging SystemDigitalTwin with ServiceRegistry → large codebase touch
- **Mitigation:** Keep original classes, wrap in "facade" first, then deprecate

## 📁 STATUS: PLACEHOLDER - IMPLEMENTATION GUIDE NEEDED 