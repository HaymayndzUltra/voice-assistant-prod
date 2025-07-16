#!/usr/bin/env python3
"""
Phase 1 Deployment Script
Deploys and tests the consolidated services according to the 4th proposal Phase 1 specification.
"""

import sys
import os
import time
import asyncio
import subprocess
import logging
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

# Add project paths
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_implementation/logs/deployment.log')
    ]
)
logger = logging.getLogger("Phase1Deployment")

class Phase1Deployer:
    """Handles deployment and testing of Phase 1 consolidated services"""
    
    def __init__(self):
        self.services = {}
        self.processes = {}
        self.executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix='Phase1Deploy')
        
        # Service definitions from Phase 1 spec
        self.service_definitions = {
            "CoreOrchestrator": {
                "script": "phase1_implementation/consolidated_agents/core_orchestrator/core_orchestrator.py",
                "port": 7000,
                "health_port": 7100,
                "hardware": "MainPC",
                "description": "ServiceRegistry, SystemDigitalTwin, RequestCoordinator, UnifiedSystemAgent consolidated"
            },
            "ObservabilityHub": {
                "script": "phase1_implementation/consolidated_agents/observability_hub/observability_hub.py",
                "port": 7002,
                "health_port": 7102,
                "hardware": "PC2",
                "description": "PredictiveHealthMonitor, PerformanceMonitor, HealthMonitor, PerformanceLoggerAgent, SystemHealthManager consolidated"
            }
        }
        
        # Configuration for deployment modes
        self.deployment_modes = {
            "unified": {
                "ENABLE_UNIFIED_REGISTRY": "true",
                "ENABLE_UNIFIED_TWIN": "true", 
                "ENABLE_UNIFIED_COORDINATOR": "true",
                "ENABLE_UNIFIED_SYSTEM": "true",
                "ENABLE_UNIFIED_HEALTH": "true",
                "ENABLE_UNIFIED_PERFORMANCE": "true",
                "ENABLE_UNIFIED_PREDICTION": "true"
            },
            "delegation": {
                "ENABLE_UNIFIED_REGISTRY": "false",
                "ENABLE_UNIFIED_TWIN": "false",
                "ENABLE_UNIFIED_COORDINATOR": "false", 
                "ENABLE_UNIFIED_SYSTEM": "false",
                "ENABLE_UNIFIED_HEALTH": "false",
                "ENABLE_UNIFIED_PERFORMANCE": "false",
                "ENABLE_UNIFIED_PREDICTION": "false"
            },
            "gradual": {
                "ENABLE_UNIFIED_REGISTRY": "true",
                "ENABLE_UNIFIED_TWIN": "false",  # Start with registry only
                "ENABLE_UNIFIED_COORDINATOR": "false",
                "ENABLE_UNIFIED_SYSTEM": "false",
                "ENABLE_UNIFIED_HEALTH": "true",  # Enable health monitoring
                "ENABLE_UNIFIED_PERFORMANCE": "false",
                "ENABLE_UNIFIED_PREDICTION": "false"
            }
        }
    
    def setup_environment(self, mode: str = "unified"):
        """Setup environment variables for deployment mode"""
        if mode not in self.deployment_modes:
            raise ValueError(f"Unknown deployment mode: {mode}. Available modes: {list(self.deployment_modes.keys())}")
        
        env_vars = self.deployment_modes[mode]
        for key, value in env_vars.items():
            os.environ[key] = value
        
        logger.info(f"Environment configured for {mode} mode")
        logger.info(f"Feature flags: {env_vars}")
    
    def create_log_directory(self):
        """Create logs directory if it doesn't exist"""
        log_dir = Path("phase1_implementation/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_dependencies(self):
        """Validate that required dependencies are available"""
        required_modules = ["fastapi", "uvicorn", "psutil"]
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            logger.error(f"Missing required modules: {missing_modules}")
            logger.info("Install with: pip install fastapi uvicorn psutil")
            return False
        
        return True
    
    def start_service_async(self, service_name: str, service_config: Dict):
        """Start a service asynchronously"""
        try:
            script_path = service_config["script"]
            
            if not Path(script_path).exists():
                logger.error(f"Service script not found: {script_path}")
                return False
            
            logger.info(f"Starting {service_name} on port {service_config['port']} ({service_config['hardware']})")
            
            # Start the service process
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=os.environ.copy(),
                cwd=project_root
            )
            
            self.processes[service_name] = process
            
            # Wait a moment for startup
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info(f"✅ {service_name} started successfully (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"❌ {service_name} failed to start")
                logger.error(f"STDOUT: {stdout.decode()}")
                logger.error(f"STDERR: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting {service_name}: {e}")
            return False
    
    def test_service_health(self, service_name: str, service_config: Dict) -> bool:
        """Test service health endpoint"""
        try:
            health_url = f"http://localhost:{service_config['port']}/health"
            
            # Try multiple times with backoff
            for attempt in range(5):
                try:
                    response = requests.get(health_url, timeout=5)
                    if response.status_code == 200:
                        health_data = response.json()
                        logger.info(f"✅ {service_name} health check passed: {health_data.get('status', 'unknown')}")
                        return True
                except requests.RequestException:
                    pass
                
                time.sleep(2 ** attempt)  # Exponential backoff
            
            logger.warning(f"⚠️ {service_name} health check failed after retries")
            return False
            
        except Exception as e:
            logger.error(f"Error testing {service_name} health: {e}")
            return False
    
    def test_service_functionality(self, service_name: str, service_config: Dict) -> bool:
        """Test basic service functionality"""
        try:
            base_url = f"http://localhost:{service_config['port']}"
            
            if service_name == "CoreOrchestrator":
                return self._test_core_orchestrator_functionality(base_url)
            elif service_name == "ObservabilityHub":
                return self._test_observability_hub_functionality(base_url)
            
            return True
            
        except Exception as e:
            logger.error(f"Error testing {service_name} functionality: {e}")
            return False
    
    def _test_core_orchestrator_functionality(self, base_url: str) -> bool:
        """Test CoreOrchestrator specific functionality"""
        try:
            # Test agent registration
            test_agent = {
                "name": "TestAgent",
                "port": 9999,
                "host": "localhost",
                "capabilities": ["testing"]
            }
            
            response = requests.post(f"{base_url}/register_agent", json=test_agent, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Agent registration test failed: {response.status_code}")
                return False
            
            # Test agent discovery
            response = requests.get(f"{base_url}/get_agent_endpoint/TestAgent", timeout=10)
            if response.status_code != 200:
                logger.warning(f"Agent discovery test failed: {response.status_code}")
                return False
            
            # Test list agents
            response = requests.get(f"{base_url}/list_agents", timeout=10)
            if response.status_code != 200:
                logger.warning(f"List agents test failed: {response.status_code}")
                return False
            
            logger.info("✅ CoreOrchestrator functionality tests passed")
            return True
            
        except Exception as e:
            logger.error(f"CoreOrchestrator functionality test error: {e}")
            return False
    
    def _test_observability_hub_functionality(self, base_url: str) -> bool:
        """Test ObservabilityHub specific functionality"""
        try:
            # Test metrics endpoint
            response = requests.get(f"{base_url}/metrics", timeout=10)
            if response.status_code != 200:
                logger.warning(f"Metrics test failed: {response.status_code}")
                return False
            
            # Test health summary
            response = requests.get(f"{base_url}/health_summary", timeout=10)
            if response.status_code != 200:
                logger.warning(f"Health summary test failed: {response.status_code}")
                return False
            
            # Test agent health update
            test_health = {
                "agent_name": "TestAgent",
                "status": "healthy",
                "details": {"test": "data"},
                "location": "MainPC"
            }
            
            response = requests.post(f"{base_url}/update_agent_health", json=test_health, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Health update test failed: {response.status_code}")
                return False
            
            # Test add alert rule
            test_rule = {
                "rule_id": "test_cpu_high",
                "metric_name": "cpu_percent",
                "condition": "gt",
                "threshold": 90.0,
                "severity": "warning"
            }
            
            response = requests.post(f"{base_url}/add_alert_rule", json=test_rule, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Alert rule test failed: {response.status_code}")
                return False
            
            logger.info("✅ ObservabilityHub functionality tests passed")
            return True
            
        except Exception as e:
            logger.error(f"ObservabilityHub functionality test error: {e}")
            return False
    
    def deploy_phase1(self, mode: str = "unified") -> bool:
        """Deploy all Phase 1 services"""
        try:
            logger.info("=" * 60)
            logger.info("STARTING PHASE 1 DEPLOYMENT")
            logger.info("=" * 60)
            
            # Setup
            self.create_log_directory()
            
            if not self.validate_dependencies():
                return False
            
            self.setup_environment(mode)
            
            # Start services
            success_count = 0
            total_services = len(self.service_definitions)
            
            for service_name, service_config in self.service_definitions.items():
                logger.info(f"\n--- Deploying {service_name} ---")
                
                if self.start_service_async(service_name, service_config):
                    success_count += 1
                else:
                    logger.error(f"Failed to start {service_name}")
            
            if success_count == 0:
                logger.error("❌ No services started successfully")
                return False
            
            logger.info(f"\n✅ Started {success_count}/{total_services} services")
            
            # Health checks
            logger.info("\n--- Running Health Checks ---")
            healthy_services = 0
            
            for service_name, service_config in self.service_definitions.items():
                if service_name in self.processes:
                    if self.test_service_health(service_name, service_config):
                        healthy_services += 1
            
            logger.info(f"✅ {healthy_services}/{success_count} services passed health checks")
            
            # Functionality tests
            logger.info("\n--- Running Functionality Tests ---")
            functional_services = 0
            
            for service_name, service_config in self.service_definitions.items():
                if service_name in self.processes:
                    if self.test_service_functionality(service_name, service_config):
                        functional_services += 1
            
            logger.info(f"✅ {functional_services}/{success_count} services passed functionality tests")
            
            # Summary
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 1 DEPLOYMENT SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Mode: {mode}")
            logger.info(f"Services Started: {success_count}/{total_services}")
            logger.info(f"Health Checks Passed: {healthy_services}/{success_count}")
            logger.info(f"Functionality Tests Passed: {functional_services}/{success_count}")
            
            if functional_services == success_count and success_count > 0:
                logger.info("🎉 PHASE 1 DEPLOYMENT SUCCESSFUL!")
                return True
            else:
                logger.warning("⚠️ PHASE 1 DEPLOYMENT PARTIALLY SUCCESSFUL")
                return False
                
        except Exception as e:
            logger.error(f"Deployment error: {e}")
            return False
    
    def stop_services(self):
        """Stop all running services"""
        logger.info("Stopping Phase 1 services...")
        
        for service_name, process in self.processes.items():
            try:
                if process.poll() is None:  # Process is still running
                    logger.info(f"Stopping {service_name} (PID: {process.pid})")
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Force killing {service_name}")
                        process.kill()
                    
                    logger.info(f"✅ {service_name} stopped")
                
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
        
        self.processes.clear()
        logger.info("All services stopped")
    
    def show_service_status(self):
        """Show status of all services"""
        logger.info("\n--- Service Status ---")
        
        for service_name, service_config in self.service_definitions.items():
            if service_name in self.processes:
                process = self.processes[service_name]
                if process.poll() is None:
                    status = f"✅ RUNNING (PID: {process.pid})"
                else:
                    status = "❌ STOPPED"
            else:
                status = "❌ NOT STARTED"
            
            logger.info(f"{service_name:20} | Port: {service_config['port']:4} | {status}")

def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Phase 1 consolidated services")
    parser.add_argument("--mode", choices=["unified", "delegation", "gradual"], 
                       default="unified", help="Deployment mode")
    parser.add_argument("--test-only", action="store_true", 
                       help="Run tests only, don't start services")
    parser.add_argument("--stop", action="store_true", 
                       help="Stop running services")
    
    args = parser.parse_args()
    
    deployer = Phase1Deployer()
    
    try:
        if args.stop:
            deployer.stop_services()
            return
        
        if args.test_only:
            # Run unit tests
            logger.info("Running Phase 1 unit tests...")
            
            test_commands = [
                "python3 phase1_implementation/tests/unit/test_core_orchestrator_unit.py",
                "python3 phase1_implementation/tests/unit/test_observability_hub_unit.py"
            ]
            
            for cmd in test_commands:
                logger.info(f"Running: {cmd}")
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("✅ Test passed")
                else:
                    logger.error(f"❌ Test failed: {result.stderr}")
            
            return
        
        # Deploy services
        success = deployer.deploy_phase1(args.mode)
        
        if success:
            logger.info("\nServices are running. Press Ctrl+C to stop.")
            
            try:
                # Keep services running
                while True:
                    time.sleep(30)
                    deployer.show_service_status()
                    
            except KeyboardInterrupt:
                logger.info("\nShutdown requested by user")
        
    except Exception as e:
        logger.error(f"Deployment error: {e}")
    
    finally:
        deployer.stop_services()

if __name__ == "__main__":
    main() 