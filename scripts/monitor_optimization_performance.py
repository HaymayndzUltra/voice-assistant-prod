#!/usr/bin/env python3
"""
Monitor Optimization Performance - Phase 1 Week 3 Day 3
Real-time tracking of optimization effectiveness using distributed ObservabilityHub
"""

import sys
import os
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta
import statistics

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

class OptimizationPerformanceMonitor:
    """Monitor and track optimization performance in real-time"""
    
    def __init__(self):
        self.central_hub_url = "http://localhost:9000"
        self.edge_hub_url = "http://localhost:9100"
        self.monitoring_interval = 30  # seconds
        self.baseline_data = {}
        self.optimization_data = {}
        self.performance_history = []
        
        # Performance thresholds
        self.thresholds = {
            "target_improvement": 40.0,  # 40% improvement target
            "minimum_improvement": 20.0,  # 20% minimum acceptable
            "regression_threshold": -5.0  # -5% indicates regression
        }
    
    def monitor_optimization_effectiveness(self, agents_file: str, baseline_comparison: bool = True):
        """Monitor optimization effectiveness with baseline comparison"""
        print("📊 OPTIMIZATION PERFORMANCE MONITORING")
        print("=" * 50)
        
        # Load optimized agents list
        optimized_agents = self._load_agents_list(agents_file)
        print(f"✅ Monitoring {len(optimized_agents)} optimized agents")
        
        # Load baseline data if available
        if baseline_comparison:
            self._load_baseline_data()
        
        # Start monitoring loop
        print("\n🔄 Starting real-time performance monitoring...")
        print("Press Ctrl+C to stop monitoring and generate report")
        
        monitoring_start = time.time()
        monitoring_sessions = 0
        
        try:
            while True:
                session_start = time.time()
                
                # Collect current metrics
                current_metrics = self._collect_current_metrics(optimized_agents)
                
                # Analyze performance
                performance_analysis = self._analyze_performance(current_metrics, baseline_comparison)
                
                # Display real-time summary
                self._display_monitoring_summary(performance_analysis, monitoring_sessions)
                
                # Store historical data
                self.performance_history.append({
                    "timestamp": session_start,
                    "metrics": current_metrics,
                    "analysis": performance_analysis
                })
                
                monitoring_sessions += 1
                
                # Sleep until next monitoring interval
                sleep_time = max(self.monitoring_interval - (time.time() - session_start), 1)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Monitoring stopped after {monitoring_sessions} sessions")
            
            # Generate comprehensive report
            self._generate_performance_report(monitoring_start, monitoring_sessions)
            
            return True
    
    def _load_agents_list(self, agents_file: str) -> List[str]:
        """Load list of agents to monitor"""
        try:
            if agents_file.endswith('.txt'):
                agents_path = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / agents_file
                with open(agents_path, 'r') as f:
                    return [line.strip() for line in f if line.strip()]
            else:
                # Direct file path
                with open(agents_file, 'r') as f:
                    return [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"❌ Error loading agents list: {e}")
            return []
    
    def _load_baseline_data(self):
        """Load baseline performance data for comparison"""
        try:
            baseline_file = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "optimization_baseline.json"
            if baseline_file.exists():
                with open(baseline_file, 'r') as f:
                    self.baseline_data = json.load(f)
                print(f"✅ Loaded baseline data from {baseline_file}")
            else:
                print("⚠️  No baseline data found, creating new baseline...")
                self._create_baseline()
        except Exception as e:
            print(f"⚠️  Error loading baseline data: {e}")
    
    def _create_baseline(self):
        """Create baseline performance data"""
        print("📊 Creating performance baseline...")
        
        # Collect current metrics as baseline
        try:
            baseline_agents = self._get_all_monitored_agents()
            baseline_metrics = self._collect_current_metrics(baseline_agents)
            
            self.baseline_data = {
                "timestamp": time.time(),
                "created_by": "optimization_monitor",
                "agents": baseline_metrics
            }
            
            # Save baseline data
            baseline_file = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "optimization_baseline.json"
            with open(baseline_file, 'w') as f:
                json.dump(self.baseline_data, f, indent=2)
            
            print(f"✅ Baseline created with {len(baseline_agents)} agents")
            
        except Exception as e:
            print(f"❌ Error creating baseline: {e}")
    
    def _get_all_monitored_agents(self) -> List[str]:
        """Get list of all agents being monitored by ObservabilityHub"""
        agents = []
        
        try:
            # Get agents from Central Hub
            response = requests.get(f"{self.central_hub_url}/api/v1/agents", timeout=10)
            if response.status_code == 200:
                central_data = response.json()
                agents.extend([agent['name'] for agent in central_data.get('agents', [])])
            
            # Get agents from Edge Hub
            response = requests.get(f"{self.edge_hub_url}/api/v1/agents", timeout=10)
            if response.status_code == 200:
                edge_data = response.json()
                agents.extend([agent['name'] for agent in edge_data.get('agents', [])])
            
        except Exception as e:
            print(f"⚠️  Error getting monitored agents: {e}")
        
        return list(set(agents))  # Remove duplicates
    
    def _collect_current_metrics(self, agents: List[str]) -> Dict[str, Any]:
        """Collect current performance metrics for specified agents"""
        metrics = {}
        
        try:
            # Get metrics from Central Hub
            central_metrics = self._get_hub_metrics(self.central_hub_url, "central")
            
            # Get metrics from Edge Hub  
            edge_metrics = self._get_hub_metrics(self.edge_hub_url, "edge")
            
            # Combine metrics
            all_metrics = {**central_metrics, **edge_metrics}
            
            # Filter for specified agents
            for agent in agents:
                if agent in all_metrics:
                    metrics[agent] = all_metrics[agent]
                else:
                    # Try to get basic health status
                    metrics[agent] = self._get_basic_agent_metrics(agent)
            
        except Exception as e:
            print(f"⚠️  Error collecting metrics: {e}")
        
        return metrics
    
    def _get_hub_metrics(self, hub_url: str, hub_type: str) -> Dict[str, Any]:
        """Get metrics from a specific ObservabilityHub"""
        metrics = {}
        
        try:
            # Get Prometheus metrics
            response = requests.get(f"{hub_url}/metrics", timeout=10)
            if response.status_code == 200:
                metrics_text = response.text
                agent_metrics = self._parse_prometheus_metrics(metrics_text, hub_type)
                metrics.update(agent_metrics)
            
            # Get agent status from API
            response = requests.get(f"{hub_url}/api/v1/agents", timeout=10)
            if response.status_code == 200:
                agents_data = response.json()
                for agent in agents_data.get('agents', []):
                    agent_name = agent['name']
                    if agent_name not in metrics:
                        metrics[agent_name] = {}
                    
                    metrics[agent_name].update({
                        'hub_type': hub_type,
                        'status': agent.get('status', 'unknown'),
                        'last_check': agent.get('last_check'),
                        'response_time': agent.get('response_time'),
                        'port': agent.get('port')
                    })
        
        except Exception as e:
            print(f"⚠️  Error getting {hub_type} hub metrics: {e}")
        
        return metrics
    
    def _parse_prometheus_metrics(self, metrics_text: str, hub_type: str) -> Dict[str, Any]:
        """Parse Prometheus metrics text to extract agent performance data"""
        agent_metrics = {}
        
        lines = metrics_text.split('\n')
        for line in lines:
            if line.startswith('#') or not line.strip():
                continue
                
            try:
                # Parse metric lines
                if 'agent_health_status' in line:
                    # Extract agent name and health status
                    parts = line.split('{')
                    if len(parts) >= 2:
                        labels = parts[1].split('}')[0]
                        value = float(parts[1].split('}')[1].strip())
                        
                        # Extract agent name from labels
                        if 'agent_name="' in labels:
                            agent_name = labels.split('agent_name="')[1].split('"')[0]
                            if agent_name not in agent_metrics:
                                agent_metrics[agent_name] = {}
                            agent_metrics[agent_name]['health_status'] = value
                            agent_metrics[agent_name]['hub_type'] = hub_type
                
                elif 'agent_response_time_seconds' in line:
                    # Extract response time metrics
                    parts = line.split('{')
                    if len(parts) >= 2:
                        labels = parts[1].split('}')[0]
                        value = float(parts[1].split('}')[1].strip())
                        
                        if 'agent_name="' in labels:
                            agent_name = labels.split('agent_name="')[1].split('"')[0]
                            if agent_name not in agent_metrics:
                                agent_metrics[agent_name] = {}
                            agent_metrics[agent_name]['response_time'] = value
                            
            except Exception:
                continue  # Skip malformed lines
        
        return agent_metrics
    
    def _get_basic_agent_metrics(self, agent_name: str) -> Dict[str, Any]:
        """Get basic metrics for an agent not found in ObservabilityHub"""
        return {
            'status': 'unknown',
            'health_status': 0.0,
            'response_time': None,
            'hub_type': 'unknown',
            'last_check': None
        }
    
    def _analyze_performance(self, current_metrics: Dict, baseline_comparison: bool) -> Dict[str, Any]:
        """Analyze current performance against baseline and targets"""
        analysis = {
            "total_agents": len(current_metrics),
            "healthy_agents": 0,
            "improved_agents": 0,
            "regressed_agents": 0,
            "improvements": {},
            "performance_summary": {},
            "alerts": []
        }
        
        for agent_name, metrics in current_metrics.items():
            agent_analysis = {
                "status": metrics.get('status', 'unknown'),
                "health_status": metrics.get('health_status', 0.0),
                "response_time": metrics.get('response_time'),
                "improvement": None,
                "performance_category": "unknown"
            }
            
            # Count healthy agents
            if metrics.get('health_status', 0.0) > 0.5:
                analysis["healthy_agents"] += 1
            
            # Compare with baseline if available
            if baseline_comparison and agent_name in self.baseline_data.get('agents', {}):
                baseline_metrics = self.baseline_data['agents'][agent_name]
                improvement = self._calculate_improvement(baseline_metrics, metrics)
                
                agent_analysis["improvement"] = improvement
                
                if improvement >= self.thresholds["target_improvement"]:
                    agent_analysis["performance_category"] = "excellent"
                    analysis["improved_agents"] += 1
                elif improvement >= self.thresholds["minimum_improvement"]:
                    agent_analysis["performance_category"] = "good"
                    analysis["improved_agents"] += 1
                elif improvement <= self.thresholds["regression_threshold"]:
                    agent_analysis["performance_category"] = "regressed"
                    analysis["regressed_agents"] += 1
                    analysis["alerts"].append(f"{agent_name}: Performance regression detected ({improvement:.1f}%)")
                else:
                    agent_analysis["performance_category"] = "stable"
            
            analysis["improvements"][agent_name] = agent_analysis
        
        # Calculate overall performance summary
        if analysis["total_agents"] > 0:
            analysis["performance_summary"] = {
                "health_rate": (analysis["healthy_agents"] / analysis["total_agents"]) * 100,
                "improvement_rate": (analysis["improved_agents"] / analysis["total_agents"]) * 100,
                "regression_rate": (analysis["regressed_agents"] / analysis["total_agents"]) * 100
            }
        
        return analysis
    
    def _calculate_improvement(self, baseline: Dict, current: Dict) -> float:
        """Calculate performance improvement percentage"""
        try:
            # Use response time as primary performance metric
            baseline_time = baseline.get('response_time')
            current_time = current.get('response_time')
            
            if baseline_time and current_time and baseline_time > 0:
                # Lower response time is better, so improvement is reduction in time
                improvement = ((baseline_time - current_time) / baseline_time) * 100
                return improvement
            
            # Fallback to health status improvement
            baseline_health = baseline.get('health_status', 0.0)
            current_health = current.get('health_status', 0.0)
            
            if baseline_health > 0:
                health_improvement = ((current_health - baseline_health) / baseline_health) * 100
                return health_improvement
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _display_monitoring_summary(self, analysis: Dict, session_count: int):
        """Display real-time monitoring summary"""
        print(f"\n📊 MONITORING SESSION {session_count + 1} | {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 60)
        
        summary = analysis.get("performance_summary", {})
        
        print(f"🔍 Agents Monitored: {analysis['total_agents']}")
        print(f"💚 Healthy Agents: {analysis['healthy_agents']}/{analysis['total_agents']} ({summary.get('health_rate', 0):.1f}%)")
        print(f"📈 Improved Agents: {analysis['improved_agents']} ({summary.get('improvement_rate', 0):.1f}%)")
        print(f"📉 Regressed Agents: {analysis['regressed_agents']} ({summary.get('regression_rate', 0):.1f}%)")
        
        # Show top performers
        improvements = analysis.get("improvements", {})
        top_performers = sorted(
            [(name, data.get("improvement", 0)) for name, data in improvements.items() if data.get("improvement") is not None],
            key=lambda x: x[1], reverse=True
        )[:3]
        
        if top_performers:
            print(f"\n🏆 Top Performers:")
            for name, improvement in top_performers:
                print(f"   • {name}: {improvement:+.1f}%")
        
        # Show alerts
        alerts = analysis.get("alerts", [])
        if alerts:
            print(f"\n⚠️  Alerts:")
            for alert in alerts[:3]:  # Show first 3 alerts
                print(f"   • {alert}")
        
        print("-" * 60)
    
    def _generate_performance_report(self, monitoring_start: float, sessions: int):
        """Generate comprehensive performance monitoring report"""
        try:
            report_file = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_3_DAY_3_PERFORMANCE_MONITORING_REPORT.json"
            
            monitoring_duration = time.time() - monitoring_start
            
            # Calculate aggregate statistics
            if self.performance_history:
                final_analysis = self.performance_history[-1]["analysis"]
                
                # Calculate average improvements
                all_improvements = []
                for session in self.performance_history:
                    for agent_data in session["analysis"]["improvements"].values():
                        if agent_data.get("improvement") is not None:
                            all_improvements.append(agent_data["improvement"])
                
                avg_improvement = statistics.mean(all_improvements) if all_improvements else 0.0
                max_improvement = max(all_improvements) if all_improvements else 0.0
                min_improvement = min(all_improvements) if all_improvements else 0.0
            else:
                final_analysis = {}
                avg_improvement = max_improvement = min_improvement = 0.0
            
            report_data = {
                "monitoring_session": {
                    "start_time": monitoring_start,
                    "duration_seconds": monitoring_duration,
                    "duration_formatted": str(timedelta(seconds=int(monitoring_duration))),
                    "sessions_completed": sessions,
                    "monitoring_interval": self.monitoring_interval
                },
                "performance_results": {
                    "final_analysis": final_analysis,
                    "aggregate_statistics": {
                        "average_improvement": avg_improvement,
                        "maximum_improvement": max_improvement,
                        "minimum_improvement": min_improvement,
                        "total_agents_monitored": final_analysis.get("total_agents", 0),
                        "total_improved_agents": final_analysis.get("improved_agents", 0)
                    }
                },
                "optimization_assessment": {
                    "target_achievement": avg_improvement >= self.thresholds["target_improvement"],
                    "minimum_threshold_met": avg_improvement >= self.thresholds["minimum_improvement"],
                    "regression_detected": min_improvement <= self.thresholds["regression_threshold"]
                },
                "historical_data": self.performance_history,
                "thresholds": self.thresholds
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n📋 PERFORMANCE MONITORING REPORT")
            print("=" * 40)
            print(f"📊 Monitoring Duration: {timedelta(seconds=int(monitoring_duration))}")
            print(f"📈 Average Improvement: {avg_improvement:+.1f}%")
            print(f"🏆 Best Improvement: {max_improvement:+.1f}%")
            print(f"📉 Worst Performance: {min_improvement:+.1f}%")
            print(f"🎯 Target Achievement: {'✅' if avg_improvement >= self.thresholds['target_improvement'] else '❌'}")
            print(f"📋 Report Saved: {report_file}")
            
        except Exception as e:
            print(f"❌ Error generating performance report: {e}")

def main():
    """Main monitoring execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor optimization performance")
    parser.add_argument("--agents", default="batch1_optimized.txt", help="File containing optimized agents to monitor")
    parser.add_argument("--baseline-comparison", action="store_true", default=True, help="Compare against baseline performance")
    parser.add_argument("--interval", type=int, default=30, help="Monitoring interval in seconds")
    
    args = parser.parse_args()
    
    monitor = OptimizationPerformanceMonitor()
    monitor.monitoring_interval = args.interval
    
    success = monitor.monitor_optimization_effectiveness(
        args.agents,
        args.baseline_comparison
    )
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 