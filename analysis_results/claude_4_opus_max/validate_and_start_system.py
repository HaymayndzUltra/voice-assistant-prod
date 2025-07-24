#!/usr/bin/env python3
"""
Comprehensive system validation and startup script.
This script validates all fixes and starts the MainPC system in phases.
"""

import os
import sys
import time
import yaml
import subprocess
import ast
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path("/workspace")
MAINPC_ROOT = PROJECT_ROOT / "main_pc_code"
CONFIG_PATH = MAINPC_ROOT / "config" / "startup_config.yaml"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)


class SystemValidator:
    """Validates the system before startup."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.fixed_files = []
        
    def validate_syntax(self) -> bool:
        """Validate Python syntax in all agent files."""
        logger.info("Validating Python syntax in all agent files...")
        
        agent_dirs = [
            MAINPC_ROOT / "agents",
            MAINPC_ROOT / "services",
            MAINPC_ROOT / "FORMAINPC",
            MAINPC_ROOT / "scripts"
        ]
        
        error_count = 0
        checked_count = 0
        
        for agent_dir in agent_dirs:
            if not agent_dir.exists():
                continue
                
            for py_file in agent_dir.rglob("*.py"):
                if '__pycache__' in str(py_file) or '.bak' in str(py_file):
                    continue
                    
                checked_count += 1
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError as e:
                    error_count += 1
                    self.errors.append(f"Syntax error in {py_file}: {e}")
                    logger.error(f"❌ Syntax error in {py_file.name}: {e}")
                except Exception as e:
                    self.warnings.append(f"Could not check {py_file}: {e}")
                    
        logger.info(f"Checked {checked_count} files, found {error_count} syntax errors")
        return error_count == 0
    
    def validate_imports(self) -> bool:
        """Validate that all required imports are available."""
        logger.info("Validating required imports...")
        
        required_modules = [
            "zmq", "yaml", "redis", "psutil", "requests",
            "numpy", "torch", "transformers", "msgpack"
        ]
        
        missing = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)
                self.errors.append(f"Missing required module: {module}")
                
        if missing:
            logger.error(f"❌ Missing modules: {', '.join(missing)}")
            return False
            
        logger.info("✅ All required modules are available")
        return True
    
    def validate_config(self) -> bool:
        """Validate startup configuration."""
        logger.info("Validating startup configuration...")
        
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
                
            if 'agent_groups' not in config:
                self.errors.append("Missing 'agent_groups' in startup config")
                return False
                
            # Check for duplicate ports
            ports_used = {}
            health_ports_used = {}
            
            for group_name, agents in config['agent_groups'].items():
                for agent_name, agent_config in agents.items():
                    port = agent_config.get('port')
                    health_port = agent_config.get('health_check_port')
                    
                    if port:
                        if port in ports_used:
                            self.errors.append(
                                f"Port {port} conflict: {agent_name} and {ports_used[port]}"
                            )
                        ports_used[port] = agent_name
                        
                    if health_port:
                        if health_port in health_ports_used:
                            self.errors.append(
                                f"Health port {health_port} conflict: {agent_name} and {health_ports_used[health_port]}"
                            )
                        health_ports_used[health_port] = agent_name
                        
            logger.info(f"✅ Configuration validated: {len(ports_used)} agents configured")
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Failed to load config: {e}")
            return False
    
    def check_docker_services(self) -> bool:
        """Check if required Docker services are running."""
        logger.info("Checking Docker services...")
        
        try:
            # Check if Docker is running
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                self.errors.append("Docker is not running")
                return False
                
            # Check for required containers
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )
            
            running_containers = result.stdout.strip().split('\n')
            required_services = ["redis", "nats"]
            
            missing_services = []
            for service in required_services:
                if not any(service in container for container in running_containers):
                    missing_services.append(service)
                    
            if missing_services:
                self.warnings.append(f"Docker services not running: {', '.join(missing_services)}")
                logger.warning(f"⚠️  Missing Docker services: {', '.join(missing_services)}")
                
            logger.info("✅ Docker is available")
            return True
            
        except Exception as e:
            self.warnings.append(f"Could not check Docker: {e}")
            return True  # Don't fail if Docker check fails
    
    def generate_report(self) -> str:
        """Generate validation report."""
        report = []
        report.append("=" * 80)
        report.append("SYSTEM VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        if self.errors:
            report.append(f"❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                report.append(f"  - {error}")
            report.append("")
            
        if self.warnings:
            report.append(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                report.append(f"  - {warning}")
            report.append("")
            
        if not self.errors:
            report.append("✅ System validation PASSED!")
        else:
            report.append("❌ System validation FAILED!")
            
        return "\n".join(report)


class SystemStarter:
    """Starts the system in phases."""
    
    def __init__(self):
        self.config = None
        self.running_agents = {}
        
    def load_config(self):
        """Load startup configuration."""
        with open(CONFIG_PATH, 'r') as f:
            self.config = yaml.safe_load(f)
            
    def start_agent(self, agent_name: str, agent_config: dict) -> subprocess.Popen:
        """Start a single agent."""
        script_path = PROJECT_ROOT / agent_config['script_path']
        
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return None
            
        cmd = [
            sys.executable,
            str(script_path),
            "--name", agent_name,
            "--port", str(agent_config.get('port', 5000)),
            "--health-port", str(agent_config.get('health_check_port', 6000))
        ]
        
        log_file = LOGS_DIR / f"{agent_name.lower()}.log"
        
        with open(log_file, 'w') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                env={**os.environ, 'PYTHONPATH': str(PROJECT_ROOT)}
            )
            
        logger.info(f"Started {agent_name} (PID: {process.pid})")
        return process
    
    def check_agent_health(self, agent_name: str, health_port: int, timeout: int = 30) -> bool:
        """Check if an agent is healthy via HTTP health check."""
        url = f"http://localhost:{health_port}/health"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == 'healthy':
                        logger.info(f"✅ {agent_name} is healthy")
                        return True
            except:
                pass
            time.sleep(1)
            
        logger.error(f"❌ {agent_name} failed health check")
        return False
    
    def start_phase(self, phase_name: str, agents: list) -> bool:
        """Start all agents in a phase."""
        logger.info(f"\nStarting phase: {phase_name}")
        logger.info("-" * 60)
        
        # Start all agents in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            
            for agent_config in agents:
                agent_name = agent_config['name']
                future = executor.submit(self.start_agent, agent_name, agent_config)
                futures[future] = agent_name
                
            # Wait for all to start
            for future in as_completed(futures):
                agent_name = futures[future]
                process = future.result()
                if process:
                    self.running_agents[agent_name] = process
                    
        # Check health of all agents in phase
        all_healthy = True
        for agent_config in agents:
            agent_name = agent_config['name']
            if agent_name in self.running_agents:
                health_port = agent_config.get('health_check_port', 6000)
                if not self.check_agent_health(agent_name, health_port):
                    all_healthy = False
                    
        return all_healthy
    
    def start_system(self) -> bool:
        """Start the entire system in dependency order."""
        self.load_config()
        
        # Define startup phases
        phases = [
            ("Core Services", ["ServiceRegistry", "SystemDigitalTwin"]),
            ("Core Coordination", ["RequestCoordinator", "UnifiedSystemAgent", "ObservabilityHub"]),
            ("Model Management", ["ModelManagerSuite"]),
            ("Memory System", ["MemoryClient", "SessionMemoryAgent", "KnowledgeBase"]),
            ("Learning Services", ["LearningOrchestrationService", "LearningOpportunityDetector"]),
            ("Utility Services", ["CodeGenerator", "PredictiveHealthMonitor", "Executor"]),
            ("Language Processing", ["NLUAgent", "TranslationService", "Responder"]),
            ("Audio Interface", ["AudioCapture", "StreamingSpeechRecognition", "StreamingTTSAgent"]),
            ("Emotion System", ["EmotionEngine", "MoodTrackerAgent", "EmpathyAgent"])
        ]
        
        for phase_name, agent_names in phases:
            # Collect agent configs for this phase
            phase_agents = []
            
            for group_name, agents in self.config['agent_groups'].items():
                for agent_name, agent_config in agents.items():
                    if agent_name in agent_names:
                        agent_config['name'] = agent_name
                        phase_agents.append(agent_config)
                        
            if phase_agents:
                if not self.start_phase(phase_name, phase_agents):
                    logger.error(f"Failed to start phase: {phase_name}")
                    return False
                    
                # Wait between phases
                time.sleep(5)
                
        logger.info("\n✅ All phases started successfully!")
        return True
    
    def stop_all(self):
        """Stop all running agents."""
        logger.info("\nStopping all agents...")
        
        for agent_name, process in self.running_agents.items():
            try:
                process.terminate()
                logger.info(f"Stopped {agent_name}")
            except:
                pass
                
        # Wait for all to stop
        time.sleep(2)
        
        # Force kill any remaining
        for agent_name, process in self.running_agents.items():
            try:
                process.kill()
            except:
                pass


def main():
    """Main function."""
    print("=" * 80)
    print("MAINPC SYSTEM VALIDATION AND STARTUP")
    print("=" * 80)
    
    # Phase 1: Validation
    validator = SystemValidator()
    
    validation_steps = [
        ("Python Syntax", validator.validate_syntax),
        ("Required Imports", validator.validate_imports),
        ("Configuration", validator.validate_config),
        ("Docker Services", validator.check_docker_services)
    ]
    
    all_valid = True
    for step_name, step_func in validation_steps:
        logger.info(f"\nValidating: {step_name}")
        if not step_func():
            all_valid = False
            
    # Generate report
    report = validator.generate_report()
    print("\n" + report)
    
    # Save report
    report_path = PROJECT_ROOT / "validation_report.txt"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    if not all_valid:
        print("\n❌ Validation failed. Please fix errors before starting the system.")
        return 1
        
    # Phase 2: Ask to start system
    print("\n" + "=" * 80)
    response = input("Validation passed! Start the system? (y/n): ")
    
    if response.lower() != 'y':
        print("Startup cancelled.")
        return 0
        
    # Phase 3: Start system
    starter = SystemStarter()
    
    try:
        if starter.start_system():
            print("\n✅ System started successfully!")
            print("\nPress Ctrl+C to stop the system...")
            
            # Keep running
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        starter.stop_all()
        print("System stopped.")
        
    return 0


if __name__ == "__main__":
    sys.exit(main())