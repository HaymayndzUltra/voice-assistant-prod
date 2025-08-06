#!/usr/bin/env python3
"""
Modern Agent System Startup Script v2.0
=======================================
Based on current startup_config.yaml structure with proper agent groups.
Addresses Background Agent findings and removes all outdated references.
Enhanced with Universal Config Manager support.
"""

import os
import sys
import time
import subprocess
import signal
import psutil
import argparse
import redis
from pathlib import Path
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from common.utils.log_setup import configure_logging

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common.config_manager import load_unified_config, get_agents_by_machine, validate_config_consistency
from common.utils.path_manager import PathManager

# --- CONFIGURATION ---
RETRIES = 5
RETRY_DELAY = 15  # Increased for heavy containers
HEALTH_CHECK_TIMEOUT = 10
PYTHON_EXEC = sys.executable or "python3"

# --- PATHS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "main_pc_code" / "config" / "startup_config.yaml"
LOGS_DIR = PROJECT_ROOT / "logs"

# --- LOGGING SETUP ---
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SystemStartup")

class ModernDependencyResolver:
    """Handles dependency resolution based on current startup_config.yaml structure"""
    
    def __init__(self, unified_config):
        self.unified_config = unified_config
        self.agents = {}  # name -> agent dict with group info
        self.dependencies = defaultdict(set)  # name -> dependencies
        self.dependents = defaultdict(set)  # name -> dependents
        self.agent_groups = {}  # group_name -> [agent_names]
        self.extract_agents()
        self.build_dependency_graph()
    
    def extract_agents(self):
        """Extract agents from unified config structure"""
        # Get MainPC agents from unified config
        mainpc_agents = get_agents_by_machine(self.unified_config, 'mainpc')
        
        for agent_data in mainpc_agents:
            agent_name = agent_data['name']
            group_name = agent_data['group']
            
            # Store agent data
            self.agents[agent_name] = agent_data
            
            # Group agents by group
            if group_name not in self.agent_groups:
                self.agent_groups[group_name] = []
            self.agent_groups[group_name].append(agent_name)
            
            # Extract dependencies
            deps = agent_data.get('dependencies', [])
            for dep in deps:
                self.dependencies[agent_name].add(dep)
    
    def build_dependency_graph(self):
        """Build reverse dependency graph"""
        for agent_name, deps in self.dependencies.items():
            for dep in deps:
                self.dependents[dep].add(agent_name)
    
    def get_startup_phases(self):
        """Calculate startup phases using topological sort"""
        in_degree = {name: len(deps) for name, deps in self.dependencies.items()}
        
        # Initialize agents with no dependencies
        for name in self.agents:
            if name not in in_degree:
                in_degree[name] = 0
        
        queue = deque([name for name, count in in_degree.items() if count == 0])
        phases = []
        
        while queue:
            level_size = len(queue)
            current_phase = []
            
            for _ in range(level_size):
                agent_name = queue.popleft()
                agent_config = self.agents[agent_name].copy()
                agent_config['phase'] = len(phases) + 1
                current_phase.append(agent_config)
                
                # Update dependents
                for dependent in self.dependents[agent_name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            phases.append(current_phase)
        
        # Check for circular dependencies
        total_agents = sum(len(phase) for phase in phases)
        if total_agents != len(self.agents):
            missing = set(self.agents.keys()) - {agent['name'] for phase in phases for agent in phase}
            logger.warning(f"Circular dependencies detected for agents: {missing}")
        
        return phases
    
    def get_agents_by_group(self, group_name):
        """Get all agents for a specific group"""
        return [self.agents[name] for name in self.agent_groups.get(group_name, [])]

class HealthChecker:
    """Standardized health checker using unified health checking system"""
    
    def __init__(self):
        self.redis_client = None
        self._connect_redis()
    
    def _connect_redis(self):
        """Connect to Redis for ready signal checks"""
        try:
            redis_host = os.getenv('REDIS_HOST', 'redis')
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=6379, 
                db=0, 
                decode_responses=True,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_host}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def check_agent_health(self, agent, timeout=HEALTH_CHECK_TIMEOUT):
        """Use standardized health checking for comprehensive agent health"""
        agent_name = agent['name']
        port = agent.get('port', 0)
        
        try:
            # Import here to avoid circular imports during startup
            from common.health.standardized_health import check_agent_health
            
            # Perform standardized health check
            health = check_agent_health(agent_name, port)
            
            # Log detailed health information
            logger.info(f"    📊 {agent_name} health: {health.status.value}")
            
            # Log individual check results
            for check_name, result in health.checks.items():
                status_icon = "✅" if result else "❌"
                logger.info(f"      {status_icon} {check_name}")
            
            # Consider healthy or degraded as acceptable
            is_healthy = health.status.value in ['healthy', 'degraded']
            
            if is_healthy:
                logger.info(f"    ✅ {agent_name}: Health check passed ({health.status.value})")
            else:
                logger.warning(f"    ❌ {agent_name}: Health check failed ({health.status.value})")
                if health.error_message:
                    logger.warning(f"      Error: {health.error_message}")
            
            return is_healthy
            
        except Exception as e:
            # Fallback to legacy check if standardized check fails
            logger.warning(f"Standardized health check failed for {agent_name}: {e}")
            return self._legacy_health_check(agent, timeout)
    
    def _legacy_health_check(self, agent, timeout):
        """Fallback to legacy health checking"""
        agent_name = agent['name']
        
        # Check 1: Redis ready signal
        if self.redis_client:
            try:
                ready_key = f"agent:ready:{agent_name}"
                ready_data = self.redis_client.get(ready_key)
                if ready_data:
                    logger.info(f"    ✅ {agent_name}: Ready signal found")
                    return True
            except Exception as e:
                logger.warning(f"Redis ready signal check failed: {e}")
        
        # Check 2: Port connectivity
        port = agent.get('port')
        if port:
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    logger.info(f"    🔌 {agent_name}: Port {port} responding")
                    return True
                else:
                    logger.warning(f"    ❌ {agent_name}: Port {port} not responding")
            except Exception as e:
                logger.warning(f"Port check failed for {agent_name}: {e}")
        
        return False

class ProcessManager:
    """Manages agent processes with proper cleanup"""
    
    def __init__(self):
        self.processes = []
        self.agent_pids = {}
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._cleanup_handler)
        signal.signal(signal.SIGINT, self._cleanup_handler)
    
    def _cleanup_handler(self, signum, frame):
        """Clean shutdown of all processes"""
        logger.info("Shutdown signal received. Cleaning up...")
        self.cleanup_all()
        sys.exit(0)
    
    def kill_existing_processes(self, agent_name):
        """Kill any existing processes for agent"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline'] and len(proc.info['cmdline']) > 1:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if agent_name.lower() in cmdline.lower() and 'python' in cmdline.lower():
                        logger.info(f"🧹 Killing existing {agent_name} process: PID {proc.info['pid']}")
                        try:
                            proc.terminate()
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        except Exception as e:
                            logger.warning(f"Failed to kill process {proc.info['pid']}: {e}")
        except Exception as e:
            logger.warning(f"Error checking for existing processes: {e}")
    
    def start_agent(self, agent):
        """Start an individual agent process"""
        agent_name = agent['name']
        script_path = agent['script_path']
        
        # Clean up any existing instances
        self.kill_existing_processes(agent_name)
        
        # Resolve script path using PathManager (fixes script validation bug)
        abs_script = PathManager.resolve_script(script_path)
        if abs_script is None or not abs_script.exists():
            logger.error(f"❌ Script not found for {agent_name}: {script_path}")
            return None
        
        # Setup logging
        if not LOGS_DIR.exists():
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        log_file = LOGS_DIR / fstr(PathManager.get_logs_dir() / "{agent_name}.log")
        
        # Setup environment
        env = os.environ.copy()
        env.update({
            'AGENT_NAME': agent_name,
            'AGENT_PORT': str(agent.get('port', 0)),
            'HEALTH_CHECK_PORT': str(agent.get('health_check_port', 0)),
            'AGENT_GROUP': agent.get('group', 'unknown')
        })
        
        # Add agent-specific env vars
        if 'env_vars' in agent:
            env.update(agent['env_vars'])
        
        try:
            # Start process
            proc = subprocess.Popen(
                [PYTHON_EXEC, str(abs_script)],
                stdout=open(log_file, 'a'),
                stderr=subprocess.STDOUT,
                env=env
            )
            
            self.processes.append(proc)
            self.agent_pids[agent_name] = proc.pid
            
            logger.info(f"🚀 Started {agent_name} (PID: {proc.pid}) -> {abs_script}")
            return proc
            
        except Exception as e:
            logger.error(f"❌ Failed to start {agent_name}: {e}")
            return None
    
    def cleanup_all(self):
        """Clean up all managed processes"""
        for proc in self.processes:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                logger.warning(f"Error cleaning up process: {e}")

class ModernSystemStartup:
    """Main system startup orchestrator"""
    
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path = config_path
        self.config = None
        self.resolver = None
        self.health_checker = HealthChecker()
        self.process_manager = ProcessManager()
        
        self.load_config()
    
    def load_config(self):
        """Load startup configuration using unified config manager"""
        try:
            # Load unified config
            self.unified_config = load_unified_config(str(self.config_path))
            
            # Validate config for issues
            issues = validate_config_consistency(self.unified_config)
            if issues:
                logger.warning(f"⚠️  Configuration issues found:")
                for issue in issues[:5]:  # Show first 5 issues
                    logger.warning(f"   - {issue}")
            
            # Create dependency resolver with unified config
            self.resolver = ModernDependencyResolver(self.unified_config)
            logger.info(f"✅ Loaded unified config with {len(self.resolver.agents)} agents in {len(self.resolver.agent_groups)} groups")
            
        except Exception as e:
            logger.error(f"❌ Failed to load config from {self.config_path}: {e}")
            sys.exit(1)
    
    def start_phase(self, phase_agents, phase_num):
        """Start all agents in a phase"""
        logger.info(f"\n🚀 === STARTING PHASE {phase_num} ({len(phase_agents)} agents) ===")
        
        # Group agents by group for logging
        by_group = defaultdict(list)
        for agent in phase_agents:
            by_group[agent['group']].append(agent['name'])
        
        for group, agents in by_group.items():
            logger.info(f"  📁 {group}: {', '.join(agents)}")
        
        # Start all agents in parallel
        started_procs = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_agent = {
                executor.submit(self.process_manager.start_agent, agent): agent 
                for agent in phase_agents
            }
            
            for future in as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    proc = future.result()
                    if proc:
                        started_procs.append((agent, proc))
                except Exception as e:
                    logger.error(f"❌ Error starting {agent['name']}: {e}")
        
        logger.info(f"⏳ Started {len(started_procs)} agents, waiting {RETRY_DELAY}s for initialization...")
        time.sleep(RETRY_DELAY)
        
        return started_procs
    
    def verify_phase_health(self, phase_agents, phase_num):
        """Verify health of all agents in a phase"""
        logger.info(f"🔍 === HEALTH CHECK PHASE {phase_num} ===")
        
        agent_status = {}
        
        for attempt in range(1, RETRIES + 1):
            logger.info(f"  🩺 Health check attempt {attempt}/{RETRIES}...")
            
            # Check all agents in parallel
            with ThreadPoolExecutor(max_workers=8) as executor:
                future_to_agent = {
                    executor.submit(self.health_checker.check_agent_health, agent): agent
                    for agent in phase_agents
                }
                
                for future in as_completed(future_to_agent):
                    agent = future_to_agent[future]
                    try:
                        healthy = future.result()
                        agent_status[agent['name']] = healthy
                    except Exception as e:
                        logger.error(f"    ❌ Health check error for {agent['name']}: {e}")
                        agent_status[agent['name']] = False
            
            # Check results
            healthy_agents = [name for name, status in agent_status.items() if status]
            unhealthy_agents = [name for name, status in agent_status.items() if not status]
            
            logger.info(f"  📊 Healthy: {len(healthy_agents)}, Unhealthy: {len(unhealthy_agents)}")
            
            if not unhealthy_agents:
                logger.info(f"  ✅ All agents in Phase {phase_num} are healthy!")
                return True
            
            # Check if any required agents failed
            failed_required = []
            for agent in phase_agents:
                if agent['name'] in unhealthy_agents and agent.get('required', True):
                    failed_required.append(agent['name'])
            
            if failed_required and attempt == RETRIES:
                logger.error(f"  💥 Required agents failed: {failed_required}")
                return False
            
            if unhealthy_agents:
                logger.warning(f"    ⏳ Unhealthy agents: {', '.join(unhealthy_agents)}")
                if attempt < RETRIES:
                    logger.info(f"    ⏰ Retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
        
        # Final decision
        critical_failures = [
            agent['name'] for agent in phase_agents 
            if agent['name'] in agent_status and not agent_status[agent['name']] and agent.get('required', True)
        ]
        
        if critical_failures:
            logger.error(f"  ❌ Critical failures in Phase {phase_num}: {critical_failures}")
            return False
        else:
            logger.warning(f"  ⚠️  Phase {phase_num} has some issues but no critical failures. Proceeding...")
            return True
    
    def run_container_group(self, group_name):
        """Run agents for a specific container group (for Docker mode)"""
        logger.info(f"🐳 === CONTAINER GROUP MODE: {group_name} ===")
        
        agents = self.resolver.get_agents_by_group(group_name)
        if not agents:
            logger.error(f"❌ No agents found for group: {group_name}")
            return False
        
        logger.info(f"📋 Starting {len(agents)} agents for group {group_name}")
        
        # Start all agents
        for agent in agents:
            self.process_manager.start_agent(agent)
        
        # Wait for initialization
        time.sleep(RETRY_DELAY)
        
        # Health check
        if self.verify_phase_health(agents, 1):
            logger.info(f"✅ Container group {group_name} started successfully!")
            return True
        else:
            logger.error(f"❌ Container group {group_name} failed health checks!")
            return False
    
    def run_full_system(self, max_phases=None):
        """Run the complete system startup"""
        logger.info("🌟 === FULL SYSTEM STARTUP ===")
        
        phases = self.resolver.get_startup_phases()
        logger.info(f"📊 System has {len(phases)} dependency phases")
        
        if max_phases:
            phases = phases[:max_phases]
            logger.info(f"🎯 Running only first {max_phases} phases (demo mode)")
        
        total_agents = sum(len(phase) for phase in phases)
        logger.info(f"🔢 Total agents to start: {total_agents}")
        
        # Start each phase
        for phase_num, phase_agents in enumerate(phases, 1):
            self.start_phase(phase_agents, phase_num)
            
            if not self.verify_phase_health(phase_agents, phase_num):
                logger.error(f"💥 Phase {phase_num} failed! Aborting system startup.")
                return False
        
        logger.info("\n🎉 === SYSTEM STARTUP COMPLETE ===")
        return True
    
    def monitor_system(self):
        """Monitor system health after startup"""
        logger.info("👁️  === SYSTEM MONITORING MODE ===")
        logger.info("Press Ctrl+C to shutdown system...")
        
        try:
            while True:
                time.sleep(30)
                
                # Check if any critical processes died
                alive_count = sum(1 for p in self.process_manager.processes if p.poll() is None)
                total_count = len(self.process_manager.processes)
                
                if alive_count == 0:
                    logger.warning("⚠️  All agent processes have exited!")
                    break
                elif alive_count < total_count:
                    logger.warning(f"⚠️  Some agents died: {alive_count}/{total_count} still running")
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Shutdown signal received")
        
        self.process_manager.cleanup_all()
        logger.info("✅ System shutdown complete")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Modern AI System Startup v2.0")
    parser.add_argument('--group', help='Start specific container group only')
    parser.add_argument('--phases', type=int, help='Limit to first N phases (demo mode)')
    parser.add_argument('--config', help='Custom config file path')
    args = parser.parse_args()
    
    # Initialize startup system
    config_path = Path(args.config) if args.config else CONFIG_PATH
    startup = ModernSystemStartup(config_path)
    
    try:
        if args.group:
            # Container group mode
            success = startup.run_container_group(args.group)
            if success:
                startup.monitor_system()
            else:
                sys.exit(1)
        else:
            # Full system mode
            success = startup.run_full_system(args.phases)
            if success:
                startup.monitor_system()
            else:
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"💥 Fatal error during startup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 