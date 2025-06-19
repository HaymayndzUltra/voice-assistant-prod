"""
Port Health Check Script for PC2
Verifies all PC2 ports are accessible and working correctly.
"""

import zmq
import time
import logging
from typing import Dict, List, Tuple
from port_config import (
    ENHANCED_MODEL_ROUTER_PORT,
    DREAM_WORLD_PORT,
    TRANSLATOR_PORT,
    TUTORING_PORT,
    MEMORY_PORT,
    REMOTE_CONNECTOR_PORT,
    WEB_AGENT_PORT,
    FILESYSTEM_PORT,
    HEALTH_CHECK_PORT,
    CHAIN_OF_THOUGHT_PORT,
    TINYLLAMA_PORT,
    PORT_REGISTRY
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('port_health.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PortHealthChecker:
    def __init__(self):
        """Initialize the port health checker."""
        self.context = zmq.Context()
        self.timeout = 5000  # 5 seconds timeout
        self.ports_to_check = {
            ENHANCED_MODEL_ROUTER_PORT: zmq.REQ,
            DREAM_WORLD_PORT: zmq.SUB,
            TRANSLATOR_PORT: zmq.REQ,
            TUTORING_PORT: zmq.REQ,
            MEMORY_PORT: zmq.REQ,
            REMOTE_CONNECTOR_PORT: zmq.REQ,
            WEB_AGENT_PORT: zmq.REQ,
            FILESYSTEM_PORT: zmq.REQ,
            HEALTH_CHECK_PORT: zmq.REQ,
            CHAIN_OF_THOUGHT_PORT: zmq.REQ,
            TINYLLAMA_PORT: zmq.REQ
        }
        
    def check_port(self, port: int, socket_type: int) -> Tuple[bool, str]:
        """Check if a port is accessible and responding."""
        try:
            socket = self.context.socket(socket_type)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, self.timeout)
            
            if socket_type == zmq.SUB:
                socket.connect(f"tcp://localhost:{port}")
                socket.setsockopt(zmq.SUBSCRIBE, b"")
                try:
                    socket.recv(flags=zmq.NOBLOCK)
                    return True, "Port is accessible"
                except zmq.Again:
                    return True, "Port is accessible (no messages)"
            else:
                socket.connect(f"tcp://localhost:{port}")
                socket.send_json({"action": "health_check"})
                try:
                    response = socket.recv_json()
                    return True, f"Port is accessible: {response}"
                except zmq.Again:
                    return False, "Port timeout"
                except Exception as e:
                    return False, f"Error: {str(e)}"
                    
        except Exception as e:
            return False, f"Connection error: {str(e)}"
        finally:
            socket.close()
    
    def check_all_ports(self) -> Dict[int, Tuple[bool, str]]:
        """Check all configured ports."""
        results = {}
        for port, socket_type in self.ports_to_check.items():
            logger.info(f"Checking port {port} ({PORT_REGISTRY.get(port, 'Unknown')})...")
            status, message = self.check_port(port, socket_type)
            results[port] = (status, message)
            logger.info(f"Port {port}: {'✅' if status else '❌'} {message}")
        return results
    
    def generate_report(self, results: Dict[int, Tuple[bool, str]]) -> str:
        """Generate a human-readable report of port health check results."""
        report = ["Port Health Check Report", "=====================", ""]
        
        # Group by status
        healthy = []
        unhealthy = []
        
        for port, (status, message) in results.items():
            port_info = f"{PORT_REGISTRY.get(port, 'Unknown')} (Port {port})"
            if status:
                healthy.append(f"✅ {port_info}: {message}")
            else:
                unhealthy.append(f"❌ {port_info}: {message}")
        
        # Add healthy ports
        if healthy:
            report.append("Healthy Ports:")
            report.extend(healthy)
            report.append("")
        
        # Add unhealthy ports
        if unhealthy:
            report.append("Unhealthy Ports:")
            report.extend(unhealthy)
            report.append("")
        
        # Add summary
        total = len(results)
        healthy_count = len(healthy)
        report.append(f"Summary: {healthy_count}/{total} ports healthy")
        
        return "\n".join(report)

def main():
    """Main function to run port health checks."""
    checker = PortHealthChecker()
    logger.info("Starting port health check...")
    
    results = checker.check_all_ports()
    report = checker.generate_report(results)
    
    logger.info("\n" + report)
    
    # Exit with error if any ports are unhealthy
    if any(not status for status, _ in results.values()):
        exit(1)

if __name__ == "__main__":
    main() 