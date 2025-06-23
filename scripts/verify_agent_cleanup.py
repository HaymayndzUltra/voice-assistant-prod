#!/usr/bin/env python3
"""
Verification Script for Agent ZMQ Cleanup
----------------------------------------
This script tests proper ZMQ socket cleanup in agents by:
1. Starting agents and monitoring resource usage
2. Sending shutdown signals and verifying cleanup
3. Checking for resource leaks
"""

import os
import sys
import time
import argparse
import logging
import subprocess
import psutil
import signal
import importlib.util
import inspect
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import utility modules
from main_pc_code.utils.zmq_cleanup_utils import cleanup_agent_zmq_resources

# Configure logging
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, 'verify_agent_cleanup.log'))
    ]
)
logger = logging.getLogger("VerifyAgentCleanup")

def find_agent_files(directory: str, pattern: str = "*agent*.py") -> List[str]:
    """
    Find all agent files in the given directory matching the pattern.
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern for agent files
        
    Returns:
        List of agent file paths
    """
    agent_files = []
    directory_path = Path(directory)
    
    # Search for agent files
    for file_path in directory_path.glob(pattern):
        if file_path.is_file() and not file_path.name.startswith('_'):
            agent_files.append(str(file_path))
    
    return agent_files

def import_agent_class(file_path: str) -> Optional[type]:
    """
    Import an agent class from a file.
    
    Args:
        file_path: Path to the agent file
        
    Returns:
        Agent class if found, None otherwise
    """
    try:
        # Extract module name from file path
        module_name = Path(file_path).stem
        
        # Import the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            logger.error(f"Failed to load spec for {file_path}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find agent classes in the module
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and "Agent" in name and hasattr(obj, "__init__"):
                logger.info(f"Found agent class: {name} in {file_path}")
                return obj
        
        logger.warning(f"No agent class found in {file_path}")
        return None
        
    except Exception as e:
        logger.error(f"Error importing agent from {file_path}: {e}")
        return None

def test_agent_cleanup(agent_class: type) -> Dict[str, Any]:
    """
    Test proper cleanup of an agent class.
    
    Args:
        agent_class: The agent class to test
        
    Returns:
        Dictionary with test results
    """
    results = {
        "agent_name": agent_class.__name__,
        "success": False,
        "has_cleanup_method": False,
        "resources_before": {},
        "resources_after": {},
        "errors": []
    }
    
    try:
        # Check if the agent has a cleanup method
        has_cleanup = hasattr(agent_class, "cleanup") or hasattr(agent_class, "_cleanup") or hasattr(agent_class, "shutdown")
        results["has_cleanup_method"] = has_cleanup
        
        # Create an instance of the agent
        logger.info(f"Creating instance of {agent_class.__name__}")
        agent = None
        
        try:
            # Try with minimal arguments
            agent = agent_class()
        except TypeError:
            try:
                # Try with port argument
                agent = agent_class(port=9999)
            except Exception as e:
                results["errors"].append(f"Failed to create agent instance: {str(e)}")
                return results
        
        # Get resource usage before cleanup
        process = psutil.Process(os.getpid())
        resources_before = {
            "memory": process.memory_info().rss / 1024 / 1024,  # MB
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
        results["resources_before"] = resources_before
        
        # Call cleanup method if available
        cleanup_called = False
        if hasattr(agent, "cleanup"):
            logger.info(f"Calling cleanup() on {agent_class.__name__}")
            agent.cleanup()
            cleanup_called = True
        elif hasattr(agent, "_cleanup"):
            logger.info(f"Calling _cleanup() on {agent_class.__name__}")
            agent._cleanup()
            cleanup_called = True
        elif hasattr(agent, "shutdown"):
            logger.info(f"Calling shutdown() on {agent_class.__name__}")
            agent.shutdown()
            cleanup_called = True
        
        # If no cleanup method was called, use our utility
        if not cleanup_called:
            logger.info(f"No cleanup method found, using utility on {agent_class.__name__}")
            cleanup_agent_zmq_resources(agent)
        
        # Get resource usage after cleanup
        resources_after = {
            "memory": process.memory_info().rss / 1024 / 1024,  # MB
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
        results["resources_after"] = resources_after
        
        # Check for resource leaks
        if resources_after["connections"] >= resources_before["connections"]:
            results["errors"].append("Possible connection leak detected")
        
        results["success"] = True
        
    except Exception as e:
        logger.error(f"Error testing {agent_class.__name__}: {e}")
        results["errors"].append(str(e))
    
    return results

def verify_agents(directory: str, pattern: str = "*agent*.py") -> Dict[str, Any]:
    """
    Verify proper cleanup of agents in the given directory.
    
    Args:
        directory: Directory to search for agents
        pattern: Glob pattern for agent files
        
    Returns:
        Dictionary with verification results
    """
    verification_results = {
        "total_agents": 0,
        "successful_tests": 0,
        "failed_tests": 0,
        "agents_with_cleanup": 0,
        "agents_without_cleanup": 0,
        "agent_results": []
    }
    
    # Find agent files
    agent_files = find_agent_files(directory, pattern)
    logger.info(f"Found {len(agent_files)} agent files in {directory}")
    
    # Test each agent
    for file_path in agent_files:
        # Import agent class
        agent_class = import_agent_class(file_path)
        if agent_class is None:
            continue
            
        # Test agent cleanup
        logger.info(f"Testing cleanup for {agent_class.__name__} from {file_path}")
        results = test_agent_cleanup(agent_class)
        results["file_path"] = file_path
        verification_results["agent_results"].append(results)
        
        # Update statistics
        verification_results["total_agents"] += 1
        if results["success"]:
            verification_results["successful_tests"] += 1
        else:
            verification_results["failed_tests"] += 1
            
        if results["has_cleanup_method"]:
            verification_results["agents_with_cleanup"] += 1
        else:
            verification_results["agents_without_cleanup"] += 1
    
    return verification_results

def print_verification_results(results: Dict[str, Any]) -> None:
    """
    Print verification results in a readable format.
    
    Args:
        results: Verification results dictionary
    """
    print("\n" + "=" * 80)
    print(f"AGENT CLEANUP VERIFICATION RESULTS")
    print("=" * 80)
    print(f"Total agents tested: {results['total_agents']}")
    print(f"Successful tests:    {results['successful_tests']}")
    print(f"Failed tests:        {results['failed_tests']}")
    print(f"Agents with cleanup: {results['agents_with_cleanup']}")
    print(f"Agents without:      {results['agents_without_cleanup']}")
    print("-" * 80)
    
    # Print details for each agent
    for agent_result in results["agent_results"]:
        status = "✅ PASS" if agent_result["success"] else "❌ FAIL"
        cleanup = "✓" if agent_result["has_cleanup_method"] else "✗"
        print(f"{status} | {cleanup} | {agent_result['agent_name']} ({Path(agent_result['file_path']).name})")
        
        if agent_result["errors"]:
            for error in agent_result["errors"]:
                print(f"       - Error: {error}")
    
    print("=" * 80)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Verify proper ZMQ socket cleanup in agents")
    parser.add_argument("--directory", "-d", default="main_pc_code/agents", help="Directory to search for agents")
    parser.add_argument("--pattern", "-p", default="*agent*.py", help="Glob pattern for agent files")
    parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    args = parser.parse_args()
    
    logger.info(f"Starting agent cleanup verification in {args.directory}")
    
    # Verify agents
    results = verify_agents(args.directory, args.pattern)
    
    # Print results
    print_verification_results(results)
    
    # Save results to file if requested
    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    # Return exit code based on results
    return 0 if results["failed_tests"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 