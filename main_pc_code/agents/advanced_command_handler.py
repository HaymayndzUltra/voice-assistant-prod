"""
Advanced Command Handler for Voice Assistant
--------------------------------------------

Extends the custom command handler with advanced features:
1. Command Sequences - Execute multiple commands in sequence
2. Script Execution - Run local Python/Bash scripts
3. Domain-specific command modules
4. Advanced coordination with Jarvis Memory Agent
"""
from common.utils.path_manager import PathManager
import sys
import os
MAIN_PC_CODE_DIR = PathManager.get_main_pc_code()
if str(MAIN_PC_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))
import json
import logging
import time
import sys
import os
import re
import uuid
import importlib.util
from typing import Dict, List, Any, Optional, Tuple
from common.core.base_agent import BaseAgent
from main_pc_code.agents.needtoverify.custom_command_handler import CustomCommandHandler
from common.config_manager import load_unified_config
config = load_unified_config(os.path.join(PathManager.get_project_root(), 'main_pc_code', 'config', 'startup_config.yaml'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AdvancedCommandHandler')
ZMQ_EXECUTOR_PORT = 6001
ZMQ_COORDINATOR_PORT = 5590
ZMQ_REQUEST_TIMEOUT = 5000
SCRIPT_TYPES = {'.py': 'python', '.sh': 'bash', '.ps1': 'powershell -ExecutionPolicy Bypass -File', '.bat': 'cmd /c', '.js': 'node'}

class AdvancedCommandHandler(CustomCommandHandler, BaseAgent):
    """
    Extends the custom command handler with advanced features for Phase 4 Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""

    def __init__(self):
        """
        Initialize the advanced command handler
        
        Args:
            zmq_port: Port for Jarvis Memory Agent
            executor_port: Port for Executor Agent
            coordinator_port: Port for RequestCoordinator
        """
        self.config = config
        agent_name = str(self.config.get('name', 'AdvancedCommandHandler'))
        agent_port = int(self.config.get('port', 5598))
        super().__init__(port=agent_port)
        self.name = agent_name
        self.running = True
        self.start_time = time.time()
        executor_port = int(self.config.get('executor_port', ZMQ_EXECUTOR_PORT))
        coordinator_port = int(self.config.get('coordinator_port', ZMQ_COORDINATOR_PORT))
        _host = self.config.get('host', 'localhost')
        self.executor_socket = self.context.socket(zmq.REQ)
        self.executor_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.executor_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        executor_host = os.environ.get('EXECUTOR_HOST', _host)
        self.executor_socket.connect(f'tcp://{executor_host}:{executor_port}')
        logger.info(f'Connected to Executor Agent on port {executor_port}')
        self.coordinator_socket = self.context.socket(zmq.REQ)
        self.coordinator_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.coordinator_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.coordinator_socket.connect(f'tcp://{_host}:{coordinator_port}')
        logger.info(f'Connected to RequestCoordinator on port {coordinator_port}')
        self.running_processes = {}
        self.domain_modules = {}
        self.available_domains = []
        self.load_domain_modules()
        self.registration_patterns = getattr(self, 'registration_patterns', [])
        self.registration_patterns.extend([re.compile('create\\s+(?:a\\s+)?sequence\\s+(?:called\\s+)?["\\\']?([^"\\\']+)["\\\']?\\s+to\\s+run\\s+(.*)', re.IGNORECASE), re.compile('create\\s+(?:a\\s+)?script\\s+command\\s+(?:called\\s+)?["\\\']?([^"\\\']+)["\\\']?\\s+to\\s+run\\s+(?:file\\s+)?["\\\']?([^"\\\']+)["\\\']?', re.IGNORECASE), re.compile('gumawa\\s+ng\\s+sequence\\s+na\\s+["\\\']?([^"\\\']+)["\\\']?\\s+para\\s+i-run\\s+(.*)', re.IGNORECASE)])
        self.commands_processed = 0

    def load_domain_modules(self):
        """Load domain-specific command modules"""
        domains_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'domain_modules')
        if not os.path.exists(domains_dir):
            os.makedirs(domains_dir)
            logger.info(f'Created domains directory: {domains_dir}')
            return
        domain_files = [f for f in os.listdir(domains_dir) if f.endswith('.py') and (not f.startswith('__'))]
        for domain_file in domain_files:
            domain_name = domain_file[:-3]
            try:
                module_path = os.path.join(domains_dir, domain_file)
                spec = importlib.util.spec_from_file_location(domain_name, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, 'get_commands') and callable(module.get_commands):
                        self.domain_modules[domain_name] = module
                        self.available_domains.append(domain_name)
                        logger.info(f'Loaded domain module: {domain_name}')
                    else:
                        logger.warning(f'Domain module {domain_name} does not have required interface')
            except Exception as e:
                logger.error(f'Error loading domain module {domain_name}: {e}')
        logger.info(f"Loaded {len(self.available_domains)} domain modules: {', '.join(self.available_domains)}")

    def get_domain_commands(self, domain_name: str) -> List[Dict[str, Any]]:
        """
        Get commands from a specific domain module
        
        Args:
            domain_name: Name of the domain module
            
        Returns:
            List of command definitions for the domain
        """
        if domain_name not in self.domain_modules:
            logger.warning(f'Domain module {domain_name} not found')
            return []
        try:
            return self.domain_modules[domain_name].get_commands()
        except Exception as e:
            logger.error(f'Error getting commands from domain {domain_name}: {e}')
            return []

    def get_available_domains(self) -> List[str]:
        """
        Get list of available domain modules
        
        Returns:
            List of domain module names
        """
        return self.available_domains

    def toggle_domain(self, domain_name: str, enabled: bool=True) -> bool:
        """
        Enable or disable a domain module
        
        Args:
            domain_name: Name of the domain module
            enabled: Whether to enable or disable the domain
            
        Returns:
            True if successful, False otherwise
        """
        if domain_name not in self.domain_modules:
            logger.warning(f'Domain module {domain_name} not found')
            return False
        try:
            request = {'action': 'update_memory', 'memory_type': 'system_config', 'memory_id': f'domain_{domain_name}', 'memory_data': {'name': domain_name, 'enabled': enabled, 'last_updated': time.time()}}
            self.memory_socket.send_string(json.dumps(request))
            response = self.memory_socket.recv_string()
            result = json.loads(response)
            if result.get('status') == 'ok':
                logger.info(f"Domain {domain_name} {('enabled' if enabled else 'disabled')}")
                return True
            else:
                logger.warning(f"Failed to update domain status: {result.get('reason', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f'Error toggling domain {domain_name}: {e}')
            return False

    def detect_command_registration(self, text: str) -> Optional[Tuple[str, str, str]]:
        """
        Detect command registration intent in text with extended support for sequences and scripts
        
        Args:
            text: Text to check for command registration
            
        Returns:
            Tuple of (trigger_phrase, action_type, action_value) if command registration detected,
            None otherwise
        """
        base_result = super().detect_command_registration(text)
        if base_result:
            (trigger_phrase, action_value) = base_result
            if 'alias' in text.lower():
                action_type = 'alias_for'
            else:
                action_type = 'execute_command'
            return (trigger_phrase, action_type, action_value)
        for pattern in self.registration_patterns[-3:]:
            match = pattern.search(text)
            if match:
                trigger_phrase = match.group(1).strip()
                action_value = match.group(2).strip()
                if 'sequence' in pattern.pattern:
                    action_type = 'sequence'
                elif 'script' in pattern.pattern:
                    action_type = 'script'
                else:
                    action_type = 'execute_command'
                return (trigger_phrase, action_type, action_value)
        return None

    def register_command(self, trigger_phrase: str, action_type: str, action_value: str, user_id: str='default') -> bool:
        """
        Register a new custom command with extended types support
        
        Args:
            trigger_phrase: Phrase that triggers the command
            action_type: Type of action ("alias_for", "execute_command", "sequence", "script")
            action_value: Value associated with the action type
            user_id: User ID to register command for
            
        Returns:
            True if command was registered successfully, False otherwise
        """
        valid_action_types = ['alias_for', 'execute_command', 'sequence', 'script']
        if action_type not in valid_action_types:
            logger.warning(f'Invalid action type: {action_type}')
            return False
        if action_type == 'script':
            script_path = os.path.expanduser(action_value)
            if not os.path.exists(script_path):
                logger.warning(f'Script path does not exist: {script_path}')
                return False
            action_value = os.path.abspath(script_path)
        if action_type == 'sequence':
            try:
                commands = self._parse_sequence(action_value)
                if not commands:
                    logger.warning(f'Invalid sequence format: {action_value}')
                    return False
                action_value = json.dumps(commands)
            except Exception as e:
                logger.error(f'Error parsing sequence: {e}')
                return False
        try:
            memory_data = {'type': 'custom_command', 'trigger_phrase': trigger_phrase, 'action_type': action_type, 'action_value': action_value, 'created_at': time.time(), 'memory_id': str(uuid.uuid4())}
            request = {'action': 'store_memory', 'user_id': user_id, 'memory': memory_data}
            self.memory_socket.send_string(json.dumps(request))
            response = self.memory_socket.recv_string()
            result = json.loads(response)
            if result.get('status') == 'ok':
                if user_id not in self.command_cache:
                    self.command_cache[user_id] = {}
                self.command_cache[user_id][trigger_phrase.lower()] = memory_data
                logger.info(f"Registered {action_type} command '{trigger_phrase}' for user {user_id}")
                return True
            else:
                logger.warning(f"Failed to store memory: {result.get('reason', 'Unknown error')}")
                return False
        except Exception as e:
            logger.error(f'Error registering command: {e}')
            return False

    def _parse_sequence(self, sequence_text: str) -> List[str]:
        """
        Parse a sequence text into individual commands
        
        Args:
            sequence_text: Text describing the sequence (e.g., "command1 then command2 then command3")
            
        Returns:
            List of individual commands
        """
        separators = [' then ', ' and then ', ' after that ', ' followed by ', ' tapos ', ' at ']
        commands = [sequence_text]
        for separator in separators:
            if separator in sequence_text.lower():
                commands = [cmd.strip() for cmd in sequence_text.lower().split(separator)]
                commands = [cmd for cmd in commands if cmd]
                break
        return commands

    def execute_command(self, command_data: Dict[str, Any], user_id: str='default') -> Dict[str, Any]:
        """
        Execute a command based on its action type
        
        Args:
            command_data: Command data dictionary
            user_id: User ID the command belongs to
            
        Returns:
            Dictionary with execution results
        """
        action_type = command_data.get('action_type')
        action_value = command_data.get('action_value')
        trigger_phrase = command_data.get('trigger_phrase')
        logger.info(f"Executing {action_type} command '{trigger_phrase}' with value: {action_value}")
        if action_type == 'alias_for':
            target_command = self.get_command(action_value, user_id)
            if not target_command:
                return {'status': 'error', 'message': f"Target command '{action_value}' not found"}
            return self.execute_command(target_command, user_id)
        elif action_type == 'execute_command':
            return {'status': 'success', 'message': f'Executing command: {action_value}', 'command': action_value}
        elif action_type == 'sequence':
            try:
                commands = json.loads(action_value)
                return self._execute_sequence(commands, user_id)
            except Exception as e:
                logger.error(f'Error executing sequence: {e}')
                return {'status': 'error', 'message': f'Error executing sequence: {str(e)}'}
        elif action_type == 'script':
            return self._execute_script(action_value)
        else:
            logger.warning(f'Unknown action type: {action_type}')
            return {'status': 'error', 'message': f'Unknown action type: {action_type}'}

    def _execute_sequence(self, commands: List[str], user_id: str='default') -> Dict[str, Any]:
        """
        Execute a sequence of commands
        
        Args:
            commands: List of command strings
            user_id: User ID the commands belong to
            
        Returns:
            Dictionary with execution results
        """
        sequence_id = str(uuid.uuid4())
        request = {'action': 'execute_sequence', 'sequence_id': sequence_id, 'commands': commands, 'user_id': user_id, 'background': False}
        try:
            self.coordinator_socket.send_string(json.dumps(request))
            response = self.coordinator_socket.recv_string()
            result = json.loads(response)
            if result.get('status') == 'started':
                return {'status': 'success', 'message': f'Started command sequence with {len(commands)} commands', 'sequence_id': sequence_id}
            else:
                return {'status': 'error', 'message': f"Failed to start sequence: {result.get('reason', 'Unknown error')}"}
        except Exception as e:
            logger.error(f'Error executing sequence: {e}')
            return {'status': 'error', 'message': f'Error executing sequence: {str(e)}'}

    def _execute_script(self, script_path: str, background: bool=False) -> Dict[str, Any]:
        """
        Execute a local script
        
        Args:
            script_path: Path to the script file
            background: Whether to run in background
            
        Returns:
            Dictionary with execution results
        """
        script_path = os.path.expanduser(script_path)
        if not os.path.exists(script_path):
            return {'status': 'error', 'message': f'Script not found: {script_path}'}
        script_ext = os.path.splitext(script_path)[1].lower()
        if script_ext not in SCRIPT_TYPES:
            return {'status': 'error', 'message': f'Unsupported script type: {script_ext}'}
        process_id = str(uuid.uuid4())
        request = {'action': 'execute_script', 'script_path': script_path, 'script_type': script_ext, 'process_id': process_id, 'background': background}
        try:
            self.executor_socket.send_string(json.dumps(request))
            response = self.executor_socket.recv_string()
            result = json.loads(response)
            if result.get('status') == 'started':
                self.running_processes[process_id] = {'type': 'script', 'path': script_path, 'started_at': time.time(), 'background': background}
                return {'status': 'success', 'message': f'Started script: {os.path.basename(script_path)}', 'process_id': process_id}
            else:
                return {'status': 'error', 'message': f"Failed to start script: {result.get('reason', 'Unknown error')}"}
        except Exception as e:
            logger.error(f'Error executing script: {e}')
            return {'status': 'error', 'message': f'Error executing script: {str(e)}'}

    def get_running_processes(self) -> List[Dict[str, Any]]:
        """
        Get list of running processes
        
        Returns:
            List of running process information
        """
        self._update_process_status()
        processes = []
        for (process_id, info) in self.running_processes.items():
            process_info = info.copy()
            process_info['process_id'] = process_id
            process_info['running_time'] = time.time() - info.get('started_at', time.time())
            processes.append(process_info)
        return processes

    def _update_process_status(self):
        """Update status of running processes"""
        if not self.running_processes:
            return
        script_processes = [pid for (pid, info) in self.running_processes.items() if info.get('type') == 'script']
        if script_processes:
            try:
                request = {'action': 'check_processes', 'process_ids': script_processes}
                self.executor_socket.send_string(json.dumps(request))
                response = self.executor_socket.recv_string()
                result = json.loads(response)
                if result.get('status') == 'ok':
                    for (process_id, is_running) in result.get('processes', {}).items():
                        if not is_running and process_id in self.running_processes:
                            del self.running_processes[process_id]
            except Exception as e:
                logger.error(f'Error checking script processes: {e}')
        sequence_processes = [pid for (pid, info) in self.running_processes.items() if info.get('type') == 'sequence']
        if sequence_processes:
            try:
                request = {'action': 'check_sequences', 'sequence_ids': sequence_processes}
                self.coordinator_socket.send_string(json.dumps(request))
                response = self.coordinator_socket.recv_string()
                result = json.loads(response)
                if result.get('status') == 'ok':
                    for (sequence_id, is_running) in result.get('sequences', {}).items():
                        if not is_running and sequence_id in self.running_processes:
                            del self.running_processes[sequence_id]
            except Exception as e:
                logger.error(f'Error checking sequence processes: {e}')

    def stop_process(self, process_id: str) -> bool:
        """
        Stop a running process
        
        Args:
            process_id: ID of the process to stop
            
        Returns:
            True if process was stopped, False otherwise
        """
        if process_id not in self.running_processes:
            logger.warning(f'Process not found: {process_id}')
            return False
        process_type = self.running_processes[process_id].get('type')
        if process_type == 'script':
            try:
                request = {'action': 'stop_process', 'process_id': process_id}
                self.executor_socket.send_string(json.dumps(request))
                response = self.executor_socket.recv_string()
                result = json.loads(response)
                if result.get('status') == 'ok':
                    del self.running_processes[process_id]
                    return True
                else:
                    logger.warning(f"Failed to stop script: {result.get('reason', 'Unknown error')}")
                    return False
            except Exception as e:
                logger.error(f'Error stopping script: {e}')
                return False
        elif process_type == 'sequence':
            try:
                request = {'action': 'stop_sequence', 'sequence_id': process_id}
                self.coordinator_socket.send_string(json.dumps(request))
                response = self.coordinator_socket.recv_string()
                result = json.loads(response)
                if result.get('status') == 'ok':
                    del self.running_processes[process_id]
                    return True
                else:
                    logger.warning(f"Failed to stop sequence: {result.get('reason', 'Unknown error')}")
                    return False
            except Exception as e:
                logger.error(f'Error stopping sequence: {e}')
                return False
        logger.warning(f'Unknown process type: {process_type}')
        return False

    def process_command_registration(self, text: str, user_id: str='default') -> Optional[str]:
        """
        Process command registration from text with extended support for sequences and scripts
        
        Args:
            text: Text containing command registration
            user_id: User ID to register command for
            
        Returns:
            Confirmation message if command was registered, None otherwise
        """
        registration = self.detect_command_registration(text)
        if not registration:
            return None
        (trigger_phrase, action_type, action_value) = registration
        success = self.register_command(trigger_phrase, action_type, action_value, user_id)
        if success:
            if action_type == 'alias_for':
                return f"I've created the alias '{trigger_phrase}' for '{action_value}'"
            elif action_type == 'sequence':
                try:
                    commands = json.loads(action_value)
                    return f"I've created the sequence '{trigger_phrase}' with {len(commands)} commands"
                except:
                    return f"I've created the sequence '{trigger_phrase}'"
            elif action_type == 'script':
                return f"I've created the script command '{trigger_phrase}' that will run: {os.path.basename(action_value)}"
            else:
                return f"I've created the command '{trigger_phrase}' that will do: {action_value}"
        else:
            return f"I couldn't create the {action_type} command. Please try again."

    def _get_health_status(self) -> Dict[str, Any]:
        """Overrides the base method to add agent-specific health metrics."""
        return {'status': 'ok', 'ready': True, 'initialized': True, 'service': 'command_handler', 'components': {'executor_connected': hasattr(self, 'executor_socket'), 'coordinator_connected': hasattr(self, 'coordinator_socket')}, 'handler_status': 'active', 'commands_processed': getattr(self, 'commands_processed', 0), 'running_processes': len(getattr(self, 'running_processes', {})), 'uptime': time.time() - self.start_time}

    def cleanup(self):
        """Gracefully shutdown the agent"""
        logger.info('Shutting down AdvancedCommandHandler')
        self.running = False
        if hasattr(self, 'executor_socket'):
            self.executor_socket.close()
        if hasattr(self, 'coordinator_socket'):
            self.coordinator_socket.close()
        super().cleanup()
        logger.info('AdvancedCommandHandler shutdown complete')

    def run(self):
        """Run the main agent loop."""
        logger.info('Starting AdvancedCommandHandler main loop')
        super().run()
        while self.running:
            try:
                time.sleep(0.1)
            except Exception as e:
                logger.error(f'Error in main loop: {e}')
if __name__ == '__main__':
    agent = None
    try:
        agent = AdvancedCommandHandler()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {(agent.name if agent else 'agent')}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {(agent.name if agent else 'agent')}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f'Cleaning up {agent.name}...')
            agent.cleanup()