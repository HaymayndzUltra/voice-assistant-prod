#!/usr/bin/env python3
"""
ModelManagerAgent Observation Status Check
Phase 1 Week 4 Day 4 - Stability Assessment
Checks 24-hour observation progress and migration stability for second agent decision.
"""

import sys
import os
import json
import subprocess
import time
import requests
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class MMAObservationStatusChecker:
    """Check ModelManagerAgent observation status and stability"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.migration_start_time = None
        self.observation_status = {
            "monitoring_active": False,
            "elapsed_hours": 0,
            "checkpoints_completed": 0,
            "stability_score": 0,
            "ready_for_second_migration": False
        }
        
    def check_monitoring_process(self):
        """Check if observation monitoring process is still running"""
        print("🔍 CHECKING OBSERVATION MONITORING PROCESS")
        print("=" * 50)
        
        try:
            result = subprocess.run([
                "pgrep", "-f", "start_24h_observation_monitoring.py"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                pid = result.stdout.strip()
                self.observation_status["monitoring_active"] = True
                print(f"✅ Observation monitoring running (PID: {pid})")
                
                # Check process uptime
                ps_result = subprocess.run([
                    "ps", "-o", "etime", "-p", pid
                ], capture_output=True, text=True)
                
                if ps_result.returncode == 0:
                    uptime = ps_result.stdout.split('\n')[1].strip()
                    print(f"⏰ Process uptime: {uptime}")
                
                return True
            else:
                self.observation_status["monitoring_active"] = False
                print("❌ Observation monitoring process not found")
                return False
                
        except Exception as e:
            print(f"⚠️ Error checking monitoring process: {e}")
            return False
    
    def analyze_migration_execution_report(self):
        """Analyze the migration execution report for baseline metrics"""
        print("\n📊 ANALYZING MIGRATION EXECUTION BASELINE")
        print("-" * 50)
        
        try:
            execution_report_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_DAY_3_MMA_MIGRATION_EXECUTION_REPORT.json"
            
            if not execution_report_file.exists():
                print("⚠️ Migration execution report not found")
                return False
            
            with open(execution_report_file, 'r') as f:
                execution_report = json.load(f)
            
            # Extract migration start time
            migration_time = execution_report["migration_execution"]["timestamp"]
            self.migration_start_time = datetime.fromisoformat(migration_time)
            
            # Calculate elapsed time
            current_time = datetime.now()
            elapsed_time = current_time - self.migration_start_time
            elapsed_hours = elapsed_time.total_seconds() / 3600
            self.observation_status["elapsed_hours"] = round(elapsed_hours, 2)
            
            # Check migration success
            migration_success = execution_report["migration_execution"]["success"]
            rollback_triggered = execution_report["migration_execution"]["rollback_triggered"]
            
            print(f"✅ Migration executed: {migration_time}")
            print(f"⏰ Elapsed time: {elapsed_hours:.2f} hours")
            print(f"🎯 Migration success: {migration_success}")
            print(f"🔄 Rollback triggered: {rollback_triggered}")
            
            if not migration_success or rollback_triggered:
                print("❌ Migration baseline failed - not ready for second migration")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error analyzing migration report: {e}")
            return False
    
    def check_checkpoint_reports(self):
        """Check for checkpoint validation reports"""
        print("\n🎯 CHECKING CHECKPOINT VALIDATION REPORTS")
        print("-" * 50)
        
        expected_checkpoints = [6, 12, 18, 24]
        completed_checkpoints = 0
        checkpoint_results = {}
        
        for checkpoint_hour in expected_checkpoints:
            checkpoint_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / f"PHASE_1_WEEK_4_DAY_3_CHECKPOINT_{checkpoint_hour}H_REPORT.json"
            
            if checkpoint_file.exists():
                try:
                    with open(checkpoint_file, 'r') as f:
                        checkpoint_data = json.load(f)
                    
                    completed_checkpoints += 1
                    checkpoint_results[checkpoint_hour] = checkpoint_data
                    
                    # Extract key metrics
                    metrics = checkpoint_data.get("metrics", {})
                    success_rate = metrics.get("success_rate_percent", 0)
                    
                    print(f"✅ Checkpoint {checkpoint_hour}h: {success_rate}% success rate")
                    
                except Exception as e:
                    print(f"⚠️ Error reading checkpoint {checkpoint_hour}h: {e}")
            else:
                if self.observation_status["elapsed_hours"] >= checkpoint_hour:
                    print(f"❌ Missing checkpoint {checkpoint_hour}h report (expected)")
                else:
                    print(f"⏳ Checkpoint {checkpoint_hour}h pending (not due yet)")
        
        self.observation_status["checkpoints_completed"] = completed_checkpoints
        print(f"\n📊 Checkpoints completed: {completed_checkpoints}/{len(expected_checkpoints)}")
        
        return checkpoint_results
    
    def assess_current_system_health(self):
        """Assess current system health status"""
        print("\n🏥 ASSESSING CURRENT SYSTEM HEALTH")
        print("-" * 50)
        
        health_score = 0
        max_score = 5
        
        # Check GPU health
        try:
            result = subprocess.run([
                "nvidia-smi", "--query-gpu=memory.used,memory.total,temperature.gpu", 
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                memory_used, memory_total, temp = result.stdout.strip().split(', ')
                memory_percent = (int(memory_used) / int(memory_total)) * 100
                
                if memory_percent < 85 and int(temp) < 85:
                    health_score += 1
                    print(f"✅ GPU health: {memory_percent:.1f}% memory, {temp}°C")
                else:
                    print(f"⚠️ GPU stress: {memory_percent:.1f}% memory, {temp}°C")
            else:
                print("⚠️ GPU health check failed")
        except Exception as e:
            print(f"⚠️ GPU check error: {e}")
        
        # Check system load
        try:
            with open('/proc/loadavg', 'r') as f:
                load_avg = float(f.read().split()[0])
            
            if load_avg < 5.0:
                health_score += 1
                print(f"✅ System load: {load_avg:.2f}")
            else:
                print(f"⚠️ High system load: {load_avg:.2f}")
        except Exception as e:
            print(f"⚠️ Load check error: {e}")
        
        # Check memory usage
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
                mem_available = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1])
                mem_usage_percent = ((mem_total - mem_available) / mem_total) * 100
            
            if mem_usage_percent < 90:
                health_score += 1
                print(f"✅ Memory usage: {mem_usage_percent:.1f}%")
            else:
                print(f"⚠️ High memory usage: {mem_usage_percent:.1f}%")
        except Exception as e:
            print(f"⚠️ Memory check error: {e}")
        
        # Check migration file integrity
        try:
            mma_file = self.project_root / "main_pc_code" / "agents" / "model_manager_agent.py"
            
            if mma_file.exists():
                with open(mma_file, 'r') as f:
                    content = f.read()
                
                if "MODELMANAGERAGENT MIGRATION APPLIED" in content:
                    health_score += 1
                    print("✅ Migration integrity: Markers present")
                else:
                    print("❌ Migration integrity: Markers missing")
            else:
                print("❌ Migration file missing")
        except Exception as e:
            print(f"⚠️ Migration integrity check error: {e}")
        
        # Check backup integrity
        try:
            backup_manifest = self.project_root / "backups" / "week4_mma_migration" / "backup_manifest.json"
            
            if backup_manifest.exists():
                health_score += 1
                print("✅ Backup integrity: Manifest available")
            else:
                print("❌ Backup integrity: Manifest missing")
        except Exception as e:
            print(f"⚠️ Backup check error: {e}")
        
        health_percentage = (health_score / max_score) * 100
        self.observation_status["stability_score"] = health_percentage
        
        print(f"\n📊 Current health score: {health_score}/{max_score} ({health_percentage:.1f}%)")
        
        return health_percentage >= 80
    
    def evaluate_second_migration_readiness(self):
        """Evaluate if system is ready for second high-risk agent migration"""
        print("\n🎯 EVALUATING SECOND MIGRATION READINESS")
        print("=" * 50)
        
        readiness_criteria = {
            "monitoring_active": self.observation_status["monitoring_active"],
            "minimum_observation_time": self.observation_status["elapsed_hours"] >= 6,  # At least 6 hours
            "system_health": self.observation_status["stability_score"] >= 80,
            "no_critical_issues": True  # Will be determined from checkpoints
        }
        
        # Check if any checkpoints failed
        checkpoint_files = list(self.project_root.glob("implementation_roadmap/PHASE1_ACTION_PLAN/PHASE_1_WEEK_4_DAY_3_CHECKPOINT_*H_REPORT.json"))
        
        for checkpoint_file in checkpoint_files:
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                
                metrics = checkpoint_data.get("metrics", {})
                success_rate = metrics.get("success_rate_percent", 0)
                
                if success_rate < 80:
                    readiness_criteria["no_critical_issues"] = False
                    print(f"❌ Checkpoint failure detected: {success_rate}% success rate")
                    break
                    
            except Exception as e:
                print(f"⚠️ Error checking checkpoint: {e}")
        
        # Evaluate overall readiness
        passed_criteria = sum(readiness_criteria.values())
        total_criteria = len(readiness_criteria)
        readiness_score = (passed_criteria / total_criteria) * 100
        
        print(f"\n📊 Readiness Criteria Assessment:")
        for criterion, passed in readiness_criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {criterion}: {status}")
        
        print(f"\n🎯 Overall readiness: {passed_criteria}/{total_criteria} ({readiness_score:.1f}%)")
        
        self.observation_status["ready_for_second_migration"] = readiness_score >= 75
        
        if self.observation_status["ready_for_second_migration"]:
            print("\n✅ SYSTEM READY FOR SECOND HIGH-RISK MIGRATION")
        else:
            print("\n❌ SYSTEM NOT READY - Continue observation period")
        
        return self.observation_status["ready_for_second_migration"]
    
    def save_status_report(self):
        """Save comprehensive observation status report"""
        report = {
            "observation_status_check": {
                "timestamp": datetime.now().isoformat(),
                "migration_start_time": self.migration_start_time.isoformat() if self.migration_start_time else None,
                "elapsed_hours": self.observation_status["elapsed_hours"],
                "assessment_day": "Day 4"
            },
            "current_status": self.observation_status,
            "readiness_assessment": {
                "ready_for_second_migration": self.observation_status["ready_for_second_migration"],
                "stability_score": self.observation_status["stability_score"],
                "monitoring_active": self.observation_status["monitoring_active"],
                "checkpoints_completed": self.observation_status["checkpoints_completed"]
            },
            "recommendations": {
                "proceed_with_second_migration": self.observation_status["ready_for_second_migration"],
                "continue_observation": True,
                "additional_monitoring_hours": 24 - self.observation_status["elapsed_hours"] if self.observation_status["elapsed_hours"] < 24 else 0
            }
        }
        
        status_report_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_DAY_4_MMA_OBSERVATION_STATUS.json"
        
        with open(status_report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📋 Status report saved: {status_report_file}")
        return status_report_file
    
    def run_complete_status_check(self):
        """Run complete observation status check and readiness assessment"""
        print("\n" + "="*70)
        print("🔍 MODELMANAGERAGENT OBSERVATION STATUS CHECK")
        print("📅 Phase 1 Week 4 Day 4 - Migration Stability Assessment")
        print("="*70)
        
        # Step 1: Check monitoring process
        monitoring_active = self.check_monitoring_process()
        
        # Step 2: Analyze migration baseline
        migration_valid = self.analyze_migration_execution_report()
        
        # Step 3: Check checkpoint reports
        checkpoint_results = self.check_checkpoint_reports()
        
        # Step 4: Assess current system health
        system_healthy = self.assess_current_system_health()
        
        # Step 5: Evaluate second migration readiness
        ready_for_second = self.evaluate_second_migration_readiness()
        
        # Step 6: Save status report
        status_report = self.save_status_report()
        
        print("\n" + "="*70)
        print("📊 OBSERVATION STATUS SUMMARY")
        print("="*70)
        print(f"⏰ Elapsed time: {self.observation_status['elapsed_hours']:.2f} hours")
        print(f"📊 Stability score: {self.observation_status['stability_score']:.1f}%")
        print(f"🎯 Checkpoints completed: {self.observation_status['checkpoints_completed']}")
        print(f"🔄 Monitoring active: {self.observation_status['monitoring_active']}")
        print(f"✅ Ready for second migration: {self.observation_status['ready_for_second_migration']}")
        print("="*70)
        
        return {
            "ready_for_second_migration": ready_for_second,
            "stability_score": self.observation_status["stability_score"],
            "elapsed_hours": self.observation_status["elapsed_hours"],
            "status_report": status_report
        }

def main():
    checker = MMAObservationStatusChecker()
    results = checker.run_complete_status_check()
    
    print(f"\n🚀 Status Check Results:")
    print(f"  🎯 Ready for second migration: {results['ready_for_second_migration']}")
    print(f"  📊 Stability score: {results['stability_score']:.1f}%")
    print(f"  ⏰ Observation time: {results['elapsed_hours']:.2f} hours")
    print(f"  📋 Status report: {results['status_report']}")

if __name__ == "__main__":
    main() 