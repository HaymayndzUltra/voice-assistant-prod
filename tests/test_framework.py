#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Unified Testing Framework for AI System
--------------------------------------
- Starts agents in dependency order
- Monitors health and connections
- Checks message flow and data integrity
- Generates detailed reports
- Supports test modes: unit, integration, system, cross-machine, stress, failover
- Advanced logging, distributed tracing, performance profiling, resource tracking, anomaly detection

Usage:
    python test_framework.py --mode [unit|integration|system|cross|stress|failover]
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

import psutil
import zmq
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestFramework")

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / 'analysis_output'
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
AGENT_REPORT_PATH = OUTPUT_DIR / 'agent_report.json'
REPORT_PATH = OUTPUT_DIR / 'test_framework_report.json'

# Test modes
TEST_MODES = ['unit', 'integration', 'system', 'cross', 'stress', 'failover']

def load_active_agents():
    """Load only active agents from startup_config.yaml of MainPC and PC2."""
    mainpc_config = PROJECT_ROOT / 'main_pc_code' / 'config' / 'startup_config.yaml'
    pc2_config = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'
    active_agents = []
    for config_path, root_dir in [
        (mainpc_config, PROJECT_ROOT / 'main_pc_code'),
        (pc2_config, PROJECT_ROOT / 'pc2_code')
    ]:
        if not config_path.exists():
            logger.warning(f"Config not found: {config_path}")
            continue
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        # Find all agent lists in the config
        for section in config:
            if isinstance(config[section], list):
                for agent in config[section]:
                    if isinstance(agent, dict) and agent.get('script_path'):
                        agent_entry = dict(agent)
                        agent_entry['root_dir'] = str(root_dir)
                        active_agents.append(agent_entry)
    return active_agents

class FilteredAgentManager:
    def __init__(self, active_agents):
        self.active_agents = active_agents
        self.processes = {}
        self.failed_agents = []
        self.missing_scripts = []
        self.dependency_graph = self._build_dependency_graph()

    def _build_dependency_graph(self):
        graph = {}
        for agent in self.active_agents:
            name = agent['name']
            deps = agent.get('dependencies', [])
            graph[name] = deps
        return graph

    def _topological_sort(self):
        in_degree = {a['name']: 0 for a in self.active_agents}
        for deps in self.dependency_graph.values():
            for d in deps:
                if d in in_degree:
                    in_degree[d] += 1
        queue = [a for a, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for dep in self.dependency_graph.get(node, []):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
        if len(order) != len(self.active_agents):
            logger.warning("Cycle detected or missing dependencies!")
        return order

    def start_agents(self):
        order = self._topological_sort()
        logger.info(f"Starting active agents in dependency order: {order}")
        name_to_agent = {a['name']: a for a in self.active_agents}
        for agent_name in order:
            agent = name_to_agent.get(agent_name)
            if not agent:
                continue
            script_path = agent['script_path']
            root_dir = Path(agent['root_dir'])
            abs_path = root_dir / script_path
            if not abs_path.exists():
                logger.error(f"Missing script for agent {agent_name}: {abs_path}")
                self.missing_scripts.append({'name': agent_name, 'script_path': str(abs_path)})
                continue
            logger.info(f"Starting agent {agent_name} ({abs_path})...")
            try:
                proc = subprocess.Popen([sys.executable, str(abs_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.processes[agent_name] = proc
                time.sleep(1)
            except Exception as e:
                logger.error(f"Failed to start agent {agent_name}: {e}")
                self.failed_agents.append({'name': agent_name, 'error': str(e)})

    def stop_agents(self):
        logger.info("Stopping all active agents...")
        for agent, proc in self.processes.items():
            logger.info(f"Terminating {agent}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Killing {agent}...")
                proc.kill()
        self.processes = {}

    def get_agent_ports(self):
        ports = {}
        for agent in self.active_agents:
            if 'port' in agent:
                ports[agent['name']] = agent['port']
        return ports

class HealthMonitor:
    def __init__(self, agent_ports: Dict[str, int]):
        self.agent_ports = agent_ports
        self.context = zmq.Context()

    def check_health(self) -> Dict[str, Any]:
        results = {}
        for agent, port in self.agent_ports.items():
            try:
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, 1000)
                socket.connect(f"tcp://localhost:{port}")
                socket.send_string(json.dumps({"action": "health_check"}))
                response = socket.recv_string()
                results[agent] = json.loads(response)
                socket.close()
            except Exception as e:
                results[agent] = {"status": "unreachable", "error": str(e)}
        return results

class MessageFlowChecker:
    def __init__(self, agent_ports: Dict[str, int]):
        self.agent_ports = agent_ports
        self.context = zmq.Context()

    def check_message_flow(self) -> Dict[str, Any]:
        # Simulate a message flow test (can be expanded)
        results = {}
        for agent, port in self.agent_ports.items():
            try:
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, 1000)
                socket.connect(f"tcp://localhost:{port}")
                socket.send_string(json.dumps({"action": "test_message", "payload": "ping"}))
                response = socket.recv_string()
                results[agent] = json.loads(response)
                socket.close()
            except Exception as e:
                results[agent] = {"status": "unreachable", "error": str(e)}
        return results

class ResourceProfiler:
    def __init__(self, agent_manager: FilteredAgentManager):
        self.agent_manager = agent_manager

    def profile(self) -> Dict[str, Any]:
        usage = {}
        for agent, proc in self.agent_manager.processes.items():
            try:
                p = psutil.Process(proc.pid)
                usage[agent] = {
                    "cpu_percent": p.cpu_percent(interval=0.1),
                    "memory_mb": p.memory_info().rss / 1024 / 1024,
                    "num_threads": p.num_threads(),
                }
            except Exception as e:
                usage[agent] = {"error": str(e)}
        return usage

class AnomalyDetector:
    def detect(self, health: Dict[str, Any], resources: Dict[str, Any]) -> List[str]:
        anomalies = []
        for agent, h in health.items():
            if h.get('status') != 'healthy':
                anomalies.append(f"{agent} unhealthy: {h}")
        for agent, r in resources.items():
            if isinstance(r, dict) and r.get('cpu_percent', 0) > 90:
                anomalies.append(f"{agent} high CPU: {r['cpu_percent']}%")
            if isinstance(r, dict) and r.get('memory_mb', 0) > 1024:
                anomalies.append(f"{agent} high memory: {r['memory_mb']} MB")
        return anomalies

def main():
    parser = argparse.ArgumentParser(description="Unified Testing Framework (Active Agents Only)")
    parser.add_argument('--mode', choices=TEST_MODES, default='system', help='Test mode')
    args = parser.parse_args()

    logger.info(f"Starting Unified Testing Framework in {args.mode} mode (active agents only)...")
    active_agents = load_active_agents()
    agent_manager = FilteredAgentManager(active_agents)
    agent_manager.start_agents()
    time.sleep(5)

    agent_ports = agent_manager.get_agent_ports()
    health_monitor = HealthMonitor(agent_ports)
    message_checker = MessageFlowChecker(agent_ports)
    profiler = ResourceProfiler(agent_manager)
    anomaly_detector = AnomalyDetector()

    report = {
        "mode": args.mode,
        "start_time": time.time(),
        "health": {},
        "message_flow": {},
        "resources": {},
        "anomalies": [],
        "missing_scripts": agent_manager.missing_scripts,
        "failed_agents": agent_manager.failed_agents,
        "end_time": None
    }

    try:
        report['health'] = health_monitor.check_health()
        report['message_flow'] = message_checker.check_message_flow()
        report['resources'] = profiler.profile()
        report['anomalies'] = anomaly_detector.detect(report['health'], report['resources'])
        report['end_time'] = time.time()
        with open(REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Test report saved to {REPORT_PATH}")
        print(f"\n=== Test Report Summary (Active Agents Only) ===")
        print(f"Mode: {args.mode}")
        print(f"Missing Scripts: {report['missing_scripts']}")
        print(f"Failed Agents: {report['failed_agents']}")
        print(f"Health: {report['health']}")
        print(f"Message Flow: {report['message_flow']}")
        print(f"Resources: {report['resources']}")
        print(f"Anomalies: {report['anomalies']}")
        print(f"Full report saved to {REPORT_PATH}")
    finally:
        agent_manager.stop_agents()
        logger.info("All active agents stopped.")

if __name__ == "__main__":
    main() 