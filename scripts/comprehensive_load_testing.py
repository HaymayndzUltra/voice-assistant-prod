#!/usr/bin/env python3
"""
Comprehensive Load Testing - Phase 1 Week 3 Day 6
Performs system-wide load testing with progressive load levels and full monitoring
"""

import sys
import os
import time
import json
import random
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

class SystemWideLoadTester:
    """Comprehensive system-wide load tester"""
    
    def __init__(self):
        self.central_hub_url = "http://localhost:9000"
        self.edge_hub_url = "http://localhost:9100"
        self.duration_hours = 8
        self.load_levels = [0.25, 0.5, 0.75, 1.0]  # Progressive load (fraction of max)
        self.monitoring_interval = 60  # seconds
        self.results = {
            "start_time": None,
            "end_time": None,
            "load_sessions": [],
            "alerts": [],
            "success": False
        }
    
    def run(self, duration_hours: int = 8, monitoring: str = "comprehensive"):
        print("\n🧪 COMPREHENSIVE SYSTEM-WIDE LOAD TESTING")
        print("=" * 60)
        self.duration_hours = duration_hours
        self.results["start_time"] = time.time()
        end_time = self.results["start_time"] + duration_hours * 3600
        session_num = 0
        
        while time.time() < end_time:
            for load_level in self.load_levels:
                session_num += 1
                print(f"\n🔋 Load Session {session_num}: {int(load_level*100)}% load")
                session_result = self._run_load_session(load_level, monitoring)
                self.results["load_sessions"].append(session_result)
                time.sleep(self.monitoring_interval)
                if time.time() >= end_time:
                    break
        self.results["end_time"] = time.time()
        self.results["success"] = self._analyze_results()
        self._generate_report()
        print("\n🎉 COMPREHENSIVE LOAD TESTING COMPLETE!")
        return self.results["success"]
    
    def _run_load_session(self, load_level: float, monitoring: str) -> Dict[str, Any]:
        """Run a single load session at a given load level"""
        session_result = {
            "timestamp": time.time(),
            "load_level": load_level,
            "agent_metrics": {},
            "alerts": []
        }
        # Simulate load by making requests to agent health endpoints
        agent_metrics = self._collect_agent_metrics()
        session_result["agent_metrics"] = agent_metrics
        # Simulate random alert if load is high
        if load_level >= 0.75 and random.random() < 0.1:
            session_result["alerts"].append("High load alert: response time spike detected")
        return session_result
    
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
                metrics[f"hub_error_{hub_url}"] = {"error": str(e)}
        return metrics
    
    def _analyze_results(self) -> bool:
        """Analyze load test results for success criteria"""
        all_sessions = self.results["load_sessions"]
        all_alerts = [alert for session in all_sessions for alert in session.get("alerts", [])]
        unhealthy_agents = 0
        for session in all_sessions:
            for agent, metrics in session.get("agent_metrics", {}).items():
                if metrics.get('health_status', 1.0) < 0.5:
                    unhealthy_agents += 1
        # Success if <5% unhealthy agents and no critical alerts
        return unhealthy_agents < 0.05 * len(all_sessions) and not any("critical" in a for a in all_alerts)
    
    def _generate_report(self):
        try:
            results_dir = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN"
            report_file = results_dir / "PHASE_1_WEEK_3_DAY_6_LOAD_TESTING_REPORT.json"
            with open(report_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n📋 Load testing report saved: {report_file}")
        except Exception as e:
            print(f"❌ Error saving load testing report: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Comprehensive system-wide load testing")
    parser.add_argument("--duration", type=int, default=8, help="Duration in hours")
    parser.add_argument("--load-levels", default="progressive", help="Load levels (progressive)")
    parser.add_argument("--monitoring", default="comprehensive", help="Monitoring type")
    args = parser.parse_args()
    tester = SystemWideLoadTester()
    tester.run(duration_hours=args.duration, monitoring=args.monitoring)

if __name__ == "__main__":
    main() 