#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Dreaming Mode Agent
------------------
Coordinates with DreamWorldAgent to manage system dreaming and simulation cycles.

Features:
- Manages dreaming intervals and schedules
- Coordinates with DreamWorldAgent for simulations
- Monitors system state for optimal dreaming times
- Provides dreaming insights and recommendations
- Handles dream world state transitions
- Manages dream memory and learning cycles

This agent uses ZMQ REP socket on port 7127 to receive commands and coordinate with other agents.
"""

import zmq
import json
import logging
import time
import threading
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import random


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", ".."))
from common.utils.path_manager import PathManager
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root)

# Import config parser utility with fallback
try:
from pc2_code.agents.utils.config_parser import parse_agent_args
    except ImportError as e:
        print(f"Import error: {e}")
    _agent_args 
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from common.env_helpers import get_env

# Load configuration at the module level
config = load_config()= parse_agent_args()
except ImportError:
    class DummyArgs(BaseAgent):
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = PathManager.join_path("logs", str(PathManager.get_logs_dir() / "dreaming_mode_agent.log")
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DreamingModeAgent")

# ZMQ ports
DREAMING_MODE_PORT = 7127
DREAMING_MODE_HEALTH_PORT = 7128
DREAM_WORLD_PORT = 7104  # DreamWorldAgent port

class DreamingModeAgent:
    """Dreaming Mode Agent for coordinating system dreaming cycles"""
    def __init__(self, port=None):
         super().__init__(name="DummyArgs", port=None)
self.main_port = port if port else DREAMING_MODE_PORT
        self.health_port = self.main_port + 1
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.main_port}")
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://*:{self.health_port}")
        logger.info(f"DreamingModeAgent health socket bound to port {self.health_port}")
        self.dreamworld_socket = self.context.socket(zmq.REQ)
        try:
            self.dreamworld_socket.connect(f"tcp://localhost:{DREAM_WORLD_PORT}")
            logger.info(f"Connected to DreamWorldAgent on port {DREAM_WORLD_PORT}")
        except Exception as e:
            logger.warning(f"Failed to connect to DreamWorldAgent: {e}")
            self.dreamworld_socket = None
        self.is_dreaming = False
        self.dream_thread = None
        self.running = True
        self.dream_interval = 3600
        self.last_dream_time = 0
        self.dream_duration = 300
        self.dream_count = 0
        self.total_dream_time = 0
        self.start_time = time.time()
        self.dream_memory = []
        self.dream_success_rate = 0.0
        self.avg_dream_quality = 0.0
        logger.info(f"DreamingModeAgent initialized on port {self.main_port}")

    def _health_check(self) -> Dict[str, Any]:
        return {
            'status': 'success',
            'agent': 'DreamingModeAgent',
            'timestamp': datetime.now().isoformat(),
            'is_dreaming': self.is_dreaming,
            'dream_count': self.dream_count,
            'total_dream_time': self.total_dream_time,
            'dream_success_rate': self.dream_success_rate,
            'avg_dream_quality': self.avg_dream_quality,
            'uptime': time.time() - self.start_time,
            'port': self.main_port,
            'dreamworld_connected': self.dreamworld_socket is not None
        }

    def start_dreaming(self) -> Dict[str, Any]:
        if self.is_dreaming:
            return {"status": "error", "message": "Already dreaming"}
        self.is_dreaming = True
        self.dream_count += 1
        dream_start_time = time.time()
        logger.info(f"Starting dream cycle #{self.dream_count}")
        self.dream_thread = threading.Thread(target=self._dream_cycle, daemon=True)
        self.dream_thread.start()
        return {"status": "success", "message": f"Dream cycle #{self.dream_count} started", "dream_id": self.dream_count, "start_time": dream_start_time}

    def stop_dreaming(self) -> Dict[str, Any]:
        if not self.is_dreaming:
            return {"status": "error", "message": "Not currently dreaming"}
        self.is_dreaming = False
        logger.info("Stopping dream cycle")
        return {"status": "success", "message": "Dream cycle stopped"}

    def _dream_cycle(self):
        try:
            dream_start = time.time()
            if self.dreamworld_socket:
                simulation_request = {"action": "run_simulation", "scenario": "ethical", "iterations": 100}
                try:
                    self.dreamworld_socket.send_json(simulation_request)
                    if self.dreamworld_socket.poll(30000):
                        response = self.dreamworld_socket.recv_json()
                        if response.get("status") == "success":
                            logger.info("Dream simulation completed successfully")
                            self._record_dream_result(True, response.get("quality", 0.5)
                        else:
                            logger.warning(f"Dream simulation failed: {response.get('error', 'Unknown error')}")
                            self._record_dream_result(False, 0.0)
                    else:
                        logger.warning("Dream simulation timeout")
                        self._record_dream_result(False, 0.0)
                except Exception as e:
                    logger.error(f"Error communicating with DreamWorldAgent: {e}")
                    self._record_dream_result(False, 0.0)
            else:
                logger.info("DreamWorldAgent not available, simulating dream cycle")
                time.sleep(self.dream_duration)
                self._record_dream_result(True, 0.5)
            dream_duration = time.time() - dream_start
            self.total_dream_time += dream_duration
            logger.info(f"Dream cycle completed in {dream_duration:.2f} seconds")
        except Exception as e:
            logger.error(f"Error in dream cycle: {e}")
            self._record_dream_result(False, 0.0)
        finally:
            self.is_dreaming = False

    def _record_dream_result(self, success: bool, quality: float):
        dream_record = {"timestamp": time.time(), "success": success, "quality": quality, "duration": self.dream_duration}
        self.dream_memory.append(dream_record)
        if len(self.dream_memory) > 100:
            self.dream_memory = self.dream_memory[-100:]
        successful_dreams = sum(1 for dream in self.dream_memory if dream["success"])
        self.dream_success_rate = successful_dreams / len(self.dream_memory) if self.dream_memory else 0.0
        total_quality = sum(dream["quality"] for dream in self.dream_memory)
        self.avg_dream_quality = total_quality / len(self.dream_memory) if self.dream_memory else 0.0

    def get_dream_status(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "is_dreaming": self.is_dreaming,
            "dream_count": self.dream_count,
            "total_dream_time": self.total_dream_time,
            "dream_success_rate": self.dream_success_rate,
            "avg_dream_quality": self.avg_dream_quality,
            "last_dream_time": self.last_dream_time,
            "next_dream_time": self.last_dream_time + self.dream_interval,
            "dream_interval": self.dream_interval,
            "recent_dreams": self.dream_memory[-10:] if self.dream_memory else []
        }

    def set_dream_interval(self, interval: int) -> Dict[str, Any]:
        if interval < 60:
            return {"status": "error", "message": "Dream interval must be at least 60 seconds"}
        self.dream_interval = interval
        logger.info(f"Dream interval set to {interval} seconds")
        return {"status": "success", "message": f"Dream interval updated to {interval} seconds", "new_interval": interval}

    def optimize_dream_schedule(self) -> Dict[str, Any]:
        if not self.dream_memory:
            return {"status": "error", "message": "No dream data available for optimization"}
        if self.dream_success_rate < 0.5:
            new_interval = min(self.dream_interval * 1.5, 7200)
            self.dream_interval = int(new_interval)
            optimization_type = "increase_interval"
        elif self.dream_success_rate > 0.8:
            new_interval = max(self.dream_interval * 0.8, 1800)
            self.dream_interval = int(new_interval)
            optimization_type = "decrease_interval"
        else:
            optimization_type = "no_change"
        logger.info(f"Dream schedule optimized: {optimization_type}")
        return {"status": "success", "message": "Dream schedule optimized", "optimization_type": optimization_type, "new_interval": self.dream_interval, "success_rate": self.dream_success_rate}

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            action = request.get('action', '')
            if action == 'health_check':
                return self._health_check()
            elif action == 'start_dreaming':
                return self.start_dreaming()
            elif action == 'stop_dreaming':
                return self.stop_dreaming()
            elif action == 'get_dream_status':
                return self.get_dream_status()
            elif action == 'set_dream_interval':
                interval = request.get('interval', 3600)
                return self.set_dream_interval(interval)
            elif action == 'optimize_schedule':
                return self.optimize_dream_schedule()
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {'status': 'error', 'error': str(e)}

    def run(self):
        logger.info(f"DreamingModeAgent starting on port {self.main_port}")
        health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        health_thread.start()
        scheduler_thread = threading.Thread(target=self._dream_scheduler_loop, daemon=True)
        scheduler_thread.start()
        try:
            while self.running:
                try:
                    if self.socket.poll(1000) == 0:
                        continue
                    message = self.socket.recv_json()
                    logger.debug(f"Received request: {message}")
                    response = self.handle_request(message)
                    self.socket.send_json(response)
                except zmq.error.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    logger.error(f"ZMQ error in main loop: {e}")
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()

    def _health_check_loop(self):
        logger.info("Starting health check loop")
        while self.running:
            try:
                if self.health_socket.poll(1000) == 0:
                    continue
                message = self.health_socket.recv_json()
                if message.get("action") == "health_check":
                    response = self._health_check()
                else:
                    response = {"status": "error", "error": "Invalid health check request"}
                self.health_socket.send_json(response)
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue
                logger.error(f"ZMQ error in health check loop: {e}")
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    def _dream_scheduler_loop(self):
        logger.info("Starting dream scheduler loop")
        while self.running:
            try:
                current_time = time.time()
                if (not self.is_dreaming and current_time - self.last_dream_time >= self.dream_interval):
                    logger.info("Scheduled dream time reached, starting dream cycle")
                    self.start_dreaming()
                    self.last_dream_time = current_time
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in dream scheduler loop: {e}")
                time.sleep(60)

    def cleanup(self):
        logger.info("Cleaning up DreamingModeAgent resources...")
        self.running = False
        if self.is_dreaming:
            self.stop_dreaming()
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'dreamworld_socket'):
            self.dreamworld_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        logger.info("Cleanup complete")


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to DummyArgs

        base_status.update({

            'service': 'DummyArgs',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status

    def stop(self):
        self.running = False



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = DummyArgs()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()