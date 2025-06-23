import os
import sys
import yaml
import time
import socket
import signal
import logging
import subprocess
from graphlib import TopologicalSorter, CycleError

# Add project root to Python path for common_utils import
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import common utilities
try:
    from common_utils.env_loader import get_env, get_ip
    from common_utils.zmq_helper import check_zmq_port
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False
    print("[WARNING] common_utils modules not found. Using default environment settings.")

# --- Configuration ---
CONFIG_PATH = "config/startup_config.yaml"
LOGS_DIR = "logs"
HEALTH_CHECK_TIMEOUT = 120  # seconds
HEALTH_CHECK_INTERVAL = 2   # seconds
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432

# Define active agent directories (exclude archive/reference folders)
AGENT_DIRS = ["agents", "agents/core_agents", "agents/ForPC2"]

# --- Global State ---
child_processes = []

# --- Logging Setup ---
def setup_logging():
    """Sets up the main logger for the launcher."""
    os.makedirs(os.path.join(BASE_DIR, LOGS_DIR), exist_ok=True)
    log_file = os.path.join(BASE_DIR, LOGS_DIR, "system_launcher.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("PC2SystemLauncher")

logger = setup_logging()

# --- Pre-flight Checks ---
def check_postgres():
    """Performs a pre-flight check to ensure PostgreSQL is accessible."""
    logger.info(f"Performing pre-flight check for PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}...")
    try:
        with socket.create_connection((POSTGRES_HOST, POSTGRES_PORT), timeout=5):
            logger.info("PostgreSQL connection successful. Pre-flight check passed.")
            return True
    except (socket.error, ConnectionRefusedError):
        logger.critical("--- CRITICAL: PostgreSQL IS NOT RUNNING ---")
        logger.critical(f"Could not connect to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}.")
        logger.critical("The AI system's memory components will fail to initialize.")
        logger.critical("Please ensure the PostgreSQL database server is running before starting the system.")
        return False

# --- Core Logic ---
def load_config():
    """Loads the canonical YAML configuration."""
    config_file = os.path.join(BASE_DIR, CONFIG_PATH)
    logger.info(f"Loading canonical configuration from: {config_file}")
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"FATAL: Configuration file not found at {config_file}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"FATAL: Error parsing YAML configuration: {e}")
        return None

def build_dependency_graph(agents_config):
    """Builds a dependency graph from the agent configurations."""
    return {agent['name']: set(agent.get('dependencies', [])) for agent in agents_config}

def calculate_startup_batches(graph):
    """Calculates the startup order in batches using TopologicalSorter."""
    try:
        ts = TopologicalSorter(graph)
        startup_order = tuple(ts.static_order())
        logger.info(f"Calculated startup order: {startup_order}")
        
        batches = []
        launched_agents = set()
        remaining_agents = set(startup_order)

        while remaining_agents:
            batch = {agent for agent in remaining_agents if graph[agent].issubset(launched_agents)}
            if not batch:
                logger.error(f"FATAL: Dependency issue. Cannot find next batch. Launched: {launched_agents}, Remaining: {remaining_agents}")
                return None
            
            batches.append(list(batch))
            launched_agents.update(batch)
            remaining_agents.difference_update(batch)
        
        logger.info(f"Successfully calculated startup batches: {batches}")
        return batches
    except CycleError as e:
        logger.error(f"FATAL: A dependency cycle was detected in the configuration: {e.args[1]}")
        return None

def launch_agent(agent_config):
    """Launches a single agent as a subprocess."""
    name = agent_config['name']
    relative_script_path = agent_config['script_path']
    script_path = os.path.join(BASE_DIR, relative_script_path)
    log_file_path = os.path.join(BASE_DIR, LOGS_DIR, f"{name.replace(' ', '_')}.log")

    if not os.path.exists(script_path):
        logger.error(f"Agent '{name}': Script not found at {script_path}. Skipping.")
        return None

    env = os.environ.copy()
    project_root = os.path.dirname(BASE_DIR)
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{env.get('PYTHONPATH', '')}"
    
    # Add common_utils to PYTHONPATH
    common_utils_path = os.path.join(project_root, "common_utils")
    if os.path.exists(common_utils_path):
        env["PYTHONPATH"] = f"{common_utils_path}{os.pathsep}{env['PYTHONPATH']}"
    
    logger.info(f"Launching agent: {name}")
    logger.info(f"  - Script: {script_path}")
    logger.info(f"  - Log: {log_file_path}")

    try:
        with open(log_file_path, 'w') as log_file:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=BASE_DIR,
                env=env
            )
        child_processes.append(process)
        logger.info(f"Agent '{name}' started with PID: {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to launch agent '{name}': {e}")
        return None

def check_agent_health(agent_config):
    """Checks if an agent is healthy by probing its TCP port."""
    host = agent_config.get('host', '127.0.0.1')
    port = agent_config['port']
    name = agent_config['name']
    
    # Use environment variables for host if available
    if host == "0.0.0.0" and USE_COMMON_UTILS:
        host = get_ip("pc2")
    
    try:
        if USE_COMMON_UTILS and "zmq" in agent_config.get('protocol', '').lower():
            is_healthy = check_zmq_port(host, port)
        else:
            with socket.create_connection((host, port), timeout=1):
                is_healthy = True
                
        if is_healthy:
            logger.info(f"Health check PASSED for {name} at {host}:{port}")
            return True
        else:
            logger.debug(f"Health check pending for {name} at {host}:{port}...")
            return False
    except (socket.error, ConnectionRefusedError):
        logger.debug(f"Health check pending for {name} at {host}:{port}...")
        return False

def check_batch_health(batch, agents_map):
    """Monitors a batch of agents until all are healthy or a timeout is reached."""
    start_time = time.time()
    healthy_agents = set()
    agents_in_batch = set(batch)

    while time.time() - start_time < HEALTH_CHECK_TIMEOUT:
        for agent_name in list(agents_in_batch - healthy_agents):
            agent_config = agents_map[agent_name]
            if check_agent_health(agent_config):
                healthy_agents.add(agent_name)
        
        if healthy_agents == agents_in_batch:
            logger.info(f"All agents in batch {batch} are healthy.")
            return True
            
        time.sleep(HEALTH_CHECK_INTERVAL)

    failed_agents = agents_in_batch - healthy_agents
    logger.error(f"FATAL: Health check timed out after {HEALTH_CHECK_TIMEOUT} seconds.")
    logger.error(f"Failed to confirm health for agents: {list(failed_agents)}")
    return False

def graceful_shutdown(signum, frame):
    """Handles graceful shutdown of all child processes."""
    logger.warning(f"Shutdown signal ({signal.strsignal(signum)}) received. Terminating all agent processes...")
    for p in reversed(child_processes):
        if p.poll() is None:
            try:
                logger.info(f"Terminating process with PID: {p.pid}")
                p.terminate()
            except Exception as e:
                logger.error(f"Error terminating process {p.pid}: {e}")
    
    # Wait for processes to terminate
    for p in child_processes:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"Process {p.pid} did not terminate gracefully. Killing.")
            p.kill()

    logger.info("All agent processes have been shut down. Exiting.")
    sys.exit(0)

def free_up_ports(agents_config):
    """Attempt to free up ports that might be in use by previous runs."""
    ports = []
    for agent in agents_config:
        if "port" in agent:
            ports.append(str(agent["port"]))

    if not ports:
        return

    logger.info(f"Checking if ports are in use: {', '.join(ports)}")
    try:
        # On Windows, use netstat instead of lsof
        if sys.platform == "win32":
            cmd = ["netstat", "-ano"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("netstat command failed, skipping port check")
                return

            # Parse output to find PIDs
            pids_by_port = {}
            for line in result.stdout.strip().split("\n"):
                if "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        addr_port = parts[1]
                        if ":" in addr_port:
                            port = addr_port.split(":")[-1]
                            if port in ports:
                                pid = parts[-1]
                                pids_by_port[port] = pid

            # Kill processes
            for port, pid in pids_by_port.items():
                logger.info(f"Killing process {pid} using port {port}")
                try:
                    subprocess.run(["taskkill", "/F", "/PID", pid], check=False)
                except Exception as e:
                    logger.error(f"Error killing process {pid}: {e}")
        else:
            # On Unix-like systems, use lsof
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
                logger.info(f"Killing processes using required ports: {pids}")
                for pid in pids:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass  # Process already gone
    except FileNotFoundError:
        logger.warning("Port checking command not found, skipping port check")
    except Exception as e:
        logger.error(f"Error checking ports: {e}")

def main():
    """Main function to orchestrate the system launch."""
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    if not check_postgres():
        logger.warning("Proceeding without PostgreSQL connection. Some components may fail.")

    config = load_config()
    if not config:
        logger.critical("Failed to load configuration. Exiting.")
        sys.exit(1)

    agents_config = config.get('agents', [])
    if not agents_config:
        logger.critical("No agents defined in configuration. Exiting.")
        sys.exit(1)

    # Free up ports before starting
    free_up_ports(agents_config)

    # Build dependency graph and calculate startup batches
    graph = build_dependency_graph(agents_config)
    batches = calculate_startup_batches(graph)
    if not batches:
        logger.critical("Failed to calculate startup batches. Exiting.")
        sys.exit(1)

    # Create a mapping of agent name to agent config
    agents_map = {agent['name']: agent for agent in agents_config}

    # Launch agents in batches
    for i, batch in enumerate(batches, 1):
        logger.info(f"Launching batch {i} of {len(batches)}: {batch}")
        batch_processes = {}

        for agent_name in batch:
            agent_config = agents_map[agent_name]
            process = launch_agent(agent_config)
            if process:
                batch_processes[agent_name] = process

        # Wait for all agents in this batch to become healthy
        if not check_batch_health(batch, agents_map):
            logger.critical("Failed to confirm health for all agents in batch. Shutting down.")
            graceful_shutdown(signal.SIGTERM, None)
            sys.exit(1)

    logger.info("All agents successfully launched and verified healthy.")
    logger.info("System is now running. Press Ctrl+C to shut down.")

    # Keep the main process running until interrupted
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        graceful_shutdown(signal.SIGINT, None)

if __name__ == "__main__":
    main()
