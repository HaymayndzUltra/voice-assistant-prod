#!/usr/bin/env python3
"""
PC2 Container Testing Script

This script performs a comprehensive test of PC2 containers to verify their
health, connectivity, and basic functionality.

Usage:
    python test_pc2_containers.py [--containers all|core|memory|ai|user|monitoring]
"""

import sys
import time
import json
import argparse
import subprocess
import requests
from typing import Dict, Tuple
import logging
from common.env_helpers import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pc2_container_test")

# Constants
DEFAULT_TIMEOUT = 5  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Define container groups to test
CONTAINER_GROUPS = {
    "core": ["ai-system-pc2-core", "ai-system-pc2-redis"],
    "memory": ["ai-system-pc2-memory"],
    "ai": ["ai-system-pc2-ai-models", "ai-system-pc2-translation"],
    "user": ["ai-system-pc2-user-services"],
    "monitoring": ["ai-system-pc2-ai-monitoring"]
}

class ContainerTester:
    """Class to test Docker containers in the PC2 system."""
    
    def __init__(self):
        self.results = {
            "container_health": {},
            "agent_health": {},
            "connectivity": {},
            "functionality": {},
            "summary": {
                "passed": 0,
                "failed": 0,
                "skipped": 0
            }
        }
    
    def check_container_running(self, container_name: str) -> bool:
        """Check if a container is running."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", container_name],
                capture_output=True,
                text=True,
                check=False
            )
            return result.stdout.strip() == "true"
        except Exception as e:
            logger.error(f"Error checking container {container_name}: {e}")
            return False
    
    def check_container_health(self, container_name: str) -> str:
        """Check the health status of a container."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_name],
                capture_output=True,
                text=True,
                check=False
            )
            status = result.stdout.strip()
            if not status:
                # Container doesn't have health check
                return "no-healthcheck"
            return status
        except Exception as e:
            logger.error(f"Error checking health for {container_name}: {e}")
            return "unknown"
    
    def check_agent_health(self, agent_name: str, host: str, port: int) -> Tuple[bool, Dict]:
        """Check the health of an agent via its health check endpoint."""
        url = f"http://{host}:{port}/health"
        for _ in range(MAX_RETRIES):
            try:
                response = requests.get(url, timeout=DEFAULT_TIMEOUT)
                if response.status_code == 200:
                    return True, response.json()
                time.sleep(RETRY_DELAY)
            except requests.RequestException:
                time.sleep(RETRY_DELAY)
        return False, {"status": "unreachable"}
    
    def check_connectivity(self, source_container: str, target_host: str, target_port: int) -> bool:
        """Check if a container can connect to a target host:port."""
        try:
            cmd = f"docker exec {source_container} timeout {DEFAULT_TIMEOUT} bash -c 'nc -zv {target_host} {target_port} 2>&1'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
            return "succeeded" in result.stdout.lower() or "open" in result.stdout.lower()
        except Exception as e:
            logger.error(f"Error checking connectivity from {source_container} to {target_host}:{target_port}: {e}")
            return False
    
    def test_memory_service(self, host: str = get_env("BIND_ADDRESS", "0.0.0.0"), port: int = 7140) -> Dict:
        """Test the Memory Orchestrator Service functionality."""
        test_key = f"test_key_{int(time.time())}"
        test_value = {"test": "data", "timestamp": time.time()}
        
        try:
            # Test storing data
            store_url = f"http://{host}:{port}/memory/store"
            store_response = requests.post(
                store_url,
                json={"key": test_key, "value": test_value},
                timeout=DEFAULT_TIMEOUT
            )
            
            if store_response.status_code != 200:
                return {"success": False, "error": f"Failed to store data: {store_response.text}"}
            
            # Test retrieving data
            retrieve_url = f"http://{host}:{port}/memory/retrieve"
            retrieve_response = requests.get(
                retrieve_url,
                params={"key": test_key},
                timeout=DEFAULT_TIMEOUT
            )
            
            if retrieve_response.status_code != 200:
                return {"success": False, "error": f"Failed to retrieve data: {retrieve_response.text}"}
            
            # Compare stored and retrieved data
            retrieved_data = retrieve_response.json()
            if retrieved_data.get("test") == test_value["test"]:
                return {"success": True, "message": "Memory service store/retrieve test passed"}
            else:
                return {"success": False, "error": "Retrieved data doesn't match stored data"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_container_group(self, group: str) -> None:
        """Test all containers in a specified group."""
        if group not in CONTAINER_GROUPS:
            logger.error(f"Invalid container group: {group}")
            return
        
        containers = CONTAINER_GROUPS[group]
        logger.info(f"Testing {group} container group: {containers}")
        
        # Test container health
        for container in containers:
            is_running = self.check_container_running(container)
            health_status = self.check_container_health(container)
            
            self.results["container_health"][container] = {
                "running": is_running,
                "health_status": health_status,
                "passed": is_running and (health_status == "healthy" or health_status == "no-healthcheck")
            }
            
            if self.results["container_health"][container]["passed"]:
                self.results["summary"]["passed"] += 1
            else:
                self.results["summary"]["failed"] += 1
        
        # Test connectivity between containers
        if group == "core":
            # Test core container connectivity
            for container in containers:
                for target in ["ai-system-pc2-memory:7140", "ai-system-pc2-redis:6379"]:
                    target_host, target_port = target.split(":")
                    can_connect = self.check_connectivity(container, target_host, int(target_port))
                    
                    self.results["connectivity"][f"{container}_to_{target_host}"] = {
                        "connected": can_connect,
                        "passed": can_connect
                    }
                    
                    if can_connect:
                        self.results["summary"]["passed"] += 1
                    else:
                        self.results["summary"]["failed"] += 1
        
        # Test specific functionality
        if group == "memory":
            memory_test_result = self.test_memory_service()
            self.results["functionality"]["memory_service"] = {
                "test": "store_retrieve",
                "passed": memory_test_result["success"],
                "details": memory_test_result
            }
            
            if memory_test_result["success"]:
                self.results["summary"]["passed"] += 1
            else:
                self.results["summary"]["failed"] += 1
    
    def run_all_tests(self) -> Dict:
        """Run all container tests and return results."""
        for group in CONTAINER_GROUPS:
            self.test_container_group(group)
        
        self.results["overall_success"] = self.results["summary"]["failed"] == 0
        return self.results


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(description="Test PC2 containers")
    parser.add_argument(
        "--containers",
        choices=["all"] + list(CONTAINER_GROUPS.keys()),
        default="all",
        help="Which container groups to test"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for JSON results"
    )
    args = parser.parse_args()
    
    tester = ContainerTester()
    
    if args.containers == "all":
        results = tester.run_all_tests()
    else:
        tester.test_container_group(args.containers)
        results = tester.results
    
    # Print results
    print(f"\n{'='*50}")
    print("PC2 CONTAINER TEST RESULTS")
    print(f"{'='*50}")
    
    print("\nCONTAINER HEALTH:")
    for container, data in results.get("container_health", {}).items():
        status = "✅ PASSED" if data.get("passed") else "❌ FAILED"
        print(f"  {container}: {status} (Running: {data.get('running')}, Health: {data.get('health_status')})")
    
    print("\nCONNECTIVITY TESTS:")
    for connection, data in results.get("connectivity", {}).items():
        status = "✅ PASSED" if data.get("passed") else "❌ FAILED"
        print(f"  {connection}: {status}")
    
    print("\nFUNCTIONALITY TESTS:")
    for test, data in results.get("functionality", {}).items():
        status = "✅ PASSED" if data.get("passed") else "❌ FAILED"
        print(f"  {test}: {status}")
    
    print("\nSUMMARY:")
    summary = results.get("summary", {})
    print(f"  Passed: {summary.get('passed', 0)}")
    print(f"  Failed: {summary.get('failed', 0)}")
    print(f"  Skipped: {summary.get('skipped', 0)}")
    
    overall = "✅ PASSED" if results.get("overall_success") else "❌ FAILED"
    print(f"\nOVERALL RESULT: {overall}")
    
    # Save results to file if requested
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {args.output}")
        except Exception as e:
            print(f"\nError saving results: {e}")
    
    return 0 if results.get("overall_success") else 1


if __name__ == "__main__":
    sys.exit(main()) 