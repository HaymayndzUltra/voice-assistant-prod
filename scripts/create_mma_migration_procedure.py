#!/usr/bin/env python3
"""
ModelManagerAgent Specialized Migration Procedure
Phase 1 Week 4 Day 2 - Task 4B
Creates specialized migration procedure based on Day 1 analysis findings.
"""

import sys
import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class MMAMigrationProcedureCreator:
    """Create specialized migration procedure for ModelManagerAgent"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.mma_file = self.project_root / "main_pc_code" / "agents" / "model_manager_agent.py"
        self.analysis_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_DAY_1_MMA_ANALYSIS.json"
        self.backup_dir = self.project_root / "backups" / "week4_mma_migration"
        self.migration_procedure = {
            "metadata": {
                "created": datetime.now().isoformat(),
                "target_agent": "ModelManagerAgent",
                "risk_level": "CRITICAL",
                "approach": "STAGED_MIGRATION"
            },
            "phases": [],
            "rollback_procedures": [],
            "validation_steps": [],
            "monitoring_requirements": []
        }
    
    def load_analysis_results(self):
        """Load Day 1 analysis results"""
        print("📊 LOADING DAY 1 ANALYSIS RESULTS")
        print("=" * 50)
        
        with open(self.analysis_file, 'r') as f:
            self.analysis = json.load(f)
        
        print(f"✅ Loaded analysis for {self.analysis['file_info']['file_size_kb']:.1f}KB file")
        print(f"🔌 Socket patterns: {len(self.analysis['socket_patterns'])}")
        print(f"🧵 Threading patterns: {len(self.analysis['threading_patterns'])}")
        print(f"🚨 Risk level: {self.analysis['migration_risk_assessment']['risk_level']}")
    
    def create_backup_strategy(self):
        """Create comprehensive backup strategy"""
        print("\n💾 CREATING BACKUP STRATEGY")
        print("-" * 50)
        
        backup_strategy = {
            "phase": "PRE_MIGRATION",
            "name": "Comprehensive Backup Strategy",
            "critical_importance": "MAXIMUM - 227KB critical component",
            "backup_targets": [
                {
                    "target": "main_pc_code/agents/model_manager_agent.py",
                    "backup_path": "backups/week4_mma_migration/model_manager_agent_original.py",
                    "description": "Original ModelManagerAgent source",
                    "validation": "File size and MD5 checksum verification"
                },
                {
                    "target": "main_pc_code/config/startup_config.yaml",
                    "backup_path": "backups/week4_mma_migration/startup_config_original.yaml",
                    "description": "Original startup configuration",
                    "validation": "YAML syntax and agent registration verification"
                },
                {
                    "target": "main_pc_code/config/llm_config.yaml",
                    "backup_path": "backups/week4_mma_migration/llm_config_original.yaml",
                    "description": "Model configuration dependencies",
                    "validation": "Model registry completeness check"
                }
            ],
            "parallel_environment": {
                "enabled": True,
                "approach": "Create testing copy with different port",
                "test_port": 5571,  # Original uses 5570
                "validation_endpoint": "http://localhost:5571/health",
                "gpu_isolation": "Use CUDA_VISIBLE_DEVICES=1 for testing if available"
            },
            "automated_scripts": [
                "scripts/backup_mma_environment.py",
                "scripts/restore_mma_environment.py",
                "scripts/validate_mma_backup.py"
            ]
        }
        
        self.migration_procedure["phases"].append(backup_strategy)
        print(f"✅ Backup strategy created for {len(backup_strategy['backup_targets'])} targets")
        print(f"🔄 Parallel testing environment on port {backup_strategy['parallel_environment']['test_port']}")
    
    def create_socket_migration_plan(self):
        """Create socket management migration plan"""
        print("\n🔌 CREATING SOCKET MIGRATION PLAN")
        print("-" * 50)
        
        socket_migration = {
            "phase": "INFRASTRUCTURE_MIGRATION",
            "name": "Socket Management Migration",
            "priority": "HIGH - 53 socket patterns identified",
            "approach": "Gradual replacement with BaseAgent patterns",
            "socket_categories": {
                "zmq_rep_sockets": {
                    "count": self._count_socket_type("zmq.REP"),
                    "migration_strategy": "Migrate to BaseAgent request handling",
                    "baseagent_equivalent": "self.handle_request() method",
                    "validation": "Request-response pattern testing"
                },
                "zmq_pub_sockets": {
                    "count": self._count_socket_type("zmq.PUB"),
                    "migration_strategy": "Migrate to BaseAgent status publishing",
                    "baseagent_equivalent": "self.publish_status() method",
                    "validation": "Status broadcast verification"
                },
                "raw_sockets": {
                    "count": self._count_socket_type("socket.socket"),
                    "migration_strategy": "Replace with BaseAgent health checks",
                    "baseagent_equivalent": "BaseAgent health system",
                    "validation": "Health check endpoint verification"
                }
            },
            "migration_steps": [
                {
                    "step": 1,
                    "action": "Identify all ZMQ socket creation patterns",
                    "validation": "Catalog all socket.bind() and socket.connect() calls"
                },
                {
                    "step": 2,
                    "action": "Replace REP sockets with BaseAgent request handling",
                    "validation": "Test model loading/unloading via BaseAgent patterns"
                },
                {
                    "step": 3,
                    "action": "Replace PUB sockets with BaseAgent status system",
                    "validation": "Verify status publishing to ObservabilityHub"
                },
                {
                    "step": 4,
                    "action": "Migrate raw socket health checks to BaseAgent",
                    "validation": "Confirm _get_health_status() integration"
                }
            ],
            "rollback_triggers": [
                "Any socket connection failure",
                "Model request handling failure",
                "Status publishing failure",
                "Health check endpoint unavailable"
            ]
        }
        
        self.migration_procedure["phases"].append(socket_migration)
        print(f"✅ Socket migration plan created")
        print(f"🔍 Identified {len(socket_migration['socket_categories'])} socket categories")
    
    def create_threading_migration_plan(self):
        """Create threading migration plan"""
        print("\n🧵 CREATING THREADING MIGRATION PLAN")
        print("-" * 50)
        
        threading_migration = {
            "phase": "CONCURRENCY_MIGRATION",
            "name": "Threading Pattern Migration",
            "priority": "CRITICAL - 7 custom threads running",
            "approach": "Integrate with BaseAgent lifecycle",
            "thread_categories": {
                "memory_management": {
                    "current_pattern": "self._memory_management_loop",
                    "migration_target": "BaseAgent background task",
                    "critical_functions": ["check_idle_models", "vram_optimization"],
                    "validation": "VRAM usage monitoring, model unloading verification"
                },
                "health_monitoring": {
                    "current_pattern": "self._health_check_loop",
                    "migration_target": "BaseAgent health system",
                    "critical_functions": ["_check_model_health", "GPU status"],
                    "validation": "Health endpoint responsiveness, GPU state accuracy"
                },
                "request_handling": {
                    "current_pattern": "self._handle_model_requests_loop",
                    "migration_target": "BaseAgent request processing",
                    "critical_functions": ["load_model", "unload_model", "model_status"],
                    "validation": "Model loading performance, request queue processing"
                }
            },
            "migration_steps": [
                {
                    "step": 1,
                    "action": "Analyze thread dependencies and shared state",
                    "validation": "Map all threading.Lock() usage and shared variables"
                },
                {
                    "step": 2,
                    "action": "Migrate memory management to BaseAgent background tasks",
                    "validation": "Verify VRAM optimization continues functioning"
                },
                {
                    "step": 3,
                    "action": "Integrate health monitoring with BaseAgent health system",
                    "validation": "Confirm GPU status reporting via BaseAgent health"
                },
                {
                    "step": 4,
                    "action": "Migrate request handling to BaseAgent patterns",
                    "validation": "Test model loading/unloading performance"
                }
            ],
            "critical_validations": [
                "VRAM optimization performance (must maintain <20% degradation)",
                "Model loading time (must not increase >10%)",
                "GPU memory tracking accuracy",
                "Thread synchronization (no race conditions)",
                "Memory leak prevention (proper cleanup)"
            ]
        }
        
        self.migration_procedure["phases"].append(threading_migration)
        print(f"✅ Threading migration plan created")
        print(f"🎯 Identified {len(threading_migration['thread_categories'])} thread categories")
    
    def create_rollback_procedures(self):
        """Create comprehensive rollback procedures"""
        print("\n🔄 CREATING ROLLBACK PROCEDURES")
        print("-" * 50)
        
        rollback_procedures = [
            {
                "trigger": "GPU operation failure",
                "severity": "CRITICAL",
                "timeframe": "Immediate (< 2 minutes)",
                "procedure": [
                    "Stop ModelManagerAgent immediately",
                    "Restore original model_manager_agent.py",
                    "Restart with original configuration",
                    "Verify GPU memory state",
                    "Confirm model loading capability"
                ],
                "validation": "GPU operations return to normal, no VRAM leaks"
            },
            {
                "trigger": "Model loading/unloading failure",
                "severity": "HIGH",
                "timeframe": "Fast (< 5 minutes)",
                "procedure": [
                    "Attempt graceful model unloading",
                    "If unsuccessful, force restart ModelManagerAgent",
                    "Restore backup configuration",
                    "Clear GPU memory cache",
                    "Restart with known-good state"
                ],
                "validation": "All models load/unload successfully"
            },
            {
                "trigger": "Performance degradation >20%",
                "severity": "MEDIUM",
                "timeframe": "Planned (< 15 minutes)",
                "procedure": [
                    "Document performance metrics",
                    "Stop new model requests",
                    "Complete pending operations",
                    "Restore previous version",
                    "Verify performance restoration"
                ],
                "validation": "Performance returns to baseline levels"
            },
            {
                "trigger": "Cross-machine communication failure",
                "severity": "HIGH",
                "timeframe": "Fast (< 5 minutes)",
                "procedure": [
                    "Check network connectivity to PC2",
                    "Verify ObservabilityHub status",
                    "Restore original socket configuration",
                    "Re-establish cross-machine coordination",
                    "Validate PC2 agent communication"
                ],
                "validation": "PC2 agents respond normally, metrics flow restored"
            }
        ]
        
        self.migration_procedure["rollback_procedures"] = rollback_procedures
        print(f"✅ Created {len(rollback_procedures)} rollback procedures")
        print(f"⚡ Fastest rollback: {min([p['timeframe'] for p in rollback_procedures])}")
    
    def create_validation_framework(self):
        """Create comprehensive validation framework"""
        print("\n✅ CREATING VALIDATION FRAMEWORK")
        print("-" * 50)
        
        validation_steps = [
            {
                "category": "GPU Operations",
                "tests": [
                    "CUDA availability check",
                    "GPU memory allocation test",
                    "Model loading to GPU verification",
                    "VRAM optimization functionality",
                    "GPU memory cleanup verification"
                ],
                "success_criteria": "All GPU operations complete successfully, no memory leaks"
            },
            {
                "category": "Model Management",
                "tests": [
                    "Load model from registry",
                    "Unload model and free memory",
                    "Multiple model switching",
                    "Model performance benchmarking",
                    "Model status reporting accuracy"
                ],
                "success_criteria": "Model operations maintain <10% performance variance"
            },
            {
                "category": "BaseAgent Integration",
                "tests": [
                    "Health endpoint responsiveness",
                    "Request handling via BaseAgent",
                    "Status publishing to ObservabilityHub",
                    "Configuration loading via BaseAgent",
                    "Prometheus metrics exposure"
                ],
                "success_criteria": "All BaseAgent features functional, no regressions"
            },
            {
                "category": "Cross-Machine Coordination",
                "tests": [
                    "PC2 agent communication",
                    "Metrics synchronization",
                    "Status broadcasting",
                    "Error reporting to PC2 ErrorBus",
                    "Failover behavior testing"
                ],
                "success_criteria": "Cross-machine communication maintains current functionality"
            }
        ]
        
        self.migration_procedure["validation_steps"] = validation_steps
        print(f"✅ Created {len(validation_steps)} validation categories")
        print(f"🧪 Total tests: {sum(len(cat['tests']) for cat in validation_steps)}")
    
    def create_monitoring_requirements(self):
        """Create enhanced monitoring requirements"""
        print("\n📊 CREATING MONITORING REQUIREMENTS")
        print("-" * 50)
        
        monitoring_requirements = {
            "real_time_metrics": [
                {
                    "metric": "gpu_memory_usage",
                    "frequency": "5 seconds",
                    "alert_threshold": "> 90% VRAM usage",
                    "source": "ModelManagerAgent CUDA monitoring"
                },
                {
                    "metric": "model_loading_time",
                    "frequency": "Per operation",
                    "alert_threshold": "> 10% increase from baseline",
                    "source": "Model loading performance timer"
                },
                {
                    "metric": "thread_health_status",
                    "frequency": "10 seconds",
                    "alert_threshold": "Any thread failure or deadlock",
                    "source": "Thread monitoring system"
                },
                {
                    "metric": "socket_connection_status",
                    "frequency": "30 seconds",
                    "alert_threshold": "Connection failure or timeout",
                    "source": "Socket health monitoring"
                }
            ],
            "observability_hub_integration": {
                "enabled": True,
                "custom_metrics": [
                    "mma_gpu_memory_utilization",
                    "mma_model_operation_latency",
                    "mma_thread_status",
                    "mma_socket_health"
                ],
                "dashboard_updates": "Add ModelManagerAgent-specific panels"
            },
            "automated_alerts": [
                {
                    "condition": "GPU memory > 95%",
                    "action": "Trigger model unloading sequence",
                    "severity": "WARNING"
                },
                {
                    "condition": "Model loading failure",
                    "action": "Alert + investigate GPU state",
                    "severity": "ERROR"
                },
                {
                    "condition": "Thread deadlock detected",
                    "action": "Immediate rollback trigger",
                    "severity": "CRITICAL"
                }
            ]
        }
        
        self.migration_procedure["monitoring_requirements"] = monitoring_requirements
        print(f"✅ Created monitoring for {len(monitoring_requirements['real_time_metrics'])} metrics")
        print(f"🚨 {len(monitoring_requirements['automated_alerts'])} automated alerts configured")
    
    def _count_socket_type(self, socket_type: str) -> int:
        """Count specific socket types from analysis"""
        return len([p for p in self.analysis['socket_patterns'] if socket_type in p['pattern']])
    
    def save_migration_procedure(self):
        """Save the complete migration procedure"""
        procedure_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_MMA_MIGRATION_PROCEDURE.json"
        
        with open(procedure_file, 'w') as f:
            json.dump(self.migration_procedure, f, indent=2)
        
        print(f"\n📋 Migration procedure saved: {procedure_file}")
        return procedure_file
    
    def generate_migration_scripts(self):
        """Generate automated migration support scripts"""
        print("\n⚙️ GENERATING MIGRATION SUPPORT SCRIPTS")
        print("-" * 50)
        
        scripts_created = []
        
        # Backup script
        backup_script = self.project_root / "scripts" / "backup_mma_environment.py"
        backup_content = '''#!/usr/bin/env python3
"""
ModelManagerAgent Environment Backup Script
Automated backup for Week 4 migration
"""
import shutil
import os
from pathlib import Path
from datetime import datetime

def create_backup():
    project_root = Path(__file__).parent.parent
    backup_dir = project_root / "backups" / "week4_mma_migration"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup targets
    targets = [
        ("main_pc_code/agents/model_manager_agent.py", "model_manager_agent_original.py"),
        ("main_pc_code/config/startup_config.yaml", "startup_config_original.yaml"),
        ("main_pc_code/config/llm_config.yaml", "llm_config_original.yaml")
    ]
    
    print(f"🔄 Creating backup at {backup_dir}")
    for source, backup_name in targets:
        source_path = project_root / source
        backup_path = backup_dir / backup_name
        if source_path.exists():
            shutil.copy2(source_path, backup_path)
            print(f"✅ Backed up {source}")
        else:
            print(f"⚠️ Warning: {source} not found")
    
    # Create backup manifest
    manifest = {
        "created": datetime.now().isoformat(),
        "files": targets,
        "original_file_size": (project_root / "main_pc_code/agents/model_manager_agent.py").stat().st_size if (project_root / "main_pc_code/agents/model_manager_agent.py").exists() else 0
    }
    
    with open(backup_dir / "backup_manifest.json", 'w') as f:
        import json
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Backup complete with manifest")

if __name__ == "__main__":
    create_backup()
'''
        
        with open(backup_script, 'w') as f:
            f.write(backup_content)
        scripts_created.append(str(backup_script))
        
        # Rollback script
        rollback_script = self.project_root / "scripts" / "rollback_mma_migration.py"
        rollback_content = '''#!/usr/bin/env python3
"""
ModelManagerAgent Migration Rollback Script
Emergency rollback for Week 4 migration
"""
import shutil
import subprocess
import time
from pathlib import Path

def emergency_rollback():
    project_root = Path(__file__).parent.parent
    backup_dir = project_root / "backups" / "week4_mma_migration"
    
    print("🚨 EMERGENCY ROLLBACK INITIATED")
    
    # Stop ModelManagerAgent
    try:
        subprocess.run(["pkill", "-f", "model_manager_agent"], check=False)
        print("⏹️ ModelManagerAgent stopped")
        time.sleep(2)
    except:
        print("⚠️ Could not stop ModelManagerAgent via pkill")
    
    # Restore files
    if (backup_dir / "model_manager_agent_original.py").exists():
        shutil.copy2(
            backup_dir / "model_manager_agent_original.py",
            project_root / "main_pc_code/agents/model_manager_agent.py"
        )
        print("✅ ModelManagerAgent restored from backup")
    
    if (backup_dir / "startup_config_original.yaml").exists():
        shutil.copy2(
            backup_dir / "startup_config_original.yaml",
            project_root / "main_pc_code/config/startup_config.yaml"
        )
        print("✅ Startup config restored from backup")
    
    print("🔄 Manual restart required for ModelManagerAgent")
    print("✅ Rollback complete")

if __name__ == "__main__":
    emergency_rollback()
'''
        
        with open(rollback_script, 'w') as f:
            f.write(rollback_content)
        scripts_created.append(str(rollback_script))
        
        print(f"✅ Generated {len(scripts_created)} migration support scripts:")
        for script in scripts_created:
            print(f"  📜 {script}")
        
        return scripts_created
    
    def run_complete_procedure_creation(self):
        """Run complete migration procedure creation"""
        print("\n" + "="*80)
        print("🛠️ MODELMANAGERAGENT SPECIALIZED MIGRATION PROCEDURE CREATION")
        print("📅 Phase 1 Week 4 Day 2 - Task 4B")
        print("="*80)
        
        self.load_analysis_results()
        self.create_backup_strategy()
        self.create_socket_migration_plan()
        self.create_threading_migration_plan()
        self.create_rollback_procedures()
        self.create_validation_framework()
        self.create_monitoring_requirements()
        
        procedure_file = self.save_migration_procedure()
        support_scripts = self.generate_migration_scripts()
        
        print("\n" + "="*80)
        print("✅ SPECIALIZED MIGRATION PROCEDURE COMPLETE")
        print("🎯 Ready for Task 4C: Enhanced Monitoring Setup")
        print("="*80)
        
        return {
            "procedure_file": procedure_file,
            "support_scripts": support_scripts,
            "phases": len(self.migration_procedure["phases"]),
            "rollback_procedures": len(self.migration_procedure["rollback_procedures"]),
            "validation_categories": len(self.migration_procedure["validation_steps"])
        }

def main():
    creator = MMAMigrationProcedureCreator()
    results = creator.run_complete_procedure_creation()
    
    print(f"\n🚀 Migration Procedure Summary:")
    print(f"  📋 Procedure file: {results['procedure_file']}")
    print(f"  📜 Support scripts: {len(results['support_scripts'])}")
    print(f"  🔄 Migration phases: {results['phases']}")
    print(f"  ⚡ Rollback procedures: {results['rollback_procedures']}")
    print(f"  ✅ Validation categories: {results['validation_categories']}")

if __name__ == "__main__":
    main() 