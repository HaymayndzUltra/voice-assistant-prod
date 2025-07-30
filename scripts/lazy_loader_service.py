#!/usr/bin/env python3
"""
LazyLoader Service - Phase 2
Monitors RequestCoordinator events and loads optional agents on-demand
"""

import os
import sys
import yaml
import time
import json
import threading
import subprocess
import logging
import requests
import zmq
from typing import Dict, Set, Optional, List
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('LazyLoader')

@dataclass
class AgentRequest:
    """Represents a request to load an agent"""
    agent_name: str
    requested_by: str
    timestamp: datetime
    priority: int = 0

class LazyLoaderService:
    """TODO: Add description for LazyLoaderService."""
    def __init__(self, config_path: str = "config/unified_startup_phase2.yaml"):
        self.config_path = config_path
        self.config = None
        self.loaded_agents: Set[str] = set()
        self.loading_agents: Set[str] = set()
        self.agent_processes: Dict[str, subprocess.Popen] = {}
        self.agent_info: Dict[str, Dict] = {}
        self.request_queue: List[AgentRequest] = []
        self.lock = threading.Lock()
        self.running = True

        # ZMQ setup for monitoring RequestCoordinator
        self.zmq_context = zmq.Context()
        self.coordinator_sub = None

        # Health check endpoint
        self.health_port = int(os.environ.get('HEALTH_CHECK_PORT', '8202'))

    def load_config(self):
        """Load and parse the YAML configuration"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")

            # Extract all optional agents
            self._extract_optional_agents()

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def _extract_optional_agents(self):
        """Extract all optional agents from configuration"""
        self.optional_agents = {}

        if 'agent_groups' not in self.config:
            return

        for group_name, group_agents in self.config['agent_groups'].items():
            for agent_name, agent_config in group_agents.items():
                # Check if agent is optional and has autoload: on_demand
                if not agent_config.get('required', True) and \
                   agent_config.get('autoload') == 'on_demand':
                    self.optional_agents[agent_name] = {
                        **agent_config,
                        'group': group_name,
                        'name': agent_name
                    }

        logger.info(f"Found {len(self.optional_agents)} optional agents available for lazy loading")

    def connect_to_coordinator(self):
        """Connect to RequestCoordinator for event monitoring"""
        try:
            self.coordinator_sub = self.zmq_context.socket(zmq.SUB)
            coordinator_endpoint = os.environ.get('COORDINATOR_ENDPOINT', 'tcp://localhost:7201')

            # Subscribe to agent request events
            self.coordinator_sub.connect(f"{coordinator_endpoint}_events")
            self.coordinator_sub.setsockopt_string(zmq.SUBSCRIBE, "agent_request:")
            self.coordinator_sub.setsockopt_string(zmq.SUBSCRIBE, "task:")

            logger.info(f"Connected to RequestCoordinator at {coordinator_endpoint}")

        except Exception as e:
            logger.error(f"Failed to connect to RequestCoordinator: {e}")
            raise

    def monitor_events(self):
        """Monitor events from RequestCoordinator"""
        while self.running:
            try:
                if self.coordinator_sub.poll(timeout=1000):  # 1 second timeout
                    message = self.coordinator_sub.recv_string()
                    self._process_event(message)

                # Process any pending requests
                self._process_request_queue()

            except Exception as e:
                logger.error(f"Error monitoring events: {e}")
                time.sleep(1)

    def _process_event(self, message: str):
        """Process an event from RequestCoordinator"""
        try:
            # Parse event format: "event_type:data"
            if ':' in message:
                event_type, data = message.split(':', 1)

                if event_type == "agent_request":
                    # Direct agent request
                    agent_data = json.loads(data)
                    agent_name = agent_data.get('agent_name')
                    if agent_name and agent_name in self.optional_agents:
                        self._queue_agent_load(agent_name, agent_data.get('requested_by', 'unknown'))

                elif event_type == "task":
                    # Task that might require specific agents
                    task_data = json.loads(data)
                    self._analyze_task_requirements(task_data)

        except Exception as e:
            logger.error(f"Error processing event: {e}")

    def _analyze_task_requirements(self, task_data: Dict):
        """Analyze a task to determine which agents might be needed"""
        task_type = task_data.get('type', '')
        task_meta = task_data.get('metadata', {})

        # Map task types to required agents
        task_agent_mapping = {
            'vision': ['FaceRecognitionAgent', 'VisionProcessingAgent'],
            'emotion': ['EmotionEngine', 'MoodTrackerAgent', 'EmpathyAgent'],
            'reasoning': ['ChainOfThoughtAgent', 'GoTToTAgent'],
            'learning': ['LearningOrchestrationService', 'LearningManager'],
            'code': ['CodeGenerator', 'Executor'],
            'translation': ['TranslationService', 'NLLBAdapter'],
            'tutoring': ['TutorAgent', 'TutoringAgent'],
            'web': ['UnifiedWebAgent', 'FileSystemAssistantAgent'],
            'dream': ['DreamWorldAgent', 'DreamingModeAgent'],
        }

        # Check task type
        for keyword, agents in task_agent_mapping.items():
            if keyword in task_type.lower() or keyword in str(task_meta).lower():
                for agent in agents:
                    if agent in self.optional_agents:
                        self._queue_agent_load(agent, f"task_{task_type}")

    def _queue_agent_load(self, agent_name: str, requested_by: str):
        """Queue an agent for loading"""
        with self.lock:
            # Check if already loaded or loading
            if agent_name in self.loaded_agents or agent_name in self.loading_agents:
                return

            # Add to queue
            request = AgentRequest(
                agent_name=agent_name,
                requested_by=requested_by,
                timestamp=datetime.now()
            )

            # Check if already in queue
            for req in self.request_queue:
                if req.agent_name == agent_name:
                    return

            self.request_queue.append(request)
            logger.info(f"Queued {agent_name} for loading (requested by {requested_by})")

    def _process_request_queue(self):
        """Process pending agent load requests"""
        with self.lock:
            if not self.request_queue:
                return

            # Process oldest request first
            request = self.request_queue.pop(0)

        # Load the agent
        self._load_agent(request.agent_name)

    def _load_agent(self, agent_name: str):
        """Load a single agent and its dependencies"""
        if agent_name in self.loaded_agents or agent_name in self.loading_agents:
            return

        logger.info(f"Loading agent: {agent_name}")

        with self.lock:
            self.loading_agents.add(agent_name)

        try:
            agent_config = self.optional_agents.get(agent_name)
            if not agent_config:
                logger.error(f"Agent {agent_name} not found in optional agents")
                return

            # Load dependencies first
            dependencies = agent_config.get('dependencies', [])
            for dep in dependencies:
                if dep in self.optional_agents and dep not in self.loaded_agents:
                    logger.info(f"Loading dependency {dep} for {agent_name}")
                    self._load_agent(dep)

            # Start the agent
            if self._start_agent(agent_name, agent_config):
                with self.lock:
                    self.loaded_agents.add(agent_name)
                    self.loading_agents.discard(agent_name)

                # Report to ObservabilityHub
                self._report_agent_loaded(agent_name)

                logger.info(f"Successfully loaded {agent_name}")
            else:
                logger.error(f"Failed to load {agent_name}")
                with self.lock:
                    self.loading_agents.discard(agent_name)

        except Exception as e:
            logger.error(f"Error loading agent {agent_name}: {e}")
            with self.lock:
                self.loading_agents.discard(agent_name)

    def _start_agent(self, agent_name: str, agent_config: Dict) -> bool:
        """Start a single agent process"""
        try:
            script_path = agent_config['script_path']

            # Check if script exists
            if not os.path.exists(script_path):
                logger.error(f"Script not found for {agent_name}: {script_path}")
                return False

            # Prepare environment
            env = os.environ.copy()

            # Substitute environment variables
            port = self._substitute_env_vars(str(agent_config.get('port', '')))
            health_port = self._substitute_env_vars(str(agent_config.get('health_check_port', '')))

            env['AGENT_NAME'] = agent_name
            env['AGENT_PORT'] = port
            env['HEALTH_CHECK_PORT'] = health_port

            # Add any agent-specific config
            if 'config' in agent_config:
                for key, value in agent_config['config'].items():
                    env_key = f"AGENT_CONFIG_{key.upper()}"
                    env[env_key] = str(value)

            # Start the process
            cmd = [sys.executable, script_path]
            logger.info(f"Starting {agent_name} on port {port} (health: {health_port})")

            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.agent_processes[agent_name] = process
            self.agent_info[agent_name] = {
                'port': port,
                'health_port': health_port,
                'script': script_path,
                'group': agent_config.get('group', 'unknown'),
                'load_time': datetime.now()
            }

            # Wait for agent to become healthy
            timeout = self.config.get('lazy_loader', {}).get('startup_timeout_seconds', 30)
            start_time = time.time()

            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    # Process died
                    stdout, stderr = process.communicate()
                    logger.error(f"Agent {agent_name} died during startup")
                    logger.error(f"STDOUT: {stdout}")
                    logger.error(f"STDERR: {stderr}")
                    return False

                # Check health
                if self._check_agent_health(agent_name):
                    return True

                time.sleep(2)

            logger.error(f"Agent {agent_name} failed to become healthy within {timeout}s")
            process.terminate()
            process.wait()
            return False

        except Exception as e:
            logger.error(f"Failed to start agent {agent_name}: {e}")
            return False

    def _check_agent_health(self, agent_name: str) -> bool:
        """Check if an agent is healthy"""
        agent_info = self.agent_info.get(agent_name)
        if not agent_info:
            return False

        health_port = agent_info['health_port']
        url = f"http://localhost:{health_port}/health"

        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def _substitute_env_vars(self, value: str) -> str:
        """Substitute environment variables in configuration values"""
        if isinstance(value, str) and '${' in value:
            # Handle PORT_OFFSET substitution
            if 'PORT_OFFSET' not in os.environ:
                os.environ['PORT_OFFSET'] = '0'

            import re
            pattern = r'\$\{([^}]+)\}'

            def replacer(match):
                var_expr = match.group(1)

                # Handle arithmetic expressions
                if '+' in var_expr:
                    parts = var_expr.split('+')
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        offset = parts[1].strip()
                        if var_name in os.environ and offset.isdigit():
                            return str(int(os.environ[var_name]) + int(offset))

                return os.environ.get(var_expr, match.group(0))

            return re.sub(pattern, replacer, value)
        return value

    def _report_agent_loaded(self, agent_name: str):
        """Report to ObservabilityHub that an agent was loaded"""
        try:
            obs_endpoint = os.environ.get('OBS_HUB_ENDPOINT', 'http://localhost:9000')
            url = f"{obs_endpoint}/metrics/agent_loaded"

            data = {
                'agent_name': agent_name,
                'timestamp': datetime.now().isoformat(),
                'loader': 'LazyLoader',
                'load_time': self.agent_info[agent_name]['load_time'].isoformat()
            }

            requests.post(url, json=data, timeout=2)

        except Exception as e:
            logger.debug(f"Failed to report to ObservabilityHub: {e}")

    def start_health_endpoint(self):
        """Start the health check endpoint"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json

        service = self

             """TODO: Add description for HealthHandler."""
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/health':
                    status = {
                        'status': 'healthy',
                        'service': 'LazyLoader',
                        'loaded_agents': list(service.loaded_agents),
                        'loading_agents': list(service.loading_agents),
                        'queue_size': len(service.request_queue),
                        'total_optional': len(service.optional_agents)
                    }

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(status).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logs

        server = HTTPServer(('0.0.0.0', self.health_port), HealthHandler)

        # Run in thread
        health_thread = threading.Thread(target=server.serve_forever)
        health_thread.daemon = True
        health_thread.start()

        logger.info(f"Health endpoint started on port {self.health_port}")

    def monitor_loaded_agents(self):
        """Monitor loaded agents and restart if they crash"""
        while self.running:
            try:
                time.sleep(30)  # Check every 30 seconds

                with self.lock:
                    agents_to_check = list(self.agent_processes.items())

                for agent_name, process in agents_to_check:
                    if process.poll() is not None:
                        # Agent crashed
                        logger.warning(f"Agent {agent_name} crashed (exit code: {process.returncode})")

                        with self.lock:
                            self.loaded_agents.discard(agent_name)
                            del self.agent_processes[agent_name]

                        # Re-queue for loading
                        self._queue_agent_load(agent_name, "auto_restart")

            except Exception as e:
                logger.error(f"Error monitoring agents: {e}")

    def run(self):
        """Main execution loop"""
        try:
            # Load configuration
            self.load_config()

            # Start health endpoint
            self.start_health_endpoint()

            # Connect to RequestCoordinator
            self.connect_to_coordinator()

            # Start monitoring thread
            monitor_thread = threading.Thread(target=self.monitor_loaded_agents)
            monitor_thread.daemon = True
            monitor_thread.start()

            logger.info("LazyLoader service started successfully")

            # Main event monitoring loop
            self.monitor_events()

        except KeyboardInterrupt:
            logger.info("Shutting down LazyLoader...")
            self.shutdown()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.shutdown()
            raise

    def shutdown(self):
        """Gracefully shutdown the service"""
        self.running = False

        # Stop all loaded agents
        for agent_name, process in self.agent_processes.items():
            if process.poll() is None:
                logger.info(f"Stopping {agent_name}...")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        # Cleanup ZMQ
        if self.coordinator_sub:
            self.coordinator_sub.close()
        self.zmq_context.term()

        logger.info("LazyLoader shutdown complete")

if __name__ == "__main__":
    service = LazyLoaderService()
    service.run()
