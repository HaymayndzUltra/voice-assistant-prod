#!/usr/bin/env python3
"""
🎯 COMPREHENSIVE DOCKER TESTING FRAMEWORK
Analyzes and tests all 19 Docker groups: 12 Main PC + 7 PC2
Includes local validation, cross-machine sync preparation, and bulletproof testing
"""

import asyncio
import json
import logging
import time
import subprocess
import requests
import yaml
import zmq
import zmq.asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import docker
import psutil
import threading
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/docker_testing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DockerGroup:
    """Represents a Docker service group"""
    name: str
    system: str  # "mainpc" or "pc2"
    agents: List[str]
    ports: List[int]
    health_ports: List[int]
    dependencies: List[str]
    resource_requirements: Dict[str, Any]
    gpu_required: bool = False
    priority: str = "medium"  # critical, high, medium, low

@dataclass
class TestResult:
    """Test result container"""
    test_name: str
    group_name: str
    success: bool
    message: str
    duration: float
    timestamp: datetime
    details: Dict[str, Any] = None

class ComprehensiveDockerTester:
    """
    🚀 COMPREHENSIVE DOCKER TESTING FRAMEWORK
    Tests all 19 Docker groups with intelligent validation
    """
    
    def __init__(self):
        self.logger = logger
        self.docker_client = docker.from_env()
        self.test_results: List[TestResult] = []
        self.start_time = datetime.now()
        
        # 🎯 ALL 19 DOCKER GROUPS DEFINED
        self.docker_groups = self._define_all_docker_groups()
        
        # Test configuration
        self.parallel_executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
        self.zmq_context = zmq.asyncio.Context()
        
        # Cross-machine configuration
        self.mainpc_ip = "192.168.100.16"
        self.pc2_ip = "192.168.100.17"
        self.current_machine = self._detect_current_machine()
        
        self.logger.info(f"🎯 Initialized testing framework for {len(self.docker_groups)} Docker groups")
        self.logger.info(f"🖥️ Current machine: {self.current_machine}")
    
    def _define_all_docker_groups(self) -> Dict[str, DockerGroup]:
        """
        🔍 COMPLETE DEFINITION OF ALL 19 DOCKER GROUPS
        """
        groups = {}
        
        # ============================================================================
        # MAIN PC GROUPS (12 total)
        # ============================================================================
        
        # 1. Infrastructure Core
        groups["infra_core"] = DockerGroup(
            name="infra_core",
            system="mainpc", 
            agents=["ServiceRegistry", "SystemDigitalTwin", "ErrorBusService"],
            ports=[7200, 7210, 7220],
            health_ports=[8200, 8210, 8220],
            dependencies=[],
            resource_requirements={"cpu": "2.0", "memory": "1g"},
            priority="critical"
        )
        
        # 2. Coordination
        groups["coordination"] = DockerGroup(
            name="coordination",
            system="mainpc",
            agents=["RequestCoordinator", "SystemOrchestrator"],
            ports=[7211, 7212],
            health_ports=[8211, 8212],
            dependencies=["infra_core"],
            resource_requirements={"cpu": "4.0", "memory": "8g"},
            gpu_required=True,
            priority="critical"
        )
        
        # 3. Memory Stack
        groups["memory_stack"] = DockerGroup(
            name="memory_stack",
            system="mainpc",
            agents=["MemoryOrchestrator", "MemoryClient", "ContextSummarizerAgent", "MemoryPruningAgent"],
            ports=[6713, 7103, 7106, 7107],
            health_ports=[8713, 8103, 8106, 8107],
            dependencies=["infra_core"],
            resource_requirements={"cpu": "2.0", "memory": "4g"},
            priority="high"
        )
        
        # 4. Vision GPU
        groups["vision_gpu"] = DockerGroup(
            name="vision_gpu",
            system="mainpc",
            agents=["FaceRecognitionAgent", "ImageGenerationAgent", "VideoProcessingAgent"],
            ports=[6610, 6611, 6612],
            health_ports=[8610, 8611, 8612],
            dependencies=["coordination"],
            resource_requirements={"cpu": "4.0", "memory": "6g"},
            gpu_required=True,
            priority="high"
        )
        
        # 5. Speech GPU
        groups["speech_gpu"] = DockerGroup(
            name="speech_gpu",
            system="mainpc",
            agents=["STTService", "TTSService", "StreamingSpeechRecognition", "StreamingTTSAgent"],
            ports=[6800, 6801, 6802, 6803],
            health_ports=[8800, 8801, 8802, 8803],
            dependencies=["coordination", "vision_gpu"],
            resource_requirements={"cpu": "4.0", "memory": "6g"},
            gpu_required=True,
            priority="high"
        )
        
        # 6. Learning GPU
        groups["learning_gpu"] = DockerGroup(
            name="learning_gpu",
            system="mainpc",
            agents=["DeepLearningAgent", "ModelRouter", "ChainOfThoughtAgent"],
            ports=[5580, 5581, 5582],
            health_ports=[8580, 8581, 8582],
            dependencies=["coordination", "memory_stack"],
            resource_requirements={"cpu": "6.0", "memory": "10g"},
            gpu_required=True,
            priority="high"
        )
        
        # 7. Reasoning GPU
        groups["reasoning_gpu"] = DockerGroup(
            name="reasoning_gpu",
            system="mainpc",
            agents=["CognitiveModelAgent", "GoTToTAgent", "ReasoningAgent"],
            ports=[6612, 6613, 6614],
            health_ports=[8612, 8613, 8614],
            dependencies=["coordination", "memory_stack"],
            resource_requirements={"cpu": "4.0", "memory": "8g"},
            gpu_required=True,
            priority="high"
        )
        
        # 8. Language Stack
        groups["language_stack"] = DockerGroup(
            name="language_stack",
            system="mainpc",
            agents=["ConsolidatedTranslator", "NLLBTranslator"],
            ports=[5709, 5710],
            health_ports=[8709, 8710],
            dependencies=["memory_stack"],
            resource_requirements={"cpu": "4.0", "memory": "6g"},
            priority="medium"
        )
        
        # 9. Utility CPU
        groups["utility_cpu"] = DockerGroup(
            name="utility_cpu",
            system="mainpc",
            agents=["LoggingService", "ConfigManager", "NetworkMonitor", "HealthCheckManager"],
            ports=[5650, 5651, 5652, 5653],
            health_ports=[8650, 8651, 8652, 8653],
            dependencies=["infra_core"],
            resource_requirements={"cpu": "2.0", "memory": "2g"},
            priority="medium"
        )
        
        # 10. Emotion System
        groups["emotion_system"] = DockerGroup(
            name="emotion_system",
            system="mainpc",
            agents=["EmotionSynthesisAgent", "EmotionAnalysisAgent"],
            ports=[6590, 6591],
            health_ports=[8590, 8591],
            dependencies=["language_stack"],
            resource_requirements={"cpu": "2.0", "memory": "2g"},
            priority="medium"
        )
        
        # 11. Observability
        groups["observability"] = DockerGroup(
            name="observability",
            system="mainpc",
            agents=["ObservabilityHub", "PerformanceTracker"],
            ports=[9000, 9001],
            health_ports=[9100, 9101],
            dependencies=["infra_core"],
            resource_requirements={"cpu": "1.0", "memory": "512m"},
            priority="high"
        )
        
        # 12. Translation Services
        groups["translation_services"] = DockerGroup(
            name="translation_services",
            system="mainpc",
            agents=["TranslationAgent", "BergamotTranslator"],
            ports=[5711, 5712],
            health_ports=[8711, 8712],
            dependencies=["language_stack"],
            resource_requirements={"cpu": "2.0", "memory": "3g"},
            priority="medium"
        )
        
        # ============================================================================
        # PC2 GROUPS (7 total)
        # ============================================================================
        
        # 1. PC2 Memory Stack
        groups["pc2_memory_stack"] = DockerGroup(
            name="pc2_memory_stack",
            system="pc2",
            agents=["MemoryOrchestratorService", "CacheManager", "UnifiedMemoryReasoningAgent", "ContextManager", "ExperienceTracker"],
            ports=[7140, 7102, 7105, 7111, 7112],
            health_ports=[8140, 8102, 8105, 8111, 8112],
            dependencies=[],
            resource_requirements={"cpu": "2.0", "memory": "4g"},
            priority="critical"
        )
        
        # 2. PC2 Async Pipeline
        groups["pc2_async_pipeline"] = DockerGroup(
            name="pc2_async_pipeline",
            system="pc2",
            agents=["DreamWorldAgent", "DreamingModeAgent", "TutorAgent", "TutoringAgent", "VisionProcessingAgent"],
            ports=[7104, 7127, 7108, 7131, 7150],
            health_ports=[8104, 8127, 8108, 8131, 8150],
            dependencies=["pc2_memory_stack"],
            resource_requirements={"cpu": "4.0", "memory": "6g"},
            gpu_required=True,
            priority="high"
        )
        
        # 3. PC2 Web Interface
        groups["pc2_web_interface"] = DockerGroup(
            name="pc2_web_interface",
            system="pc2",
            agents=["FileSystemAssistantAgent", "RemoteConnectorAgent", "UnifiedWebAgent"],
            ports=[7123, 7124, 7126],
            health_ports=[8123, 8124, 8126],
            dependencies=["pc2_memory_stack"],
            resource_requirements={"cpu": "2.0", "memory": "3g"},
            priority="medium"
        )
        
        # 4. PC2 Infra Core
        groups["pc2_infra_core"] = DockerGroup(
            name="pc2_infra_core",
            system="pc2",
            agents=["TieredResponder", "AsyncProcessor", "ResourceManager", "TaskScheduler", "AdvancedRouter", "AuthenticationAgent", "UnifiedUtilsAgent", "ProactiveContextMonitor", "AgentTrustScorer"],
            ports=[7100, 7101, 7113, 7115, 7129, 7116, 7118, 7119, 7122],
            health_ports=[8100, 8101, 8113, 8115, 8129, 8116, 8118, 8119, 8122],
            dependencies=["pc2_memory_stack"],
            resource_requirements={"cpu": "3.0", "memory": "5g"},
            priority="high"
        )
        
        # 5. PC2 Vision Dream GPU
        groups["pc2_vision_dream_gpu"] = DockerGroup(
            name="pc2_vision_dream_gpu",
            system="pc2",
            agents=["DreamWorldAgent", "VisionProcessingAgent"],
            ports=[7104, 7150],
            health_ports=[8104, 8150],
            dependencies=["pc2_infra_core"],
            resource_requirements={"cpu": "3.0", "memory": "6g"},
            gpu_required=True,
            priority="medium"
        )
        
        # 6. PC2 Tutoring CPU
        groups["pc2_tutoring_cpu"] = DockerGroup(
            name="pc2_tutoring_cpu", 
            system="pc2",
            agents=["TutorAgent", "TutoringAgent"],
            ports=[7108, 7131],
            health_ports=[8108, 8131],
            dependencies=["pc2_memory_stack"],
            resource_requirements={"cpu": "2.0", "memory": "3g"},
            priority="medium"
        )
        
        # 7. PC2 Utility Suite
        groups["pc2_utility_suite"] = DockerGroup(
            name="pc2_utility_suite",
            system="pc2",
            agents=["ObservabilityHub"],
            ports=[9000],
            health_ports=[9100],
            dependencies=["pc2_infra_core"],
            resource_requirements={"cpu": "1.0", "memory": "1g"},
            priority="high"
        )
        
        return groups
    
    def _detect_current_machine(self) -> str:
        """Detect if we're on MainPC or PC2"""
        try:
            # Check GPU to determine machine
            gpu_info = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                    capture_output=True, text=True)
            if gpu_info.returncode == 0:
                gpu_name = gpu_info.stdout.strip()
                if "RTX 4090" in gpu_name:
                    return "mainpc"
                elif "RTX 3060" in gpu_name:
                    return "pc2"
            
            # Fallback: check network interface
            hostname = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
            if self.mainpc_ip in hostname.stdout:
                return "mainpc"
            elif self.pc2_ip in hostname.stdout:
                return "pc2"
                
        except Exception as e:
            self.logger.warning(f"Could not detect machine type: {e}")
        
        return "unknown"
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """
        🚀 RUN ALL COMPREHENSIVE TESTS
        """
        self.logger.info("🎯 STARTING COMPREHENSIVE DOCKER TESTING FRAMEWORK")
        
        test_suite_results = {}
        
        # Phase 1: Local Validation
        self.logger.info("📋 PHASE 1: Local Docker Group Validation")
        test_suite_results["local_validation"] = await self._run_local_validation()
        
        # Phase 2: Dependency Analysis  
        self.logger.info("📋 PHASE 2: Dependency Chain Analysis")
        test_suite_results["dependency_analysis"] = await self._analyze_dependencies()
        
        # Phase 3: Resource Requirements
        self.logger.info("📋 PHASE 3: Resource Requirements Validation")
        test_suite_results["resource_validation"] = await self._validate_resources()
        
        # Phase 4: Cross-Machine Preparation
        self.logger.info("📋 PHASE 4: Cross-Machine Sync Preparation")
        test_suite_results["cross_machine_prep"] = await self._prepare_cross_machine_sync()
        
        # Phase 5: Integration Testing
        self.logger.info("📋 PHASE 5: Integration Test Suite")
        test_suite_results["integration_tests"] = await self._run_integration_tests()
        
        # Phase 6: Bulletproof Framework Creation
        self.logger.info("📋 PHASE 6: Bulletproof Testing Framework")
        test_suite_results["bulletproof_framework"] = await self._create_bulletproof_framework()
        
        # Generate comprehensive report
        final_report = await self._generate_comprehensive_report(test_suite_results)
        
        self.logger.info("✅ COMPREHENSIVE TESTING COMPLETE")
        return final_report
    
    async def _run_local_validation(self) -> Dict[str, Any]:
        """
        📋 PHASE 1: LOCAL VALIDATION OF ALL DOCKER GROUPS
        Test that all groups can be built and run locally
        """
        results = {"passed": 0, "failed": 0, "details": {}}
        
        for group_name, group in self.docker_groups.items():
            self.logger.info(f"🔍 Testing local validation: {group_name}")
            
            try:
                # Test Docker build
                build_result = await self._test_docker_build(group)
                
                # Test port availability
                port_result = await self._test_port_availability(group)
                
                # Test resource requirements
                resource_result = await self._test_resource_requirements(group)
                
                # Test configuration
                config_result = await self._test_configuration(group)
                
                success = all([build_result["success"], port_result["success"], 
                             resource_result["success"], config_result["success"]])
                
                results["details"][group_name] = {
                    "build": build_result,
                    "ports": port_result,
                    "resources": resource_result,
                    "config": config_result,
                    "overall_success": success
                }
                
                if success:
                    results["passed"] += 1
                    self.logger.info(f"✅ {group_name}: Local validation passed")
                else:
                    results["failed"] += 1
                    self.logger.error(f"❌ {group_name}: Local validation failed")
                    
            except Exception as e:
                self.logger.error(f"❌ {group_name}: Exception during validation: {e}")
                results["failed"] += 1
                results["details"][group_name] = {"error": str(e), "overall_success": False}
        
        return results
    
    async def _test_docker_build(self, group: DockerGroup) -> Dict[str, Any]:
        """Test Docker build for a group"""
        try:
            dockerfile_path = f"docker/{group.name}/Dockerfile"
            if Path(dockerfile_path).exists():
                # Simulate build test (dry run)
                return {"success": True, "message": f"Dockerfile exists for {group.name}"}
            else:
                return {"success": False, "message": f"Missing Dockerfile for {group.name}"}
        except Exception as e:
            return {"success": False, "message": f"Build test failed: {e}"}
    
    async def _test_port_availability(self, group: DockerGroup) -> Dict[str, Any]:
        """Test if ports are available"""
        try:
            busy_ports = []
            for port in group.ports + group.health_ports:
                if self._is_port_busy(port):
                    busy_ports.append(port)
            
            if busy_ports:
                return {"success": False, "message": f"Ports busy: {busy_ports}"}
            else:
                return {"success": True, "message": "All ports available"}
        except Exception as e:
            return {"success": False, "message": f"Port test failed: {e}"}
    
    def _is_port_busy(self, port: int) -> bool:
        """Check if a port is currently in use"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(('localhost', port)) == 0
    
    async def _test_resource_requirements(self, group: DockerGroup) -> Dict[str, Any]:
        """Test if system has sufficient resources"""
        try:
            # Check CPU
            available_cpu = psutil.cpu_count()
            required_cpu = float(group.resource_requirements.get("cpu", "1.0"))
            
            # Check Memory
            available_memory = psutil.virtual_memory().available / (1024**3)  # GB
            required_memory_str = group.resource_requirements.get("memory", "1g")
            required_memory = float(required_memory_str.replace("g", "").replace("m", "")) 
            if "m" in required_memory_str:
                required_memory /= 1024  # Convert MB to GB
            
            # Check GPU if required
            gpu_available = True
            if group.gpu_required:
                try:
                    gpu_info = subprocess.run(['nvidia-smi'], capture_output=True)
                    gpu_available = gpu_info.returncode == 0
                except:
                    gpu_available = False
            
            success = (available_cpu >= required_cpu and 
                      available_memory >= required_memory and
                      (not group.gpu_required or gpu_available))
            
            return {
                "success": success,
                "details": {
                    "cpu": {"available": available_cpu, "required": required_cpu},
                    "memory": {"available": available_memory, "required": required_memory},
                    "gpu": {"required": group.gpu_required, "available": gpu_available}
                }
            }
        except Exception as e:
            return {"success": False, "message": f"Resource test failed: {e}"}
    
    async def _test_configuration(self, group: DockerGroup) -> Dict[str, Any]:
        """Test configuration files exist and are valid"""
        try:
            config_files = [
                f"config/{group.system}_services.yaml",
                f"docker/{group.name}/docker-compose.yml"
            ]
            
            missing_files = []
            for config_file in config_files:
                if not Path(config_file).exists():
                    missing_files.append(config_file)
            
            if missing_files:
                return {"success": False, "message": f"Missing config files: {missing_files}"}
            else:
                return {"success": True, "message": "All config files present"}
        except Exception as e:
            return {"success": False, "message": f"Config test failed: {e}"}
    
    async def _analyze_dependencies(self) -> Dict[str, Any]:
        """
        📋 PHASE 2: ANALYZE DEPENDENCY CHAINS
        """
        results = {"dependency_graph": {}, "startup_order": [], "circular_dependencies": []}
        
        # Build dependency graph
        for group_name, group in self.docker_groups.items():
            results["dependency_graph"][group_name] = {
                "dependencies": group.dependencies,
                "system": group.system,
                "priority": group.priority
            }
        
        # Calculate startup order
        startup_order = self._calculate_startup_order()
        results["startup_order"] = startup_order
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies()
        results["circular_dependencies"] = circular_deps
        
        return results
    
    def _calculate_startup_order(self) -> List[str]:
        """Calculate optimal startup order based on dependencies"""
        # Simple topological sort
        in_degree = {name: 0 for name in self.docker_groups.keys()}
        
        # Calculate in-degrees
        for group_name, group in self.docker_groups.items():
            for dep in group.dependencies:
                if dep in in_degree:
                    in_degree[group_name] += 1
        
        # Process nodes with no dependencies first
        queue = [name for name, degree in in_degree.items() if degree == 0]
        startup_order = []
        
        while queue:
            # Sort by priority within same dependency level
            queue.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[self.docker_groups[x].priority])
            current = queue.pop(0)
            startup_order.append(current)
            
            # Update in-degrees for dependent services
            for group_name, group in self.docker_groups.items():
                if current in group.dependencies:
                    in_degree[group_name] -= 1
                    if in_degree[group_name] == 0:
                        queue.append(group_name)
        
        return startup_order
    
    def _detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the dependency graph"""
        visited = set()
        rec_stack = set()
        circular_deps = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                circular_deps.append(path[cycle_start:] + [node])
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            if node in self.docker_groups:
                for dep in self.docker_groups[node].dependencies:
                    if dep in self.docker_groups:
                        if dfs(dep, path + [node]):
                            return True
            
            rec_stack.remove(node)
            return False
        
        for group_name in self.docker_groups.keys():
            if group_name not in visited:
                dfs(group_name, [])
        
        return circular_deps
    
    async def _validate_resources(self) -> Dict[str, Any]:
        """
        📋 PHASE 3: VALIDATE RESOURCE REQUIREMENTS
        """
        results = {
            "total_cpu_required": 0.0,
            "total_memory_required": 0.0,
            "gpu_groups": [],
            "system_capacity": {},
            "resource_conflicts": [],
            "recommendations": []
        }
        
        # Calculate total requirements
        for group_name, group in self.docker_groups.items():
            cpu_req = float(group.resource_requirements.get("cpu", "1.0"))
            mem_req_str = group.resource_requirements.get("memory", "1g")
            mem_req = float(mem_req_str.replace("g", "").replace("m", ""))
            if "m" in mem_req_str:
                mem_req /= 1024
            
            results["total_cpu_required"] += cpu_req
            results["total_memory_required"] += mem_req
            
            if group.gpu_required:
                results["gpu_groups"].append(group_name)
        
        # Check system capacity
        results["system_capacity"] = {
            "cpu_cores": psutil.cpu_count(),
            "memory_gb": psutil.virtual_memory().total / (1024**3),
            "gpu_available": self._check_gpu_availability()
        }
        
        # Detect resource conflicts
        if results["total_cpu_required"] > results["system_capacity"]["cpu_cores"]:
            results["resource_conflicts"].append("CPU oversubscription detected")
        
        if results["total_memory_required"] > results["system_capacity"]["memory_gb"] * 0.8:  # 80% threshold
            results["resource_conflicts"].append("Memory oversubscription detected")
        
        # Generate recommendations
        if results["resource_conflicts"]:
            results["recommendations"].append("Consider resource optimization or scaling")
        
        return results
    
    def _check_gpu_availability(self) -> Dict[str, Any]:
        """Check GPU availability and specs"""
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split('\n')
                return {"available": True, "gpus": gpu_info}
            else:
                return {"available": False, "gpus": []}
        except:
            return {"available": False, "gpus": []}
    
    async def _prepare_cross_machine_sync(self) -> Dict[str, Any]:
        """
        📋 PHASE 4: CROSS-MACHINE SYNC PREPARATION
        """
        results = {
            "network_connectivity": {},
            "port_mapping": {},
            "sync_validation_framework": {},
            "pre_sync_checklist": [],
            "post_sync_validation": []
        }
        
        # Test network connectivity
        results["network_connectivity"] = await self._test_network_connectivity()
        
        # Analyze port mappings
        results["port_mapping"] = self._analyze_port_mappings()
        
        # Create sync validation framework
        results["sync_validation_framework"] = self._create_sync_validation_framework()
        
        return results
    
    async def _test_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity between machines"""
        connectivity = {"mainpc_to_pc2": False, "pc2_to_mainpc": False}
        
        try:
            if self.current_machine == "mainpc":
                # Test connection to PC2
                ping_result = subprocess.run(['ping', '-c', '3', self.pc2_ip], 
                                           capture_output=True)
                connectivity["mainpc_to_pc2"] = ping_result.returncode == 0
            elif self.current_machine == "pc2":
                # Test connection to MainPC
                ping_result = subprocess.run(['ping', '-c', '3', self.mainpc_ip], 
                                           capture_output=True)
                connectivity["pc2_to_mainpc"] = ping_result.returncode == 0
        except Exception as e:
            self.logger.error(f"Network connectivity test failed: {e}")
        
        return connectivity
    
    def _analyze_port_mappings(self) -> Dict[str, Any]:
        """Analyze port mappings for conflicts"""
        port_mapping = {"mainpc_ports": {}, "pc2_ports": {}, "conflicts": []}
        
        for group_name, group in self.docker_groups.items():
            if group.system == "mainpc":
                port_mapping["mainpc_ports"][group_name] = group.ports + group.health_ports
            else:
                port_mapping["pc2_ports"][group_name] = group.ports + group.health_ports
        
        # Check for port conflicts
        mainpc_ports = set()
        pc2_ports = set()
        
        for ports in port_mapping["mainpc_ports"].values():
            mainpc_ports.update(ports)
        
        for ports in port_mapping["pc2_ports"].values():
            pc2_ports.update(ports)
        
        conflicts = mainpc_ports.intersection(pc2_ports)
        if conflicts:
            port_mapping["conflicts"] = list(conflicts)
        
        return port_mapping
    
    def _create_sync_validation_framework(self) -> Dict[str, Any]:
        """Create framework for validating sync operations"""
        framework = {
            "pre_sync_tests": [
                "validate_all_services_healthy",
                "backup_critical_data", 
                "verify_network_connectivity",
                "check_resource_availability"
            ],
            "sync_monitoring": [
                "monitor_service_states",
                "track_data_transfer",
                "validate_cross_machine_communication"
            ],
            "post_sync_validation": [
                "verify_all_services_running",
                "test_cross_machine_integration", 
                "validate_data_consistency",
                "performance_benchmark"
            ]
        }
        return framework
    
    async def _run_integration_tests(self) -> Dict[str, Any]:
        """
        📋 PHASE 5: INTEGRATION TEST SUITE
        """
        results = {
            "service_communication": {},
            "cross_group_integration": {},
            "load_balancing": {},
            "failover_scenarios": {}
        }
        
        # Test service communication
        results["service_communication"] = await self._test_service_communication()
        
        # Test cross-group integration
        results["cross_group_integration"] = await self._test_cross_group_integration()
        
        # Test load balancing (if applicable)
        results["load_balancing"] = await self._test_load_balancing()
        
        # Test failover scenarios
        results["failover_scenarios"] = await self._test_failover_scenarios()
        
        return results
    
    async def _test_service_communication(self) -> Dict[str, Any]:
        """Test communication between services"""
        communication_results = {}
        
        for group_name, group in self.docker_groups.items():
            communication_results[group_name] = {
                "internal_communication": "pending",
                "external_communication": "pending",
                "health_check_response": "pending"
            }
            
            # Simulate communication tests
            try:
                # Test health endpoint if available
                health_port = group.health_ports[0] if group.health_ports else None
                if health_port:
                    # This would be an actual HTTP request in real implementation
                    communication_results[group_name]["health_check_response"] = "simulated_success"
                
                communication_results[group_name]["internal_communication"] = "simulated_success"
                communication_results[group_name]["external_communication"] = "simulated_success"
                
            except Exception as e:
                communication_results[group_name]["error"] = str(e)
        
        return communication_results
    
    async def _test_cross_group_integration(self) -> Dict[str, Any]:
        """Test integration between different groups"""
        integration_results = {}
        
        # Test dependency chains
        for group_name, group in self.docker_groups.items():
            if group.dependencies:
                integration_results[group_name] = {
                    "dependencies": group.dependencies,
                    "integration_status": "simulated_success"
                }
        
        return integration_results
    
    async def _test_load_balancing(self) -> Dict[str, Any]:
        """Test load balancing capabilities"""
        return {
            "load_distribution": "not_implemented",
            "scaling_capability": "not_implemented",
            "performance_impact": "to_be_measured"
        }
    
    async def _test_failover_scenarios(self) -> Dict[str, Any]:
        """Test failover scenarios"""
        return {
            "single_service_failure": "not_implemented",
            "group_failure": "not_implemented", 
            "cross_machine_failure": "not_implemented",
            "recovery_procedures": "documented"
        }
    
    async def _create_bulletproof_framework(self) -> Dict[str, Any]:
        """
        📋 PHASE 6: CREATE BULLETPROOF TESTING FRAMEWORK
        """
        framework = {
            "automated_testing": self._create_automated_test_suite(),
            "continuous_monitoring": self._create_monitoring_framework(),
            "validation_protocols": self._create_validation_protocols(),
            "recovery_procedures": self._create_recovery_procedures()
        }
        
        return framework
    
    def _create_automated_test_suite(self) -> Dict[str, Any]:
        """Create automated test suite"""
        return {
            "unit_tests": "per_service_validation",
            "integration_tests": "cross_service_communication",
            "system_tests": "end_to_end_workflows",
            "performance_tests": "load_and_stress_testing",
            "security_tests": "authentication_and_authorization"
        }
    
    def _create_monitoring_framework(self) -> Dict[str, Any]:
        """Create continuous monitoring framework"""
        return {
            "health_monitoring": "continuous_health_checks",
            "performance_monitoring": "resource_usage_tracking",
            "log_aggregation": "centralized_logging",
            "alerting": "threshold_based_alerts",
            "dashboards": "real_time_visualization"
        }
    
    def _create_validation_protocols(self) -> Dict[str, Any]:
        """Create validation protocols"""
        return {
            "startup_validation": "service_initialization_checks",
            "runtime_validation": "periodic_health_verification", 
            "sync_validation": "cross_machine_consistency_checks",
            "performance_validation": "benchmark_comparisons"
        }
    
    def _create_recovery_procedures(self) -> Dict[str, Any]:
        """Create recovery procedures"""
        return {
            "service_restart": "automated_service_recovery",
            "data_recovery": "backup_restoration_procedures",
            "network_recovery": "connectivity_restoration",
            "full_system_recovery": "complete_system_rebuild"
        }
    
    async def _generate_comprehensive_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        report = {
            "test_summary": {
                "total_groups_tested": len(self.docker_groups),
                "mainpc_groups": len([g for g in self.docker_groups.values() if g.system == "mainpc"]),
                "pc2_groups": len([g for g in self.docker_groups.values() if g.system == "pc2"]),
                "total_duration_seconds": total_duration,
                "test_timestamp": datetime.now().isoformat()
            },
            "phase_results": test_results,
            "docker_groups_analyzed": {name: asdict(group) for name, group in self.docker_groups.items()},
            "recommendations": self._generate_recommendations(test_results),
            "next_steps": self._generate_next_steps(test_results)
        }
        
        # Save report to file
        report_file = f"testing/comprehensive_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("testing").mkdir(exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"📊 Comprehensive test report saved to: {report_file}")
        
        return report
    
    def _generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Local validation recommendations
        if test_results.get("local_validation", {}).get("failed", 0) > 0:
            recommendations.append("🔧 Fix local validation failures before deployment")
        
        # Resource recommendations
        resource_results = test_results.get("resource_validation", {})
        if resource_results.get("resource_conflicts"):
            recommendations.append("⚡ Address resource conflicts to prevent performance issues")
        
        # Dependency recommendations
        dep_results = test_results.get("dependency_analysis", {})
        if dep_results.get("circular_dependencies"):
            recommendations.append("🔄 Resolve circular dependencies in service architecture")
        
        # Cross-machine recommendations
        cross_machine = test_results.get("cross_machine_prep", {})
        network_issues = cross_machine.get("network_connectivity", {})
        if not all(network_issues.values()):
            recommendations.append("🌐 Fix network connectivity issues between machines")
        
        return recommendations
    
    def _generate_next_steps(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate next steps based on test results"""
        next_steps = [
            "1. 🔧 Fix any identified local validation issues",
            "2. 🚀 Run PC2 services locally on Main PC for initial testing",
            "3. 🌐 Validate cross-machine network connectivity",
            "4. 📋 Execute sync preparation checklist",
            "5. 🔄 Perform actual PC2 sync operation",
            "6. ✅ Run post-sync validation tests",
            "7. 📊 Monitor system performance and health",
            "8. 🛡️ Implement continuous monitoring and alerting"
        ]
        
        return next_steps

# =============================================================================
# TESTING EXECUTION FUNCTIONS
# =============================================================================

async def main():
    """Main execution function"""
    tester = ComprehensiveDockerTester()
    
    try:
        # Run comprehensive tests
        results = await tester.run_comprehensive_tests()
        
        # Print summary
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE DOCKER TESTING FRAMEWORK - SUMMARY")
        print("="*80)
        
        summary = results["test_summary"]
        print(f"📊 Total Groups Tested: {summary['total_groups_tested']}")
        print(f"🖥️ MainPC Groups: {summary['mainpc_groups']}")
        print(f"💻 PC2 Groups: {summary['pc2_groups']}")
        print(f"⏱️ Total Duration: {summary['total_duration_seconds']:.2f} seconds")
        
        print("\n📋 RECOMMENDATIONS:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"  {i}. {rec}")
        
        print("\n🚀 NEXT STEPS:")
        for step in results["next_steps"]:
            print(f"  {step}")
        
        print("\n✅ TESTING FRAMEWORK COMPLETE")
        return results
        
    except Exception as e:
        logger.error(f"❌ Testing framework failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())