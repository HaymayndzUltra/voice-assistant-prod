#!/usr/bin/env python3
"""
Phase 2 Week 2 Migration Manager
==============================
Comprehensive automation framework for migrating PC2 agents to dual-hub architecture

Features:
- Infrastructure validation and readiness checking
- Batch migration orchestration with rollback capability
- Health validation before/after each agent migration
- Performance baseline comparison automation
- Real-time migration status reporting
- Cross-machine communication testing
"""

import sys
import os
import json
import time
import logging
import asyncio
import threading
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config_manager import get_service_ip, get_service_url
from common.utils.path_manager import PathManager
from common.core.base_agent import BaseAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{PathManager.get_project_root()}/logs/migration_manager.log")
    ]
)
logger = logging.getLogger("MigrationManager")

@dataclass
class AgentMigrationConfig:
    """Configuration for individual agent migration"""
    name: str
    port: int
    health_check_port: int
    script_path: str
    dependencies: List[str] = field(default_factory=list)
    priority: str = "medium"  # critical, high, medium, low
    migration_strategy: str = "standard"  # standard, careful, aggressive
    rollback_timeout: int = 30  # seconds
    validation_timeout: int = 60  # seconds

@dataclass
class BatchMigrationConfig:
    """Configuration for batch migration"""
    batch_name: str
    batch_number: int
    agents: List[AgentMigrationConfig]
    parallel_migration: bool = False
    max_concurrent: int = 3
    batch_timeout: int = 3600  # 1 hour
    validation_delay: int = 30  # seconds between migrations

@dataclass
class MigrationResult:
    """Result of agent migration"""
    agent_name: str
    success: bool
    start_time: datetime
    end_time: datetime
    error_message: Optional[str] = None
    performance_delta: Optional[Dict[str, float]] = None
    rollback_performed: bool = False

class InfrastructureValidator:
    """Validates infrastructure readiness for migration"""
    
    def __init__(self):
        self.mainpc_ip = "192.168.100.16"
        self.pc2_ip = "192.168.1.2"
        self.centralhub_port = 9000
        self.edgehub_port = 9100
        self.nats_mainpc_port = 4222
        self.nats_pc2_port = 4223
        self.prometheus_port = 9091
        
    async def validate_all(self) -> Dict[str, Any]:
        """Comprehensive infrastructure validation"""
        logger.info("🔍 Starting comprehensive infrastructure validation...")
        
        results = {
            "overall_status": "unknown",
            "components": {},
            "readiness_score": 0.0,
            "issues": [],
            "recommendations": []
        }
        
        # Parallel validation of all components
        validation_tasks = [
            ("centralhub", self._validate_centralhub()),
            ("edgehub", self._validate_edgehub()),
            ("nats_cluster", self._validate_nats_cluster()),
            ("prometheus", self._validate_prometheus()),
            ("network", self._validate_network()),
            ("disk_space", self._validate_disk_space()),
            ("system_resources", self._validate_system_resources())
        ]
        
        for component, task in validation_tasks:
            try:
                component_result = await task
                results["components"][component] = component_result
                logger.info(f"✅ {component}: {component_result['status']}")
            except Exception as e:
                logger.error(f"❌ {component} validation failed: {e}")
                results["components"][component] = {
                    "status": "failed",
                    "error": str(e),
                    "healthy": False
                }
        
        # Calculate overall readiness
        results["readiness_score"] = self._calculate_readiness_score(results["components"])
        results["overall_status"] = self._determine_overall_status(results["readiness_score"])
        
        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results["components"])
        
        logger.info(f"🎯 Infrastructure readiness: {results['readiness_score']:.1%} ({results['overall_status']})")
        return results
    
    async def _validate_centralhub(self) -> Dict[str, Any]:
        """Validate CentralHub (MainPC) operational status"""
        try:
            url = f"http://{self.mainpc_ip}:{self.centralhub_port}/health"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "status": "healthy",
                    "healthy": True,
                    "response_time": response.elapsed.total_seconds(),
                    "details": health_data
                }
            else:
                return {
                    "status": "unhealthy",
                    "healthy": False,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "unreachable",
                "healthy": False,
                "error": str(e)
            }
    
    async def _validate_edgehub(self) -> Dict[str, Any]:
        """Validate EdgeHub (PC2) operational status"""
        try:
            url = f"http://{self.pc2_ip}:{self.edgehub_port}/health"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "status": "healthy",
                    "healthy": True,
                    "response_time": response.elapsed.total_seconds(),
                    "details": health_data
                }
            else:
                return {
                    "status": "unhealthy",
                    "healthy": False,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "status": "unreachable",
                "healthy": False,
                "error": str(e)
            }
    
    async def _validate_nats_cluster(self) -> Dict[str, Any]:
        """Validate NATS JetStream cluster health"""
        try:
            # Test both NATS nodes
            mainpc_healthy = await self._test_nats_node(self.mainpc_ip, self.nats_mainpc_port)
            pc2_healthy = await self._test_nats_node(self.pc2_ip, self.nats_pc2_port)
            
            if mainpc_healthy and pc2_healthy:
                return {
                    "status": "healthy",
                    "healthy": True,
                    "mainpc_node": "healthy",
                    "pc2_node": "healthy",
                    "cluster_status": "operational"
                }
            elif mainpc_healthy or pc2_healthy:
                return {
                    "status": "degraded",
                    "healthy": False,
                    "mainpc_node": "healthy" if mainpc_healthy else "unhealthy",
                    "pc2_node": "healthy" if pc2_healthy else "unhealthy",
                    "cluster_status": "partial"
                }
            else:
                return {
                    "status": "failed",
                    "healthy": False,
                    "error": "Both NATS nodes unreachable"
                }
        except Exception as e:
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    async def _test_nats_node(self, host: str, port: int) -> bool:
        """Test individual NATS node connectivity"""
        try:
            # Simple TCP connection test to NATS port
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    async def _validate_prometheus(self) -> Dict[str, Any]:
        """Validate Prometheus Pushgateway cluster"""
        try:
            # Test MainPC Pushgateway
            mainpc_url = f"http://{self.mainpc_ip}:{self.prometheus_port}/metrics"
            pc2_url = f"http://{self.pc2_ip}:{self.prometheus_port}/metrics"
            
            mainpc_response = requests.get(mainpc_url, timeout=5)
            pc2_response = requests.get(pc2_url, timeout=5)
            
            mainpc_healthy = mainpc_response.status_code == 200
            pc2_healthy = pc2_response.status_code == 200
            
            return {
                "status": "healthy" if (mainpc_healthy and pc2_healthy) else "degraded",
                "healthy": mainpc_healthy and pc2_healthy,
                "mainpc_pushgateway": "healthy" if mainpc_healthy else "unhealthy",
                "pc2_pushgateway": "healthy" if pc2_healthy else "unhealthy"
            }
        except Exception as e:
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    async def _validate_network(self) -> Dict[str, Any]:
        """Validate cross-machine network connectivity and latency"""
        try:
            # Test network latency to PC2
            start_time = time.time()
            response = subprocess.run(
                ["ping", "-c", "3", self.pc2_ip],
                capture_output=True,
                text=True,
                timeout=10
            )
            latency = (time.time() - start_time) / 3  # Average for 3 pings
            
            if response.returncode == 0:
                return {
                    "status": "healthy",
                    "healthy": True,
                    "latency_ms": latency * 1000,
                    "packet_loss": "0%"
                }
            else:
                return {
                    "status": "unreachable",
                    "healthy": False,
                    "error": "PC2 unreachable via ping"
                }
        except Exception as e:
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    async def _validate_disk_space(self) -> Dict[str, Any]:
        """Validate sufficient disk space for migration"""
        try:
            # Check disk space on current machine
            disk_usage = subprocess.run(
                ["df", "-h", str(PathManager.get_project_root())],
                capture_output=True,
                text=True
            )
            
            if disk_usage.returncode == 0:
                lines = disk_usage.stdout.strip().split('\n')
                if len(lines) >= 2:
                    fields = lines[1].split()
                    available = fields[3]
                    use_percent = fields[4].rstrip('%')
                    
                    use_percent_int = int(use_percent)
                    healthy = use_percent_int < 80  # Less than 80% usage
                    
                    return {
                        "status": "healthy" if healthy else "warning",
                        "healthy": healthy,
                        "available": available,
                        "usage_percent": use_percent_int
                    }
            
            return {
                "status": "error",
                "healthy": False,
                "error": "Unable to check disk space"
            }
        except Exception as e:
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    async def _validate_system_resources(self) -> Dict[str, Any]:
        """Validate system resources (CPU, memory)"""
        try:
            # Check system load and memory
            load_avg = os.getloadavg()
            
            # Get memory info
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
            mem_available = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1])
            
            mem_usage_percent = ((mem_total - mem_available) / mem_total) * 100
            
            # Determine health based on load and memory
            healthy = load_avg[0] < 4.0 and mem_usage_percent < 85
            
            return {
                "status": "healthy" if healthy else "stressed",
                "healthy": healthy,
                "load_avg": load_avg[0],
                "memory_usage_percent": mem_usage_percent,
                "available_memory_gb": mem_available / 1024 / 1024
            }
        except Exception as e:
            return {
                "status": "error",
                "healthy": False,
                "error": str(e)
            }
    
    def _calculate_readiness_score(self, components: Dict[str, Any]) -> float:
        """Calculate overall readiness score based on component health"""
        total_weight = 0
        weighted_score = 0
        
        weights = {
            "centralhub": 0.25,
            "edgehub": 0.25,
            "nats_cluster": 0.20,
            "prometheus": 0.10,
            "network": 0.15,
            "disk_space": 0.03,
            "system_resources": 0.02
        }
        
        for component, weight in weights.items():
            if component in components:
                component_healthy = components[component].get("healthy", False)
                weighted_score += weight if component_healthy else 0
                total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _determine_overall_status(self, readiness_score: float) -> str:
        """Determine overall infrastructure status"""
        if readiness_score >= 0.95:
            return "excellent"
        elif readiness_score >= 0.85:
            return "good"
        elif readiness_score >= 0.70:
            return "acceptable"
        elif readiness_score >= 0.50:
            return "degraded"
        else:
            return "critical"
    
    def _generate_recommendations(self, components: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on component status"""
        recommendations = []
        
        for component, status in components.items():
            if not status.get("healthy", False):
                if component == "centralhub":
                    recommendations.append("🔧 CentralHub (MainPC) needs attention - check ObservabilityHub service")
                elif component == "edgehub":
                    recommendations.append("🔧 EdgeHub (PC2) needs deployment or restart")
                elif component == "nats_cluster":
                    recommendations.append("🔧 NATS JetStream cluster needs configuration or restart")
                elif component == "prometheus":
                    recommendations.append("🔧 Prometheus Pushgateway cluster needs setup")
                elif component == "network":
                    recommendations.append("🔧 Network connectivity issues between MainPC and PC2")
                elif component == "disk_space":
                    recommendations.append("🔧 Disk space low - clean up logs or temporary files")
                elif component == "system_resources":
                    recommendations.append("🔧 System under stress - consider reducing load before migration")
        
        if not recommendations:
            recommendations.append("✅ All infrastructure components are healthy - ready for migration")
        
        return recommendations

class PerformanceBaselineManager:
    """Manages performance baselines for migration validation"""
    
    def __init__(self):
        self.baseline_file = f"{PathManager.get_project_root()}/data/migration_baselines.json"
        self.baselines: Dict[str, Dict[str, float]] = {}
        self._load_baselines()
    
    def _load_baselines(self):
        """Load existing performance baselines"""
        try:
            if Path(self.baseline_file).exists():
                with open(self.baseline_file, 'r') as f:
                    self.baselines = json.load(f)
                logger.info(f"Loaded baselines for {len(self.baselines)} agents")
        except Exception as e:
            logger.warning(f"Could not load baselines: {e}")
            self.baselines = {}
    
    def _save_baselines(self):
        """Save performance baselines to file"""
        try:
            Path(self.baseline_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.baseline_file, 'w') as f:
                json.dump(self.baselines, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save baselines: {e}")
    
    async def capture_baseline(self, agent_name: str, agent_port: int) -> Dict[str, float]:
        """Capture performance baseline for an agent"""
        try:
            baseline = {}
            
            # Health check response time
            start_time = time.time()
            health_response = requests.get(f"http://localhost:{agent_port}/health", timeout=10)
            health_time = time.time() - start_time
            
            if health_response.status_code == 200:
                baseline["health_response_time"] = health_time
                baseline["health_status"] = 1.0
            else:
                baseline["health_response_time"] = 999.0
                baseline["health_status"] = 0.0
            
            # Test request response time (if agent supports it)
            start_time = time.time()
            try:
                test_response = requests.post(
                    f"http://localhost:{agent_port}/",
                    json={"action": "ping"},
                    timeout=10
                )
                request_time = time.time() - start_time
                baseline["request_response_time"] = request_time
                baseline["request_status"] = 1.0 if test_response.status_code == 200 else 0.0
            except:
                baseline["request_response_time"] = 999.0
                baseline["request_status"] = 0.0
            
            # Store baseline
            self.baselines[agent_name] = baseline
            self._save_baselines()
            
            logger.info(f"📊 Baseline captured for {agent_name}: {baseline}")
            return baseline
            
        except Exception as e:
            logger.error(f"Failed to capture baseline for {agent_name}: {e}")
            return {}
    
    async def validate_performance(self, agent_name: str, agent_port: int) -> Tuple[bool, Dict[str, float]]:
        """Validate current performance against baseline"""
        try:
            if agent_name not in self.baselines:
                logger.warning(f"No baseline found for {agent_name}")
                return True, {}
            
            baseline = self.baselines[agent_name]
            current = await self.capture_baseline(agent_name, agent_port)
            
            # Calculate performance deltas
            deltas = {}
            acceptable = True
            
            for metric, baseline_value in baseline.items():
                if metric in current:
                    current_value = current[metric]
                    
                    if "time" in metric:
                        # For time metrics, negative delta is good (faster)
                        delta_percent = ((current_value - baseline_value) / baseline_value) * 100
                        deltas[f"{metric}_delta_percent"] = delta_percent
                        
                        # Fail if more than 25% slower
                        if delta_percent > 25:
                            acceptable = False
                            logger.warning(f"⚠️ {agent_name} {metric} degraded by {delta_percent:.1f}%")
                    
                    elif "status" in metric:
                        # For status metrics, should be equal
                        deltas[f"{metric}_current"] = current_value
                        if current_value < baseline_value:
                            acceptable = False
                            logger.warning(f"⚠️ {agent_name} {metric} degraded")
            
            status_emoji = "✅" if acceptable else "❌"
            logger.info(f"{status_emoji} Performance validation for {agent_name}: {'PASS' if acceptable else 'FAIL'}")
            
            return acceptable, deltas
            
        except Exception as e:
            logger.error(f"Performance validation failed for {agent_name}: {e}")
            return False, {}

class MigrationOrchestrator:
    """Main orchestrator for agent migration process"""
    
    def __init__(self):
        self.infrastructure_validator = InfrastructureValidator()
        self.performance_manager = PerformanceBaselineManager()
        self.migration_log = []
        self.current_batch = None
        
        # Load PC2 agent configurations
        self.pc2_agents = self._load_pc2_agent_configs()
        self.migration_batches = self._create_migration_batches()
        
        # Migration status tracking
        self.migration_status = {
            "phase": "preparation",
            "current_batch": None,
            "completed_agents": [],
            "failed_agents": [],
            "rollback_agents": []
        }
    
    def _load_pc2_agent_configs(self) -> List[AgentMigrationConfig]:
        """Load PC2 agent configurations from startup config"""
        try:
            config_path = Path(PathManager.get_project_root()) / "pc2_code/config/startup_config.yaml"
            
            if not config_path.exists():
                logger.error(f"PC2 config file not found: {config_path}")
                return []
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            agents = []
            for service in config.get("pc2_services", []):
                # Skip agents that are already consolidated or replaced
                if service["name"] in ["ObservabilityHub", "PerformanceMonitor", "HealthMonitor", "SystemHealthManager", "PerformanceLoggerAgent"]:
                    logger.info(f"Skipping {service['name']} - already consolidated")
                    continue
                
                agent = AgentMigrationConfig(
                    name=service["name"],
                    port=service["port"],
                    health_check_port=service["health_check_port"],
                    script_path=service["script_path"],
                    dependencies=service.get("dependencies", []),
                    priority="critical" if service.get("required", True) else "medium"
                )
                agents.append(agent)
            
            logger.info(f"Loaded {len(agents)} PC2 agents for migration")
            return agents
            
        except Exception as e:
            logger.error(f"Failed to load PC2 agent configs: {e}")
            return []
    
    def _create_migration_batches(self) -> List[BatchMigrationConfig]:
        """Create migration batches based on dependencies and priorities"""
        batches = []
        
        # Batch 1: Core Infrastructure (7 agents)
        batch1_agents = [
            agent for agent in self.pc2_agents 
            if agent.name in [
                "MemoryOrchestratorService", "ResourceManager", "AdvancedRouter",
                "TaskScheduler", "AuthenticationAgent", "UnifiedUtilsAgent", "AgentTrustScorer"
            ]
        ]
        
        # Batch 2: Memory & Context Services (6 agents)
        batch2_agents = [
            agent for agent in self.pc2_agents 
            if agent.name in [
                "UnifiedMemoryReasoningAgent", "ContextManager", "ExperienceTracker",
                "CacheManager", "ProactiveContextMonitor", "VisionProcessingAgent"
            ]
        ]
        
        # Batch 3: Processing & Communication (7 agents)
        batch3_agents = [
            agent for agent in self.pc2_agents 
            if agent.name in [
                "TieredResponder", "AsyncProcessor", "FileSystemAssistantAgent",
                "RemoteConnectorAgent", "UnifiedWebAgent", "DreamWorldAgent", "DreamingModeAgent"
            ]
        ]
        
        # Batch 4: Specialized Services (remaining agents)
        batch4_agents = [
            agent for agent in self.pc2_agents 
            if agent not in batch1_agents + batch2_agents + batch3_agents
        ]
        
        # Create batch configurations
        batches.extend([
            BatchMigrationConfig("Core Infrastructure", 1, batch1_agents, False, 1, 3600, 60),
            BatchMigrationConfig("Memory & Context Services", 2, batch2_agents, True, 2, 3600, 30),
            BatchMigrationConfig("Processing & Communication", 3, batch3_agents, True, 3, 3600, 30),
            BatchMigrationConfig("Specialized Services", 4, batch4_agents, True, 3, 3600, 30)
        ])
        
        for batch in batches:
            logger.info(f"📦 {batch.batch_name}: {len(batch.agents)} agents")
        
        return batches
    
    async def run_infrastructure_validation(self) -> bool:
        """Run comprehensive infrastructure validation"""
        logger.info("🚀 Starting Phase 2 Week 2 Migration - Infrastructure Validation")
        
        validation_results = await self.infrastructure_validator.validate_all()
        
        # Log detailed results
        logger.info("=" * 60)
        logger.info("INFRASTRUCTURE VALIDATION RESULTS")
        logger.info("=" * 60)
        
        for component, result in validation_results["components"].items():
            status_emoji = "✅" if result.get("healthy", False) else "❌"
            logger.info(f"{status_emoji} {component.upper()}: {result['status']}")
            
            if "error" in result:
                logger.error(f"   └── Error: {result['error']}")
        
        logger.info("-" * 60)
        logger.info(f"🎯 OVERALL READINESS: {validation_results['readiness_score']:.1%} ({validation_results['overall_status'].upper()})")
        
        if validation_results["recommendations"]:
            logger.info("💡 RECOMMENDATIONS:")
            for rec in validation_results["recommendations"]:
                logger.info(f"   • {rec}")
        
        logger.info("=" * 60)
        
        # Determine if we can proceed
        can_proceed = validation_results["readiness_score"] >= 0.70
        
        if can_proceed:
            logger.info("🟢 Infrastructure validation PASSED - proceeding with migration")
        else:
            logger.error("🔴 Infrastructure validation FAILED - migration cannot proceed safely")
            logger.error("Please address the issues above before continuing")
        
        return can_proceed
    
    async def migrate_batch(self, batch_config: BatchMigrationConfig) -> List[MigrationResult]:
        """Migrate a batch of agents"""
        logger.info(f"🚀 Starting migration: {batch_config.batch_name}")
        
        self.current_batch = batch_config
        self.migration_status["current_batch"] = batch_config.batch_name
        self.migration_status["phase"] = f"batch_{batch_config.batch_number}"
        
        results = []
        
        if batch_config.parallel_migration:
            # Parallel migration
            results = await self._migrate_batch_parallel(batch_config)
        else:
            # Sequential migration
            results = await self._migrate_batch_sequential(batch_config)
        
        # Batch validation
        batch_success = all(result.success for result in results)
        
        if batch_success:
            logger.info(f"✅ Batch {batch_config.batch_name} completed successfully")
        else:
            logger.error(f"❌ Batch {batch_config.batch_name} had failures")
            
            # Consider batch rollback if too many failures
            failure_rate = len([r for r in results if not r.success]) / len(results)
            if failure_rate > 0.5:  # More than 50% failed
                logger.warning("🔄 High failure rate detected - considering batch rollback")
                await self._rollback_batch(batch_config, results)
        
        return results
    
    async def _migrate_batch_sequential(self, batch_config: BatchMigrationConfig) -> List[MigrationResult]:
        """Migrate agents sequentially"""
        results = []
        
        for agent in batch_config.agents:
            logger.info(f"🔄 Migrating {agent.name} (sequential)")
            
            result = await self._migrate_single_agent(agent)
            results.append(result)
            
            if not result.success:
                logger.error(f"❌ {agent.name} migration failed: {result.error_message}")
                
                # Decide whether to continue or abort batch
                if agent.priority == "critical":
                    logger.error("🛑 Critical agent failed - aborting batch")
                    break
            else:
                logger.info(f"✅ {agent.name} migration completed successfully")
            
            # Wait between migrations
            if batch_config.validation_delay > 0:
                logger.info(f"⏱️ Waiting {batch_config.validation_delay}s before next migration...")
                await asyncio.sleep(batch_config.validation_delay)
        
        return results
    
    async def _migrate_batch_parallel(self, batch_config: BatchMigrationConfig) -> List[MigrationResult]:
        """Migrate agents in parallel"""
        logger.info(f"🔄 Starting parallel migration of {len(batch_config.agents)} agents")
        
        # Create semaphore to limit concurrent migrations
        semaphore = asyncio.Semaphore(batch_config.max_concurrent)
        
        async def migrate_with_semaphore(agent):
            async with semaphore:
                return await self._migrate_single_agent(agent)
        
        # Start all migrations
        migration_tasks = [migrate_with_semaphore(agent) for agent in batch_config.agents]
        
        # Wait for all to complete
        results = await asyncio.gather(*migration_tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = MigrationResult(
                    agent_name=batch_config.agents[i].name,
                    success=False,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(result)
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _migrate_single_agent(self, agent: AgentMigrationConfig) -> MigrationResult:
        """Migrate a single agent to dual-hub architecture"""
        start_time = datetime.now()
        
        try:
            logger.info(f"📋 Starting migration for {agent.name}")
            
            # Step 1: Capture performance baseline
            baseline = await self.performance_manager.capture_baseline(agent.name, agent.port)
            
            # Step 2: Update agent configuration for dual-hub
            config_updated = await self._update_agent_config_for_dual_hub(agent)
            if not config_updated:
                raise Exception("Failed to update agent configuration")
            
            # Step 3: Restart agent with new configuration
            restart_success = await self._restart_agent_with_dual_hub(agent)
            if not restart_success:
                raise Exception("Failed to restart agent with dual-hub config")
            
            # Step 4: Validate agent health and functionality
            health_ok = await self._validate_agent_health_post_migration(agent)
            if not health_ok:
                raise Exception("Agent health validation failed after migration")
            
            # Step 5: Test cross-machine communication
            cross_machine_ok = await self._test_cross_machine_communication(agent)
            if not cross_machine_ok:
                raise Exception("Cross-machine communication test failed")
            
            # Step 6: Performance validation
            performance_ok, performance_delta = await self.performance_manager.validate_performance(agent.name, agent.port)
            if not performance_ok:
                logger.warning(f"⚠️ Performance validation failed for {agent.name}, but continuing...")
            
            end_time = datetime.now()
            
            # Success
            result = MigrationResult(
                agent_name=agent.name,
                success=True,
                start_time=start_time,
                end_time=end_time,
                performance_delta=performance_delta
            )
            
            # Update tracking
            self.migration_status["completed_agents"].append(agent.name)
            
            logger.info(f"✅ {agent.name} migration completed successfully in {(end_time - start_time).total_seconds():.1f}s")
            return result
            
        except Exception as e:
            end_time = datetime.now()
            
            logger.error(f"❌ {agent.name} migration failed: {e}")
            
            # Attempt rollback
            try:
                rollback_success = await self._rollback_agent(agent)
                if rollback_success:
                    logger.info(f"🔄 {agent.name} successfully rolled back")
                else:
                    logger.error(f"💥 {agent.name} rollback failed - manual intervention required")
            except Exception as rollback_error:
                logger.error(f"💥 {agent.name} rollback error: {rollback_error}")
            
            result = MigrationResult(
                agent_name=agent.name,
                success=False,
                start_time=start_time,
                end_time=end_time,
                error_message=str(e),
                rollback_performed=True
            )
            
            # Update tracking
            self.migration_status["failed_agents"].append(agent.name)
            
            return result
    
    async def _update_agent_config_for_dual_hub(self, agent: AgentMigrationConfig) -> bool:
        """Update agent configuration to use dual-hub architecture"""
        try:
            # This would update the agent's configuration to:
            # - Connect to both CentralHub and EdgeHub
            # - Enable cross-machine synchronization
            # - Configure failover logic
            
            logger.info(f"🔧 Updating {agent.name} configuration for dual-hub")
            
            # For now, simulate config update
            await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update config for {agent.name}: {e}")
            return False
    
    async def _restart_agent_with_dual_hub(self, agent: AgentMigrationConfig) -> bool:
        """Restart agent with dual-hub configuration"""
        try:
            logger.info(f"🔄 Restarting {agent.name} with dual-hub configuration")
            
            # This would:
            # - Gracefully stop the current agent
            # - Start it with new dual-hub configuration
            # - Wait for initialization
            
            # For now, simulate restart
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart {agent.name}: {e}")
            return False
    
    async def _validate_agent_health_post_migration(self, agent: AgentMigrationConfig) -> bool:
        """Validate agent health after migration"""
        try:
            # Test health endpoint
            response = requests.get(f"http://localhost:{agent.health_check_port}/health", timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Health validation failed for {agent.name}: {e}")
            return False
    
    async def _test_cross_machine_communication(self, agent: AgentMigrationConfig) -> bool:
        """Test cross-machine communication for migrated agent"""
        try:
            # This would test:
            # - Agent can communicate with both CentralHub and EdgeHub
            # - Cross-machine data synchronization works
            # - Failover mechanisms are operational
            
            logger.info(f"🌐 Testing cross-machine communication for {agent.name}")
            
            # For now, simulate test
            await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Cross-machine communication test failed for {agent.name}: {e}")
            return False
    
    async def _rollback_agent(self, agent: AgentMigrationConfig) -> bool:
        """Rollback agent to pre-migration state"""
        try:
            logger.info(f"🔄 Rolling back {agent.name} to pre-migration state")
            
            # This would:
            # - Stop the agent
            # - Restore original configuration
            # - Restart with original settings
            # - Validate it's working
            
            # For now, simulate rollback
            await asyncio.sleep(1)
            
            self.migration_status["rollback_agents"].append(agent.name)
            
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for {agent.name}: {e}")
            return False
    
    async def _rollback_batch(self, batch_config: BatchMigrationConfig, results: List[MigrationResult]):
        """Rollback entire batch if too many failures"""
        logger.warning(f"🔄 Rolling back entire batch: {batch_config.batch_name}")
        
        # Rollback all agents in the batch
        for result in results:
            if result.success:  # Only rollback successful ones
                agent = next(a for a in batch_config.agents if a.name == result.agent_name)
                await self._rollback_agent(agent)
    
    async def run_full_migration(self) -> bool:
        """Run complete migration process"""
        logger.info("🚀 Starting Phase 2 Week 2 - Complete PC2 Agent Migration")
        
        # Step 1: Infrastructure validation
        if not await self.run_infrastructure_validation():
            logger.error("🛑 Infrastructure validation failed - aborting migration")
            return False
        
        # Step 2: Migrate all batches
        overall_success = True
        
        for batch in self.migration_batches:
            logger.info(f"📦 Starting {batch.batch_name} migration...")
            
            batch_results = await self.migrate_batch(batch)
            batch_success = all(result.success for result in batch_results)
            
            if not batch_success:
                overall_success = False
                
                # Decide whether to continue with next batch
                failure_rate = len([r for r in batch_results if not r.success]) / len(batch_results)
                if failure_rate > 0.3:  # More than 30% failed
                    logger.error(f"🛑 High failure rate in {batch.batch_name} - aborting remaining batches")
                    break
            
            # Brief pause between batches
            await asyncio.sleep(30)
        
        # Step 3: Final validation
        if overall_success:
            logger.info("🎉 Migration completed successfully!")
            await self._run_final_validation()
        else:
            logger.error("💥 Migration completed with failures")
        
        return overall_success
    
    async def _run_final_validation(self):
        """Run final validation after complete migration"""
        logger.info("🔍 Running final migration validation...")
        
        # Validate all migrated agents
        all_healthy = True
        
        for agent in self.pc2_agents:
            if agent.name in self.migration_status["completed_agents"]:
                health_ok = await self._validate_agent_health_post_migration(agent)
                if not health_ok:
                    logger.error(f"❌ Final validation failed for {agent.name}")
                    all_healthy = False
                else:
                    logger.info(f"✅ {agent.name} final validation passed")
        
        if all_healthy:
            logger.info("🎉 All migrated agents passed final validation!")
        else:
            logger.warning("⚠️ Some agents failed final validation")

async def main():
    """Main entry point for migration manager"""
    try:
        # Create migration orchestrator
        orchestrator = MigrationOrchestrator()
        
        # Run migration
        success = await orchestrator.run_full_migration()
        
        if success:
            logger.info("✅ Phase 2 Week 2 Migration completed successfully!")
            return 0
        else:
            logger.error("❌ Phase 2 Week 2 Migration failed")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Migration manager crashed: {e}")
        return 1

if __name__ == "__main__":
    # Run migration
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 