#!/usr/bin/env python3
"""
Foundation Services Startup Script
==================================

Starts only the foundation_services agent group for testing purposes.
Launches agents in dependency order to ensure proper startup sequence.
"""

import os
import sys
import time
import logging
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FoundationServices')

class FoundationServiceManager:
    """Manages foundation services startup and health monitoring"""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.agent_configs = {
            'ServiceRegistry': {
                'script': 'main_pc_code/agents/service_registry_agent.py',
                'port': 7200,
                'health_port': 8200,
                'dependencies': [],
                'env': {'BACKEND': 'memory'}
            },
            'SystemDigitalTwin': {
                'script': 'main_pc_code/agents/system_digital_twin.py',
                'port': 7220,
                'health_port': 8220,
                'dependencies': ['ServiceRegistry'],
                'env': {'DB_PATH': '/app/data/unified_memory.db'}
            },
            'RequestCoordinator': {
                'script': 'main_pc_code/agents/request_coordinator.py',
                'port': 26002,
                'health_port': 27002,
                'dependencies': ['SystemDigitalTwin'],
                'env': {}
            },
            'ModelManagerSuite': {
                'script': 'main_pc_code/model_manager_suite.py',
                'port': 7211,
                'health_port': 8211,
                'dependencies': ['SystemDigitalTwin'],
                'env': {
                    'MODELS_DIR': '/app/models',
                    'VRAM_BUDGET_PERCENTAGE': '80',
                    'IDLE_TIMEOUT': '300'
                }
            },
            'VRAMOptimizerAgent': {
                'script': 'main_pc_code/agents/vram_optimizer_agent.py',
                'port': 5572,
                'health_port': 6572,
                'dependencies': ['ModelManagerSuite', 'RequestCoordinator', 'SystemDigitalTwin'],
                'env': {}
            },
            'ObservabilityHub': {
                'script': 'phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py',
                'port': 9000,
                'health_port': 9001,
                'dependencies': ['SystemDigitalTwin'],
                'env': {
                    'PROMETHEUS_ENABLED': 'true',
                    'PARALLEL_HEALTH_CHECKS': 'true',
                    'PREDICTION_ENABLED': 'true'
                }
            },
            'UnifiedSystemAgent': {
                'script': 'main_pc_code/agents/unified_system_agent.py',
                'port': 7201,
                'health_port': 8201,
                'dependencies': ['SystemDigitalTwin'],
                'env': {}
            }
        }
        
    def wait_for_port(self, port: int, timeout: int = 30) -> bool:
        """Wait for a port to become available"""
        import socket
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('localhost', port))
                    if result == 0:
                        return True
            except:
                pass
            time.sleep(1)
        return False
    
    def check_health(self, agent_name: str, health_port: int) -> bool:
        """Check agent health via HTTP endpoint"""
        try:
            import requests
            response = requests.get(f'http://localhost:{health_port}/health', timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ {agent_name} is healthy")
                return True
            else:
                logger.warning(f"⚠️ {agent_name} health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"⚠️ {agent_name} health check error: {e}")
            return False
    
    def start_agent(self, agent_name: str, config: Dict) -> bool:
        """Start a single agent"""
        script_path = config['script']
        port = config['port']
        health_port = config['health_port']
        
        # Check if script exists
        if not Path(script_path).exists():
            logger.error(f"❌ Script not found: {script_path}")
            return False
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            'PYTHONPATH': '/app',
            'PORT_OFFSET': '0',
            'LOG_LEVEL': 'INFO',
            'TEST_MODE': 'true',
            'SKIP_GPU_CHECKS': 'true',
            'MOCK_MODELS': 'true'
        })
        env.update(config['env'])
        
        # Start agent
        try:
            cmd = [
                'python3', script_path,
                '--port', str(port),
                '--health-port', str(health_port)
            ]
            
            logger.info(f"🚀 Starting {agent_name} on port {port}")
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[agent_name] = process
            
            # Wait for port to be available
            if self.wait_for_port(port, timeout=30):
                logger.info(f"✅ {agent_name} started successfully")
                return True
            else:
                logger.error(f"❌ {agent_name} failed to start (port timeout)")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start {agent_name}: {e}")
            return False
    
    def start_foundation_services(self) -> bool:
        """Start all foundation services in dependency order"""
        logger.info("🏗️ Starting Foundation Services...")
        
        # Determine startup order based on dependencies
        started = set()
        startup_order = []
        
        while len(startup_order) < len(self.agent_configs):
            for agent_name, config in self.agent_configs.items():
                if agent_name in startup_order:
                    continue
                    
                # Check if all dependencies are started
                if all(dep in started for dep in config['dependencies']):
                    startup_order.append(agent_name)
                    started.add(agent_name)
        
        logger.info(f"📋 Startup order: {' -> '.join(startup_order)}")
        
        # Start agents in order
        for agent_name in startup_order:
            config = self.agent_configs[agent_name]
            if not self.start_agent(agent_name, config):
                logger.error(f"❌ Failed to start {agent_name}, stopping all services")
                self.stop_all_services()
                return False
            
            # Wait a bit between starts
            time.sleep(2)
        
        logger.info("✅ All foundation services started successfully")
        return True
    
    def monitor_services(self):
        """Monitor service health"""
        logger.info("🔍 Starting service monitoring...")
        
        while True:
            all_healthy = True
            
            for agent_name, config in self.agent_configs.items():
                if agent_name in self.processes:
                    health_port = config['health_port']
                    if not self.check_health(agent_name, health_port):
                        all_healthy = False
            
            if all_healthy:
                logger.info("✅ All foundation services are healthy")
            else:
                logger.warning("⚠️ Some services are unhealthy")
            
            time.sleep(30)  # Check every 30 seconds
    
    def stop_all_services(self):
        """Stop all running services"""
        logger.info("🛑 Stopping all foundation services...")
        
        for agent_name, process in self.processes.items():
            try:
                logger.info(f"🛑 Stopping {agent_name}")
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ Force killing {agent_name}")
                process.kill()
            except Exception as e:
                logger.error(f"❌ Error stopping {agent_name}: {e}")
        
        self.processes.clear()
        logger.info("✅ All services stopped")

def main():
    """Main entry point"""
    manager = FoundationServiceManager()
    
    try:
        # Start foundation services
        if not manager.start_foundation_services():
            logger.error("❌ Failed to start foundation services")
            sys.exit(1)
        
        # Start monitoring in background
        monitor_thread = threading.Thread(target=manager.monitor_services, daemon=True)
        monitor_thread.start()
        
        logger.info("🎉 Foundation services are running! Press Ctrl+C to stop.")
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        manager.stop_all_services()

if __name__ == "__main__":
    main() 