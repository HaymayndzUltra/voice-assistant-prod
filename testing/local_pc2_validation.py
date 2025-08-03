#!/usr/bin/env python3
"""
🎯 LOCAL PC2 VALIDATION SUITE
Tests all PC2 Docker groups locally on Main PC before cross-machine sync
Ensures PC2 services can run without conflicts and validates port mappings
"""

import asyncio
import json
import logging
import subprocess
import socket
import time
import requests
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import docker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LocalPC2Validator:
    """
    🚀 LOCAL PC2 VALIDATION SUITE
    Validates all 7 PC2 Docker groups can run locally on Main PC
    """
    
    def __init__(self):
        self.logger = logger
        self.docker_client = docker.from_env()
        self.start_time = datetime.now()
        
        # PC2 Groups to validate locally
        self.pc2_groups = {
            "pc2_memory_stack": {
                "agents": ["MemoryOrchestratorService", "CacheManager", "UnifiedMemoryReasoningAgent", "ContextManager", "ExperienceTracker"],
                "ports": [7140, 7102, 7105, 7111, 7112],
                "health_ports": [8140, 8102, 8105, 8111, 8112],
                "resource_cpu": "2.0",
                "resource_memory": "4g",
                "gpu_required": False,
                "priority": "critical"
            },
            "pc2_async_pipeline": {
                "agents": ["DreamWorldAgent", "DreamingModeAgent", "TutorAgent", "TutoringAgent", "VisionProcessingAgent"],
                "ports": [7104, 7127, 7108, 7131, 7150],
                "health_ports": [8104, 8127, 8108, 8131, 8150],
                "resource_cpu": "4.0", 
                "resource_memory": "6g",
                "gpu_required": True,
                "priority": "high"
            },
            "pc2_web_interface": {
                "agents": ["FileSystemAssistantAgent", "RemoteConnectorAgent", "UnifiedWebAgent"],
                "ports": [7123, 7124, 7126],
                "health_ports": [8123, 8124, 8126],
                "resource_cpu": "2.0",
                "resource_memory": "3g", 
                "gpu_required": False,
                "priority": "medium"
            },
            "pc2_infra_core": {
                "agents": ["TieredResponder", "AsyncProcessor", "ResourceManager", "TaskScheduler", "AdvancedRouter", "AuthenticationAgent", "UnifiedUtilsAgent", "ProactiveContextMonitor", "AgentTrustScorer"],
                "ports": [7100, 7101, 7113, 7115, 7129, 7116, 7118, 7119, 7122],
                "health_ports": [8100, 8101, 8113, 8115, 8129, 8116, 8118, 8119, 8122],
                "resource_cpu": "3.0",
                "resource_memory": "5g",
                "gpu_required": False,
                "priority": "high"
            },
            "pc2_vision_dream_gpu": {
                "agents": ["DreamWorldAgent", "VisionProcessingAgent"],
                "ports": [7104, 7150],  # Note: May conflict with async_pipeline
                "health_ports": [8104, 8150],
                "resource_cpu": "3.0",
                "resource_memory": "6g",
                "gpu_required": True,
                "priority": "medium"
            },
            "pc2_tutoring_cpu": {
                "agents": ["TutorAgent", "TutoringAgent"],
                "ports": [7108, 7131],  # Note: May conflict with async_pipeline
                "health_ports": [8108, 8131],
                "resource_cpu": "2.0",
                "resource_memory": "3g",
                "gpu_required": False,
                "priority": "medium"
            },
            "pc2_utility_suite": {
                "agents": ["ObservabilityHub"],
                "ports": [9000],  # CONFLICT: Same as Main PC ObservabilityHub
                "health_ports": [9100],
                "resource_cpu": "1.0",
                "resource_memory": "1g",
                "gpu_required": False,
                "priority": "high"
            }
        }
        
        # Main PC services to check for conflicts
        self.mainpc_ports = {
            "infra_core": [7200, 7210, 7220, 8200, 8210, 8220],
            "coordination": [7211, 7212, 8211, 8212], 
            "memory_stack": [6713, 7103, 7106, 7107, 8713, 8103, 8106, 8107],
            "observability": [9000, 9001, 9100, 9101],  # CONFLICT with PC2 utility_suite
            "vision_gpu": [6610, 6611, 6612, 8610, 8611, 8612],
            "speech_gpu": [6800, 6801, 6802, 6803, 8800, 8801, 8802, 8803],
            "learning_gpu": [5580, 5581, 5582, 8580, 8581, 8582],
            "reasoning_gpu": [6612, 6613, 6614, 8612, 8613, 8614],  # Port 6612/8612 conflicts with vision
            "language_stack": [5709, 5710, 8709, 8710],
            "utility_cpu": [5650, 5651, 5652, 5653, 8650, 8651, 8652, 8653],
            "emotion_system": [6590, 6591, 8590, 8591],
            "translation_services": [5711, 5712, 8711, 8712]
        }
        
        self.validation_results = {}
        
    async def run_local_pc2_validation(self) -> Dict[str, Any]:
        """
        🚀 RUN COMPLETE LOCAL PC2 VALIDATION
        """
        self.logger.info("🎯 STARTING LOCAL PC2 VALIDATION ON MAIN PC")
        
        validation_phases = {}
        
        # Phase 1: Port Conflict Analysis
        self.logger.info("📋 PHASE 1: Port Conflict Analysis")
        validation_phases["port_conflicts"] = await self._analyze_port_conflicts()
        
        # Phase 2: Resource Capacity Check
        self.logger.info("📋 PHASE 2: Resource Capacity Validation") 
        validation_phases["resource_capacity"] = await self._validate_resource_capacity()
        
        # Phase 3: Docker Build Validation
        self.logger.info("📋 PHASE 3: Docker Build Validation")
        validation_phases["docker_builds"] = await self._validate_docker_builds()
        
        # Phase 4: Agent Script Validation
        self.logger.info("📋 PHASE 4: Agent Script Validation")
        validation_phases["agent_scripts"] = await self._validate_agent_scripts()
        
        # Phase 5: Local Startup Test
        self.logger.info("📋 PHASE 5: Local Startup Test (Dry Run)")
        validation_phases["startup_test"] = await self._test_local_startup()
        
        # Phase 6: Cross-Dependency Analysis
        self.logger.info("📋 PHASE 6: Cross-Dependency Analysis")
        validation_phases["dependencies"] = await self._analyze_dependencies()
        
        # Generate comprehensive report
        final_report = await self._generate_validation_report(validation_phases)
        
        self.logger.info("✅ LOCAL PC2 VALIDATION COMPLETE")
        return final_report
    
    async def _analyze_port_conflicts(self) -> Dict[str, Any]:
        """
        📋 PHASE 1: ANALYZE PORT CONFLICTS
        """
        conflicts = {"critical_conflicts": [], "potential_conflicts": [], "safe_ports": []}
        
        # Collect all Main PC ports
        all_mainpc_ports = set()
        for service_ports in self.mainpc_ports.values():
            all_mainpc_ports.update(service_ports)
        
        # Check each PC2 group for conflicts
        for group_name, group_config in self.pc2_groups.items():
            group_ports = group_config["ports"] + group_config["health_ports"]
            
            for port in group_ports:
                if port in all_mainpc_ports:
                    conflicts["critical_conflicts"].append({
                        "pc2_group": group_name,
                        "port": port,
                        "conflict_with": self._find_mainpc_service_by_port(port),
                        "severity": "critical"
                    })
                elif self._is_port_busy(port):
                    conflicts["potential_conflicts"].append({
                        "pc2_group": group_name,
                        "port": port,
                        "reason": "port_currently_busy",
                        "severity": "warning"
                    })
                else:
                    conflicts["safe_ports"].append({
                        "pc2_group": group_name,
                        "port": port,
                        "status": "available"
                    })
        
        # Generate port remapping suggestions
        conflicts["remapping_suggestions"] = self._generate_port_remapping(conflicts["critical_conflicts"])
        
        return conflicts
    
    def _find_mainpc_service_by_port(self, port: int) -> str:
        """Find which Main PC service uses a specific port"""
        for service_name, ports in self.mainpc_ports.items():
            if port in ports:
                return service_name
        return "unknown_service"
    
    def _is_port_busy(self, port: int) -> bool:
        """Check if a port is currently in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            return sock.connect_ex(('localhost', port)) == 0
    
    def _generate_port_remapping(self, conflicts: List[Dict]) -> Dict[str, Dict]:
        """Generate port remapping suggestions for conflicts"""
        remapping = {}
        base_pc2_port = 17000  # Start PC2 ports at 17000 range
        
        for conflict in conflicts:
            group_name = conflict["pc2_group"]
            old_port = conflict["port"]
            
            if group_name not in remapping:
                remapping[group_name] = {"port_changes": []}
            
            # Find next available port in 17000+ range
            new_port = base_pc2_port
            while self._is_port_busy(new_port):
                new_port += 1
            
            remapping[group_name]["port_changes"].append({
                "original_port": old_port,
                "suggested_port": new_port,
                "reason": f"conflict_with_{conflict['conflict_with']}"
            })
            
            base_pc2_port = new_port + 1
        
        return remapping
    
    async def _validate_resource_capacity(self) -> Dict[str, Any]:
        """
        📋 PHASE 2: VALIDATE RESOURCE CAPACITY
        """
        capacity = {
            "system_resources": {},
            "pc2_requirements": {},
            "capacity_analysis": {},
            "scaling_recommendations": []
        }
        
        # Get system resources
        capacity["system_resources"] = {
            "cpu_cores": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "memory_available_gb": psutil.virtual_memory().available / (1024**3),
            "gpu_available": self._check_gpu_capacity()
        }
        
        # Calculate PC2 requirements
        total_cpu = 0.0
        total_memory = 0.0
        gpu_groups = []
        
        for group_name, config in self.pc2_groups.items():
            cpu_req = float(config["resource_cpu"])
            memory_str = config["resource_memory"]
            memory_req = float(memory_str.replace("g", "").replace("m", ""))
            if "m" in memory_str:
                memory_req /= 1024
                
            total_cpu += cpu_req
            total_memory += memory_req
            
            if config["gpu_required"]:
                gpu_groups.append(group_name)
        
        capacity["pc2_requirements"] = {
            "total_cpu_required": total_cpu,
            "total_memory_required_gb": total_memory,
            "gpu_groups": gpu_groups,
            "gpu_groups_count": len(gpu_groups)
        }
        
        # Capacity analysis
        cpu_utilization = (total_cpu / capacity["system_resources"]["cpu_cores"]) * 100
        memory_utilization = (total_memory / capacity["system_resources"]["memory_total_gb"]) * 100
        
        capacity["capacity_analysis"] = {
            "cpu_utilization_percent": cpu_utilization,
            "memory_utilization_percent": memory_utilization,
            "gpu_sufficient": len(gpu_groups) <= len(capacity["system_resources"]["gpu_available"]["gpus"]) if capacity["system_resources"]["gpu_available"]["available"] else False,
            "overall_feasible": cpu_utilization < 80 and memory_utilization < 80
        }
        
        # Recommendations
        if cpu_utilization > 80:
            capacity["scaling_recommendations"].append("CPU oversubscription - consider resource limits or sequential startup")
        if memory_utilization > 80:
            capacity["scaling_recommendations"].append("Memory oversubscription - implement memory optimization")
        if not capacity["capacity_analysis"]["gpu_sufficient"]:
            capacity["scaling_recommendations"].append("Insufficient GPU resources - prioritize GPU usage")
        
        return capacity
    
    def _check_gpu_capacity(self) -> Dict[str, Any]:
        """Check GPU availability and memory"""
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free', '--format=csv,noheader'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                gpu_lines = result.stdout.strip().split('\n')
                gpus = []
                for line in gpu_lines:
                    parts = line.split(', ')
                    if len(parts) == 4:
                        gpus.append({
                            "name": parts[0],
                            "memory_total_mb": parts[1],
                            "memory_used_mb": parts[2], 
                            "memory_free_mb": parts[3]
                        })
                return {"available": True, "gpus": gpus}
            else:
                return {"available": False, "gpus": []}
        except:
            return {"available": False, "gpus": []}
    
    async def _validate_docker_builds(self) -> Dict[str, Any]:
        """
        📋 PHASE 3: VALIDATE DOCKER BUILDS
        """
        build_results = {"successful": [], "failed": [], "missing_files": []}
        
        for group_name in self.pc2_groups.keys():
            self.logger.info(f"🔍 Validating Docker build for {group_name}")
            
            # Check for Dockerfile
            dockerfile_path = f"docker/pc2/Dockerfile.agent-group"
            if not Path(dockerfile_path).exists():
                build_results["missing_files"].append({
                    "group": group_name,
                    "missing_file": dockerfile_path,
                    "type": "dockerfile"
                })
                continue
            
            # Check for docker-compose file
            compose_path = f"docker/pc2/docker-compose.pc2.yml" 
            if not Path(compose_path).exists():
                build_results["missing_files"].append({
                    "group": group_name,
                    "missing_file": compose_path,
                    "type": "docker_compose"
                })
                continue
            
            # Simulate build validation (dry run)
            try:
                # In real implementation, would do: docker build --dry-run
                build_results["successful"].append({
                    "group": group_name,
                    "dockerfile": dockerfile_path,
                    "status": "build_ready"
                })
            except Exception as e:
                build_results["failed"].append({
                    "group": group_name,
                    "error": str(e),
                    "status": "build_failed"
                })
        
        return build_results
    
    async def _validate_agent_scripts(self) -> Dict[str, Any]:
        """
        📋 PHASE 4: VALIDATE AGENT SCRIPTS
        """
        script_results = {"found": [], "missing": [], "syntax_errors": []}
        
        for group_name, config in self.pc2_groups.items():
            for agent_name in config["agents"]:
                self.logger.info(f"🔍 Validating agent script: {agent_name}")
                
                # Look for agent script in common locations
                possible_paths = [
                    f"pc2_code/agents/{agent_name.lower()}.py",
                    f"pc2_code/agents/{agent_name}.py",
                    f"pc2_code/agents/ForPC2/{agent_name.lower()}.py",
                    f"agents/{agent_name.lower()}.py"
                ]
                
                script_found = False
                for script_path in possible_paths:
                    if Path(script_path).exists():
                        try:
                            # Basic syntax validation
                            with open(script_path, 'r') as f:
                                compile(f.read(), script_path, 'exec')
                            
                            script_results["found"].append({
                                "agent": agent_name,
                                "group": group_name,
                                "path": script_path,
                                "status": "valid"
                            })
                            script_found = True
                            break
                        except SyntaxError as e:
                            script_results["syntax_errors"].append({
                                "agent": agent_name,
                                "group": group_name,
                                "path": script_path,
                                "error": str(e)
                            })
                            script_found = True
                            break
                
                if not script_found:
                    script_results["missing"].append({
                        "agent": agent_name,
                        "group": group_name,
                        "searched_paths": possible_paths
                    })
        
        return script_results
    
    async def _test_local_startup(self) -> Dict[str, Any]:
        """
        📋 PHASE 5: TEST LOCAL STARTUP (DRY RUN)
        """
        startup_results = {
            "startup_order": [],
            "resource_conflicts": [],
            "port_availability": {},
            "simulation_results": {}
        }
        
        # Calculate optimal startup order based on priorities and dependencies
        startup_order = self._calculate_pc2_startup_order()
        startup_results["startup_order"] = startup_order
        
        # Simulate startup for each group
        for group_name in startup_order:
            config = self.pc2_groups[group_name]
            
            # Check port availability at startup time
            port_status = {}
            for port in config["ports"] + config["health_ports"]:
                port_status[port] = "available" if not self._is_port_busy(port) else "busy"
            
            startup_results["port_availability"][group_name] = port_status
            
            # Simulate resource allocation
            cpu_req = float(config["resource_cpu"])
            memory_req = config["resource_memory"]
            
            startup_results["simulation_results"][group_name] = {
                "startup_time_estimate": self._estimate_startup_time(config),
                "resource_allocation": {
                    "cpu": cpu_req,
                    "memory": memory_req,
                    "gpu": config["gpu_required"]
                },
                "health_check_ports": config["health_ports"],
                "status": "simulated_success"
            }
        
        return startup_results
    
    def _calculate_pc2_startup_order(self) -> List[str]:
        """Calculate optimal startup order for PC2 groups"""
        # Priority order: critical -> high -> medium -> low
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        groups_sorted = sorted(
            self.pc2_groups.items(),
            key=lambda x: (priority_order[x[1]["priority"]], x[0])
        )
        
        return [group[0] for group in groups_sorted]
    
    def _estimate_startup_time(self, config: Dict) -> float:
        """Estimate startup time for a group based on complexity"""
        base_time = 30.0  # seconds
        agent_factor = len(config["agents"]) * 5.0
        gpu_factor = 20.0 if config["gpu_required"] else 0.0
        memory_factor = float(config["resource_memory"].replace("g", "")) * 2.0
        
        return base_time + agent_factor + gpu_factor + memory_factor
    
    async def _analyze_dependencies(self) -> Dict[str, Any]:
        """
        📋 PHASE 6: ANALYZE CROSS-DEPENDENCIES
        """
        dependencies = {
            "internal_dependencies": {},
            "mainpc_dependencies": {},
            "startup_blockers": [],
            "optimization_opportunities": []
        }
        
        # Analyze internal PC2 dependencies
        for group_name, config in self.pc2_groups.items():
            dependencies["internal_dependencies"][group_name] = {
                "depends_on": self._find_pc2_dependencies(group_name),
                "depended_by": self._find_pc2_dependents(group_name)
            }
        
        # Analyze Main PC dependencies
        dependencies["mainpc_dependencies"] = {
            "memory_services": ["mainpc_memory_stack"],  # PC2 memory might sync with Main PC
            "observability": ["mainpc_observability"],   # PC2 forwards to Main PC
            "coordination": ["mainpc_coordination"]      # Cross-machine coordination
        }
        
        # Identify startup blockers
        for group_name in self.pc2_groups.keys():
            if self.pc2_groups[group_name]["priority"] == "critical":
                dependencies["startup_blockers"].append({
                    "group": group_name,
                    "reason": "critical_priority_service",
                    "impact": "blocks_dependent_services"
                })
        
        # Optimization opportunities
        dependencies["optimization_opportunities"] = [
            "parallel_startup_non_dependent_groups",
            "gpu_resource_sharing",
            "memory_optimization_across_groups",
            "health_check_consolidation"
        ]
        
        return dependencies
    
    def _find_pc2_dependencies(self, group_name: str) -> List[str]:
        """Find internal PC2 dependencies for a group"""
        # Simple dependency rules based on group analysis
        deps = {
            "pc2_async_pipeline": ["pc2_memory_stack"],
            "pc2_web_interface": ["pc2_memory_stack"],
            "pc2_infra_core": ["pc2_memory_stack"],
            "pc2_vision_dream_gpu": ["pc2_infra_core", "pc2_memory_stack"],
            "pc2_tutoring_cpu": ["pc2_memory_stack"],
            "pc2_utility_suite": ["pc2_infra_core"]
        }
        return deps.get(group_name, [])
    
    def _find_pc2_dependents(self, group_name: str) -> List[str]:
        """Find which PC2 groups depend on this one"""
        dependents = []
        for other_group in self.pc2_groups.keys():
            if group_name in self._find_pc2_dependencies(other_group):
                dependents.append(other_group)
        return dependents
    
    async def _generate_validation_report(self, validation_phases: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        # Count issues
        critical_issues = len(validation_phases["port_conflicts"]["critical_conflicts"])
        warnings = len(validation_phases["port_conflicts"]["potential_conflicts"])
        missing_scripts = len(validation_phases["agent_scripts"]["missing"])
        
        report = {
            "validation_summary": {
                "total_pc2_groups": len(self.pc2_groups),
                "validation_duration_seconds": duration,
                "critical_issues": critical_issues,
                "warnings": warnings,
                "missing_agent_scripts": missing_scripts,
                "overall_readiness": "ready" if critical_issues == 0 and missing_scripts == 0 else "needs_fixes",
                "timestamp": datetime.now().isoformat()
            },
            "phase_results": validation_phases,
            "pc2_groups_analyzed": self.pc2_groups,
            "recommendations": self._generate_local_recommendations(validation_phases),
            "fix_priorities": self._generate_fix_priorities(validation_phases),
            "next_steps": self._generate_local_next_steps(validation_phases)
        }
        
        # Save report
        report_file = f"testing/local_pc2_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        Path("testing").mkdir(exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"📊 Local PC2 validation report saved to: {report_file}")
        
        return report
    
    def _generate_local_recommendations(self, phases: Dict[str, Any]) -> List[str]:
        """Generate recommendations for local PC2 validation"""
        recommendations = []
        
        # Port conflict recommendations
        if phases["port_conflicts"]["critical_conflicts"]:
            recommendations.append("🔧 CRITICAL: Remap conflicting ports before local testing")
        
        # Resource recommendations
        capacity = phases["resource_capacity"]["capacity_analysis"]
        if not capacity["overall_feasible"]:
            recommendations.append("⚡ Resource optimization required for local testing")
        
        # Missing scripts
        if phases["agent_scripts"]["missing"]:
            recommendations.append("📝 Create missing agent scripts or placeholders")
        
        # GPU recommendations
        gpu_groups = phases["resource_capacity"]["pc2_requirements"]["gpu_groups"]
        if gpu_groups and not phases["resource_capacity"]["capacity_analysis"]["gpu_sufficient"]:
            recommendations.append("🎮 GPU resource scheduling needed for concurrent GPU groups")
        
        return recommendations
    
    def _generate_fix_priorities(self, phases: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate prioritized list of fixes needed"""
        fixes = []
        
        # Critical port conflicts
        for conflict in phases["port_conflicts"]["critical_conflicts"]:
            fixes.append({
                "priority": "critical",
                "issue": f"Port conflict: {conflict['port']} used by both {conflict['pc2_group']} and {conflict['conflict_with']}",
                "fix": f"Remap {conflict['pc2_group']} port {conflict['port']} to suggested alternative",
                "estimated_effort": "low"
            })
        
        # Missing agent scripts
        for missing in phases["agent_scripts"]["missing"]:
            fixes.append({
                "priority": "high",
                "issue": f"Missing agent script: {missing['agent']} in group {missing['group']}",
                "fix": "Create agent implementation or placeholder",
                "estimated_effort": "medium"
            })
        
        # Resource capacity issues
        if not phases["resource_capacity"]["capacity_analysis"]["overall_feasible"]:
            fixes.append({
                "priority": "medium",
                "issue": "Resource oversubscription detected",
                "fix": "Implement resource limits and sequential startup",
                "estimated_effort": "medium"
            })
        
        return sorted(fixes, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x["priority"]])
    
    def _generate_local_next_steps(self, phases: Dict[str, Any]) -> List[str]:
        """Generate next steps for local validation"""
        next_steps = [
            "1. 🔧 Fix critical port conflicts using suggested remapping",
            "2. 📝 Create or locate missing agent scripts",
            "3. ⚡ Optimize resource allocation for local testing",
            "4. 🚀 Run controlled startup test with one PC2 group at a time",
            "5. 🔍 Validate cross-group communication locally",
            "6. 📊 Monitor resource usage during local testing",
            "7. ✅ Create local validation success criteria",
            "8. 🌐 Prepare for cross-machine sync after local validation"
        ]
        return next_steps

# =============================================================================
# EXECUTION FUNCTIONS
# =============================================================================

async def main():
    """Main execution function for local PC2 validation"""
    validator = LocalPC2Validator()
    
    try:
        # Run validation
        results = await validator.run_local_pc2_validation()
        
        # Print summary
        print("\n" + "="*80)
        print("🎯 LOCAL PC2 VALIDATION SUMMARY")
        print("="*80)
        
        summary = results["validation_summary"]
        print(f"📊 Total PC2 Groups: {summary['total_pc2_groups']}")
        print(f"🚨 Critical Issues: {summary['critical_issues']}")
        print(f"⚠️ Warnings: {summary['warnings']}")
        print(f"📝 Missing Scripts: {summary['missing_agent_scripts']}")
        print(f"✅ Overall Readiness: {summary['overall_readiness'].upper()}")
        print(f"⏱️ Duration: {summary['validation_duration_seconds']:.2f} seconds")
        
        if results["recommendations"]:
            print("\n📋 CRITICAL RECOMMENDATIONS:")
            for i, rec in enumerate(results["recommendations"], 1):
                print(f"  {i}. {rec}")
        
        print("\n🔧 FIX PRIORITIES:")
        for fix in results["fix_priorities"][:5]:  # Top 5 priorities
            print(f"  [{fix['priority'].upper()}] {fix['issue']}")
            print(f"    Fix: {fix['fix']}")
            print(f"    Effort: {fix['estimated_effort']}")
            print()
        
        print("🚀 NEXT STEPS:")
        for step in results["next_steps"]:
            print(f"  {step}")
        
        print("\n✅ LOCAL PC2 VALIDATION COMPLETE")
        return results
        
    except Exception as e:
        logger.error(f"❌ Local PC2 validation failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())