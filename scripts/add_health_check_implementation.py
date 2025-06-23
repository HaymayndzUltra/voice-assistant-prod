#!/usr/bin/env python3
"""
Add Health Check Implementation

This script adds health check implementation to agents that are missing it.
It reads the agent file, analyzes its structure, and adds the necessary code
for health check functionality.

Usage:
    python scripts/add_health_check_implementation.py <agent_file_path>
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Health check template for agents that don't inherit from BaseAgent
HEALTH_CHECK_TEMPLATE = '''
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logging.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logging.info("Health check loop started")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._get_health_status()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logging.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        uptime = time.time() - self.start_time
        
        return {
            "agent": self.name,
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime
        }
'''

# Imports to add if not already present
IMPORTS_TO_ADD = [
    "import threading",
    "from datetime import datetime",
    "from typing import Dict, Any",
    "import time"
]

# Common utilities import block
COMMON_UTILS_IMPORT = """
# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False
"""

# Socket initialization block
SOCKET_INIT_BLOCK = """
        # Initialize health check socket
        try:
            if USE_COMMON_UTILS:
                self.health_socket = create_socket(self.context, zmq.REP, server=True)
            else:
                self.health_socket = self.context.socket(zmq.REP)
                self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}")
            logging.info(f"Health check socket bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logging.error(f"Failed to bind health check socket: {e}")
            raise
"""

# Init additions
INIT_ADDITIONS = """
        self.name = "{class_name}"
        self.running = True
        self.start_time = time.time()
        self.health_port = self.port + 1
"""

# Start health check call
START_HEALTH_CHECK_CALL = """
        # Start health check thread
        self._start_health_check()
"""

# Cleanup additions
CLEANUP_ADDITIONS = """
        # Set running flag to false to stop all threads
        self.running = False
        
        # Wait for threads to finish
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
            logging.info("Health thread joined")
        
        # Close health socket if it exists
        if hasattr(self, "health_socket"):
            self.health_socket.close()
            logging.info("Health socket closed")
"""

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Add health check implementation to agents")
    parser.add_argument("agent_file", help="Path to the agent file to modify")
    return parser.parse_args()

def read_file(file_path: str) -> str:
    """Read file content."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(file_path: str, content: str) -> None:
    """Write content to file."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def extract_class_name(content: str) -> Optional[str]:
    """Extract the main agent class name from the file content."""
    # Look for class definitions with Agent or Service in the name
    class_pattern = r"class\s+(\w+(?:Agent|Service))\s*(?:\(.*\))?\s*:"
    matches = re.findall(class_pattern, content)
    
    if matches:
        # Return the first match that contains "Agent" or "Service"
        for match in matches:
            if "Agent" in match or "Service" in match:
                return match
    
    return None

def find_init_method(content: str) -> Tuple[int, int, str]:
    """Find the __init__ method in the class."""
    # Look for __init__ method
    init_pattern = r"def\s+__init__\s*\(self(?:,\s*[^)]*)*\)\s*:((?:.|\n)*?)(?=\n\s{0,4}def|\n\s{0,4}@|\n\s{0,4}class|\Z)"
    match = re.search(init_pattern, content)
    
    if match:
        init_body = match.group(1)
        start_pos = match.start()
        end_pos = match.end()
        return start_pos, end_pos, init_body
    
    return -1, -1, ""

def find_cleanup_method(content: str) -> Tuple[int, int, str]:
    """Find the cleanup/stop method in the class."""
    # Look for cleanup or stop method
    cleanup_pattern = r"def\s+(cleanup|stop)\s*\(self(?:,\s*[^)]*)*\)\s*:((?:.|\n)*?)(?=\n\s{0,4}def|\n\s{0,4}@|\n\s{0,4}class|\Z)"
    match = re.search(cleanup_pattern, content)
    
    if match:
        cleanup_body = match.group(2)
        start_pos = match.start()
        end_pos = match.end()
        return start_pos, end_pos, cleanup_body
    
    return -1, -1, ""

def find_handle_request_method(content: str) -> Tuple[int, int, str]:
    """Find the handle_request method in the class."""
    # Look for handle_request method
    handle_pattern = r"def\s+handle_request\s*\(self(?:,\s*[^)]*)*\)\s*:((?:.|\n)*?)(?=\n\s{0,4}def|\n\s{0,4}@|\n\s{0,4}class|\Z)"
    match = re.search(handle_pattern, content)
    
    if match:
        handle_body = match.group(1)
        start_pos = match.start()
        end_pos = match.end()
        return start_pos, end_pos, handle_body
    
    return -1, -1, ""

def find_last_import(content: str) -> int:
    """Find the position after the last import statement."""
    import_pattern = r"^(?:import|from)\s+.*$"
    matches = list(re.finditer(import_pattern, content, re.MULTILINE))
    
    if matches:
        last_match = matches[-1]
        return last_match.end()
    
    return 0

def add_health_check_to_agent(file_path: str) -> None:
    """Add health check implementation to an agent file."""
    content = read_file(file_path)
    
    # Extract class name
    class_name = extract_class_name(content)
    if not class_name:
        print(f"Error: Could not find agent class in {file_path}")
        return
    
    print(f"Found agent class: {class_name}")
    
    # Check if health check is already implemented
    if "_health_check_loop" in content or "_start_health_check" in content:
        print(f"Health check already implemented in {file_path}")
        return
    
    # Find init method
    init_start, init_end, init_body = find_init_method(content)
    if init_start == -1:
        print(f"Error: Could not find __init__ method in {file_path}")
        return
    
    # Find cleanup/stop method
    cleanup_start, cleanup_end, cleanup_body = find_cleanup_method(content)
    if cleanup_start == -1:
        print(f"Warning: Could not find cleanup/stop method in {file_path}")
    
    # Find handle_request method
    handle_start, handle_end, handle_body = find_handle_request_method(content)
    
    # Find position to add imports
    last_import_pos = find_last_import(content)
    
    # Add missing imports
    missing_imports = []
    for imp in IMPORTS_TO_ADD:
        if imp not in content:
            missing_imports.append(imp)
    
    # Add common utils import if not present
    if "common_utils.zmq_helper" not in content:
        missing_imports.append(COMMON_UTILS_IMPORT)
    
    # Build the modified content
    modified_content = content[:last_import_pos]
    if missing_imports:
        modified_content += "\n" + "\n".join(missing_imports) + "\n"
    modified_content += content[last_import_pos:init_start]
    
    # Modify init method
    init_method = content[init_start:init_end]
    
    # Add name, running, start_time, health_port
    init_additions = INIT_ADDITIONS.format(class_name=class_name)
    if "self.name" not in init_body:
        init_method = init_method.replace(":", ":\n" + init_additions, 1)
    
    # Add health socket initialization
    if "health_socket" not in init_body:
        # Find where to add socket initialization (after main socket initialization)
        socket_pattern = r"self\.socket\s*=.*?\n"
        socket_match = re.search(socket_pattern, init_method)
        if socket_match:
            socket_end = socket_match.end()
            init_method = init_method[:socket_end] + SOCKET_INIT_BLOCK + init_method[socket_end:]
    
    # Add health check thread start
    if "_start_health_check" not in init_body:
        # Find the end of the init method body
        init_end_pattern = r"\n(\s{4,8})(?:return|pass|#|$)"
        init_end_match = re.search(init_end_pattern, init_method)
        if init_end_match:
            indent = init_end_match.group(1)
            init_method = init_method[:init_end_match.start()] + f"\n{indent}" + START_HEALTH_CHECK_CALL + init_method[init_end_match.start():]
        else:
            # Just add it at the end
            init_method = init_method + START_HEALTH_CHECK_CALL
    
    modified_content += init_method
    
    # Add health check methods after init
    modified_content += HEALTH_CHECK_TEMPLATE
    
    # Add the rest of the content up to cleanup method
    if cleanup_start != -1:
        modified_content += content[init_end:cleanup_start]
        
        # Modify cleanup method
        cleanup_method = content[cleanup_start:cleanup_end]
        
        # Add cleanup for health check resources
        if "health_thread" not in cleanup_body and "health_socket" not in cleanup_body:
            # Find where to add cleanup code
            cleanup_end_pattern = r"\n(\s{4,8})(?:return|pass|#|$)"
            cleanup_end_match = re.search(cleanup_end_pattern, cleanup_method)
            if cleanup_end_match:
                indent = cleanup_end_match.group(1)
                cleanup_method = cleanup_method[:cleanup_end_match.start()] + f"\n{indent}" + CLEANUP_ADDITIONS + cleanup_method[cleanup_end_match.start():]
            else:
                # Just add it at the end
                cleanup_method = cleanup_method + CLEANUP_ADDITIONS
        
        modified_content += cleanup_method
        modified_content += content[cleanup_end:]
    else:
        # No cleanup method found, add the rest of the content
        modified_content += content[init_end:]
    
    # Update handle_request method if it exists
    if handle_start != -1:
        # Check if health check handling is already implemented
        if "health_check" not in handle_body and "ping" not in handle_body:
            handle_method = modified_content[handle_start:handle_end]
            
            # Add health check handling
            health_check_code = """
        # Handle health check requests
        if action in ["health_check", "health", "ping"]:
            return self._get_health_status()
            
"""
            # Find where to add health check handling
            handle_start_pattern = r"def\s+handle_request.*?:\s*\n"
            handle_start_match = re.search(handle_start_pattern, handle_method)
            if handle_start_match:
                handle_end = handle_start_match.end()
                handle_method = handle_method[:handle_end] + health_check_code + handle_method[handle_end:]
                
                # Update the modified content
                modified_content = modified_content[:handle_start] + handle_method + modified_content[handle_end:]
    
    # Write the modified content back to the file
    write_file(file_path, modified_content)
    print(f"Added health check implementation to {file_path}")

def main():
    """Main function."""
    args = parse_args()
    
    if not os.path.exists(args.agent_file):
        print(f"Error: File {args.agent_file} does not exist")
        sys.exit(1)
    
    add_health_check_to_agent(args.agent_file)

if __name__ == "__main__":
    main()
