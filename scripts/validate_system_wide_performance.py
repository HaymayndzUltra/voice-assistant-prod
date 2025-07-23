#!/usr/bin/env python3
"""
Validate System-Wide Performance - Phase 1 Week 3 Day 4
Comprehensive validation of system-wide optimization effectiveness
Generates a detailed report for Day 4 completion
"""

import sys
import os
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import statistics

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

class SystemWidePerformanceValidator:
    """Validate system-wide optimization effectiveness"""
    
    def __init__(self):
        self.central_hub_url = "http://localhost:9000"
        self.edge_hub_url = "http://localhost:9100"
        self.validation_results = {
            "total_agents": 0,
            "healthy_agents": 0,
            "optimized_agents": 0,
            "average_improvement": 0.0,
            "regressions": [],
            "alerts": [],
            "agent_metrics": {},
            "success": False
        }
        self.optimization_report_path = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_3_DAY_4_SYSTEM_WIDE_OPTIMIZATION_REPORT.json"
    
    def validate(self):
        print("\n📊 SYSTEM-WIDE PERFORMANCE VALIDATION")
        print("=" * 50)
        
        # Load optimization deployment report
        optimization_data = self._load_optimization_report()
        if not optimization_data:
            print("❌ Optimization deployment report not found.")
            return False
        
        # Collect agent health and metrics
        agent_metrics = self._collect_agent_metrics()
        self.validation_results["agent_metrics"] = agent_metrics
        
        # Analyze health and improvements
        healthy_agents = sum(1 for m in agent_metrics.values() if m.get('health_status', 0.0) > 0.5)
        self.validation_results["healthy_agents"] = healthy_agents
        self.validation_results["total_agents"] = len(agent_metrics)
        
        # Analyze improvements
        improvements = [d.get('estimated_improvement', 0) for d in optimization_data.get('detailed_results', {}).values() if d.get('success')]
        avg_improvement = statistics.mean(improvements) if improvements else 0.0
        self.validation_results["average_improvement"] = avg_improvement
        self.validation_results["optimized_agents"] = len(improvements)
        
        # Check for regressions
        regressions = [name for name, m in agent_metrics.items() if m.get('health_status', 0.0) < 0.5]
        self.validation_results["regressions"] = regressions
        
        # Alerts
        if avg_improvement < 20.0:
            self.validation_results["alerts"].append("Average improvement below target threshold (20%)")
        if regressions:
            self.validation_results["alerts"].append(f"{len(regressions)} agents unhealthy after optimization")
        
        # Success criteria
        self.validation_results["success"] = (
            healthy_agents == len(agent_metrics) and
            avg_improvement >= 20.0
        )
        
        # Generate report
        self._generate_report()
        
        print(f"\n🎯 VALIDATION SUMMARY:")
        print(f"   🟢 Healthy Agents: {healthy_agents}/{len(agent_metrics)}")
        print(f"   🚀 Average Improvement: {avg_improvement:.1f}%")
        print(f"   🏆 Optimized Agents: {len(improvements)}")
        if self.validation_results["alerts"]:
            print(f"   ⚠️  Alerts: {self.validation_results['alerts']}")
        if self.validation_results["success"]:
            print(f"\n✅ SYSTEM-WIDE OPTIMIZATION VALIDATION PASSED!")
        else:
            print(f"\n⚠️  SYSTEM-WIDE OPTIMIZATION VALIDATION NEEDS ATTENTION!")
        
        return self.validation_results["success"]
    
    def _load_optimization_report(self):
        try:
            if self.optimization_report_path.exists():
                with open(self.optimization_report_path, 'r') as f:
                    return json.load(f)
            else:
                return None
        except Exception as e:
            print(f"❌ Error loading optimization report: {e}")
            return None
    
    def _collect_agent_metrics(self) -> Dict[str, Any]:
        """Collect agent health and performance metrics from both hubs"""
        metrics = {}
        for hub_url in [self.central_hub_url, self.edge_hub_url]:
            try:
                response = requests.get(f"{hub_url}/api/v1/agents", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for agent in data.get('agents', []):
                        metrics[agent['name']] = {
                            'status': agent.get('status', 'unknown'),
                            'health_status': 1.0 if agent.get('status') == 'healthy' else 0.0,
                            'last_check': agent.get('last_check'),
                            'response_time': agent.get('response_time'),
                            'port': agent.get('port')
                        }
            except Exception as e:
                print(f"⚠️  Error collecting metrics from {hub_url}: {e}")
        return metrics
    
    def _generate_report(self):
        try:
            results_dir = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN"
            report_file = results_dir / "PHASE_1_WEEK_3_DAY_4_SYSTEM_WIDE_VALIDATION_REPORT.json"
            
            with open(report_file, 'w') as f:
                json.dump(self.validation_results, f, indent=2)
            print(f"\n📋 Validation report saved: {report_file}")
        except Exception as e:
            print(f"❌ Error saving validation report: {e}")

def main():
    validator = SystemWidePerformanceValidator()
    success = validator.validate()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 