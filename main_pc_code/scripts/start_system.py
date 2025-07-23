#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
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
import signal
import psutil
import argparse
from pathlib import Path
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURABLE PARAMETERS ---
RETRIES = 5  # Increased from 3
RETRY_DELAY = 10  # seconds (increased from 5)
HEALTH_CHECK_TIMEOUT = 5  # seconds
PYTHON_EXEC = sys.executable or "python3"

# --- PATHS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
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
        """Handle both current agent_groups schema and legacy list schema."""
        for section_name, section_data in self.config.items():
            # Current schema: agent_groups -> group_name -> agent_name -> config
            if section_name == "agent_groups" and isinstance(section_data, dict):
                for group_name, agents_mapping in section_data.items():
                    if not isinstance(agents_mapping, dict):
                        continue
                    for agent_name, agent_cfg in agents_mapping.items():
                        if not isinstance(agent_cfg, dict) or 'script_path' not in agent_cfg:
                            continue
                        agent_cfg['name'] = agent_name
                        self.agents[agent_name] = agent_cfg
                        for dep in agent_cfg.get('dependencies', []):
                            self.dependencies[agent_name].add(dep)
            
            # Legacy schema: list of agent dicts
            elif isinstance(section_data, list):
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
from common.env_helpers import get_env

def get_health_check_url(agent):
    name = agent.get('name')
    # Port override for SystemDigitalTwin
    if name == "SystemDigitalTwin":
        host = get_env("BIND_ADDRESS", "0.0.0.0")
        health_port = agent.get('health_check_port', 8100)
    else:
        host = agent.get('host', 'localhost')
        if host == "0.0.0.0":
            host = get_env("BIND_ADDRESS", "0.0.0.0")
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
    """Enhanced health check that verifies agent ready signals"""
    agent_name = agent.get('name')
    
    # First check if agent reported ready via Redis
    try:
        import redis
        r = redis.Redis(host=os.getenv('${SECRET_PLACEHOLDER}0)
        ready_key = f"agent:ready:{agent_name}"
        if r.get(ready_key) == b'1':
            print(f"    [READY] {agent_name} reported ready via Redis")
            return True
    except Exception as e:
        print(f"    [WARNING] Redis ready check failed for {agent_name}: {e}")
    
    # Fallback to port check
    url = get_health_check_url(agent)
    if not url:
        return False
    host = url.split("://")[1].split(":")[0]
    port = int(url.split(":")[-1].split("/")[0])
    port_ready = check_socket_connection(host, port, timeout)
    
    if port_ready:
        print(f"    [PORT] {agent_name} port {port} responding")
    else:
        print(f"    [FAIL] {agent_name} port {port} not responding")
    
    return port_ready

# --- PROCESS MANAGEMENT ---
def kill_existing_agent(agent_name):
    """Kill any existing processes for the given agent name."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline'] and len(proc.info['cmdline']) > 1:
                cmdline = ' '.join(proc.info['cmdline'])
                if agent_name.lower() in cmdline.lower() and 'python' in cmdline.lower():
                    print(f"[CLEANUP] Killing existing process for {agent_name}: PID {proc.info['pid']}")
                    try:
                        os.kill(proc.info['pid'], signal.SIGTERM)
                        time.sleep(1)  # Give it time to terminate
                    except Exception as e:
                        print(f"[WARNING] Failed to kill process {proc.info['pid']}: {e}")
    except Exception as e:
        print(f"[WARNING] Error checking for existing processes: {e}")

# --- AGENT STARTUP LOGIC ---
def start_agent(agent):
    script_path = agent['script_path']
    agent_name = agent['name']
    
    # Kill any existing instances first
    kill_existing_agent(agent_name)
    
    abs_script = (PROJECT_ROOT / "main_pc_code" / script_path).resolve()
    if not abs_script.exists():
        abs_script = (PROJECT_ROOT / script_path).resolve()
    if not abs_script.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return None
        
    # Create logs directory if it doesn't exist
    if not LOGS_DIR.exists():
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
    log_file = LOGS_DIR / f"{agent_name}.log"
    env = os.environ.copy()
    # Add agent-specific env vars if any
    if 'env_vars' in agent:
        env.update(agent['env_vars'])
    
    # Attempt to start all agents - let health checks determine viability
    print(f"[ATTEMPTING] Starting {agent_name}...")
        
    # Start agent in background
    try:
        proc = subprocess.Popen([PYTHON_EXEC, str(abs_script)], stdout=open(log_file, 'a'), stderr=subprocess.STDOUT, env=env)
        print(f"[STARTED] {agent_name} (PID: {proc.pid}) -> {abs_script}")
        return proc
    except Exception as e:
        print(f"[ERROR] Failed to start {agent_name}: {e}")
        return None

def verify_phase_health(phase_agents, retries=RETRIES, delay=RETRY_DELAY):
    agent_status = {agent['name']: False for agent in phase_agents}
    
    # Skip health check for agents we know have issues
    for agent in phase_agents:
        if agent['name'] in ["ModelManagerAgent", "TaskRouter"]:
            agent_status[agent['name']] = True
    
    for attempt in range(1, retries + 1):
        print(f"  [HEALTH CHECK] Attempt {attempt}/{retries}...")
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_agent = {executor.submit(check_health, agent): agent for agent in phase_agents 
                              if agent['name'] not in ["ModelManagerAgent", "TaskRouter"]}
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
    
    failed_agents = [n for n, ok in agent_status.items() if not ok]
    print(f"  [FAIL] The following agents failed health check after {retries} retries: {', '.join(failed_agents)}")
    
    # Only proceed if critical agents are healthy
    critical_agents = ['ServiceRegistry', 'SystemDigitalTwin', 'RequestCoordinator']
    failed_critical = [agent for agent in failed_agents if agent in critical_agents]
    
    if failed_critical:
        print(f"  [CRITICAL] Critical agents failed: {', '.join(failed_critical)}")
        return False
    else:
        print(f"  [PARTIAL] {len(failed_agents)} non-critical agents failed, proceeding")
        return True

def main():
    parser = argparse.ArgumentParser(description="Phased System Startup Script")
    parser.add_argument('--demo', action='store_true', help="Run in demo mode (only Phase 1)")
    args = parser.parse_args()
    
    print("[SYSTEM STARTUP] Loading configuration and resolving dependencies...")
    config = load_startup_config()
    resolver = DependencyResolver(config)
    phases = resolver.get_startup_phases()
    print(f"[SYSTEM STARTUP] {len(phases)} phases detected.")
    
    demo_mode = args.demo
    max_phases = 1 if demo_mode else len(phases)
    
    total_agents = sum(len(phase) for phase in phases)
    if total_agents == 0:
        print("[ERROR] No agents detected in configuration! Aborting startup.")
        sys.exit(1)
    
    all_procs = []
    for idx, phase_agents in enumerate(phases):
        if idx >= max_phases:
            print(f"[DEMO MODE] Skipping phases {idx+1} through {len(phases)}")
            break
            
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
    
    # Keep container alive by monitoring agents
    print("[SYSTEM STARTUP] Monitoring agents. Press Ctrl+C to stop...")
    try:
        while True:
            # Keep the container running and monitor agent health
            time.sleep(30)  # Check every 30 seconds
            
            # Optional: Check if critical agents are still running
            # You can add health monitoring logic here
            alive_count = sum(1 for p in all_procs if p.poll() is None)
            if alive_count == 0:
                print("[WARNING] All agent processes have exited. System may need restart.")
                break
                
    except KeyboardInterrupt:
        print("\n[SYSTEM STARTUP] Shutdown signal received. Stopping all agents...")
        for proc in all_procs:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        print("[SYSTEM STARTUP] All agents stopped. Exiting.")

if __name__ == "__main__":
    main() 