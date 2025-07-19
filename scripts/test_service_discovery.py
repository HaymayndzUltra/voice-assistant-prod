#!/usr/bin/env python3
"""
Service Discovery Integration Test
---------------------------------
Tests service discovery integration across agents by:
1. Starting a mock service discovery server
2. Registering test services
3. Verifying that agents can discover and connect to services
"""

import os
import sys
import time
import json
import argparse
import logging
import threading
import zmq
import socket
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from common.env_helpers import get_env

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'test_service_discovery.log'))
    ]
)
logger = logging.getLogger("ServiceDiscoveryTest")

class MockServiceDiscoveryServer:
    """
    Mock service discovery server for testing service discovery integration.
    """
    
    def __init__(self, port: int = 7120):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.services = {}
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the mock service discovery server."""
        try:
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"Mock service discovery server started on port {self.port}")
            self.running = True
            self.thread = threading.Thread(target=self._run_server)
            self.thread.daemon = True
            self.thread.start()
            return True
        except Exception as e:
            logger.error(f"Failed to start mock service discovery server: {e}")
            return False
            
    def _run_server(self):
        """Run the server loop."""
        while self.running:
            try:
                # Wait for a request
                request_data = self.socket.recv_json()
                logger.debug(f"Received request: {request_data}")
                
                # Process the request
                command = request_data.get("command")
                if command == "register":
                    response = self._handle_register(request_data)
                elif command == "discover":
                    response = self._handle_discover(request_data)
                elif command == "list":
                    response = self._handle_list()
                else:
                    response = {"status": "ERROR", "message": f"Unknown command: {command}"}
                
                # Send the response
                self.socket.send_json(response)
                
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error: {e}")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in server loop: {e}")
                time.sleep(0.1)
                
    def _handle_register(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a register request."""
        try:
            name = request.get("name")
            if not name:
                return {"status": "ERROR", "message": "Missing service name"}
                
            ip = request.get("ip", "localhost")
            port = request.get("port")
            if not port:
                return {"status": "ERROR", "message": "Missing service port"}
                
            # Register the service
            self.services[name] = {
                "name": name,
                "ip": ip,
                "port": port,
                "additional_info": request.get("additional_info", {}),
                "registered_at": time.time()
            }
            
            logger.info(f"Registered service: {name} at {ip}:{port}")
            return {
                "status": "SUCCESS",
                "message": f"Service {name} registered successfully",
                "service_id": name
            }
            
        except Exception as e:
            logger.error(f"Error handling register request: {e}")
            return {"status": "ERROR", "message": str(e)}
            
    def _handle_discover(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a discover request."""
        try:
            name = request.get("name")
            if not name:
                return {"status": "ERROR", "message": "Missing service name"}
                
            # Find the service
            service = self.services.get(name)
            if not service:
                return {
                    "status": "ERROR",
                    "message": f"Service {name} not found"
                }
                
            logger.info(f"Service discovered: {name}")
            return {
                "status": "SUCCESS",
                "message": f"Service {name} found",
                "payload": service
            }
            
        except Exception as e:
            logger.error(f"Error handling discover request: {e}")
            return {"status": "ERROR", "message": str(e)}
            
    def _handle_list(self) -> Dict[str, Any]:
        """Handle a list request."""
        try:
            return {
                "status": "SUCCESS",
                "message": f"Found {len(self.services)} services",
                "services": list(self.services.values())
            }
        except Exception as e:
            logger.error(f"Error handling list request: {e}")
            return {"status": "ERROR", "message": str(e)}
            
    def stop(self):
        """Stop the mock service discovery server."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        logger.info("Mock service discovery server stopped")

class ServiceDiscoveryTester:
    """
    Tests service discovery integration across agents.
    """
    
    def __init__(self, server_port: int = 7120, test_service_port: int = 9876):
        self.server_port = server_port
        self.test_service_port = test_service_port
        self.server = MockServiceDiscoveryServer(port=server_port)
        self.context = zmq.Context()
        self.test_services = {}
        
    def setup(self) -> bool:
        """Set up the test environment."""
        # Start the mock service discovery server
        if not self.server.start():
            logger.error("Failed to start mock service discovery server")
            return False
            
        # Register test services
        test_services = [
            {"name": "TestService1", "port": self.test_service_port},
            {"name": "TestService2", "port": self.test_service_port + 1},
            {"name": "TestService3", "port": self.test_service_port + 2}
        ]
        
        for service in test_services:
            self._register_test_service(service["name"], service["port"])
            
        return True
        
    def _register_test_service(self, name: str, port: int) -> bool:
        """Register a test service with the mock service discovery server."""
        try:
            # Create a socket to register the service
            socket = self.context.socket(zmq.REQ)
            socket.connect(f"tcp://localhost:{self.server_port}")
            
            # Send registration request
            request = {
                "command": "register",
                "name": name,
                "ip": "localhost",
                "port": port,
                "additional_info": {
                    "test": True,
                    "description": f"Test service {name}"
                }
            }
            socket.send_json(request)
            
            # Wait for response
            response = socket.recv_json()
            socket.close()
            
            if response.get("status") == "SUCCESS":
                logger.info(f"Registered test service: {name}")
                self.test_services[name] = port
                return True
            else:
                logger.error(f"Failed to register test service {name}: {response.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering test service {name}: {e}")
            return False
            
    def test_service_discovery(self, agent_module_path: str) -> Dict[str, Any]:
        """Test service discovery integration in an agent module."""
        results = {
            "module": agent_module_path,
            "success": False,
            "can_import": False,
            "can_discover": False,
            "errors": []
        }
        
        try:
            # Import the agent module
            sys.path.insert(0, os.path.dirname(agent_module_path))
            module_name = os.path.basename(agent_module_path).replace(".py", "")
            
            try:
                module = __import__(module_name)
                results["can_import"] = True
            except ImportError as e:
                results["errors"].append(f"Failed to import module: {e}")
                return results
                
            # Check if the module uses service discovery
            uses_discovery = False
            with open(agent_module_path, "r") as f:
                content = f.read()
                uses_discovery = (
                    "service_discovery_client" in content or
                    "discover_service" in content or
                    "get_service_address" in content or
                    "register_service" in content
                )
                
            if not uses_discovery:
                results["errors"].append("Module does not use service discovery")
                return results
                
            # Test service discovery functions if available
            if hasattr(module, "get_service_address"):
                # Test get_service_address
                for service_name in self.test_services:
                    try:
                        address = module.get_service_address(service_name)
                        if address:
                            logger.info(f"Successfully discovered {service_name} at {address}")
                            results["can_discover"] = True
                        else:
                            results["errors"].append(f"Failed to discover {service_name}")
                    except Exception as e:
                        results["errors"].append(f"Error discovering {service_name}: {e}")
                        
            elif hasattr(module, "discover_service"):
                # Test discover_service
                for service_name in self.test_services:
                    try:
                        response = module.discover_service(service_name)
                        if response and response.get("status") == "SUCCESS":
                            logger.info(f"Successfully discovered {service_name}")
                            results["can_discover"] = True
                        else:
                            results["errors"].append(f"Failed to discover {service_name}")
                    except Exception as e:
                        results["errors"].append(f"Error discovering {service_name}: {e}")
            
            # Set success based on results
            results["success"] = results["can_import"] and results["can_discover"]
            
        except Exception as e:
            results["errors"].append(f"Unexpected error: {e}")
            
        return results
        
    def run_tests(self, agent_modules: List[str]) -> Dict[str, Any]:
        """Run service discovery tests on multiple agent modules."""
        test_results = {
            "total_modules": len(agent_modules),
            "successful_tests": 0,
            "failed_tests": 0,
            "module_results": []
        }
        
        for module_path in agent_modules:
            logger.info(f"Testing service discovery in {module_path}")
            results = self.test_service_discovery(module_path)
            test_results["module_results"].append(results)
            
            if results["success"]:
                test_results["successful_tests"] += 1
            else:
                test_results["failed_tests"] += 1
                
        return test_results
        
    def cleanup(self):
        """Clean up resources."""
        self.server.stop()
        if self.context:
            self.context.term()

def find_agent_modules(directory: str, pattern: str = "*agent*.py") -> List[str]:
    """Find agent modules in a directory."""
    agent_modules = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and "agent" in file.lower():
                agent_modules.append(os.path.join(root, file))
    return agent_modules

def print_test_results(results: Dict[str, Any]) -> None:
    """Print test results in a readable format."""
    print("\n" + "=" * 80)
    print(f"SERVICE DISCOVERY INTEGRATION TEST RESULTS")
    print("=" * 80)
    print(f"Total modules tested: {results['total_modules']}")
    print(f"Successful tests:     {results['successful_tests']}")
    print(f"Failed tests:         {results['failed_tests']}")
    print("-" * 80)
    
    # Print details for each module
    for module_result in results["module_results"]:
        status = "✅ PASS" if module_result["success"] else "❌ FAIL"
        module_name = os.path.basename(module_result["module"])
        print(f"{status} | {module_name}")
        
        if module_result["errors"]:
            for error in module_result["errors"]:
                print(f"       - {error}")
    
    print("=" * 80)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test service discovery integration across agents")
    parser.add_argument("--directory", "-d", default="main_pc_code/agents", help="Directory to search for agent modules")
    parser.add_argument("--server-port", "-p", type=int, default=7120, help="Port for mock service discovery server")
    parser.add_argument("--test-service-port", "-t", type=int, default=9876, help="Starting port for test services")
    parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    args = parser.parse_args()
    
    # Find agent modules
    agent_modules = find_agent_modules(args.directory)
    if not agent_modules:
        logger.error(f"No agent modules found in {args.directory}")
        return 1
        
    logger.info(f"Found {len(agent_modules)} agent modules")
    
    # Set up the tester
    tester = ServiceDiscoveryTester(
        server_port=args.server_port,
        test_service_port=args.test_service_port
    )
    
    try:
        # Set up the test environment
        if not tester.setup():
            logger.error("Failed to set up test environment")
            return 1
            
        # Run the tests
        results = tester.run_tests(agent_modules)
        
        # Print results
        print_test_results(results)
        
        # Save results to file if requested
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output}")
            
        # Return exit code based on results
        return 0 if results["failed_tests"] == 0 else 1
        
    finally:
        # Clean up
        tester.cleanup()

if __name__ == "__main__":
    sys.exit(main()) 