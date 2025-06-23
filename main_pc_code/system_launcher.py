#!/usr/bin/env python3
"""
Path-Aware System Launcher

Phase 1: Loads the YAML startup configuration, resolves each agent's relative
`script_path` into an absolute path (relative to this file's directory), and
prints summary information for verification.

Future phases will add dependency analysis, batching, launching, and health
checks.

Constraints honoured:
• Read-only – no subprocesses are started.
• Python 3 and PyYAML required.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from graphlib import TopologicalSorter, CycleError

import yaml  # PyYAML
import subprocess
import os
import time
import socket
import signal
import re


CONFIG_REL_PATH = Path("config/startup_config.yaml")


def load_config(config_path: Path) -> Dict[str, Any]:
    """Load the YAML configuration and return it as a Python dictionary."""
    if not config_path.is_file():
        print(f"[ERROR] Configuration file not found at: {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        print(f"[ERROR] Failed to parse YAML: {exc}", file=sys.stderr)
        sys.exit(1)


def consolidate_agent_entries(config: Dict[str, Any], base_dir: Path) -> List[Dict[str, Any]]:
    """Extract all agent dictionaries that contain a `script_path` key.

    For each agent found, add/overwrite the key `absolute_script_path` with the
    resolved absolute path.
    """
    consolidated: List[Dict[str, Any]] = []

    for section_name, section_value in config.items():
        if not isinstance(section_value, list):
            # Skip non-list sections (e.g. `environment`, `resource_limits`, etc.).
            continue

        for entry in section_value:
            if isinstance(entry, dict) and "script_path" in entry:
                relative_path = Path(entry["script_path"])
                absolute_path = (base_dir / relative_path).resolve()
                entry["absolute_script_path"] = str(absolute_path)
                consolidated.append(entry)

    return consolidated


# ---------------------------------------------------------------------------
# TODO: Build dependency graph from the agent list.
# TODO: Determine the correct startup order (batches) based on dependencies.
# TODO: Implement agent launching logic using the absolute_script_path.
# TODO: Implement a dynamic health check system.
# ---------------------------------------------------------------------------

def build_dependency_graph(agents: List[Dict[str, Any]]) -> Dict[str, set[str]]:
    """Return a mapping of agent name -> set of dependency names."""
    graph: Dict[str, set[str]] = {}
    for agent in agents:
        name = agent.get("name")
        deps = set(agent.get("dependencies", []))
        graph[name] = deps
    return graph


def calculate_startup_batches(graph: Dict[str, set[str]]) -> List[List[str]]:
    """Return a list of batches where each batch contains agents that can start in parallel."""
    ts = TopologicalSorter(graph)
    ts.prepare()
    batches: List[List[str]] = []
    while ts.is_active():
        ready = list(ts.get_ready())
        if ready:
            batches.append(ready)
            ts.done(*ready)
    return batches


# --------------------------- Health Checking -------------------------------

def check_port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to (host, port) succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionError):
        return False


def wait_for_batch_healthy(batch_agents: List[Dict[str, Any]], timeout_seconds: int = 120) -> Tuple[bool, List[str]]:
    """Wait until all agents in the batch respond on their TCP ports or timeout.

    Returns (success, failed_agents).
    """
    start = time.time()
    healthy: set[str] = set()
    remaining = {agent["name"]: agent for agent in batch_agents}

    while time.time() - start < timeout_seconds and remaining:
        for name, agent in list(remaining.items()):
            host = agent.get("host", "localhost")
            port = int(agent.get("port"))
            if check_port_is_open(host, port):
                healthy.add(name)
                remaining.pop(name, None)
        if remaining:
            time.sleep(2)

    success = not remaining
    failed = list(remaining.keys())
    return success, failed


# --------------------------- Launching -------------------------------------

def launch_agent(agent_cfg: Dict[str, Any], base_dir: Path, project_root: Path, logs_dir: Path) -> subprocess.Popen:
    """Launch a single agent process and return the `subprocess.Popen` handle.

    Stdout and stderr are redirected to a per-agent log file within `logs_dir`.
    The PYTHONPATH for the subprocess includes both the project root and the
    `main_pc_code` directory so that intra-project imports work seamlessly.
    """
    script_path = agent_cfg["absolute_script_path"]
    log_file = logs_dir / f"{agent_cfg['name']}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(log_file, "a", buffering=1)  # line-buffered

    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}:{base_dir}:{pythonpath}" if pythonpath else f"{project_root}:{base_dir}"

    # Add agent-specific environment variables, if any
    if "env_vars" in agent_cfg and isinstance(agent_cfg["env_vars"], dict):
        for key, value in agent_cfg["env_vars"].items():
            env[key] = str(value)  # Ensure all values are strings

    cmd = [sys.executable, script_path]
    if "port" in agent_cfg:
        cmd.extend(["--port", str(agent_cfg["port"])])

    # Add dynamic parameters from the 'params' dictionary
    if "params" in agent_cfg and isinstance(agent_cfg["params"], dict):
        for key, value in agent_cfg["params"].items():
            cmd.extend([f"--{key}", str(value)])

    return subprocess.Popen(cmd, cwd=str(base_dir), stdout=log_fh, stderr=subprocess.STDOUT, env=env)


def shutdown_processes(processes: Dict[str, subprocess.Popen]) -> None:
    """Terminate all running child processes."""
    for proc in processes.values():
        if proc.poll() is None:
            proc.terminate()
    # Optionally, wait a short moment so they terminate gracefully
    time.sleep(2)


def print_failed_agent_logs(failed_agents: List[str], logs_dir: Path):
    """Prints the last 20 lines of the log file for each failed agent."""
    print("\n--- FAILED AGENT LOGS ---", file=sys.stderr)
    for name in failed_agents:
        log_file = logs_dir / f"{name}.log"
        print(f"--- Log for {name} ({log_file}) ---", file=sys.stderr)
        if log_file.exists() and log_file.stat().st_size > 0:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-20:]:
                        print(line.strip(), file=sys.stderr)
            except Exception as e:
                print(f"[ERROR] Could not read log file: {e}", file=sys.stderr)
        elif not log_file.exists():
            print("[Log file not found]", file=sys.stderr)
        else:
            print("[Log file is empty]", file=sys.stderr)
        print("-" * (len(name) + 24), file=sys.stderr)


def free_up_ports(agents: List[Dict[str, Any]]):
    """
    Checks all ports required by agents and their health checks. If a port is
    in use, it attempts to terminate the owning process using the `ss` command.
    """
    print("--- Checking and freeing required ports ---")
    ports_to_check = set()
    for agent in agents:
        port = agent.get("port")
        if port:
            ports_to_check.add(int(port))
            ports_to_check.add(int(port) + 1)  # Health check port

    try:
        result = subprocess.run(["ss", "-lntp"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print("[WARNING] `ss` command failed. Cannot check/free ports.", file=sys.stderr)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return

        pids_to_kill = set()
        lines = result.stdout.strip().split('\n')
        # Regex to find port and pid from ss output
        line_re = re.compile(r'LISTEN\s+\d+\s+\d+\s+.*?:(\d+)\s+.*users:\(\(.*?,pid=(\d+),.*?\)\)')

        for line in lines:
            match = line_re.search(line)
            if match:
                port, pid = map(int, match.groups())
                if port in ports_to_check:
                    pids_to_kill.add((pid, port))

        for pid, port in pids_to_kill:
            print(f"Port {port} is in use by PID {pid}. Terminating process...")
            try:
                os.kill(pid, signal.SIGKILL)
                print(f"Process {pid} terminated.")
            except ProcessLookupError:
                print(f"Process {pid} not found, likely already terminated.")
            except Exception as e:
                print(f"[ERROR] Failed to terminate process {pid}: {e}", file=sys.stderr)

    except FileNotFoundError:
        print("[WARNING] `ss` command not found. Cannot check/free ports.", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] An error occurred while checking ports: {e}", file=sys.stderr)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent
    config_path = base_dir / CONFIG_REL_PATH

    config: Dict[str, Any] = load_config(config_path)
    agents: List[Dict[str, Any]] = consolidate_agent_entries(config, base_dir)

    # Ensure all required ports are free before launching agents.
    free_up_ports(agents)

    graph = build_dependency_graph(agents)

    try:
        batches = calculate_startup_batches(graph)
    except CycleError as ce:
        # ce.args[1] contains the list of nodes involved in the cycle
        cycle_nodes = ", ".join(ce.args[1]) if len(ce.args) > 1 else str(ce)
        print(f"[ERROR] Circular dependency detected among: {cycle_nodes}", file=sys.stderr)
        sys.exit(1)

    # --- Launch Agents --------------------------------------------------------
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    agent_lookup = {a["name"]: a for a in agents}
    processes: Dict[str, subprocess.Popen] = {}

    total_batches = len(batches)
    for idx, batch in enumerate(batches, start=1):
        print(f"--- Launching Batch {idx} of {total_batches} ---")
        for name in batch:
            agent_cfg = agent_lookup[name]
            proc = launch_agent(agent_cfg, base_dir, project_root, logs_dir)
            processes[name] = proc
            print(f"Started {name} (pid {proc.pid}) -> log: {logs_dir / (name + '.log')}")

        batch_agents = [agent_lookup[name] for name in batch]
        success, failed_agents = wait_for_batch_healthy(batch_agents)
        if not success:
            print(f"[ERROR] Batch {idx} failed to become healthy. Failed agents: {', '.join(failed_agents)}", file=sys.stderr)
            print_failed_agent_logs(failed_agents, logs_dir)
            shutdown_processes(processes)
            sys.exit(1)

        print(f"Batch {idx} healthy.")

        if idx < total_batches:
            print("Proceeding to next batch...")

    print("All batches launched. Launcher will remain running. Press Ctrl+C to terminate.")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Terminating child processes...")
        for proc in processes.values():
            proc.terminate()
        print("Shutdown complete.")


if __name__ == "__main__":
    main()
