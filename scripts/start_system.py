#!/usr/bin/env python3
"""
Phased System Startup Script

This script starts all agents in the correct dependency order, in phases, as determined by the dependency graph.
Each phase is started in parallel, then health-checked with retries before proceeding to the next phase.
"""

import os
import sys
import time
import yaml
import subprocess
from pathlib import Path
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURABLE PARAMETERS ---
RETRIES = 3
RETRY_DELAY = 5  # seconds
HEALTH_CHECK_TIMEOUT = 5  # seconds
PYTHON_EXEC = sys.executable or "python3"

# --- PATHS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "main_pc_code" / "config" / "startup_config.yaml"
HEALTH_CHECK_SCRIPT = PROJECT_ROOT / "main_pc_code" / "scripts" / "verify_all_health_checks.py"
LOGS_DIR = PROJECT_ROOT / "logs"

# --- DEPENDENCY RESOLVER (from previous logic) ---
from collections import defaultdict, deque

def load_startup_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

class DependencyResolver:
    def __init__(self, config):
        self.config = config
        self.agents = {}  # name -> agent dict
        self.dependencies = defaultdict(set)  # name -> set of dependency names
        self.dependents = defaultdict(set)  # name -> set of agents that depend on this
        self.extract_agents()
        self.build_dependency_graph()
    
    def extract_agents(self):
        for section_name, section_data in self.config.items():
            if not isinstance(section_data, list):
                continue
            for agent in section_data:
                if not isinstance(agent, dict):
                    continue
                if 'name' not in agent or 'script_path' not in agent:
                    continue
                name = agent['name']
                self.agents[name] = agent
                if 'dependencies' in agent:
                    for dep in agent['dependencies']:
                        self.dependencies[name].add(dep)
    def build_dependency_graph(self):
        for agent_name, deps in self.dependencies.items():
            for dep in deps:
                self.dependents[dep].add(agent_name)
    def topological_sort(self):
        in_degree = {name: len(deps) for name, deps in self.dependencies.items()}
        for name in self.agents:
            if name not in in_degree:
                in_degree[name] = 0
        queue = deque([name for name, count in in_degree.items() if count == 0])
        result = []
        while queue:
            level_size = len(queue)
            current_level = []
            for _ in range(level_size):
                node = queue.popleft()
                current_level.append(node)
                for dependent in self.dependents[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            result.append(current_level)
        if sum(len(level) for level in result) != len(self.agents):
            print("WARNING: Circular dependencies detected!")
        return result
    def get_agent_details(self, name):
        return self.agents.get(name, {})
    def get_startup_phases(self):
        levels = self.topological_sort()
        phases = []
        for level_idx, level in enumerate(levels):
            phase = []
            for agent_name in level:
                agent = self.get_agent_details(agent_name)
                agent_info = agent.copy()
                agent_info['phase'] = level_idx + 1
                phase.append(agent_info)
            phases.append(phase)
        return phases

# --- HEALTH CHECK LOGIC (reuse from verify_all_health_checks.py) ---
import socket
import json

def get_health_check_url(agent):
    name = agent.get('name')
    # Port override for SystemDigitalTwin
    if name == "SystemDigitalTwin":
        host = "localhost"
        health_port = agent.get('health_check_port', 8100)
    else:
        host = agent.get('host', 'localhost')
        if host == "0.0.0.0":
            host = "localhost"
        port = agent.get('port')
        if port is None:
            return None
        health_port = agent.get('health_check_port', port + 1)
    return f"http://{host}:{health_port}/health"

def check_socket_connection(host, port, timeout):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_health(agent, timeout=HEALTH_CHECK_TIMEOUT):
    url = get_health_check_url(agent)
    if not url:
        return False
    host = url.split("://")[1].split(":")[0]
    port = int(url.split(":")[-1].split("/")[0])
    return check_socket_connection(host, port, timeout)

# --- AGENT STARTUP LOGIC ---
def start_agent(agent):
    script_path = agent['script_path']
    abs_script = (PROJECT_ROOT / "main_pc_code" / script_path).resolve()
    if not abs_script.exists():
        abs_script = (PROJECT_ROOT / script_path).resolve()
    if not abs_script.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return None
    log_file = LOGS_DIR / f"{agent['name']}.log"
    env = os.environ.copy()
    # Add agent-specific env vars if any
    if 'env_vars' in agent:
        env.update(agent['env_vars'])
    # Start agent in background
    proc = subprocess.Popen([PYTHON_EXEC, str(abs_script)], stdout=open(log_file, 'a'), stderr=subprocess.STDOUT, env=env)
    print(f"[STARTED] {agent['name']} (PID: {proc.pid}) -> {abs_script}")
    return proc

def verify_phase_health(phase_agents, retries=RETRIES, delay=RETRY_DELAY):
    agent_status = {agent['name']: False for agent in phase_agents}
    for attempt in range(1, retries + 1):
        print(f"  [HEALTH CHECK] Attempt {attempt}/{retries}...")
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_agent = {executor.submit(check_health, agent): agent for agent in phase_agents}
            for future in as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    healthy = future.result()
                    agent_status[agent['name']] = healthy
                except Exception as e:
                    print(f"    [ERROR] Health check failed for {agent['name']}: {e}")
        failed = [name for name, ok in agent_status.items() if not ok]
        if not failed:
            print("  [SUCCESS] All agents in this phase are healthy.")
            return True
        else:
            print(f"    [WAIT] Not healthy: {', '.join(failed)}. Retrying in {delay}s...")
            time.sleep(delay)
    print(f"  [FAIL] The following agents failed health check after {retries} retries: {', '.join([n for n, ok in agent_status.items() if not ok])}")
    return False

def main():
    print("[SYSTEM STARTUP] Loading configuration and resolving dependencies...")
    config = load_startup_config()
    resolver = DependencyResolver(config)
    phases = resolver.get_startup_phases()
    print(f"[SYSTEM STARTUP] {len(phases)} phases detected.")
    all_procs = []
    for idx, phase_agents in enumerate(phases):
        print(f"\n=== Starting Phase {idx+1} ({len(phase_agents)} agents) ===")
        procs = []
        for agent in phase_agents:
            proc = start_agent(agent)
            if proc:
                procs.append(proc)
                all_procs.append(proc)
        print(f"[INFO] Waiting {RETRY_DELAY}s for agents to initialize...")
        time.sleep(RETRY_DELAY)
        if not verify_phase_health(phase_agents):
            print(f"[SYSTEM STARTUP] Phase {idx+1} failed. Stopping system startup.")
            # Optionally: terminate all started processes
            for p in all_procs:
                p.terminate()
            sys.exit(1)
        print(f"[SYSTEM STARTUP] Phase {idx+1} complete.")
    print("\n[SYSTEM STARTUP] All phases complete. System is fully started.")

if __name__ == "__main__":
    main() 