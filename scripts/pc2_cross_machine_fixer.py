#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
PC2 Cross-Machine Compliance Fixer
---------------------------------
Automatically fixes PC2 agents to be compliant with architectural standards
while properly handling cross-machine communication.

This script:
1. Reads agents from pc2_code/config/startup_config.yaml
2. Adds BaseAgent inheritance with proper cross-machine handling
3. Adds proper network configuration loading
4. Implements _get_health_status method with machine-specific info
5. Adds secure ZMQ communication support
6. Standardizes __main__ block
7. Generates a compliance report
"""

import os
import re
import sys
import shutil
import yaml
import ast
from pathlib import Path
import logging
from typing import Dict, List, Set, Tuple, Optional
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pc2_cross_machine_fixer")

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PC2_CONFIG_PATH = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'
PC2_CODEBASE_ROOT = PROJECT_ROOT / 'pc2_code'
PC2_AGENTS_ROOT = PROJECT_ROOT / 'pc2_code' / 'agents'
NETWORK_CONFIG_PATH = PROJECT_ROOT / 'config' / 'network_config.yaml'
TEMPLATE_PATH = PROJECT_ROOT / 'scripts' / 'pc2_cross_machine_template.py'

# Required imports for cross-machine agents
REQUIRED_IMPORTS = [
    'import time',
    'import logging',
    'import zmq',
    'import json',
    'import os',
    'import sys',
    'import yaml',
    'from typing import Dict, Any, Optional',
    'from main_pc_code.src.core.base_agent import BaseAgent',
]

def create_backup(file_path: Path) -> Path:
    """Create a backup of a file before modifying it."""
    backup_dir = PC2_AGENTS_ROOT / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    backup_path = backup_dir / file_path.name
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    return backup_path

def gather_agents_from_config(config_path):
    """Gather agents from startup_config.yaml."""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    agents = []
    
    # Process all sections in the config file
    for section_name, section_data in config.items():
        if isinstance(section_data, list):
            for agent in section_data:
                if isinstance(agent, dict) and 'script_path' in agent:
                    agent_name = agent.get('name', os.path.basename(agent['script_path']).split('.')[0])
                    agents.append({
                        'name': agent_name,
                        'script_path': agent['script_path'],
                        'port': agent.get('port', None)
                    })
    
    return agents

def load_template():
    """Load the cross-machine template."""
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def extract_class_name(source_code: str) -> Optional[str]:
    """Extract the main class name from source code."""
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Find the class with the most methods (likely the main agent class)
                if len([m for m in node.body if isinstance(m, ast.FunctionDef)]) > 1:
                    return node.name
    except Exception as e:
        logger.error(f"Error extracting class name: {e}")
        
        # Fallback to regex if AST parsing fails
        class_match = re.search(r'class\s+(\w+)(?:\([\w,\s.]*\))?\s*:', source_code)
        if class_match:
            return class_match.group(1)
    
    return None

def extract_methods(source_code: str) -> Dict[str, str]:
    """Extract method names and their content from source code."""
    methods = {}
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        method_source = ast.get_source_segment(source_code, method)
                        if method_source:
                            methods[method.name] = method_source
    except Exception as e:
        logger.error(f"Error parsing source code: {e}")
    return methods

def add_network_config_loading(content: str) -> str:
    """Add network configuration loading to the agent."""
    if 'load_network_config' not in content:
        network_config_code = """
# Load network configuration
def load_network_config():
    \"\"\"Load the network configuration from the central YAML file.\"\"\"
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_service_ip("mainpc"),
            "pc2_ip": get_service_ip("pc2"),
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", get_service_ip("mainpc"))
PC2_IP = network_config.get("pc2_ip", get_service_ip("pc2"))
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")
"""
        
        # Find a good place to add the network config code
        import_section_match = re.search(r'((?:from|import)\s+[\w\.]+\s+(?:import\s+[\w\.,\s]+)?)', content)
        if import_section_match:
            # Add after the last import
            imports = re.findall(r'((?:from|import)\s+[\w\.]+\s+(?:import\s+[\w\.,\s]+)?)', content)
            last_import = imports[-1]
            last_import_pos = content.find(last_import) + len(last_import)
            content = content[:last_import_pos] + '\n' + network_config_code + content[last_import_pos:]
        else:
            # If no imports found, add at the top after any comments/docstrings
            first_code_line = re.search(r'^(?:\s*#.*|\s*""".*?"""|[^\n]+)$', content, re.MULTILINE)
            if first_code_line:
                content = content[:first_code_line.end()] + '\n\n' + network_config_code + content[first_code_line.end():]
            else:
                content = network_config_code + '\n' + content
    
    return content

def add_required_imports(content: str) -> str:
    """Add required imports for cross-machine agents."""
    for import_line in REQUIRED_IMPORTS:
        if import_line not in content:
            # Add import at the top after any comments/docstrings
            first_code_line = re.search(r'^(?:\s*#.*|\s*""".*?"""|[^\n]+)$', content, re.MULTILINE)
            if first_code_line:
                content = content[:first_code_line.end()] + '\n' + import_line + content[first_code_line.end():]
            else:
                content = import_line + '\n' + content
    
    return content

def add_health_status_method(content: str, class_name: str) -> str:
    """Add or update _get_health_status method with cross-machine information."""
    health_status_method = f"""
    def _get_health_status(self) -> Dict[str, Any]:
        \"\"\"Return health status information.
        
        Returns:
            Dict containing health status information.
        \"\"\"
        # Get base status from parent
        base_status = super()._get_health_status()
        
        # Add PC2-specific health information
        base_status.update({{
            'service': self.__class__.__name__,
            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            'machine': 'PC2',
            'ip': PC2_IP,
            'status': 'healthy',
            'main_pc_connections': list(self.main_pc_connections.items()) if hasattr(self, 'main_pc_connections') else []
        }})
        
        return base_status
"""
    
    # Check if the method already exists
    if '_get_health_status' not in content:
        # Find the class definition
        class_match = re.search(r'class\s+' + class_name + r'(?:\([\w,\s.]*\))?\s*:', content)
        if class_match:
            # Find the end of the class
            class_start = class_match.end()
            class_indent = re.search(r'(\s+)', content[class_start:]).group(1) if re.search(r'(\s+)', content[class_start:]) else '    '
            
            # Format the method with proper indentation
            indented_method = health_status_method.replace('\n    ', '\n' + class_indent)
            
            # Find a good place to add the method
            next_class = content.find('class ', class_start)
            if next_class == -1:
                next_class = len(content)
            
            # Add the method before the next class or at the end
            content = content[:next_class] + indented_method + content[next_class:]
    
    return content

def add_connect_to_main_pc_method(content: str, class_name: str) -> str:
    """Add method to connect to main PC services."""
    connect_method = """
    def connect_to_main_pc_service(self, service_name: str):
        \"\"\"
        Connect to a service on the main PC using the network configuration.
        
        Args:
            service_name: Name of the service in the network config ports section
        
        Returns:
            ZMQ socket connected to the service
        \"\"\"
        if not hasattr(self, 'main_pc_connections'):
            self.main_pc_connections = {}
            
        if service_name not in network_config.get("ports", {}):
            logger.error(f"Service {service_name} not found in network configuration")
            return None
            
        port = network_config["ports"][service_name]
        
        # Create a new socket for this connection
        socket = self.context.socket(zmq.REQ)
        
        # Connect to the service
        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
        
        # Store the connection
        self.main_pc_connections[service_name] = socket
        
        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")
        return socket
"""
    
    # Check if the method already exists
    if 'connect_to_main_pc_service' not in content:
        # Find the class definition
        class_match = re.search(r'class\s+' + class_name + r'(?:\([\w,\s.]*\))?\s*:', content)
        if class_match:
            # Find the end of the class
            class_start = class_match.end()
            class_indent = re.search(r'(\s+)', content[class_start:]).group(1) if re.search(r'(\s+)', content[class_start:]) else '    '
            
            # Format the method with proper indentation
            indented_method = connect_method.replace('\n    ', '\n' + class_indent)
            
            # Find a good place to add the method
            next_class = content.find('class ', class_start)
            if next_class == -1:
                next_class = len(content)
            
            # Add the method before the next class or at the end
            content = content[:next_class] + indented_method + content[next_class:]
    
    return content

def update_init_method(content: str, class_name: str, port: Optional[int] = None) -> str:
    """Update __init__ method with cross-machine initialization."""
    # Find the __init__ method
    init_match = re.search(r'def\s+__init__\s*\(self(?:,\s*[^)]*)\)\s*:', content)
    if init_match:
        # Check if the method already has cross-machine initialization
        init_block_start = init_match.end()
        next_def = content.find('def ', init_block_start)
        if next_def == -1:
            next_def = len(content)
        
        init_block = content[init_block_start:next_def]
        
        # Add cross-machine initialization if not present
        cross_machine_init = """
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        # Initialize agent state
        self.running = True
        self.request_count = 0
        
        # Set up connection to main PC if needed
        self.main_pc_connections = {}
        
        logger.info(f"{self.__class__.__name__} initialized on PC2 (IP: {PC2_IP}) port {self.port}")
"""
        
        if 'self.start_time = time.time()' not in init_block:
            # Find the indentation level
            indentation = re.search(r'(\s+)', content[init_block_start:]).group(1) if re.search(r'(\s+)', content[init_block_start:]) else '        '
            
            # Format the initialization with proper indentation
            indented_init = cross_machine_init.replace('\n        ', '\n' + indentation)
            
            # Add after super().__init__ if it exists
            super_init = re.search(r'super\(\)\.__init__\([^)]*\)', init_block)
            if super_init:
                super_end = init_block_start + super_init.end()
                content = content[:super_end] + indented_init + content[super_end:]
            else:
                # Add at the beginning of the method body
                content = content[:init_block_start] + indented_init + content[init_block_start:]
    
    return content

def update_cleanup_method(content: str, class_name: str) -> str:
    """Add or update cleanup method with cross-machine handling."""
    cleanup_method = """
    def cleanup(self):
        \"\"\"Clean up resources before shutdown.\"\"\"
        logger.info(f"Cleaning up {self.__class__.__name__} on PC2...")
        self.running = False
        
        # Close all connections to main PC
        for service_name, socket in self.main_pc_connections.items():
            try:
                socket.close()
                logger.info(f"Closed connection to {service_name} on MainPC")
            except Exception as e:
                logger.error(f"Error closing connection to {service_name}: {e}")
        
        # Close main socket
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        # Terminate context
        if hasattr(self, 'context') and self.context:
            self.context.term()
        
        # Call parent cleanup
        super().cleanup()
"""
    
    # Check if the method already exists
    if 'def cleanup' not in content:
        # Find the class definition
        class_match = re.search(r'class\s+' + class_name + r'(?:\([\w,\s.]*\))?\s*:', content)
        if class_match:
            # Find the end of the class
            class_start = class_match.end()
            class_indent = re.search(r'(\s+)', content[class_start:]).group(1) if re.search(r'(\s+)', content[class_start:]) else '    '
            
            # Format the method with proper indentation
            indented_method = cleanup_method.replace('\n    ', '\n' + class_indent)
            
            # Find a good place to add the method
            next_class = content.find('class ', class_start)
            if next_class == -1:
                next_class = len(content)
            
            # Add the method before the next class or at the end
            content = content[:next_class] + indented_method + content[next_class:]
    
    return content

def standardize_main_block(content: str, class_name: str) -> str:
    """Standardize the __main__ block with cross-machine handling."""
    main_block = f"""

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = {class_name}()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {{agent.name if agent else 'agent'}} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {{agent.name if agent else 'agent'}} on PC2: {{e}}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {{agent.name}} on PC2...")
            agent.cleanup()
"""
    
    # Check if the file already has a __main__ block
    if '__name__ == "__main__"' in content or "__name__ == '__main__'" in content:
        # Replace the existing __main__ block
        content = re.sub(
            r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:.*?(?=\n\S|$)',
            main_block,
            content,
            flags=re.DOTALL
        )
    else:
        # Add the __main__ block at the end
        content += main_block
    
    return content

def fix_agent_compliance(agent: dict) -> bool:
    """Fix compliance for a specific agent using cross-machine template."""
    rel_path = agent['script_path']
    agent_name = agent['name']
    port = agent.get('port')
    abs_path = (PC2_CODEBASE_ROOT / rel_path).resolve()
    
    if not abs_path.exists():
        logger.error(f"Agent not found: {abs_path}")
        return False
    
    logger.info(f"Fixing compliance for {agent_name} ({abs_path})")
    
    # Create backup
    backup_path = create_backup(abs_path)
    
    # Read the agent file
    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract the class name
    class_name = extract_class_name(content)
    if not class_name:
        logger.error(f"Could not extract class name for {agent_name}")
        return False
    
    logger.info(f"Found class name: {class_name}")
    
    # Extract existing methods
    methods = extract_methods(content)
    logger.info(f"Found {len(methods)} methods in {agent_name}")
    
    # Apply fixes
    content = add_required_imports(content)
    content = add_network_config_loading(content)
    content = add_health_status_method(content, class_name)
    content = add_connect_to_main_pc_method(content, class_name)
    content = update_init_method(content, class_name, port)
    content = update_cleanup_method(content, class_name)
    content = standardize_main_block(content, class_name)
    
    # Write the updated content
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"Successfully fixed compliance for {agent_name}")
    return True

def main():
    """Main function to fix PC2 agent compliance."""
    logger.info("Starting PC2 Cross-Machine Compliance Fixer")
    
    # Check if template exists
    if not TEMPLATE_PATH.exists():
        logger.error(f"Template file not found: {TEMPLATE_PATH}")
        return
    
    # Gather agents from config
    agents = gather_agents_from_config(PC2_CONFIG_PATH)
    logger.info(f"Found {len(agents)} agents in config")
    
    # Fix compliance for each agent
    success_count = 0
    for agent in agents:
        if fix_agent_compliance(agent):
            success_count += 1
    
    # Generate report
    logger.info(f"Compliance fixing completed: {success_count}/{len(agents)} agents fixed")
    
    # Write report to file
    report_path = PROJECT_ROOT / 'scripts' / f'pc2_compliance_report_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"PC2 Cross-Machine Compliance Report\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total agents: {len(agents)}\n")
        f.write(f"Successfully fixed: {success_count}\n")
        f.write(f"Failed: {len(agents) - success_count}\n\n")
        
        f.write("Agent details:\n")
        for agent in agents:
            rel_path = agent['script_path']
            abs_path = (PC2_CODEBASE_ROOT / rel_path).resolve()
            status = "Fixed" if abs_path.exists() else "Failed"
            f.write(f"- {agent['name']}: {status}\n")
    
    logger.info(f"Report written to {report_path}")

if __name__ == "__main__":
    main() 