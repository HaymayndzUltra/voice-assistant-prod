#!/usr/bin/env python3
"""
BaseAgent Migration Template - Phase 0 Day 6 Task 6C

This template provides the standardized pattern for migrating legacy agents
to inherit from BaseAgent, ensuring consistency and reliability.

Usage:
1. Use this as a reference for manual migration
2. Follow the step-by-step migration process
3. Validate each step before proceeding
"""

# ============================================================================
# MIGRATION TEMPLATE - STEP-BY-STEP GUIDE
# ============================================================================

"""
STEP 1: UPDATE IMPORTS
- Add BaseAgent import at the top
- Remove custom health check imports if any
- Ensure proper path management
"""

# BEFORE (Legacy pattern):
# import zmq
# import time
# import logging
# import threading

# AFTER (BaseAgent pattern):
import zmq
import time
import logging
import threading
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import BaseAgent - REQUIRED for all agents
from common.core.base_agent import BaseAgent

# Import standardized utilities
from common.utils.path_manager import PathManager
from common.config_manager import get_service_ip, get_service_url, get_redis_url

# Import JSON logger for standardized logging
from common.utils.logger_util import get_json_logger

"""
STEP 2: AGENT CLASS INHERITANCE
- Change class definition to inherit from BaseAgent
- Remove custom __init__ if it only handles basic setup
- Call super().__init__() with proper parameters
"""

# BEFORE (Legacy pattern):
# class MyLegacyAgent:
#     def __init__(self):
#         self.context = zmq.Context()
#         self.port = 7100
#         # ... custom initialization

# AFTER (BaseAgent pattern):
class MigratedAgent(BaseAgent):
    """
    Example migrated agent inheriting from BaseAgent.
    
    This template shows the standard pattern for BaseAgent migration.
    """
    
    def __init__(self, port: Optional[int] = None, health_check_port: Optional[int] = None, **kwargs):
        """
        Initialize the migrated agent with BaseAgent inheritance.
        
        Args:
            port: Main service port (optional, will auto-assign if not provided)
            health_check_port: Health check port (optional, defaults to port+1)
            **kwargs: Additional configuration parameters
        """
        # CRITICAL: Call BaseAgent.__init__() FIRST
        super().__init__(
            name=kwargs.get('name', 'MigratedAgent'),
            port=port,
            health_check_port=health_check_port,
            **kwargs
        )
        
        # Get JSON logger for standardized logging
        self.logger = get_json_logger(self.name)
        
        # Initialize agent-specific attributes AFTER BaseAgent init
        self.agent_specific_data = {}
        self.custom_config = kwargs.get('config', {})
        
        # Custom socket setup (if needed beyond BaseAgent's default)
        self._setup_custom_sockets()
        
        # Agent-specific initialization
        self._initialize_agent_features()
        
        self.logger.info(f"{self.name} initialized successfully", extra={
            "port": self.port,
            "health_check_port": self.health_check_port,
            "component": "initialization"
        })
    
    def _setup_custom_sockets(self):
        """Set up any custom ZMQ sockets beyond BaseAgent defaults."""
        # Example: Publisher socket for metrics
        try:
            self.publisher = self.context.socket(zmq.PUB)
            pub_port = self.port + 100  # Offset for publisher
            self.publisher.bind(f"tcp://*:{pub_port}")
            self.logger.info(f"Publisher socket bound to port {pub_port}")
        except Exception as e:
            self.logger.error(f"Failed to set up publisher socket: {e}")
            raise
    
    def _initialize_agent_features(self):
        """Initialize agent-specific features and data structures."""
        # Example: Initialize metrics collection
        self.metrics = {
            'requests_processed': 0,
            'errors_encountered': 0,
            'last_activity': time.time()
        }
        
        # Example: Start background threads if needed
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start any background tasks required by the agent."""
        # Example: Metrics collection thread
        self.metrics_thread = threading.Thread(
            target=self._metrics_collection_loop,
            daemon=True
        )
        self.metrics_thread.start()

"""
STEP 3: REMOVE CUSTOM HEALTH CHECKS
- Remove custom health check socket creation
- Remove custom health check HTTP servers
- BaseAgent provides standardized /health endpoint
"""

# BEFORE (Legacy pattern - REMOVE THIS):
# def setup_health_check(self):
#     self.health_socket = self.context.socket(zmq.REP)
#     self.health_socket.bind(f"tcp://*:{self.health_port}")

# AFTER (BaseAgent pattern - NO CUSTOM HEALTH CHECK NEEDED):
# BaseAgent automatically provides:
# - /health HTTP endpoint
# - ZMQ health socket
# - Standardized health responses

"""
STEP 4: IMPLEMENT AGENT-SPECIFIC METHODS
- Keep all business logic methods
- Update method signatures if needed
- Use standardized logging patterns
"""

    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Example business logic method - keep these as-is but update logging.
        
        Args:
            request_data: Input data to process
            
        Returns:
            Processed result data
        """
        try:
            self.logger.info("Processing request", extra={
                "request_id": request_data.get('id'),
                "component": "request_processing"
            })
            
            # Original business logic goes here
            result = {
                'status': 'success',
                'processed_at': datetime.now().isoformat(),
                'input_data': request_data
            }
            
            # Update metrics
            self.metrics['requests_processed'] += 1
            self.metrics['last_activity'] = time.time()
            
            self.logger.info("Request processed successfully", extra={
                "request_id": request_data.get('id'),
                "component": "request_processing"
            })
            
            return result
            
        except Exception as e:
            self.metrics['errors_encountered'] += 1
            self.logger.error(f"Error processing request: {e}", extra={
                "request_id": request_data.get('id'),
                "component": "request_processing",
                "error": str(e)
            })
            raise
    
    def _metrics_collection_loop(self):
        """Background metrics collection - example background task."""
        while self.running:
            try:
                # Collect and publish metrics
                current_metrics = {
                    'timestamp': time.time(),
                    'agent_name': self.name,
                    'port': self.port,
                    'metrics': self.metrics.copy()
                }
                
                # Publish to metrics topic
                if hasattr(self, 'publisher'):
                    self.publisher.send_string(
                        "metrics",
                        zmq.SNDMORE
                    )
                    self.publisher.send_string(
                        json.dumps(current_metrics)
                    )
                
                time.sleep(30)  # Metrics collection interval
                
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                time.sleep(5)  # Short delay on error

"""
STEP 5: UPDATE MAIN EXECUTION BLOCK
- Use BaseAgent's run() method
- Remove custom event loops
- Ensure proper cleanup
"""

    def run(self):
        """
        Main execution method - override if custom behavior needed.
        
        BaseAgent.run() provides:
        - Initialization sequence
        - Health check server startup
        - Error handling setup
        - Graceful shutdown handling
        """
        try:
            self.logger.info(f"Starting {self.name}")
            
            # Call parent run() method for standard startup
            super().run()
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested via KeyboardInterrupt")
        except Exception as e:
            self.logger.error(f"Fatal error in {self.name}: {e}")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        """
        Cleanup method - override to add custom cleanup logic.
        
        BaseAgent.cleanup() handles:
        - Socket cleanup
        - Thread termination
        - Resource deallocation
        """
        try:
            self.logger.info(f"Cleaning up {self.name}")
            
            # Custom cleanup logic
            if hasattr(self, 'publisher'):
                self.publisher.close()
            
            # Call parent cleanup
            super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

# BEFORE (Legacy pattern - REPLACE THIS):
# if __name__ == "__main__":
#     agent = MyLegacyAgent()
#     try:
#         agent.start()
#     except KeyboardInterrupt:
#         agent.stop()

# AFTER (BaseAgent pattern):
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description=f"Run {MigratedAgent.__name__}")
    parser.add_argument('--port', type=int, help='Main service port')
    parser.add_argument('--health-port', type=int, help='Health check port')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Create and run agent
    agent = MigratedAgent(
        port=args.port,
        health_check_port=args.health_port,
        config_file=args.config
    )
    
    agent.run()


# ============================================================================
# MIGRATION CHECKLIST
# ============================================================================

"""
MIGRATION VALIDATION CHECKLIST:

□ STEP 1: Imports Updated
  □ BaseAgent import added
  □ Removed custom health check imports
  □ Path management imports added

□ STEP 2: Class Inheritance
  □ Class inherits from BaseAgent
  □ super().__init__() called first in __init__
  □ Proper name parameter passed to BaseAgent

□ STEP 3: Health Checks Removed
  □ Custom health check sockets removed
  □ Custom health HTTP servers removed
  □ No conflicting health endpoints

□ STEP 4: Business Logic Preserved
  □ All original functionality maintained
  □ Logging updated to use JSON logger
  □ Error handling uses BaseAgent patterns

□ STEP 5: Main Block Updated
  □ Uses BaseAgent.run() method
  □ Proper argument parsing
  □ Clean startup/shutdown cycle

□ VALIDATION TESTS:
  □ Agent starts without errors
  □ Health endpoint responds: curl http://localhost:{health_port}/health
  □ Main functionality works as expected
  □ Metrics appear in ObservabilityHub
  □ Clean shutdown with Ctrl+C

□ DEPLOYMENT READY:
  □ All tests pass
  □ No regressions detected
  □ Backup created before migration
  □ Rollback plan documented
"""

# ============================================================================
# MIGRATION AUTOMATION HELPERS
# ============================================================================

def validate_migration(agent_file: str) -> bool:
    """
    Validate that an agent file has been properly migrated to BaseAgent.
    
    Args:
        agent_file: Path to the agent file to validate
        
    Returns:
        True if migration appears successful, False otherwise
    """
    try:
        with open(agent_file, 'r') as f:
            content = f.read()
        
        # Check for required patterns
        checks = [
            'from common.core.base_agent import BaseAgent',
            'class', # Has a class definition
            'BaseAgent)', # Inherits from BaseAgent
            'super().__init__', # Calls parent constructor
        ]
        
        for check in checks:
            if check not in content:
                print(f"❌ Missing: {check}")
                return False
                
        print(f"✅ {agent_file} appears to be properly migrated")
        return True
        
    except Exception as e:
        print(f"❌ Error validating {agent_file}: {e}")
        return False


def create_backup(agent_file: str) -> str:
    """
    Create a backup of an agent file before migration.
    
    Args:
        agent_file: Path to the agent file to backup
        
    Returns:
        Path to the backup file
    """
    backup_file = f"{agent_file}.backup.{int(time.time())}"
    
    try:
        import shutil
        shutil.copy2(agent_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
        return backup_file
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        raise


if __name__ == "__main__":
    # Template usage example
    print("BaseAgent Migration Template - Phase 0 Day 6")
    print("=" * 50)
    print("This template provides the standard pattern for migrating legacy agents.")
    print("Follow the step-by-step guide in the comments above.")
    print("\nFor validation, run:")
    print("  python baseagent_migration_template.py --validate <agent_file>")
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--validate' and len(sys.argv) > 2:
        validate_migration(sys.argv[2]) 