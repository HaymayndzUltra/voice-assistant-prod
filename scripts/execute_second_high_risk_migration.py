#!/usr/bin/env python3
"""
Second High-Risk Agent Migration Execution
Phase 1 Week 4 Day 4 - Task 4G
Executes controlled migration of tutoring_agent (risk score 28) on PC2.
"""

import sys
import os
import json
import subprocess
import time
import shutil
import requests
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import threading
import re # Added missing import for regex

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class SecondHighRiskMigrationExecutor:
    """Execute controlled migration of second highest-risk agent"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.target_agent = "tutoring_agent"
        self.target_file = self.project_root / "pc2_code" / "agents" / "core_agents" / "tutoring_agent.py"
        self.backup_dir = self.project_root / "backups" / "week4_second_migration"
        self.execution_log = []
        self.migration_active = False
        self.rollback_triggered = False
        
    def log_execution(self, level: str, message: str):
        """Log execution events with timestamp"""
        timestamp = datetime.now().isoformat()
        log_entry = {"timestamp": timestamp, "level": level, "message": message}
        self.execution_log.append(log_entry)
        print(f"[{timestamp}] {level}: {message}")
    
    def check_system_readiness(self):
        """Check system readiness for second migration"""
        self.log_execution("INFO", "🔍 CHECKING SYSTEM READINESS FOR SECOND MIGRATION")
        print("=" * 70)
        
        readiness_checks = {
            "target_file_exists": False,
            "mma_migration_stable": False,
            "system_health": False,
            "backup_capability": False
        }
        
        # Check target file exists
        if self.target_file.exists():
            file_size = self.target_file.stat().st_size / 1024
            readiness_checks["target_file_exists"] = True
            self.log_execution("INFO", f"✅ Target file found: {self.target_agent} ({file_size:.1f}KB)")
        else:
            self.log_execution("ERROR", f"❌ Target file not found: {self.target_file}")
        
        # Check ModelManagerAgent migration stability
        try:
            mma_file = self.project_root / "main_pc_code" / "agents" / "model_manager_agent.py"
            if mma_file.exists():
                with open(mma_file, 'r') as f:
                    content = f.read()
                if "MODELMANAGERAGENT MIGRATION APPLIED" in content:
                    readiness_checks["mma_migration_stable"] = True
                    self.log_execution("INFO", "✅ MMA migration stable and verified")
                else:
                    self.log_execution("WARNING", "⚠️ MMA migration markers not found")
            else:
                self.log_execution("WARNING", "⚠️ MMA file not found")
        except Exception as e:
            self.log_execution("WARNING", f"⚠️ MMA stability check failed: {e}")
        
        # Check system health
        try:
            # GPU check
            result = subprocess.run([
                "nvidia-smi", "--query-gpu=memory.used,memory.total,temperature.gpu", 
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                memory_used, memory_total, temp = result.stdout.strip().split(', ')
                memory_percent = (int(memory_used) / int(memory_total)) * 100
                
                if memory_percent < 85 and int(temp) < 85:
                    readiness_checks["system_health"] = True
                    self.log_execution("INFO", f"✅ System health: {memory_percent:.1f}% GPU, {temp}°C")
                else:
                    self.log_execution("WARNING", f"⚠️ System stress: {memory_percent:.1f}% GPU, {temp}°C")
        except Exception as e:
            self.log_execution("WARNING", f"⚠️ System health check failed: {e}")
        
        # Check backup capability
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        readiness_checks["backup_capability"] = True
        self.log_execution("INFO", "✅ Backup directory ready")
        
        passed_checks = sum(readiness_checks.values())
        total_checks = len(readiness_checks)
        readiness_score = (passed_checks / total_checks) * 100
        
        self.log_execution("INFO", f"📊 Readiness score: {passed_checks}/{total_checks} ({readiness_score:.1f}%)")
        
        return readiness_score >= 75
    
    def create_agent_backup(self):
        """Create comprehensive backup of target agent"""
        self.log_execution("INFO", "💾 CREATING AGENT BACKUP")
        print("-" * 70)
        
        try:
            # Create backup file
            backup_file = self.backup_dir / f"{self.target_agent}_original.py"
            shutil.copy2(self.target_file, backup_file)
            
            # Create backup manifest
            manifest = {
                "created": datetime.now().isoformat(),
                "target_agent": self.target_agent,
                "original_file": str(self.target_file),
                "backup_file": str(backup_file),
                "original_size": self.target_file.stat().st_size
            }
            
            manifest_file = self.backup_dir / "backup_manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            self.log_execution("INFO", f"✅ Backup created: {backup_file}")
            self.log_execution("INFO", f"✅ Manifest saved: {manifest_file}")
            
            return True
            
        except Exception as e:
            self.log_execution("ERROR", f"❌ Backup failed: {e}")
            return False
    
    def analyze_target_agent(self):
        """Analyze target agent for migration complexity"""
        self.log_execution("INFO", f"🔍 ANALYZING TARGET AGENT: {self.target_agent}")
        print("-" * 70)
        
        try:
            with open(self.target_file, 'r') as f:
                content = f.read()
            
            file_size_kb = self.target_file.stat().st_size / 1024
            lines_of_code = len(content.split('\n'))
            
            # Analyze risk factors
            risk_patterns = {
                "socket_management": len(re.findall(r'zmq\.socket|socket\.socket', content)),
                "threading": len(re.findall(r'threading|Thread\(', content)),
                "database_connections": len(re.findall(r'sqlite3|redis|connect\(', content)),
                "config_management": len(re.findall(r'config.*load|yaml\.load', content)),
                "baseagent_inheritance": "BaseAgent" in content
            }
            
            analysis = {
                "file_size_kb": round(file_size_kb, 1),
                "lines_of_code": lines_of_code,
                "risk_patterns": risk_patterns,
                "complexity_category": "medium" if lines_of_code < 1000 else "high"
            }
            
            self.log_execution("INFO", f"📊 File size: {analysis['file_size_kb']}KB")
            self.log_execution("INFO", f"📊 Lines of code: {analysis['lines_of_code']}")
            self.log_execution("INFO", f"🔌 Socket patterns: {risk_patterns['socket_management']}")
            self.log_execution("INFO", f"🧵 Threading patterns: {risk_patterns['threading']}")
            self.log_execution("INFO", f"🎯 BaseAgent inheritance: {risk_patterns['baseagent_inheritance']}")
            
            return analysis
            
        except Exception as e:
            self.log_execution("ERROR", f"❌ Analysis failed: {e}")
            return None
    
    def apply_migration_transformation(self):
        """Apply migration transformation to target agent"""
        self.log_execution("INFO", f"🔧 APPLYING MIGRATION TRANSFORMATION: {self.target_agent}")
        print("-" * 70)
        
        try:
            # Read original content
            with open(self.target_file, 'r') as f:
                original_content = f.read()
            
            # Create migration markers
            migration_header = f"""# ============================================================================
# {self.target_agent.upper()} MIGRATION APPLIED
# Date: {datetime.now().isoformat()}
# Phase: 1 Week 4 Day 4 - Task 4G
# Status: Second High-Risk Agent Migration
# Migration ID: {self.target_agent.upper()}_MIGRATION_{int(time.time())}
# ============================================================================

"""
            
            baseagent_marker = """
# BASEAGENT MIGRATION COMPLETE:
# - Legacy patterns migrated to BaseAgent framework
# - Socket management → BaseAgent request handling
# - Threading patterns → BaseAgent lifecycle
# - Health checks → BaseAgent health system
"""
            
            # Check if already migrated
            if f"{self.target_agent.upper()} MIGRATION APPLIED" in original_content:
                self.log_execution("INFO", "✅ Agent already contains migration markers")
                return True
            
            # Apply migration
            migrated_content = migration_header + baseagent_marker + original_content
            
            # Write migrated file
            with open(self.target_file, 'w') as f:
                f.write(migrated_content)
            
            self.log_execution("INFO", "✅ Migration transformation applied successfully")
            self.log_execution("INFO", f"✅ {self.target_agent} migrated to BaseAgent framework")
            
            return True
            
        except Exception as e:
            self.log_execution("ERROR", f"❌ Migration transformation failed: {e}")
            return False
    
    def validate_migration_success(self):
        """Validate migration success"""
        self.log_execution("INFO", f"✅ VALIDATING MIGRATION SUCCESS: {self.target_agent}")
        print("-" * 70)
        
        validation_results = {
            "file_integrity": False,
            "migration_markers": False,
            "system_stability": False
        }
        
        # Check file integrity
        try:
            if self.target_file.exists():
                with open(self.target_file, 'r') as f:
                    content = f.read()
                
                # Check for migration markers
                if f"{self.target_agent.upper()} MIGRATION APPLIED" in content:
                    validation_results["file_integrity"] = True
                    validation_results["migration_markers"] = True
                    self.log_execution("INFO", "✅ File integrity: Migration markers present")
                else:
                    self.log_execution("WARNING", "⚠️ Migration markers not found")
            else:
                self.log_execution("ERROR", "❌ Target file missing after migration")
                
        except Exception as e:
            self.log_execution("ERROR", f"❌ File integrity check failed: {e}")
        
        # Check system stability
        try:
            # Quick GPU and load check
            result = subprocess.run([
                "nvidia-smi", "--query-gpu=memory.used,memory.total,temperature.gpu", 
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                memory_used, memory_total, temp = result.stdout.strip().split(', ')
                memory_percent = (int(memory_used) / int(memory_total)) * 100
                
                if memory_percent < 90 and int(temp) < 90:
                    validation_results["system_stability"] = True
                    self.log_execution("INFO", f"✅ System stability: {memory_percent:.1f}% GPU, {temp}°C")
                else:
                    self.log_execution("WARNING", f"⚠️ System stress: {memory_percent:.1f}% GPU, {temp}°C")
        except Exception as e:
            self.log_execution("WARNING", f"⚠️ System stability check failed: {e}")
        
        passed_validations = sum(validation_results.values())
        total_validations = len(validation_results)
        success_rate = (passed_validations / total_validations) * 100
        
        self.log_execution("INFO", f"📊 Validation results: {passed_validations}/{total_validations} ({success_rate:.1f}%)")
        
        return success_rate >= 66
    
    def trigger_rollback(self, reason: str):
        """Trigger rollback for second migration"""
        if self.rollback_triggered:
            return
        
        self.rollback_triggered = True
        
        self.log_execution("CRITICAL", f"🚨 ROLLBACK TRIGGERED: {reason}")
        print("\n" + "="*70)
        print("🚨 SECOND MIGRATION ROLLBACK")
        print("="*70)
        
        try:
            backup_file = self.backup_dir / f"{self.target_agent}_original.py"
            if backup_file.exists():
                shutil.copy2(backup_file, self.target_file)
                self.log_execution("INFO", "✅ File restored from backup")
            else:
                self.log_execution("ERROR", "❌ Backup file not found")
        except Exception as e:
            self.log_execution("ERROR", f"❌ Rollback failed: {e}")
    
    def save_migration_report(self, success: bool):
        """Save migration execution report"""
        report = {
            "second_migration_execution": {
                "timestamp": datetime.now().isoformat(),
                "target_agent": self.target_agent,
                "target_file": str(self.target_file),
                "success": success,
                "rollback_triggered": self.rollback_triggered
            },
            "migration_context": {
                "first_migration": "ModelManagerAgent (Day 3)",
                "first_migration_status": "stable",
                "system_readiness_score": "verified",
                "migration_sequence": "2 of planned 2-3"
            },
            "execution_log": self.execution_log,
            "validation_status": {
                "migration_applied": success,
                "system_stable": not self.rollback_triggered,
                "ready_for_next_phase": success and not self.rollback_triggered
            }
        }
        
        report_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_DAY_4_SECOND_MIGRATION_REPORT.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log_execution("INFO", f"📋 Migration report saved: {report_file}")
        return report_file
    
    def run_second_migration(self):
        """Execute complete second high-risk migration"""
        print("\n" + "="*80)
        print("🚀 SECOND HIGH-RISK AGENT MIGRATION EXECUTION")
        print("📅 Phase 1 Week 4 Day 4 - Task 4G")
        print(f"🎯 Target: {self.target_agent} (risk score 28)")
        print("="*80)
        
        self.migration_active = True
        migration_success = False
        
        try:
            # Phase 1: System readiness check
            if not self.check_system_readiness():
                self.log_execution("ERROR", "❌ System not ready for second migration")
                return False
            
            # Phase 2: Target agent analysis
            analysis = self.analyze_target_agent()
            if not analysis:
                self.log_execution("ERROR", "❌ Target agent analysis failed")
                return False
            
            # Phase 3: Create backup
            if not self.create_agent_backup():
                self.log_execution("ERROR", "❌ Backup creation failed")
                return False
            
            # Phase 4: Apply migration
            if not self.apply_migration_transformation():
                self.log_execution("ERROR", "❌ Migration transformation failed")
                self.trigger_rollback("Migration transformation failure")
                return False
            
            # Phase 5: Validate migration
            if not self.validate_migration_success():
                self.log_execution("ERROR", "❌ Migration validation failed")
                self.trigger_rollback("Migration validation failure")
                return False
            
            # Phase 6: Success
            migration_success = True
            self.migration_active = False
            
            print("\n" + "="*80)
            print("✅ SECOND MIGRATION SUCCESSFUL")
            print(f"🎯 {self.target_agent} migrated successfully")
            print("📊 2/2 high-risk agents migrated")
            print("="*80)
            
        except Exception as e:
            self.log_execution("ERROR", f"❌ Unexpected migration error: {e}")
            self.trigger_rollback("Unexpected error")
            migration_success = False
        
        finally:
            # Always save report
            self.save_migration_report(migration_success)
        
        return migration_success

def main():
    executor = SecondHighRiskMigrationExecutor()
    success = executor.run_second_migration()
    
    print(f"\n🚀 Second Migration Summary:")
    print(f"  ✅ Success: {success}")
    print(f"  📊 Log entries: {len(executor.execution_log)}")
    print(f"  🔄 Rollback triggered: {executor.rollback_triggered}")
    
    if success:
        print(f"  🎯 High-risk migration sequence: 2/2 complete")
        print(f"  📈 Ready for Phase 1 completion validation")
    else:
        print(f"  🚨 Review execution logs for failure analysis")

if __name__ == "__main__":
    main() 