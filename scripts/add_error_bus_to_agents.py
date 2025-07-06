#!/usr/bin/env python3
"""
Script to add Error Bus connection code to all active agents in the system.
This script will:
1. Read the startup configuration files to identify active agents
2. Check if each agent already has Error Bus connection code
3. Add the necessary code to agents that don't have it
"""

import os
import re
import yaml
from pathlib import Path

# Define the code to add to each agent
ERROR_BUS_INIT_CODE = """
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
"""

ERROR_BUS_METHOD_CODE = """
    def report_error(self, error_type, message, severity="ERROR", context=None):
        error_data = {
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "context": context or {}
        }
        try:
            msg = json.dumps(error_data).encode('utf-8')
            self.error_bus_pub.send_multipart([b"ERROR:", msg])
        except Exception as e:
            print(f"Failed to publish error to Error Bus: {e}")
"""

CLASS_DOCSTRING_UPDATE = """    """
CLASS_DOCSTRING_ADDITION = """ Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""

def load_startup_config(config_path):
    """Load a startup configuration file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {config_path}: {e}")
        return {}

def get_active_agents():
    """Get all active agents from startup configuration files."""
    agents = []
    
    # Main PC agents
    main_config_path = "main_pc_code/config/startup_config.yaml"
    main_config = load_startup_config(main_config_path)
    
    # Extract agents from different sections
    for section_name, section in main_config.items():
        if isinstance(section, list) and section_name not in ['environment', 'resource_limits', 'volumes', 'health_checks', 'network']:
            for agent in section:
                if isinstance(agent, dict) and 'script_path' in agent:
                    agents.append({
                        'name': agent.get('name', ''),
                        'script_path': agent['script_path'],
                        'machine': 'main_pc'
                    })
    
    # PC2 agents
    pc2_config_path = "pc2_code/config/startup_config.yaml"
    pc2_config = load_startup_config(pc2_config_path)
    
    # Extract PC2 agents
    if 'pc2_services' in pc2_config:
        for agent in pc2_config['pc2_services']:
            if isinstance(agent, dict) and 'script_path' in agent:
                agents.append({
                    'name': agent.get('name', ''),
                    'script_path': agent['script_path'],
                    'machine': 'pc2'
                })
    
    # Extract PC2 core services
    if 'core_services' in pc2_config:
        for agent in pc2_config['core_services']:
            if isinstance(agent, dict) and 'script_path' in agent:
                agents.append({
                    'name': agent.get('name', ''),
                    'script_path': agent['script_path'],
                    'machine': 'pc2'
                })
    
    return agents

def check_and_update_agent(agent):
    """Check if an agent has Error Bus code and update if not."""
    script_path = agent['script_path']
    
    # Skip if file doesn't exist
    if not os.path.exists(script_path):
        print(f"Warning: {script_path} does not exist, skipping")
        return False
    
    # Read the file content
    try:
        with open(script_path, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {script_path}: {e}")
        return False
    
    # Check if the file already has Error Bus code
    if "error_bus_port" in content and "error_bus_pub" in content and "report_error" in content:
        print(f"✓ {agent['name']} ({script_path}) already has Error Bus code")
        return False
    
    # Update the class docstring
    class_match = re.search(r'class\s+(\w+)\(.*?\):\s*(?:"""(.*?)""")?', content, re.DOTALL)
    if not class_match:
        print(f"Warning: Could not find class definition in {script_path}, skipping")
        return False
    
    class_name = class_match.group(1)
    
    # Check if the file has a __init__ method
    init_match = re.search(r'def\s+__init__\s*\(.*?\):(.*?)(?:def|\Z)', content, re.DOTALL)
    if not init_match:
        print(f"Warning: Could not find __init__ method in {script_path}, skipping")
        return False
    
    # Check if the file imports json
    if "import json" not in content:
        # Add json import
        if "import " in content:
            content = re.sub(r'(import .*?)\n', r'\1\nimport json\n', content, count=1)
        else:
            content = "import json\n" + content
    
    # Update the class docstring
    if class_match.group(2):
        # Class has a docstring
        docstring = class_match.group(2)
        if CLASS_DOCSTRING_ADDITION not in docstring:
            updated_docstring = docstring.rstrip() + CLASS_DOCSTRING_ADDITION
            content = content.replace(docstring, updated_docstring)
    else:
        # Class doesn't have a docstring, add one
        class_def = f"class {class_name}("
        docstring = f'"""\n    {class_name}: {CLASS_DOCSTRING_ADDITION}\n    """'
        content = content.replace(class_def, f"{class_def}\n    {docstring}")
    
    # Add Error Bus initialization code to __init__
    init_body = init_match.group(1)
    # Find the end of the __init__ method body
    last_line_match = re.search(r'(\n\s+)(?![\s\n])', init_body)
    if last_line_match:
        indent = last_line_match.group(1)
        # Add error bus code with proper indentation
        error_bus_code = ERROR_BUS_INIT_CODE.replace('\n        ', f'\n{indent}')
        content = content.replace(init_body, init_body + error_bus_code)
    
    # Add report_error method if it doesn't exist
    if "def report_error" not in content:
        # Find the last method in the class
        last_method_match = re.search(r'(def\s+\w+.*?\).*?)(?:\n\s*def|\n\s*if\s+__name__|\Z)', content, re.DOTALL)
        if last_method_match:
            last_method = last_method_match.group(1)
            # Add report_error method after the last method
            # Find the indentation of the last method
            indent_match = re.search(r'\n(\s+)def', last_method)
            if indent_match:
                indent = indent_match.group(1)
                # Add report_error method with proper indentation
                error_method_code = ERROR_BUS_METHOD_CODE.replace('\n    ', f'\n{indent}')
                content = content.replace(last_method, last_method + f"\n\n{error_method_code}")
    
    # Write the updated content back to the file
    try:
        with open(script_path, 'w') as f:
            f.write(content)
        print(f"✓ Updated {agent['name']} ({script_path}) with Error Bus code")
        return True
    except Exception as e:
        print(f"Error writing to {script_path}: {e}")
        return False

def main():
    """Main function to update all active agents."""
    print("Scanning for active agents...")
    agents = get_active_agents()
    print(f"Found {len(agents)} active agents")
    
    updated_count = 0
    for agent in agents:
        if check_and_update_agent(agent):
            updated_count += 1
    
    print(f"\nSummary: Updated {updated_count} agents with Error Bus code")

if __name__ == "__main__":
    main() 