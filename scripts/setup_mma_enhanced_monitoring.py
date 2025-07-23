#!/usr/bin/env python3
"""
ModelManagerAgent Enhanced Monitoring Setup
Phase 1 Week 4 Day 2 - Task 4C
Sets up enhanced monitoring for ModelManagerAgent migration with GPU/VRAM metrics.
"""

import sys
import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class MMAEnhancedMonitoringSetup:
    """Set up enhanced monitoring for ModelManagerAgent migration"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.monitoring_config = {
            "mma_specific_metrics": [],
            "observability_hub_integration": {},
            "grafana_dashboard": {},
            "alert_rules": [],
            "performance_baselines": {}
        }
    
    def create_mma_specific_metrics(self):
        """Create ModelManagerAgent-specific Prometheus metrics"""
        print("📊 CREATING MMA-SPECIFIC METRICS")
        print("=" * 50)
        
        mma_metrics = [
            {
                "name": "mma_gpu_memory_utilization",
                "type": "gauge",
                "description": "GPU memory utilization percentage for ModelManagerAgent",
                "labels": ["gpu_device", "model_name"],
                "collection_frequency": "5s",
                "critical_threshold": 90.0
            },
            {
                "name": "mma_model_loading_duration_seconds",
                "type": "histogram",
                "description": "Time taken to load models in seconds",
                "labels": ["model_name", "model_type", "gpu_device"],
                "buckets": [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
                "collection_frequency": "per_operation"
            },
            {
                "name": "mma_model_unloading_duration_seconds",
                "type": "histogram",
                "description": "Time taken to unload models in seconds",
                "labels": ["model_name", "model_type", "reason"],
                "buckets": [0.1, 0.5, 1.0, 2.0, 5.0],
                "collection_frequency": "per_operation"
            },
            {
                "name": "mma_active_models_count",
                "type": "gauge",
                "description": "Number of currently loaded models",
                "labels": ["gpu_device"],
                "collection_frequency": "10s"
            },
            {
                "name": "mma_vram_budget_utilization",
                "type": "gauge",
                "description": "VRAM budget utilization percentage",
                "labels": ["gpu_device"],
                "collection_frequency": "5s",
                "critical_threshold": 95.0
            },
            {
                "name": "mma_thread_health_status",
                "type": "gauge",
                "description": "Health status of MMA threads (1=healthy, 0=unhealthy)",
                "labels": ["thread_name", "thread_type"],
                "collection_frequency": "10s"
            },
            {
                "name": "mma_socket_connection_status",
                "type": "gauge",
                "description": "Socket connection status (1=connected, 0=disconnected)",
                "labels": ["socket_type", "endpoint"],
                "collection_frequency": "30s"
            },
            {
                "name": "mma_model_request_total",
                "type": "counter",
                "description": "Total number of model requests processed",
                "labels": ["request_type", "model_name", "status"],
                "collection_frequency": "per_request"
            },
            {
                "name": "mma_gpu_temperature_celsius",
                "type": "gauge",
                "description": "GPU temperature in Celsius",
                "labels": ["gpu_device"],
                "collection_frequency": "15s",
                "warning_threshold": 80.0,
                "critical_threshold": 90.0
            }
        ]
        
        self.monitoring_config["mma_specific_metrics"] = mma_metrics
        print(f"✅ Created {len(mma_metrics)} MMA-specific metrics")
        print(f"🔥 GPU temperature monitoring: {[m['name'] for m in mma_metrics if 'temperature' in m['name']]}")
        print(f"📈 Performance metrics: {[m['name'] for m in mma_metrics if 'duration' in m['name']]}")
    
    def integrate_with_observability_hub(self):
        """Integrate MMA monitoring with ObservabilityHub"""
        print("\n🔗 INTEGRATING WITH OBSERVABILITY HUB")
        print("-" * 50)
        
        observability_integration = {
            "enabled": True,
            "enhanced_metrics_endpoint": "/metrics/mma",
            "custom_collectors": [
                {
                    "name": "MMAGPUCollector",
                    "description": "Collects GPU-specific metrics for ModelManagerAgent",
                    "metrics": ["mma_gpu_memory_utilization", "mma_gpu_temperature_celsius", "mma_vram_budget_utilization"],
                    "collection_interval": "5s"
                },
                {
                    "name": "MMAModelCollector",
                    "description": "Collects model operation metrics",
                    "metrics": ["mma_model_loading_duration_seconds", "mma_model_unloading_duration_seconds", "mma_active_models_count"],
                    "collection_interval": "per_operation"
                },
                {
                    "name": "MMAInfrastructureCollector",
                    "description": "Collects infrastructure health metrics",
                    "metrics": ["mma_thread_health_status", "mma_socket_connection_status"],
                    "collection_interval": "10s"
                }
            ],
            "dashboard_panels": [
                {
                    "title": "MMA GPU Memory Utilization",
                    "type": "graph",
                    "metrics": ["mma_gpu_memory_utilization", "mma_vram_budget_utilization"],
                    "alert_threshold": 90.0
                },
                {
                    "title": "MMA Model Operations",
                    "type": "table",
                    "metrics": ["mma_model_loading_duration_seconds", "mma_active_models_count"],
                    "refresh_interval": "5s"
                },
                {
                    "title": "MMA Infrastructure Health",
                    "type": "stat",
                    "metrics": ["mma_thread_health_status", "mma_socket_connection_status"],
                    "color_thresholds": {"healthy": "green", "warning": "yellow", "critical": "red"}
                }
            ],
            "cross_machine_sync": {
                "enabled": True,
                "sync_mma_metrics_to_pc2": True,
                "pc2_backup_monitoring": "Enable PC2 to monitor MMA status for failover"
            }
        }
        
        self.monitoring_config["observability_hub_integration"] = observability_integration
        print(f"✅ ObservabilityHub integration configured")
        print(f"📊 Custom collectors: {len(observability_integration['custom_collectors'])}")
        print(f"📋 Dashboard panels: {len(observability_integration['dashboard_panels'])}")
    
    def create_grafana_dashboard(self):
        """Create Grafana dashboard for MMA monitoring"""
        print("\n📈 CREATING GRAFANA DASHBOARD")
        print("-" * 50)
        
        grafana_dashboard = {
            "dashboard": {
                "id": None,
                "title": "ModelManagerAgent Migration Monitoring",
                "tags": ["modelmanager", "gpu", "migration", "week4"],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "GPU Memory Utilization",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "mma_gpu_memory_utilization",
                                "legendFormat": "GPU {{gpu_device}} - {{model_name}}"
                            }
                        ],
                        "yAxes": [{"min": 0, "max": 100, "unit": "percent"}],
                        "alert": {
                            "conditions": [{"query": {"params": ["A", "5m", "now"]}, "reducer": {"params": [], "type": "last"}, "evaluator": {"params": [90], "type": "gt"}}],
                            "executionErrorState": "alerting",
                            "noDataState": "no_data",
                            "frequency": "10s"
                        }
                    },
                    {
                        "id": 2,
                        "title": "Model Loading Performance",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "rate(mma_model_loading_duration_seconds_sum[5m]) / rate(mma_model_loading_duration_seconds_count[5m])",
                                "legendFormat": "Avg Loading Time - {{model_name}}"
                            }
                        ],
                        "yAxes": [{"min": 0, "unit": "s"}]
                    },
                    {
                        "id": 3,
                        "title": "Active Models Count",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "mma_active_models_count",
                                "legendFormat": "GPU {{gpu_device}}"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {"steps": [{"color": "green", "value": 0}, {"color": "yellow", "value": 3}, {"color": "red", "value": 5}]}
                            }
                        }
                    },
                    {
                        "id": 4,
                        "title": "Thread Health Status",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "mma_thread_health_status",
                                "legendFormat": "{{thread_name}}"
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "color": {"mode": "thresholds"},
                                "thresholds": {"steps": [{"color": "red", "value": 0}, {"color": "green", "value": 1}]}
                            }
                        }
                    },
                    {
                        "id": 5,
                        "title": "GPU Temperature",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "mma_gpu_temperature_celsius",
                                "legendFormat": "GPU {{gpu_device}} Temperature"
                            }
                        ],
                        "yAxes": [{"min": 0, "max": 100, "unit": "celsius"}],
                        "alert": {
                            "conditions": [{"query": {"params": ["A", "5m", "now"]}, "reducer": {"params": [], "type": "last"}, "evaluator": {"params": [85], "type": "gt"}}],
                            "executionErrorState": "alerting",
                            "noDataState": "no_data",
                            "frequency": "30s"
                        }
                    }
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "5s"
            }
        }
        
        self.monitoring_config["grafana_dashboard"] = grafana_dashboard
        print(f"✅ Grafana dashboard created with {len(grafana_dashboard['dashboard']['panels'])} panels")
        print(f"🚨 Alert-enabled panels: {len([p for p in grafana_dashboard['dashboard']['panels'] if 'alert' in p])}")
    
    def create_alert_rules(self):
        """Create Prometheus alert rules for MMA monitoring"""
        print("\n🚨 CREATING ALERT RULES")
        print("-" * 50)
        
        alert_rules = [
            {
                "alert": "MMAGPUMemoryHigh",
                "expr": "mma_gpu_memory_utilization > 90",
                "for": "2m",
                "labels": {"severity": "warning", "component": "ModelManagerAgent"},
                "annotations": {
                    "summary": "ModelManagerAgent GPU memory usage is high",
                    "description": "GPU memory utilization is {{ $value }}% on device {{ $labels.gpu_device }}"
                }
            },
            {
                "alert": "MMAGPUMemoryCritical",
                "expr": "mma_gpu_memory_utilization > 95",
                "for": "1m",
                "labels": {"severity": "critical", "component": "ModelManagerAgent"},
                "annotations": {
                    "summary": "ModelManagerAgent GPU memory usage is critical",
                    "description": "GPU memory utilization is {{ $value }}% on device {{ $labels.gpu_device }}. Immediate action required."
                }
            },
            {
                "alert": "MMAModelLoadingSlow",
                "expr": "rate(mma_model_loading_duration_seconds_sum[5m]) / rate(mma_model_loading_duration_seconds_count[5m]) > 10",
                "for": "3m",
                "labels": {"severity": "warning", "component": "ModelManagerAgent"},
                "annotations": {
                    "summary": "ModelManagerAgent model loading is slow",
                    "description": "Average model loading time is {{ $value }}s for model {{ $labels.model_name }}"
                }
            },
            {
                "alert": "MMAThreadUnhealthy",
                "expr": "mma_thread_health_status == 0",
                "for": "1m",
                "labels": {"severity": "critical", "component": "ModelManagerAgent"},
                "annotations": {
                    "summary": "ModelManagerAgent thread is unhealthy",
                    "description": "Thread {{ $labels.thread_name }} of type {{ $labels.thread_type }} is unhealthy"
                }
            },
            {
                "alert": "MMASocketDisconnected",
                "expr": "mma_socket_connection_status == 0",
                "for": "30s",
                "labels": {"severity": "warning", "component": "ModelManagerAgent"},
                "annotations": {
                    "summary": "ModelManagerAgent socket disconnected",
                    "description": "Socket {{ $labels.socket_type }} to {{ $labels.endpoint }} is disconnected"
                }
            },
            {
                "alert": "MMAGPUTemperatureHigh",
                "expr": "mma_gpu_temperature_celsius > 85",
                "for": "2m",
                "labels": {"severity": "warning", "component": "ModelManagerAgent"},
                "annotations": {
                    "summary": "ModelManagerAgent GPU temperature is high",
                    "description": "GPU {{ $labels.gpu_device }} temperature is {{ $value }}°C"
                }
            },
            {
                "alert": "MMAMigrationRollbackTrigger",
                "expr": "mma_thread_health_status == 0 OR mma_gpu_memory_utilization > 98 OR mma_gpu_temperature_celsius > 90",
                "for": "1m",
                "labels": {"severity": "critical", "component": "ModelManagerAgent", "action": "rollback"},
                "annotations": {
                    "summary": "ModelManagerAgent migration rollback trigger activated",
                    "description": "Critical condition detected - consider migration rollback"
                }
            }
        ]
        
        self.monitoring_config["alert_rules"] = alert_rules
        print(f"✅ Created {len(alert_rules)} alert rules")
        print(f"🚨 Critical alerts: {len([a for a in alert_rules if a['labels']['severity'] == 'critical'])}")
        print(f"⚠️ Warning alerts: {len([a for a in alert_rules if a['labels']['severity'] == 'warning'])}")
    
    def create_performance_baselines(self):
        """Create performance baselines for migration validation"""
        print("\n📊 CREATING PERFORMANCE BASELINES")
        print("-" * 50)
        
        performance_baselines = {
            "model_loading_time": {
                "small_models": {"baseline": 2.0, "max_acceptable": 2.2, "unit": "seconds"},
                "medium_models": {"baseline": 5.0, "max_acceptable": 5.5, "unit": "seconds"},
                "large_models": {"baseline": 15.0, "max_acceptable": 16.5, "unit": "seconds"}
            },
            "gpu_memory_utilization": {
                "idle": {"baseline": 10.0, "max_acceptable": 15.0, "unit": "percent"},
                "single_model": {"baseline": 40.0, "max_acceptable": 50.0, "unit": "percent"},
                "multiple_models": {"baseline": 75.0, "max_acceptable": 85.0, "unit": "percent"}
            },
            "thread_response_time": {
                "memory_management": {"baseline": 0.1, "max_acceptable": 0.2, "unit": "seconds"},
                "health_monitoring": {"baseline": 0.05, "max_acceptable": 0.1, "unit": "seconds"},
                "request_handling": {"baseline": 0.5, "max_acceptable": 0.75, "unit": "seconds"}
            },
            "socket_connection_time": {
                "local_connections": {"baseline": 0.01, "max_acceptable": 0.05, "unit": "seconds"},
                "cross_machine_connections": {"baseline": 0.1, "max_acceptable": 0.2, "unit": "seconds"}
            },
            "rollback_triggers": {
                "performance_degradation": {"threshold": 20.0, "unit": "percent"},
                "memory_utilization": {"threshold": 95.0, "unit": "percent"},
                "thread_failure": {"threshold": 1, "unit": "count"},
                "temperature": {"threshold": 90.0, "unit": "celsius"}
            }
        }
        
        self.monitoring_config["performance_baselines"] = performance_baselines
        print(f"✅ Performance baselines created for {len(performance_baselines)} categories")
        print(f"🎯 Rollback triggers: {len(performance_baselines['rollback_triggers'])}")
    
    def deploy_monitoring_configuration(self):
        """Deploy the monitoring configuration"""
        print("\n🚀 DEPLOYING MONITORING CONFIGURATION")
        print("-" * 50)
        
        # Save Prometheus configuration
        prometheus_config = {
            "global": {"scrape_interval": "15s"},
            "scrape_configs": [
                {
                    "job_name": "modelmanager-agent",
                    "static_configs": [{"targets": ["localhost:5570"]}],
                    "metrics_path": "/metrics",
                    "scrape_interval": "5s"
                },
                {
                    "job_name": "observability-hub-mma",
                    "static_configs": [{"targets": ["localhost:9000"]}],
                    "metrics_path": "/metrics/mma",
                    "scrape_interval": "10s"
                }
            ],
            "rule_files": ["alert_rules_mma.yml"]
        }
        
        prometheus_file = self.project_root / "monitoring" / "prometheus_mma.yml"
        prometheus_file.parent.mkdir(exist_ok=True)
        with open(prometheus_file, 'w') as f:
            yaml.dump(prometheus_config, f, default_flow_style=False)
        
        # Save alert rules
        alert_rules_config = {
            "groups": [
                {
                    "name": "modelmanager_agent_alerts",
                    "rules": self.monitoring_config["alert_rules"]
                }
            ]
        }
        
        alert_rules_file = self.project_root / "monitoring" / "alert_rules_mma.yml"
        with open(alert_rules_file, 'w') as f:
            yaml.dump(alert_rules_config, f, default_flow_style=False)
        
        # Save Grafana dashboard
        grafana_file = self.project_root / "monitoring" / "grafana_mma_dashboard.json"
        with open(grafana_file, 'w') as f:
            json.dump(self.monitoring_config["grafana_dashboard"], f, indent=2)
        
        print(f"✅ Prometheus config: {prometheus_file}")
        print(f"🚨 Alert rules: {alert_rules_file}")
        print(f"📈 Grafana dashboard: {grafana_file}")
        
        return {
            "prometheus_config": str(prometheus_file),
            "alert_rules": str(alert_rules_file),
            "grafana_dashboard": str(grafana_file)
        }
    
    def save_monitoring_configuration(self):
        """Save complete monitoring configuration"""
        config_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_MMA_MONITORING_CONFIG.json"
        
        with open(config_file, 'w') as f:
            json.dump(self.monitoring_config, f, indent=2)
        
        print(f"\n📋 Monitoring configuration saved: {config_file}")
        return config_file
    
    def run_complete_monitoring_setup(self):
        """Run complete enhanced monitoring setup"""
        print("\n" + "="*80)
        print("📊 MODELMANAGERAGENT ENHANCED MONITORING SETUP")
        print("📅 Phase 1 Week 4 Day 2 - Task 4C")
        print("="*80)
        
        self.create_mma_specific_metrics()
        self.integrate_with_observability_hub()
        self.create_grafana_dashboard()
        self.create_alert_rules()
        self.create_performance_baselines()
        
        deployed_files = self.deploy_monitoring_configuration()
        config_file = self.save_monitoring_configuration()
        
        print("\n" + "="*80)
        print("✅ ENHANCED MONITORING SETUP COMPLETE")
        print("🎯 Ready for Day 3: ModelManagerAgent Migration Execution")
        print("="*80)
        
        return {
            "config_file": config_file,
            "deployed_files": deployed_files,
            "metrics_count": len(self.monitoring_config["mma_specific_metrics"]),
            "alert_rules_count": len(self.monitoring_config["alert_rules"]),
            "dashboard_panels": len(self.monitoring_config["grafana_dashboard"]["dashboard"]["panels"])
        }

def main():
    setup = MMAEnhancedMonitoringSetup()
    results = setup.run_complete_monitoring_setup()
    
    print(f"\n🚀 Enhanced Monitoring Setup Summary:")
    print(f"  📊 Metrics created: {results['metrics_count']}")
    print(f"  🚨 Alert rules: {results['alert_rules_count']}")
    print(f"  📈 Dashboard panels: {results['dashboard_panels']}")
    print(f"  📋 Configuration file: {results['config_file']}")

if __name__ == "__main__":
    main() 