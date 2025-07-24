#!/usr/bin/env python3
"""
🔧 BASEAGENT PORT CONFLICT FIXER
===============================

This script fixes the port conflict issue in BaseAgent where both
ZMQ health socket and HTTP health server try to bind to the same port.
"""

import re
from pathlib import Path

def fix_baseagent_port_conflicts():
    """Fix BaseAgent port conflicts."""
    base_agent_path = Path("common/core/base_agent.py")
    
    if not base_agent_path.exists():
        print(f"❌ BaseAgent file not found: {base_agent_path}")
        return False
    
    print("🔧 Fixing BaseAgent port conflicts...")
    
    try:
        with open(base_agent_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix the port assignment logic to ensure different ports
        # Look for the health_check_port assignment section
        port_assignment_pattern = r'(# HTTP health port should be separate to avoid conflicts with ZMQ health socket\s+self\.http_health_port = self\.health_check_port \+ 1)'
        
        if re.search(port_assignment_pattern, content):
            print("  ✅ HTTP health port separation already implemented")
        else:
            # Find the health_check_port assignment and add HTTP port separation
            health_port_pattern = r'(self\.health_check_port = self\.port \+ 1)'
            
            replacement = '''self.health_check_port = self.port + 1
            
        # HTTP health port should be separate to avoid conflicts with ZMQ health socket
        self.http_health_port = self.health_check_port + 1000  # Use a different port range'''
        
            content = re.sub(health_port_pattern, replacement, content)
        
        # Ensure _start_http_health_server uses the correct port
        http_server_pattern = r'(def _start_http_health_server\(self\):.*?)(\n\s+class\s+|def\s+|\Z)'
        
        def fix_http_server_method(match):
            method_content = match.group(1)
            if 'self.http_health_port' in method_content:
                return match.group(0)  # Already fixed
            
            # Replace health_check_port with http_health_port in HTTP server
            method_content = re.sub(
                r'self\.health_check_port',
                'self.http_health_port',
                method_content
            )
            
            return method_content + (match.group(2) if match.group(2) else '')
        
        content = re.sub(http_server_pattern, fix_http_server_method, content, flags=re.DOTALL)
        
        # Add the _start_http_health_server method if it doesn't exist
        if '_start_http_health_server' not in content:
            http_server_method = '''
    def _start_http_health_server(self):
        """Start HTTP health server on a separate port."""
        try:
            from http.server import BaseHTTPRequestHandler, HTTPServer
            import threading
            import json
            
            class HealthRequestHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/health':
                        try:
                            # Get health status from the agent
                            health_data = self.server.agent._get_health_status()
                            self.send_response(200)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            self.wfile.write(json.dumps(health_data).encode())
                        except Exception as e:
                            self.send_response(500)
                            self.send_header('Content-Type', 'application/json')
                            self.end_headers()
                            error_response = {"status": "error", "message": str(e)}
                            self.wfile.write(json.dumps(error_response).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    # Suppress HTTP server logs
                    pass
            
            self.http_server = HTTPServer(('localhost', self.http_health_port), HealthRequestHandler)
            self.http_server.agent = self
            
            # Start server in daemon thread
            server_thread = threading.Thread(target=self.http_server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            logger.info(f"{self.name} HTTP health server started on port {self.http_health_port}")
            
        except Exception as e:
            logger.warning(f"Failed to start HTTP health server on port {self.http_health_port}: {e}")
'''
            
            # Insert before the last method or class end
            insertion_point = content.rfind('\nif __name__')
            if insertion_point == -1:
                insertion_point = len(content)
            
            content = content[:insertion_point] + http_server_method + content[insertion_point:]
        
        # Write back if changes were made
        if content != original_content:
            with open(base_agent_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("  ✅ Fixed BaseAgent port conflicts")
            return True
        else:
            print("  ℹ️  No changes needed for BaseAgent")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing BaseAgent: {e}")
        return False

def validate_startup_config():
    """Validate startup configuration for port conflicts."""
    config_path = Path("main_pc_code/config/startup_config.yaml")
    
    if not config_path.exists():
        print(f"❌ Startup config not found: {config_path}")
        return False
    
    print("🔍 Validating startup configuration...")
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        ports_used = {}
        health_ports_used = {}
        conflicts = []
        
        # Check each agent group
        agent_groups = config.get('agent_groups', {})
        
        for group_name, agents in agent_groups.items():
            for agent_name, agent_config in agents.items():
                port = agent_config.get('port')
                health_port = agent_config.get('health_check_port')
                
                if port:
                    if port in ports_used:
                        conflicts.append(f"Port {port}: {ports_used[port]} vs {agent_name}")
                    else:
                        ports_used[port] = agent_name
                
                if health_port:
                    if health_port in health_ports_used:
                        conflicts.append(f"Health port {health_port}: {health_ports_used[health_port]} vs {agent_name}")
                    elif health_port in ports_used:
                        conflicts.append(f"Health port {health_port} conflicts with main port of {ports_used[health_port]}")
                    else:
                        health_ports_used[health_port] = agent_name
        
        if conflicts:
            print("  ⚠️  Port conflicts found:")
            for conflict in conflicts:
                print(f"    ❌ {conflict}")
            return False
        else:
            print("  ✅ No port conflicts in startup configuration")
            return True
            
    except Exception as e:
        print(f"❌ Error validating config: {e}")
        return False

if __name__ == "__main__":
    print("🚀 BaseAgent Port Conflict Fix")
    print("=" * 40)
    
    # Fix BaseAgent
    baseagent_fixed = fix_baseagent_port_conflicts()
    
    # Validate startup config
    config_valid = validate_startup_config()
    
    print("\n📈 SUMMARY")
    print("=" * 20)
    print(f"BaseAgent fixed: {'✅' if baseagent_fixed else '❌'}")
    print(f"Config valid: {'✅' if config_valid else '❌'}")
    
    if baseagent_fixed or config_valid:
        print("\n🎉 Port conflict fixes completed!")
    else:
        print("\n📋 No port conflicts found to fix.")