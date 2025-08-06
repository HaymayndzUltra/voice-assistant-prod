#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Agent Health Issue Fixer
========================

This script fixes the "Resource temporarily unavailable" errors in agent health checks by:
1. Setting proper timeouts on ZMQ sockets
2. Improving error handling in health check requests
3. Restarting agents with proper socket configuration

Usage:
    python fix_agent_health_issues.py [--restart-agents]

Options:
    --restart-agents    Restart all agents after applying fixes

Author: AI Assistant
Date: 2025-06-20
"""

import os
import sys
import json
import time
import zmq
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentHealthFixer")

# Constants
DEFAULT_TIMEOUT = 5000  # 5 seconds in milliseconds
CONFIG_DIR = Path(__file__).parent.parent / "config"
AGENT_DIRS = [
    Path(__file__).parent.parent / "agents",
    Path(__file__).parent.parent / "src/agents",
    Path(__file__).parent.parent / "FORMAINPC",
    Path(__file__).parent.parent / "ForPC2"
]

class AgentHealthFixer:
    """Fixes agent health check issues."""
    
    def __init__(self):
        """Initialize the agent health fixer."""
        self.agent_configs = self._load_agent_configs()
        self.agent_ports = self._load_agent_ports()
        self.agent_processes = {}
        self.fixed_files = []
        
    def _load_agent_configs(self) -> Dict[str, Any]:
        """Load agent configurations."""
        try:
            config_path = CONFIG_DIR / "agent_config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Agent config file not found: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading agent configs: {e}")
            return {}
            
    def _load_agent_ports(self) -> Dict[str, int]:
        """Load agent port mappings."""
        try:
            # Try to import agent_ports.py
            sys.path.append(str(CONFIG_DIR.parent))
from main_pc_code.config.agent_ports import AgentPorts
from common.env_helpers import get_env
            
            agent_ports = AgentPorts()
            return agent_ports.get_all_ports()
        except ImportError:
            # Fall back to JSON if available
            try:
                ports_path = CONFIG_DIR / "agent_ports.json"
                if ports_path.exists():
                    with open(ports_path, 'r') as f:
                        return json.load(f)
                else:
                    logger.warning(f"Agent ports file not found: {ports_path}")
                    return {}
            except Exception as e:
                logger.error(f"Error loading agent ports: {e}")
                return {}
    
    def find_agent_files(self) -> List[Path]:
        """Find all agent Python files."""
        agent_files = []
        
        for directory in AGENT_DIRS:
            if not directory.exists():
                continue
                
            # Find all Python files in the directory and subdirectories
            for file_path in directory.glob("**/*.py"):
                # Check if file contains ZMQ code
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'zmq.REQ' in content or 'zmq.REP' in content:
                        agent_files.append(file_path)
        
        logger.info(f"Found {len(agent_files)} agent files with ZMQ sockets")
        return agent_files
        
    def fix_zmq_timeouts(self, file_path: Path) -> bool:
        """Fix ZMQ timeout settings in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Check if the file already has timeout settings
            has_rcvtimeo = 'setsockopt(zmq.RCVTIMEO' in content
            has_sndtimeo = 'setsockopt(zmq.SNDTIMEO' in content
            
            if has_rcvtimeo and has_sndtimeo:
                logger.info(f"File already has timeout settings: {file_path}")
                return False
                
            # Add imports if needed
            if 'import zmq' not in content and 'from zmq import' not in content:
                content = content.replace('import ', 'import zmq\nimport ')
                
            # Add timeout constant if needed
            if 'TIMEOUT' not in content and 'zmq.RCVTIMEO' not in content:
                constant_lines = [
                    "# ZMQ timeout settings",
                    "ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests"
                ]
                
                # Find a good place to insert the constant
                import_end = content.rfind('import')
                if import_end > 0:
                    import_end = content.find('\n', import_end)
                    if import_end > 0:
                        content = content[:import_end+1] + '\n' + '\n'.join(constant_lines) + '\n' + content[import_end+1:]
                else:
                    # Insert at the beginning after any module docstring
                    if content.startswith('"""') or content.startswith("'''"):
                        # Find end of docstring
                        end_quote = content[3:].find(content[:3])
                        if end_quote > 0:
                            end_quote += 6  # Add length of start quote + end quote
                            content = content[:end_quote] + '\n\n' + '\n'.join(constant_lines) + '\n' + content[end_quote:]
                    else:
                        # Just add at the beginning
                        content = '\n'.join(constant_lines) + '\n\n' + content
            
            # Find all socket creation lines
            socket_lines = []
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if 'socket(' in line and ('zmq.REQ' in line or 'zmq.REP' in line):
                    socket_lines.append(i)
            
            # Add timeout settings after socket creation
            modified_lines = list(lines)
            offset = 0
            for line_num in socket_lines:
                line = lines[line_num]
                indent = len(line) - len(line.lstrip())
                spaces = ' ' * indent
                
                # Adjust line number for any previous insertions
                adjusted_line = line_num + offset
                
                # Extract socket variable name
                parts = line.split('=')
                if len(parts) < 2:
                    continue
                    
                socket_var = parts[0].strip()
                
                # Add timeout settings
                timeout_lines = []
                if not has_rcvtimeo:
                    timeout_lines.append(f"{spaces}{socket_var}.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)")
                if not has_sndtimeo:
                    timeout_lines.append(f"{spaces}{socket_var}.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)")
                    
                if timeout_lines:
                    modified_lines = modified_lines[:adjusted_line+1] + timeout_lines + modified_lines[adjusted_line+1:]
                    offset += len(timeout_lines)
            
            # Save the modified file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(modified_lines))
                
            logger.info(f"Fixed ZMQ timeout settings in {file_path}")
            self.fixed_files.append(file_path)
            return True
            
        except Exception as e:
            logger.error(f"Error fixing ZMQ timeouts in {file_path}: {e}")
            return False
    
    def fix_all_agent_files(self) -> int:
        """Fix ZMQ timeout settings in all agent files."""
        agent_files = self.find_agent_files()
        fixed_count = 0
        
        for file_path in agent_files:
            if self.fix_zmq_timeouts(file_path):
                fixed_count += 1
                
        logger.info(f"Fixed {fixed_count} agent files")
        return fixed_count
        
    def restart_agents(self) -> None:
        """Restart all agents after fixing timeout settings."""
        try:
            # Detect OS
            if sys.platform == "win32":
                # Windows: Use start_all_agents.bat if available
                bat_path = Path(__file__).parent / "start_all_agents.bat"
                if bat_path.exists():
                    logger.info("Restarting agents using start_all_agents.bat")
                    subprocess.run([str(bat_path)], shell=True)
                else:
                    logger.warning(f"Agent startup script not found: {bat_path}")
            else:
                # Unix: Use start_agents.sh if available
                sh_path = Path(__file__).parent / "start_agents.sh"
                if sh_path.exists():
                    logger.info("Restarting agents using start_agents.sh")
                    subprocess.run(["bash", str(sh_path)], shell=True)
                else:
                    logger.warning(f"Agent startup script not found: {sh_path}")
                    
            logger.info("Agents restart initiated")
        except Exception as e:
            logger.error(f"Error restarting agents: {e}")
    
    def check_agent_health(self, agent_name: str, host: str, port: int) -> bool:
        """Check the health of an agent using proper error handling."""
        try:
            # Create a new context and socket for each health check
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            
            # Set timeout values to prevent hanging
            socket.setsockopt(zmq.RCVTIMEO, DEFAULT_TIMEOUT)
            socket.setsockopt(zmq.SNDTIMEO, DEFAULT_TIMEOUT)
            
            # Connect to agent
            socket.connect(f"tcp://{host}:{port}")
            
            # Send health check request
            request = {"action": "health"}
            socket.send_json(request)
            
            # Wait for response
            response = socket.recv_json()
            
            # Check response
            if "status" in response and response["status"] == "ok":
                logger.info(f"Agent {agent_name} health check passed")
                socket.close()
                context.term()
                return True
            else:
                logger.warning(f"Agent {agent_name} returned unexpected health status: {response}")
                socket.close()
                context.term()
                return False
                
        except zmq.error.Again:
            logger.warning(f"Agent {agent_name} health check failed: Timeout")
            return False
        except ConnectionRefusedError:
            logger.warning(f"Agent {agent_name} health check failed: Connection refused")
            return False
        except Exception as e:
            logger.warning(f"Agent {agent_name} health check failed: {str(e)}")
            return False
        finally:
            # Ensure we clean up the socket resources even if an exception occurs
            try:
                socket.close()
                context.term()
            except:
                pass
            return False  # Ensure we always return a boolean
            
    def verify_fixes(self) -> Dict[str, bool]:
        """Verify fixes by checking agent health."""
        results = {}
        
        # Wait for agents to start up
        logger.info("Waiting 10 seconds for agents to start up...")
        time.sleep(10)
        
        # Check health of all agents
        for agent_name, port in self.agent_ports.items():
            is_healthy = self.check_agent_health(agent_name, "localhost", port)
            results[agent_name] = is_healthy
            
        # Log results
        healthy_count = sum(1 for health in results.values() if health)
        total_count = len(results)
        
        logger.info(f"Health check results: {healthy_count}/{total_count} agents healthy")
        
        return results

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fix agent health issues")
    parser.add_argument("--restart-agents", action="store_true", help="Restart all agents after applying fixes")
    args = parser.parse_args()
    
    logger.info("Starting Agent Health Issue Fixer")
    
    fixer = AgentHealthFixer()
    
    # Fix agent files
    fixed_count = fixer.fix_all_agent_files()
    
    # Restart agents if requested
    if args.restart_agents and fixed_count > 0:
        logger.info("Restarting agents to apply fixes")
        fixer.restart_agents()
        
        # Verify fixes
        results = fixer.verify_fixes()
        
        # Print summary
        print("\n" + "=" * 60)
        print("AGENT HEALTH CHECK SUMMARY")
        print("=" * 60)
        
        for agent_name, is_healthy in results.items():
            status = "✅ HEALTHY" if is_healthy else "❌ UNHEALTHY"
            print(f"{agent_name}: {status}")
            
        print("=" * 60)
        healthy_count = sum(1 for health in results.values() if health)
        total_count = len(results)
        print(f"Total: {healthy_count}/{total_count} agents healthy")
        print("=" * 60)
    
    logger.info("Agent Health Issue Fixer completed")

if __name__ == "__main__":
    main() 