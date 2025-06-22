import os
import sys
import yaml
import time
import socket
import signal
import logging
import subprocess
from graphlib import TopologicalSorter, CycleError

# --- Configuration ---
CONFIG_PATH = "config/startup_config.yaml"
LOGS_DIR = "logs"
HEALTH_CHECK_TIMEOUT = 120  # seconds
HEALTH_CHECK_INTERVAL = 2   # seconds
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432

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
    
    try:
        with socket.create_connection((host, port), timeout=1):
            logger.info(f"Health check PASSED for {name} at {host}:{port}")
            return True
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

def main():
    """Main function to orchestrate the system launch."""
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    if not check_postgres():
        sys.exit(1)

    config = load_config()
    if not config or 'pc2_services' not in config:
        logger.error("Invalid or empty configuration. Aborting.")
        sys.exit(1)

    agents_config = config['pc2_services']
    agents_map = {agent['name']: agent for agent in agents_config}
    
    dependency_graph = build_dependency_graph(agents_config)
    startup_batches = calculate_startup_batches(dependency_graph)

    if not startup_batches:
        sys.exit(1)

    logger.info("--- PC2 AGENT LAUNCH SEQUENCE INITIATED ---")
    for i, batch in enumerate(startup_batches):
        logger.info(f"--- Starting Batch {i+1}/{len(startup_batches)}: {batch} ---")
        
        for agent_name in batch:
            launch_agent(agents_map[agent_name])
        
        logger.info(f"Batch {i+1} launched. Performing health checks...")
        if not check_batch_health(batch, agents_map):
            logger.error("A batch failed to become healthy. Aborting startup.")
            graceful_shutdown(signal.SIGTERM, None)
            sys.exit(1)

    logger.info("--- ALL PC2 AGENTS LAUNCHED SUCCESSFULLY ---")
    logger.info("System is operational. Monitoring for termination signals.")
    
    # Keep the launcher running to hold child processes
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
