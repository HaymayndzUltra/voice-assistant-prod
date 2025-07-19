#!/usr/bin/env python3
"""
Memory Scheduler Agent

This agent handles scheduled memory operations:
- Memory decay over time
- Consolidation of related memories
- Archiving of old, low-importance memories
- Memory relationship management
"""

import os
import sys
import time
import json
import logging
import threading
import zmq
import schedule  # Package is now installed
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project's pc2_code directory to the Python path
PC2_CODE_DIR = get_main_pc_code()
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())

# Add the project's root directory to the Python path
ROOT_DIR = PC2_CODE_DIR.parent
if ROOT_DIR.as_posix() not in sys.path:
    sys.path.insert(0, ROOT_DIR.as_posix())

from common.core.base_agent import BaseAgent

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
from common.env_helpers import get_env


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(join_path("logs", "memory_scheduler.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MemoryScheduler")

class MemoryScheduler(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()"""
    Memory Scheduler Agent
    
    Handles scheduled memory operations to maintain the health and efficiency
    of the memory system. Works in conjunction with MemoryOrchestratorService.
    """
    
    def __init__(self, port: int = 7142, health_check_port: int = 7143, **kwargs):
        super().__init__(name="MemoryScheduler", port=port, health_check_port=health_check_port, **kwargs)
        
        # Configuration
        self.memory_orchestrator_host = os.environ.get("PC2_IP", get_env("BIND_ADDRESS", "0.0.0.0"))
        self.memory_orchestrator_port = 7140
        self.memory_orchestrator_endpoint = f"tcp://{self.memory_orchestrator_host}:{self.memory_orchestrator_port}"
        
        # Error bus configuration
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        
        # ZMQ setup
        self.orchestrator_socket = None
        self.error_bus_pub = None
        self._setup_zmq()
        
        # Schedule configuration
        self.decay_interval_hours = 24  # Run decay once per day
        self.consolidation_interval_hours = 12  # Run consolidation twice per day
        self.cleanup_interval_days = 7  # Run cleanup once per week
        
        # Initialize schedules
        self._setup_schedules()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"{self.name} initialized successfully")
    
    def _setup_zmq(self):
        """Set up ZMQ connections"""
        try:
            # Connection to MemoryOrchestratorService
            self.orchestrator_socket = self.context.socket(zmq.REQ)
            self.orchestrator_socket.connect(self.memory_orchestrator_endpoint)
            self.orchestrator_socket.setsockopt(zmq.LINGER, 0)
            self.orchestrator_socket.setsockopt(zmq.RCVTIMEO, 5000)
            self.orchestrator_socket.setsockopt(zmq.SNDTIMEO, 5000)
            logger.info(f"Connected to MemoryOrchestratorService at {self.memory_orchestrator_endpoint}")
            
            # Connection to Error Bus
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            logger.info(f"Connected to error bus at {self.error_bus_endpoint}")
        except Exception as e:
            logger.error(f"Error setting up ZMQ connections: {e}")
            self._report_error("zmq_setup_error", str(e))
    
    def _setup_schedules(self):
        """Set up scheduled tasks"""
        # Schedule memory decay
        schedule.every(self.decay_interval_hours).hours.do(self.run_memory_decay)
        
        # Schedule memory consolidation
        schedule.every(self.consolidation_interval_hours).hours.do(self.run_memory_consolidation)
        
        # Schedule memory cleanup
        schedule.every(self.cleanup_interval_days).days.do(self.run_memory_cleanup)
        
        # Add a daily health check
        schedule.every().day.at("03:00").do(self.run_health_check)
        
        logger.info("Scheduled tasks configured")
    
    def _run_scheduler(self):
        """Run the scheduler in a background thread"""
        logger.info("Scheduler thread started")
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler thread: {e}")
                self._report_error("scheduler_error", str(e))
    
    def _send_to_orchestrator(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MemoryOrchestratorService"""
        try:
            if self.orchestrator_socket is None:
                logger.error("Orchestrator socket is not initialized")
                return {"status": "error", "message": "Orchestrator socket is not initialized"}
                
            self.orchestrator_socket.send_json(request)
            response = self.orchestrator_socket.recv_json()
            if not isinstance(response, dict):
                return {"status": "error", "message": "Invalid response from orchestrator"}
            return response
        except zmq.error.Again:
            logger.error("Request to MemoryOrchestratorService timed out")
            return {"status": "error", "message": "Request timed out"}
        except Exception as e:
            logger.error(f"Error communicating with MemoryOrchestratorService: {e}")
            return {"status": "error", "message": str(e)}
    
    def _report_error(self, error_type: str, error_message: str):
        """Report errors to the central error bus"""
        try:
            if self.error_bus_pub:
                error_data = {
                    "timestamp": time.time(),
                    "agent": self.name,
                    "error_type": error_type,
                    "message": error_message,
                    "severity": "ERROR"
                }
                self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")
    
    def run_memory_decay(self):
        """Run memory decay process"""
        logger.info("Starting memory decay process")
        try:
            # Get all memories that need decay
            request = {
                "action": "get_all_memories_for_lifecycle",
                "data": {}
            }
            response = self._send_to_orchestrator(request)
            
            if response.get("status") != "success":
                logger.error(f"Failed to get memories for decay: {response.get('message')}")
                return
            
            memories = response.get("memories", [])
            logger.info(f"Processing decay for {len(memories)} memories")
            
            # Process each memory
            for memory in memories:
                memory_id = memory.get("memory_id")
                if not memory_id:
                    continue
                
                # Apply decay
                decay_request = {
                    "action": "apply_decay",
                    "data": {
                        "memory_id": memory_id
                    }
                }
                decay_response = self._send_to_orchestrator(decay_request)
                
                if decay_response.get("status") != "success":
                    logger.warning(f"Failed to apply decay to memory {memory_id}: {decay_response.get('message')}")
            
            logger.info("Memory decay process completed")
        except Exception as e:
            logger.error(f"Error in memory decay process: {e}")
            self._report_error("decay_process_error", str(e))
    
    def run_memory_consolidation(self):
        """Run memory consolidation process"""
        logger.info("Starting memory consolidation process")
        try:
            # Get all short-term memories for consolidation
            request = {
                "action": "get_memories_for_consolidation",
                "data": {
                    "memory_tier": "short",
                    "min_age_hours": 24,  # Only consolidate memories at least 24 hours old
                    "max_importance": 0.5  # Only consolidate less important memories
                }
            }
            response = self._send_to_orchestrator(request)
            
            if response.get("status") != "success":
                logger.error(f"Failed to get memories for consolidation: {response.get('message')}")
                return
            
            memories = response.get("memories", [])
            logger.info(f"Processing consolidation for {len(memories)} memories")
            
            # Process each memory
            for memory in memories:
                memory_id = memory.get("memory_id")
                if not memory_id:
                    continue
                
                # Apply consolidation
                consolidate_request = {
                    "action": "consolidate_memory",
                    "data": {
                        "memory_id": memory_id
                    }
                }
                consolidate_response = self._send_to_orchestrator(consolidate_request)
                
                if consolidate_response.get("status") != "success":
                    logger.warning(f"Failed to consolidate memory {memory_id}: {consolidate_response.get('message')}")
            
            logger.info("Memory consolidation process completed")
        except Exception as e:
            logger.error(f"Error in memory consolidation process: {e}")
            self._report_error("consolidation_process_error", str(e))
    
    def run_memory_cleanup(self):
        """Run memory cleanup process (archive or delete very old, unimportant memories)"""
        logger.info("Starting memory cleanup process")
        try:
            # Get all old memories for cleanup
            request = {
                "action": "get_memories_for_cleanup",
                "data": {
                    "min_age_days": 90,  # Only clean up memories at least 90 days old
                    "max_importance": 0.1  # Only clean up very unimportant memories
                }
            }
            response = self._send_to_orchestrator(request)
            
            if response.get("status") != "success":
                logger.error(f"Failed to get memories for cleanup: {response.get('message')}")
                return
            
            memories = response.get("memories", [])
            logger.info(f"Processing cleanup for {len(memories)} memories")
            
            # Process each memory
            for memory in memories:
                memory_id = memory.get("memory_id")
                if not memory_id:
                    continue
                
                # Archive memory
                archive_request = {
                    "action": "archive_memory",
                    "data": {
                        "memory_id": memory_id
                    }
                }
                archive_response = self._send_to_orchestrator(archive_request)
                
                if archive_response.get("status") != "success":
                    logger.warning(f"Failed to archive memory {memory_id}: {archive_response.get('message')}")
            
            logger.info("Memory cleanup process completed")
        except Exception as e:
            logger.error(f"Error in memory cleanup process: {e}")
            self._report_error("cleanup_process_error", str(e))
    
    def run_health_check(self):
        """Run a health check on the memory system"""
        logger.info("Running memory system health check")
        try:
            # Get memory system status
            request = {
                "action": "get_memory_system_status",
                "data": {}
            }
            response = self._send_to_orchestrator(request)
            
            if response.get("status") != "success":
                logger.error(f"Memory system health check failed: {response.get('message')}")
                self._report_error("health_check_failed", response.get('message', 'Unknown error'))
                return
            
            status = response.get("system_status", {})
            
            # Log health metrics
            total_memories = status.get("total_memories", 0)
            memory_by_tier = status.get("memory_by_tier", {})
            db_size = status.get("db_size_mb", 0)
            cache_hit_rate = status.get("cache_hit_rate", 0)
            
            logger.info(f"Memory system health: {total_memories} total memories, DB size: {db_size} MB, Cache hit rate: {cache_hit_rate}%")
            logger.info(f"Memory distribution: {memory_by_tier}")
            
            # Check for issues
            issues = status.get("issues", [])
            if issues:
                for issue in issues:
                    logger.warning(f"Memory system issue: {issue}")
                    self._report_error("memory_system_issue", issue)
            
            logger.info("Memory system health check completed")
        except Exception as e:
            logger.error(f"Error in memory system health check: {e}")
            self._report_error("health_check_error", str(e))
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests"""
        action = request.get("action")
        data = request.get("data", {})
        
        if action == "health_check":
            return self.handle_health_check(data)
        elif action == "run_decay":
            self.run_memory_decay()
            return {"status": "success", "message": "Memory decay process started"}
        elif action == "run_consolidation":
            self.run_memory_consolidation()
            return {"status": "success", "message": "Memory consolidation process started"}
        elif action == "run_cleanup":
            self.run_memory_cleanup()
            return {"status": "success", "message": "Memory cleanup process started"}
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def handle_health_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check requests"""
        return {
            "status": "success",
            "agent": self.name,
            "uptime": time.time() - self.start_time,
            "scheduled_tasks": [
                {"name": "decay", "interval": f"{self.decay_interval_hours} hours"},
                {"name": "consolidation", "interval": f"{self.consolidation_interval_hours} hours"},
                {"name": "cleanup", "interval": f"{self.cleanup_interval_days} days"},
                {"name": "health_check", "schedule": "daily at 03:00"}
            ]
        }
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        logger.info("Cleaning up resources")
        if self.orchestrator_socket:
            self.orchestrator_socket.close()
        if self.error_bus_pub:
            self.error_bus_pub.close()
        super().cleanup()


    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "port": self.port,
            "health_port": getattr(self, "health_port", None),
            "error_reporting": bool(getattr(self, "error_bus", None))
        }
if __name__ == "__main__":
    try:
        scheduler = MemoryScheduler()
        scheduler.run()
    except KeyboardInterrupt:
        logger.info("MemoryScheduler shutting down")
    except Exception as e:
        logger.critical(f"MemoryScheduler failed to start: {e}", exc_info=True)
    finally:
        if 'scheduler' in locals() and hasattr(scheduler, 'cleanup'):
            scheduler.cleanup() 