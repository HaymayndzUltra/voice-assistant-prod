#!/usr/bin/env python3
from __future__ import annotations
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


# Import path manager for containerization-friendly paths
import sys
import os

# --- Bootstrap PYTHONPATH with project root so that `common.*` imports resolve
# even before PathManager is available.  We compute it as two directories up
# from this file (main_pc_code/<this_file>).  This fixes ModuleNotFoundError for
# `common.utils.path_manager` when the script is executed directly.  (issue
# #startup-002)

from pathlib import Path as _PathBootstrap
_project_root_bootstrap = _PathBootstrap(__file__).resolve().parent.parent
if str(_project_root_bootstrap) not in sys.path:
    sys.path.insert(0, str(_project_root_bootstrap))

# After bootstrap, it is safe to import PathManager for richer path handling.
from common.utils.path_manager import PathManager

# Ensure the project root is at the front of sys.path for subsequent dynamic
# imports.  This replaces the previous invalid `get_project_root()` call.
project_root_path = str(PathManager.get_project_root())
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)
from pathlib import Path
from typing import Any, Dict, List, Tuple
from graphlib import TopologicalSorter, CycleError
import argparse

# Unified configuration loader (v3)
try:
    from common.utils.unified_config_loader import get_config
    USE_UNIFIED_CONFIG = True
except ImportError:
    USE_UNIFIED_CONFIG = False

# Fallback YAML for explicit file load
import yaml  # PyYAML
import subprocess
import time
import socket
import signal
import re
from common.env_helpers import get_env

# Add project root to Python path for common_utils import
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities
try:
    from common_utils.env_loader import get_env, get_ip
    USE_COMMON_UTILS = True
except ImportError as e:
    print(f"Import error: {e}")
    USE_COMMON_UTILS = False
    print("[WARNING] common_utils.env_loader not found. Using default environment settings.")

CONFIG_REL_PATH = Path(PathManager.join_path("config", "startup_config.yaml"))

# Define active agent directories (exclude archive/reference folders)
AGENT_DIRS = ["agents", "src", "FORMAINPC"]


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
    """Extract all agent dictionaries that contain a `script_path` key and enrich
    them with additional metadata (absolute path + originating *group*).

    This helper is container-aware: it stores the YAML *agent group* name in the
    resulting dict so that the launcher can filter agents per container via the
    new `--groups` CLI flag.
    """
    consolidated: List[Dict[str, Any]] = []

    def _process_section(value, group_name: str | None = None):
        # Accept either a list of agent dicts **or** a dict keyed by agent name
        if isinstance(value, list):
            iterable = value
        elif isinstance(value, dict):
            iterable = []
            for k, v in value.items():
                if isinstance(v, dict):
                    iterable.append(v | {"name": k})
                elif isinstance(v, str) and "script_path" in str(v):
                    iterable.append({"name": k, "script_path": v})
        else:
            return

        for entry in iterable:
            if not (isinstance(entry, dict) and "script_path" in entry):
                continue

            if "name" not in entry:
                entry["name"] = entry.get("agent_name") or entry.get("id") or "unknown"

            # Record originating YAML group for later filtering
            if group_name:
                entry["group"] = group_name

            relative_path = Path(entry["script_path"])
            project_root = PathManager.get_project_root()
            entry["absolute_script_path"] = str((project_root / relative_path).resolve())

            consolidated.append(entry)

    # v3 config (MainPC) – agents nested under `agent_groups`
    if "agent_groups" in config and isinstance(config["agent_groups"], dict):
        for _group_name, group_list in config["agent_groups"].items():
            _process_section(group_list, _group_name)

    # PC2 config keeps a flat list under `pc2_services`
    if "pc2_services" in config and isinstance(config["pc2_services"], list):
        _process_section(config["pc2_services"], "pc2_services")

    # Legacy fall-back – iterate other top-level sections
    for section_name, section_value in config.items():
        if section_name in ("agent_groups", "pc2_services"):
            continue
        _process_section(section_value, section_name)

    return consolidated


# ---------------------------------------------------------------------------
# Port validation helpers
# ---------------------------------------------------------------------------


def _expand_port_value(value: Any) -> int:
    """Expand expressions like '${PORT_OFFSET}+7200' into final int using env."""
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Unsupported port value type: {type(value)}")

    # Replace ${VAR} with its env value or 0 if missing
    import re, os

    def _replace(match):
        var = match.group(1)
        return os.environ.get(var, "0")

    expr = re.sub(r"\${([^}]+)}", _replace, value)
    # Support "+" arithmetic (simple VAR+1234)
    if "+" in expr:
        parts = expr.split("+")
        try:
            base = int(parts[0]) if parts[0].strip() else 0
            offset = int(parts[1])
            return base + offset
        except ValueError:
            pass  # fallthrough
    try:
        return int(expr)
    except ValueError:
        raise ValueError(f"Unable to parse port value: {value}")


def validate_unique_ports(agents: List[Dict[str, Any]]):
    """Raise RuntimeError if any port or health port duplicates are found."""
    port_map: Dict[int, str] = {}
    duplicates: List[Tuple[int, str, str]] = []

    for agent in agents:
        for key in ("port", "health_check_port"):
            if key in agent:
                try:
                    p = _expand_port_value(agent[key])
                except ValueError as e:
                    print(f"[WARNING] {e} in agent {agent.get('name')}")
                    continue
                if p in port_map:
                    duplicates.append((p, port_map[p], agent.get("name")))
                else:
                    port_map[p] = agent.get("name")

    if duplicates:
        msgs = [f"Port {p} duplicated by {a1} and {a2}" for p, a1, a2 in duplicates]
        raise RuntimeError("Duplicate port assignments detected:\n" + "\n".join(msgs))


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
            # Use environment variables for host if available
            host = agent.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
            if host == "0.0.0.0" and USE_COMMON_UTILS:
                host = get_ip("main_pc")
            port = _expand_port_value(agent.get("port"))
            if check_port_is_open(host, port):
                healthy.add(name)
                remaining.pop(name, None)
        if remaining:
            time.sleep(2)

    success = not remaining
    failed = list(remaining.keys())
    return success, failed


# --------------------------- Launching -------------------------------------

def launch_agent(agent_cfg: Dict[str, Any], base_dir: Path, project_root: Path, logs_dir: Path, dry_run: bool = False) -> subprocess.Popen:
    """Launch a single agent process and return the `subprocess.Popen` handle.

    Stdout and stderr are redirected to a per-agent log file within `logs_dir`.
    The PYTHONPATH for the subprocess includes both the project root and the
    `main_pc_code` directory so that intra-project imports work seamlessly.
    
    If dry_run is True, only check if the agent file exists and has health check implementation.
    """
    script_path = agent_cfg["absolute_script_path"]
    
    if dry_run:
        # Check if the file exists
        if not os.path.exists(script_path):
            print(f"[WARNING] Agent file not found: {script_path}")
            return None
        
        # Check if the file has health check implementation
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                has_health_check = False
                
                # Check for health check patterns
                health_check_patterns = [
                    r'def\s+_start_health',
                    r'def\s+_health_check',
                    r'health_socket\s*=',
                    r'\.bind\(.*health_port',
                    r'\.bind\(.*\+\s*1\)',  # Common pattern where health port is main port + 1
                ]
                
                for pattern in health_check_patterns:
                    if re.search(pattern, content):
                        has_health_check = True
                        break
                
                # Check for base class inheritance that might provide health check
                if "BaseAgent" in content and ("super().__init__" in content or "super()" in content):
                    has_health_check = True
                
                if has_health_check:
                    print(f"✅ {agent_cfg['name']} has health check implementation")
                else:
                    print(f"❌ {agent_cfg['name']} does not have health check implementation")
                
                return None
        except Exception as e:
            print(f"[ERROR] Failed to check health implementation for {agent_cfg['name']}: {e}")
            return None
    
    # Route agent stdout/stderr to individual log files under logs_dir
    log_file = logs_dir / f"{agent_cfg.get('name', 'unknown_agent')}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(log_file, "a", buffering=1)  # line-buffered

    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}:{base_dir}:{pythonpath}" if pythonpath else f"{project_root}:{base_dir}"
    
    # Add common_utils to PYTHONPATH
    common_utils_path = project_root / "common_utils"
    if common_utils_path.exists():
        env["PYTHONPATH"] = f"{common_utils_path}:{env['PYTHONPATH']}"

    # Add agent-specific environment variables, if any
    if "env_vars" in agent_cfg and isinstance(agent_cfg["env_vars"], dict):
        for key, value in agent_cfg["env_vars"].items():
            env[key] = str(value)  # Ensure all values are strings

    cmd = [sys.executable, script_path]
    if "port" in agent_cfg:
        expanded_port = _expand_port_value(agent_cfg["port"])
        cmd.extend(["--port", str(expanded_port)])

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
    """Attempt to free up ports that might be in use by previous runs.

    Uses lsof to find processes using the ports, and kills them.
    """
    ports = []
    for agent in agents:
        if "port" in agent:
            ports.append(str(agent["port"]))

    if not ports:
        return

    print(f"Checking if ports are in use: {', '.join(ports)}")
    try:
        lsof_cmd = ["lsof", "-i", "tcp:" + ",".join(ports)]
        result = subprocess.run(lsof_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # No processes found using these ports
            return

        # Parse output to find PIDs
        lines = result.stdout.strip().split("\n")[1:]  # Skip header
        pids = set()
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    pids.add(int(parts[1]))
                except ValueError:
                    continue

        # Kill processes
        if pids:
            print(f"Killing processes using required ports: {pids}")
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass  # Process already gone
    except FileNotFoundError:
        print("lsof command not found, skipping port check")
    except Exception as e:
        print(f"Error checking ports: {e}")


def main() -> None:
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Launch and monitor agents from configuration")
    parser.add_argument("--dry-run", action="store_true", help="Check agents without launching them")
    parser.add_argument("--config", type=str, default=None, help="Path to configuration file")
    parser.add_argument("--groups", type=str, default=None,
                        help="Comma-separated list of YAML agent-group names to launch (e.g. core_services,gpu_infrastructure)")
    parser.add_argument("--agent-names", type=str, default=None,
                        help="Comma-separated list of explicit agent names to launch (overrides --groups)")
    args = parser.parse_args()
    
    # Determine the base directory (where this script is located)
    base_dir = Path(__file__).resolve().parent
    config_path = Path(args.config) if args.config else base_dir / CONFIG_REL_PATH
    project_root = base_dir.parent

    # Load configuration
    if args.config:
        config_path = Path(args.config)
        # Check if this is a v3 config file, use unified loader for proper machine filtering
        if config_path.name.endswith('v3.yaml') or 'v3' in config_path.name:
            print(f"Loading v3 config with machine filtering: {config_path}")
            config = get_config()
        else:
            print(f"Loading legacy config directly: {config_path}")
            config = load_config(config_path)
    elif USE_UNIFIED_CONFIG:
        config = get_config()
    else:
        config = load_config(config_path)

    # Extract and consolidate agent entries
    agents = consolidate_agent_entries(config, base_dir)

    # Optional filtering by container group or agent names
    if args.groups:
        wanted_groups = {g.strip() for g in args.groups.split(',') if g.strip()}
        agents = [a for a in agents if a.get("group") in wanted_groups]

    if args.agent_names:
        wanted_names = {n.strip() for n in args.agent_names.split(',') if n.strip()}
        agents = [a for a in agents if a.get("name") in wanted_names]

    if not agents:
        print("[ERROR] No agents match the provided --groups/--agent-names filter", file=sys.stderr)
        sys.exit(1)

    # Validate unique ports early to fail fast
    try:
        validate_unique_ports(agents)
    except RuntimeError as e:
        print(f"\nPORT VALIDATION ERROR:\n{e}", file=sys.stderr)
        sys.exit(1)

    # Print summary information
    print(f"Launching {len(agents)} agent entries after filtering.")
    for i, agent in enumerate(agents, 1):
        print(f"{i:2d}. {agent.get('name', 'Unknown'):<30} {agent.get('script_path', 'No script path')}")

    # Build dependency graph
    graph = build_dependency_graph(agents)
    print("\nDependency Graph:")
    for agent, deps in graph.items():
        if deps:
            print(f"{agent:<30} depends on: {', '.join(deps)}")
        else:
            print(f"{agent:<30} has no dependencies")

    # Calculate startup batches
    try:
        batches = calculate_startup_batches(graph)
        print("\nStartup Batches:")
        for i, batch in enumerate(batches, 1):
            print(f"Batch {i}: {', '.join(batch)}")
    except CycleError as e:
        print(f"\nERROR: Dependency cycle detected: {e}", file=sys.stderr)
        sys.exit(1)

    # Create a mapping of agent name to agent config
    agent_map = {agent["name"]: agent for agent in agents}
    
    if args.dry_run:
        print("\nDRY RUN MODE - Checking agent health implementations without launching")
        missing_health_check = []
        
        for batch in batches:
            for name in batch:
                agent_cfg = agent_map[name]
                launch_agent(agent_cfg, base_dir, project_root, base_dir / "logs", dry_run=True)
        
        if missing_health_check:
            print("\nAgents missing health check implementation:")
            for name in missing_health_check:
                print(f"❌ {name}")
            print("\nRecommendation: Add health check implementations to these agents.")
            print("Use scripts/add_health_check_implementation.py to add health checks.")
        else:
            print("\n✅ All agents have health check implementations!")
        
        return

    # Set up signal handlers for graceful shutdown
    # Container-specific logs directory – e.g. logs/core_services
    if args.groups:
        "_".join(sorted(wanted_groups))
    elif args.agent_names:
        pass

    processes: Dict[str, subprocess.Popen] = {}

    def signal_handler(sig, frame):
        print(f"\nReceived signal {sig}, shutting down...")
        shutdown_processes(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create logs directory
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Free up ports
    free_up_ports(agents)

    # Launch agents in batches
    for i, batch in enumerate(batches, 1):
        print(f"\nLaunching Batch {i}: {', '.join(batch)}")
        batch_agents = [agent_map[name] for name in batch]

        # Launch all agents in this batch
        for agent_cfg in batch_agents:
            name = agent_cfg["name"]
            print(f"Starting {name}...")
            proc = launch_agent(agent_cfg, base_dir, project_root, logs_dir)
            processes[name] = proc

        # Wait for all agents in this batch to become healthy
        print(f"Waiting for Batch {i} agents to become healthy...")
        success, failed = wait_for_batch_healthy(batch_agents)
        if not success:
            print(f"ERROR: Failed to start agents: {', '.join(failed)}", file=sys.stderr)
            print_failed_agent_logs(failed, logs_dir)
            shutdown_processes(processes)
            sys.exit(1)

    print("\nAll agents started successfully!")
    print("Press Ctrl+C to shut down all agents.")

    # Keep the main process running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        shutdown_processes(processes)


if __name__ == "__main__":
    main()
