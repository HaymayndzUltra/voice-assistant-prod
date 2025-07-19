#!/usr/bin/env python3
"""
Fix BaseAgent port conflict issue.

The issue: BaseAgent is starting HTTP health server on health_check_port + 1,
but the startup configuration expects HTTP health checks on health_check_port.
"""

import shutil
from pathlib import Path

def fix_baseagent_ports():
    """Fix the BaseAgent port configuration to match expected behavior."""
    
    base_agent_path = Path("/workspace/common/core/base_agent.py")
    
    # Backup the file
    backup_path = base_agent_path.with_suffix('.bak.ports')
    shutil.copy2(base_agent_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Read the file
    with open(base_agent_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Change HTTP health port to use health_check_port directly
    old_line = "self.http_health_port = self.health_check_port + 1"
    new_line = "self.http_health_port = self.health_check_port  # Use same port for HTTP health"
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        print("Fixed: HTTP health port now uses health_check_port directly")
    
    # Fix 2: Update the HTTP server binding to use health_check_port
    old_server_line = "self.http_server = HTTPServer(('0.0.0.0', self.http_health_port), HealthHandler)"
    new_server_line = "self.http_server = HTTPServer(('0.0.0.0', self.health_check_port), HealthHandler)"
    
    if old_server_line in content:
        content = content.replace(old_server_line, new_server_line)
        print("Fixed: HTTP server now binds to health_check_port")
    
    # Fix 3: Update log message
    old_log = 'logger.info(f"Started HTTP health server on port {self.http_health_port} (ZMQ health on {self.health_check_port})")'
    new_log = 'logger.info(f"Started HTTP health server on port {self.health_check_port}")'
    
    if old_log in content:
        content = content.replace(old_log, new_log)
        print("Fixed: Updated log message")
    
    # Fix 4: Disable ZMQ health check socket to avoid port conflict
    # Find the _init_sockets method and comment out health_socket creation
    lines = content.splitlines()
    fixed_lines = []
    in_init_sockets = False
    skip_health_socket = False
    
    for i, line in enumerate(lines):
        if 'def _init_sockets(' in line:
            in_init_sockets = True
        elif in_init_sockets and line.strip().startswith('def '):
            in_init_sockets = False
            
        if in_init_sockets and 'health_socket' in line and 'socket(zmq.REP)' in line:
            # Comment out ZMQ health socket creation
            fixed_lines.append('        # ' + line.strip() + '  # Disabled to avoid port conflict with HTTP health')
            skip_health_socket = True
        elif skip_health_socket and ('bind' in line or 'health_socket' in line) and not line.strip().startswith('#'):
            # Comment out related lines
            fixed_lines.append('        # ' + line.strip())
            if 'logger' in line or line.strip() == '':
                skip_health_socket = False
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Write the fixed content
    with open(base_agent_path, 'w') as f:
        f.write(content)
    
    print("\nBaseAgent port conflict fixed!")
    print("Changes made:")
    print("1. HTTP health server now uses health_check_port directly")
    print("2. Disabled ZMQ health socket to avoid port conflicts")
    print("3. All agents will now have HTTP health checks on their configured health_check_port")
    
    return True


def verify_startup_config():
    """Verify that startup config health check ports are correct."""
    from pathlib import Path
    import yaml
    
    config_path = Path("/workspace/main_pc_code/config/startup_config.yaml")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("\nVerifying startup configuration health check ports:")
    print("-" * 60)
    
    for group_name, agents in config.get('agent_groups', {}).items():
        print(f"\n{group_name}:")
        for agent_name, agent_config in agents.items():
            port = agent_config.get('port', 'N/A')
            health_port = agent_config.get('health_check_port', 'N/A')
            print(f"  {agent_name}: port={port}, health_check_port={health_port}")


if __name__ == "__main__":
    print("=" * 80)
    print("BASEAGENT PORT CONFLICT FIXER")
    print("=" * 80)
    
    # Fix BaseAgent
    if fix_baseagent_ports():
        print("\n✅ BaseAgent fixed successfully!")
        
    # Verify configuration
    verify_startup_config()