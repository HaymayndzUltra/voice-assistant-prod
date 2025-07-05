#!/usr/bin/env python3
"""
Test Script for Systemic Stability Improvements

This script tests the implemented components to ensure they work correctly:
1. Tests the PathManager for path resolution
2. Tests the Agent Supervisor for process management
3. Tests the Configuration Manager for configuration handling
4. Tests the Logging Manager for logging capabilities
"""

import os
import sys
import time
import json
import argparse
import threading
from pathlib import Path
from typing import Optional, Dict, Any, cast

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the components
from main_pc_code.utils.path_manager import PathManager
from main_pc_code.utils.agent_supervisor import AgentSupervisor
from main_pc_code.utils.config_manager import ConfigManager, get_config, update_config
from main_pc_code.utils.log_manager import get_logger, log_event, log_metric, log_exception

# Set up logger
logger = get_logger("test_stability")

def test_path_manager():
    """Test the PathManager component."""
    logger.info("Testing PathManager...")
    
    # Test project root resolution
    project_root = PathManager.get_project_root()
    logger.info(f"Project root: {project_root}")
    assert project_root.exists(), "Project root does not exist"
    
    # Test config directory resolution
    config_dir = PathManager.get_config_dir()
    logger.info(f"Config directory: {config_dir}")
    assert config_dir.exists(), "Config directory does not exist"
    
    # Test logs directory resolution
    logs_dir = PathManager.get_logs_dir()
    logger.info(f"Logs directory: {logs_dir}")
    assert logs_dir.exists(), "Logs directory does not exist"
    
    # Test path resolution
    test_path = "main_pc_code/utils/path_manager.py"
    resolved_path = PathManager.resolve_path(test_path)
    logger.info(f"Resolved path: {resolved_path}")
    assert resolved_path.exists(), f"Resolved path {resolved_path} does not exist"
    
    logger.info("PathManager tests passed")
    return True

def test_config_manager():
    """Test the ConfigManager component."""
    logger.info("Testing ConfigManager...")
    
    # Create a test configuration
    test_config = {
        "test_section": {
            "string_value": "test",
            "int_value": 123,
            "bool_value": True,
            "list_value": [1, 2, 3],
            "dict_value": {
                "nested": "value"
            }
        },
        "development": {
            "test_section": {
                "string_value": "development"
            }
        },
        "production": {
            "test_section": {
                "string_value": "production"
            }
        }
    }
    
    # Save configuration
    result = ConfigManager.save_config("test_config", test_config)
    logger.info(f"Save configuration result: {result}")
    assert result, "Failed to save configuration"
    
    # Load configuration
    loaded_config = ConfigManager.load_config("test_config")
    logger.info(f"Loaded configuration: {loaded_config}")
    assert "test_section" in loaded_config, "Missing section in loaded configuration"
    
    # Get configuration value
    string_value = ConfigManager.get_config("test_config", "test_section.string_value")
    logger.info(f"String value: {string_value}")
    
    # Test environment overrides
    prev_env = os.environ.get("ENV")
    try:
        os.environ["ENV"] = "development"
        dev_config = ConfigManager.load_config("test_config", reload=True)
        logger.info(f"Development configuration: {dev_config}")
        assert dev_config["test_section"]["string_value"] == "development", "Environment override failed"
        
        os.environ["ENV"] = "production"
        prod_config = ConfigManager.load_config("test_config", reload=True)
        logger.info(f"Production configuration: {prod_config}")
        assert prod_config["test_section"]["string_value"] == "production", "Environment override failed"
    finally:
        # Restore original environment
        if prev_env:
            os.environ["ENV"] = prev_env
        else:
            os.environ.pop("ENV", None)
    
    # Update configuration
    update_result = ConfigManager.update_config("test_config", {
        "test_section": {
            "new_value": "added"
        }
    })
    logger.info(f"Update configuration result: {update_result}")
    assert update_result, "Failed to update configuration"
    
    # Verify update
    updated_config = ConfigManager.load_config("test_config", reload=True)
    logger.info(f"Updated configuration: {updated_config}")
    assert updated_config["test_section"].get("new_value") == "added", "Configuration update failed"
    
    logger.info("ConfigManager tests passed")
    return True

def test_logging_manager():
    """Test the LogManager component."""
    logger.info("Testing LogManager...")
    
    # Test structured logging
    extra_data = {
        "test_key": "test_value",
        "numeric_value": 123,
        "bool_value": True
    }
    logger.info("Testing structured logging", extra={"data": json.dumps(extra_data)})
    
    # Test metrics
    log_metric("test", "test_metric", 123)
    log_metric("test", "another_metric", "string_value")
    
    # Test exception logging
    try:
        # Cause an exception
        raise ValueError("Test exception")
    except Exception as e:
        log_exception("test", e, "Caught test exception", {
            "context": "test_logging_manager"
        })
    
    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    logger.info("LogManager tests passed")
    return True

def test_agent_supervisor(test_config_path: Optional[str] = None):
    """Test the AgentSupervisor component."""
    logger.info("Testing AgentSupervisor...")
    
    # Initialize supervisor with proper type casting to handle None
    config_path = test_config_path if test_config_path is not None else ""
    supervisor = AgentSupervisor(config_path=config_path)
    
    # Test agent management directly
    if test_config_path is None:
        logger.info("No test config provided, testing agent supervisor with sample agent")
        
        # Create a simple test agent
        from main_pc_code.utils.agent_supervisor import AgentProcess
        
        # Find a Python script to use as a test agent
        test_script = PathManager.resolve_path("main_pc_code/utils/path_manager.py")
        
        # Create an agent process
        agent = AgentProcess(
            name="test_agent",
            path=str(test_script),
            port=9999,
            health_port=10000
        )
        
        # Add to supervisor
        supervisor.agents["test_agent"] = agent
        
        # Start the agent
        start_result = agent.start()
        logger.info(f"Agent start result: {start_result}")
        
        # Wait a bit
        time.sleep(2)
        
        # Stop the agent
        stop_result = agent.stop()
        logger.info(f"Agent stop result: {stop_result}")
    else:
        # Load agents from config
        logger.info(f"Testing agent supervisor with config: {test_config_path}")
        
        # Start all agents
        supervisor.start_all()
        
        # Wait for them to start
        time.sleep(5)
        
        # Check health
        health = supervisor.check_health()
        logger.info(f"Agent health: {health}")
        
        # Stop all agents
        supervisor.stop_all()
    
    logger.info("AgentSupervisor tests passed")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test systemic stability improvements")
    parser.add_argument("--path-manager", action="store_true", help="Test PathManager")
    parser.add_argument("--config-manager", action="store_true", help="Test ConfigManager")
    parser.add_argument("--log-manager", action="store_true", help="Test LogManager")
    parser.add_argument("--agent-supervisor", action="store_true", help="Test AgentSupervisor")
    parser.add_argument("--test-config", help="Path to test configuration for AgentSupervisor")
    parser.add_argument("--all", action="store_true", help="Test all components")
    args = parser.parse_args()
    
    # If no specific tests are selected, test all
    if not any([args.path_manager, args.config_manager, args.log_manager, args.agent_supervisor, args.all]):
        args.all = True
    
    # Run tests
    if args.path_manager or args.all:
        if not test_path_manager():
            logger.error("PathManager tests failed")
            return 1
    
    if args.config_manager or args.all:
        if not test_config_manager():
            logger.error("ConfigManager tests failed")
            return 1
    
    if args.log_manager or args.all:
        if not test_logging_manager():
            logger.error("LogManager tests failed")
            return 1
    
    if args.agent_supervisor or args.all:
        if not test_agent_supervisor(args.test_config):
            logger.error("AgentSupervisor tests failed")
            return 1
    
    logger.info("All tests passed")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 