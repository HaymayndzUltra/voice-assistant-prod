#!/usr/bin/env python3
"""
Deploy Advanced Monitoring - Phase 1 Week 3 Day 5
Deploys advanced monitoring dashboards and alerting for all agents
Integrates with Prometheus and ObservabilityHub
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

class AdvancedMonitoringDeployer:
    """Deploy advanced monitoring dashboards and alerting"""
    
    def __init__(self):
        self.project_root = Path(PathManager.get_project_root())
        self.prometheus_config_path = self.project_root / "monitoring" / "prometheus" / "prometheus.yml"
        self.grafana_dashboards_dir = self.project_root / "monitoring" / "grafana" / "dashboards"
        self.alert_rules_path = self.project_root / "monitoring" / "prometheus" / "alert.rules.yml"
        self.observability_hub_urls = ["http://localhost:9000", "http://localhost:9100"]
    
    def deploy(self, comprehensive: bool = True):
        print("\n📊 DEPLOYING ADVANCED MONITORING DASHBOARDS & ALERTING")
        print("=" * 60)
        
        # Step 1: Generate Prometheus config
        self._generate_prometheus_config()
        print(f"✅ Prometheus config generated: {self.prometheus_config_path}")
        
        # Step 2: Deploy Grafana dashboards
        self._deploy_grafana_dashboards()
        print(f"✅ Grafana dashboards deployed: {self.grafana_dashboards_dir}")
        
        # Step 3: Configure alert rules
        self._configure_alert_rules()
        print(f"✅ Alert rules configured: {self.alert_rules_path}")
        
        # Step 4: Reload Prometheus and Grafana (simulated)
        self._reload_monitoring_services()
        print(f"✅ Monitoring services reloaded (simulated)")
        
        print("\n🎉 ADVANCED MONITORING DEPLOYMENT COMPLETE!")
        return True
    
    def _generate_prometheus_config(self):
        """Generate Prometheus config to scrape all ObservabilityHub endpoints"""
        self.prometheus_config_path.parent.mkdir(parents=True, exist_ok=True)
        scrape_configs = [
            {
                'job_name': 'observability_hubs',
                'metrics_path': '/metrics',
                'static_configs': [
                    {'targets': [url.replace('http://', '') for url in self.observability_hub_urls]}
                ]
            }
        ]
        config = {
            'global': {'scrape_interval': '15s'},
            'scrape_configs': scrape_configs
        }
        with open(self.prometheus_config_path, 'w') as f:
            import yaml
            yaml.dump(config, f)
    
    def _deploy_grafana_dashboards(self):
        """Deploy advanced Grafana dashboards (simulated)"""
        self.grafana_dashboards_dir.mkdir(parents=True, exist_ok=True)
        # Simulate deployment by creating a sample dashboard JSON
        dashboard = {
            "title": "AI System Monitoring",
            "panels": [
                {"type": "graph", "title": "Agent Health", "targets": [{"expr": "observability_agent_health_status"}]},
                {"type": "graph", "title": "Response Time", "targets": [{"expr": "observability_response_time_seconds"}]},
                {"type": "table", "title": "Active Agents", "targets": [{"expr": "observability_active_agents_total"}]}
            ]
        }
        dashboard_path = self.grafana_dashboards_dir / "ai_system_monitoring.json"
        with open(dashboard_path, 'w') as f:
            json.dump(dashboard, f, indent=2)
    
    def _configure_alert_rules(self):
        """Configure Prometheus alert rules for system-wide performance"""
        self.alert_rules_path.parent.mkdir(parents=True, exist_ok=True)
        alert_rules = {
            'groups': [
                {
                    'name': 'ai_system_alerts',
                    'rules': [
                        {
                            'alert': 'AgentDown',
                            'expr': 'observability_agent_health_status == 0',
                            'for': '1m',
                            'labels': {'severity': 'critical'},
                            'annotations': {'summary': 'Agent is down', 'description': 'An agent has been unhealthy for more than 1 minute.'}
                        },
                        {
                            'alert': 'HighResponseTime',
                            'expr': 'observability_response_time_seconds > 2',
                            'for': '2m',
                            'labels': {'severity': 'warning'},
                            'annotations': {'summary': 'High response time', 'description': 'Agent response time is high.'}
                        },
                        {
                            'alert': 'LowActiveAgents',
                            'expr': 'observability_active_agents_total < 10',
                            'for': '5m',
                            'labels': {'severity': 'warning'},
                            'annotations': {'summary': 'Low active agents', 'description': 'Number of active agents is below threshold.'}
                        }
                    ]
                }
            ]
        }
        with open(self.alert_rules_path, 'w') as f:
            import yaml
            yaml.dump(alert_rules, f)
    
    def _reload_monitoring_services(self):
        """Simulate reload of Prometheus and Grafana services"""
        print("   - Simulating Prometheus reload...")
        print("   - Simulating Grafana reload...")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deploy advanced monitoring dashboards and alerting")
    parser.add_argument("--comprehensive", action="store_true", help="Deploy comprehensive monitoring")
    args = parser.parse_args()
    deployer = AdvancedMonitoringDeployer()
    deployer.deploy(comprehensive=args.comprehensive)

if __name__ == "__main__":
    main() 