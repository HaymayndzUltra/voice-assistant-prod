#!/usr/bin/env python3
"""
Migration Performance and Reliability Analysis
Phase 1 Week 4 Day 4 - Task 4H
Comprehensive analysis of high-risk migrations and system performance.
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

class MigrationPerformanceAnalyzer:
    """Analyze performance and reliability of high-risk migrations"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.analysis_results = {
            "migration_summary": {},
            "performance_metrics": {},
            "reliability_assessment": {},
            "system_health": {},
            "recommendations": {}
        }
        
    def analyze_migration_sequence(self):
        """Analyze the complete high-risk migration sequence"""
        print("🔍 ANALYZING MIGRATION SEQUENCE")
        print("=" * 60)
        
        migrations = [
            {
                "agent": "ModelManagerAgent",
                "day": "Day 3",
                "report_file": "PHASE_1_WEEK_4_DAY_3_MMA_MIGRATION_EXECUTION_REPORT.json",
                "risk_score": 35,
                "complexity": "CRITICAL"
            },
            {
                "agent": "tutoring_agent", 
                "day": "Day 4",
                "report_file": "PHASE_1_WEEK_4_DAY_4_SECOND_MIGRATION_REPORT.json",
                "risk_score": 28,
                "complexity": "HIGH"
            }
        ]
        
        successful_migrations = 0
        total_risk_score = 0
        migration_details = []
        
        for migration in migrations:
            report_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / migration["report_file"]
            
            if report_file.exists():
                try:
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)
                    
                    # Extract success status
                    if "migration_execution" in report_data:
                        success = report_data["migration_execution"]["success"]
                        rollback = report_data["migration_execution"]["rollback_triggered"]
                    elif "second_migration_execution" in report_data:
                        success = report_data["second_migration_execution"]["success"]
                        rollback = report_data["second_migration_execution"]["rollback_triggered"]
                    else:
                        success = False
                        rollback = True
                    
                    if success and not rollback:
                        successful_migrations += 1
                        total_risk_score += migration["risk_score"]
                    
                    migration_details.append({
                        "agent": migration["agent"],
                        "day": migration["day"],
                        "success": success,
                        "rollback": rollback,
                        "risk_score": migration["risk_score"],
                        "complexity": migration["complexity"]
                    })
                    
                    status = "✅ SUCCESS" if success and not rollback else "❌ FAILED"
                    print(f"{migration['agent']}: {status} (Risk: {migration['risk_score']}, {migration['complexity']})")
                    
                except Exception as e:
                    print(f"⚠️ Error reading {migration['agent']} report: {e}")
                    migration_details.append({
                        "agent": migration["agent"],
                        "day": migration["day"],
                        "success": False,
                        "rollback": True,
                        "risk_score": migration["risk_score"],
                        "complexity": migration["complexity"]
                    })
            else:
                print(f"⚠️ Report not found for {migration['agent']}")
        
        success_rate = (successful_migrations / len(migrations)) * 100
        
        self.analysis_results["migration_summary"] = {
            "total_migrations": len(migrations),
            "successful_migrations": successful_migrations,
            "success_rate_percent": success_rate,
            "total_risk_score_migrated": total_risk_score,
            "migration_details": migration_details
        }
        
        print(f"\n📊 Migration Sequence Summary:")
        print(f"  Successful migrations: {successful_migrations}/{len(migrations)}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Total risk score migrated: {total_risk_score}")
        
        return success_rate >= 80
    
    def assess_system_performance(self):
        """Assess current system performance metrics"""
        print("\n📈 ASSESSING SYSTEM PERFORMANCE")
        print("-" * 60)
        
        performance_metrics = {
            "gpu_performance": {},
            "system_resources": {},
            "migration_integrity": {},
            "response_times": {}
        }
        
        # GPU Performance
        try:
            result = subprocess.run([
                "nvidia-smi", 
                "--query-gpu=name,memory.used,memory.total,temperature.gpu,utilization.gpu,power.draw", 
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                name, memory_used, memory_total, temp, util, power = result.stdout.strip().split(', ')
                memory_percent = (int(memory_used) / int(memory_total)) * 100
                
                performance_metrics["gpu_performance"] = {
                    "name": name,
                    "memory_usage_percent": round(memory_percent, 1),
                    "temperature_celsius": int(temp),
                    "utilization_percent": int(util),
                    "power_watts": float(power) if power != 'N/A' else 0,
                    "status": "excellent" if memory_percent < 50 and int(temp) < 70 else "good" if memory_percent < 85 and int(temp) < 85 else "concerning"
                }
                
                print(f"✅ GPU: {name} - {memory_percent:.1f}% memory, {temp}°C")
                
        except Exception as e:
            print(f"⚠️ GPU performance check failed: {e}")
            performance_metrics["gpu_performance"] = {"status": "unknown", "error": str(e)}
        
        # System Resources
        try:
            # System load
            with open('/proc/loadavg', 'r') as f:
                load_avg = float(f.read().split()[0])
            
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
                mem_available = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1])
                mem_usage_percent = ((mem_total - mem_available) / mem_total) * 100
            
            # Disk usage
            statvfs = os.statvfs(str(self.project_root))
            disk_usage_percent = ((statvfs.f_blocks - statvfs.f_bavail) / statvfs.f_blocks) * 100
            
            performance_metrics["system_resources"] = {
                "load_average": round(load_avg, 2),
                "memory_usage_percent": round(mem_usage_percent, 1),
                "disk_usage_percent": round(disk_usage_percent, 1),
                "status": "excellent" if load_avg < 2 and mem_usage_percent < 70 else "good" if load_avg < 5 and mem_usage_percent < 90 else "concerning"
            }
            
            print(f"✅ System: Load {load_avg:.2f}, Memory {mem_usage_percent:.1f}%, Disk {disk_usage_percent:.1f}%")
            
        except Exception as e:
            print(f"⚠️ System resources check failed: {e}")
            performance_metrics["system_resources"] = {"status": "unknown", "error": str(e)}
        
        # Migration Integrity
        migration_files = [
            ("ModelManagerAgent", "main_pc_code/agents/model_manager_agent.py", "MODELMANAGERAGENT MIGRATION APPLIED"),
            ("tutoring_agent", "pc2_code/agents/core_agents/tutoring_agent.py", "TUTORING_AGENT MIGRATION APPLIED")
        ]
        
        integrity_results = {}
        for agent_name, file_path, marker in migration_files:
            try:
                full_path = self.project_root / file_path
                if full_path.exists():
                    with open(full_path, 'r') as f:
                        content = f.read()
                    
                    has_marker = marker in content
                    file_size = full_path.stat().st_size / 1024
                    
                    integrity_results[agent_name] = {
                        "migration_marker_present": has_marker,
                        "file_size_kb": round(file_size, 1),
                        "status": "intact" if has_marker else "missing_marker"
                    }
                    
                    status = "✅" if has_marker else "❌"
                    print(f"{status} {agent_name}: Migration marker {'present' if has_marker else 'missing'}")
                else:
                    integrity_results[agent_name] = {"status": "file_missing"}
                    print(f"❌ {agent_name}: File missing")
                    
            except Exception as e:
                integrity_results[agent_name] = {"status": "error", "error": str(e)}
                print(f"⚠️ {agent_name}: Check failed - {e}")
        
        performance_metrics["migration_integrity"] = integrity_results
        
        self.analysis_results["performance_metrics"] = performance_metrics
        
        return performance_metrics
    
    def evaluate_system_reliability(self):
        """Evaluate overall system reliability"""
        print("\n🛡️ EVALUATING SYSTEM RELIABILITY")
        print("-" * 60)
        
        reliability_factors = {
            "migration_stability": 0,
            "system_health": 0,
            "backup_integrity": 0,
            "monitoring_coverage": 0,
            "rollback_capability": 0
        }
        
        # Migration Stability (40% weight)
        successful_migrations = self.analysis_results["migration_summary"]["successful_migrations"]
        total_migrations = self.analysis_results["migration_summary"]["total_migrations"]
        if total_migrations > 0:
            reliability_factors["migration_stability"] = (successful_migrations / total_migrations) * 40
        
        # System Health (25% weight)
        gpu_status = self.analysis_results["performance_metrics"]["gpu_performance"].get("status", "unknown")
        system_status = self.analysis_results["performance_metrics"]["system_resources"].get("status", "unknown")
        
        health_score = 0
        if gpu_status == "excellent": health_score += 15
        elif gpu_status == "good": health_score += 10
        elif gpu_status == "concerning": health_score += 5
        
        if system_status == "excellent": health_score += 10
        elif system_status == "good": health_score += 7
        elif system_status == "concerning": health_score += 3
        
        reliability_factors["system_health"] = health_score
        
        # Backup Integrity (15% weight)
        backup_dirs = [
            "backups/week4_mma_migration",
            "backups/week4_second_migration"
        ]
        
        backup_score = 0
        for backup_dir in backup_dirs:
            backup_path = self.project_root / backup_dir
            if backup_path.exists() and (backup_path / "backup_manifest.json").exists():
                backup_score += 7.5
        
        reliability_factors["backup_integrity"] = backup_score
        
        # Monitoring Coverage (10% weight)
        monitoring_active = False
        try:
            result = subprocess.run(["pgrep", "-f", "start_24h_observation_monitoring.py"], 
                                  capture_output=True, text=True)
            monitoring_active = result.returncode == 0
        except:
            pass
        
        reliability_factors["monitoring_coverage"] = 10 if monitoring_active else 5
        
        # Rollback Capability (10% weight)
        rollback_scripts = [
            "scripts/rollback_mma_migration.py",
            "scripts/execute_second_high_risk_migration.py"  # Contains rollback logic
        ]
        
        rollback_score = 0
        for script in rollback_scripts:
            script_path = self.project_root / script
            if script_path.exists():
                rollback_score += 5
        
        reliability_factors["rollback_capability"] = rollback_score
        
        # Calculate overall reliability score
        total_reliability = sum(reliability_factors.values())
        
        self.analysis_results["reliability_assessment"] = {
            "reliability_factors": reliability_factors,
            "total_score": round(total_reliability, 1),
            "grade": "excellent" if total_reliability >= 90 else "good" if total_reliability >= 75 else "concerning" if total_reliability >= 60 else "poor"
        }
        
        print(f"📊 Reliability Factors:")
        for factor, score in reliability_factors.items():
            print(f"  {factor}: {score:.1f}")
        
        print(f"\n🎯 Overall Reliability Score: {total_reliability:.1f}/100")
        print(f"📈 Reliability Grade: {self.analysis_results['reliability_assessment']['grade'].upper()}")
        
        return total_reliability >= 75
    
    def generate_recommendations(self):
        """Generate recommendations based on analysis"""
        print("\n💡 GENERATING RECOMMENDATIONS")
        print("-" * 60)
        
        recommendations = {
            "immediate_actions": [],
            "phase_completion_readiness": {},
            "next_phase_preparation": [],
            "risk_mitigation": []
        }
        
        # Immediate Actions
        migration_success_rate = self.analysis_results["migration_summary"]["success_rate_percent"]
        reliability_score = self.analysis_results["reliability_assessment"]["total_score"]
        
        if migration_success_rate == 100:
            recommendations["immediate_actions"].append("✅ High-risk migration sequence complete - proceed to Phase 1 validation")
        else:
            recommendations["immediate_actions"].append("⚠️ Review failed migrations before Phase 1 completion")
        
        if reliability_score >= 90:
            recommendations["immediate_actions"].append("✅ System reliability excellent - ready for production validation")
        elif reliability_score >= 75:
            recommendations["immediate_actions"].append("⚠️ System reliability good - minor improvements recommended")
        else:
            recommendations["immediate_actions"].append("❌ System reliability concerning - address issues before proceeding")
        
        # Phase Completion Readiness
        phase_ready = migration_success_rate >= 80 and reliability_score >= 75
        
        recommendations["phase_completion_readiness"] = {
            "ready_for_completion": phase_ready,
            "success_criteria_met": migration_success_rate >= 80,
            "reliability_criteria_met": reliability_score >= 75,
            "recommendation": "PROCEED" if phase_ready else "DEFER"
        }
        
        # Next Phase Preparation
        if phase_ready:
            recommendations["next_phase_preparation"] = [
                "Document Phase 1 lessons learned and methodology improvements",
                "Prepare Phase 2 strategy based on migration success patterns",
                "Generate Go/No-Go decision framework for Phase 2",
                "Create Phase 2 risk assessment and mitigation strategies"
            ]
        else:
            recommendations["next_phase_preparation"] = [
                "Address identified reliability concerns",
                "Complete outstanding migration validations",
                "Extend observation periods for unstable migrations",
                "Reassess Phase 1 completion criteria"
            ]
        
        # Risk Mitigation
        gpu_status = self.analysis_results["performance_metrics"]["gpu_performance"].get("status", "unknown")
        if gpu_status == "concerning":
            recommendations["risk_mitigation"].append("Monitor GPU temperature and memory usage closely")
        
        system_status = self.analysis_results["performance_metrics"]["system_resources"].get("status", "unknown")
        if system_status == "concerning":
            recommendations["risk_mitigation"].append("Address high system load or memory usage")
        
        self.analysis_results["recommendations"] = recommendations
        
        print("📋 Key Recommendations:")
        for action in recommendations["immediate_actions"]:
            print(f"  {action}")
        
        print(f"\n🎯 Phase Completion: {recommendations['phase_completion_readiness']['recommendation']}")
        
        return recommendations
    
    def save_analysis_report(self):
        """Save comprehensive analysis report"""
        self.analysis_results["analysis_metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "analysis_day": "Phase 1 Week 4 Day 4",
            "analysis_scope": "High-risk migration performance and reliability",
            "total_agents_analyzed": 2
        }
        
        report_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_DAY_4_PERFORMANCE_ANALYSIS_REPORT.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2)
        
        print(f"\n📋 Analysis report saved: {report_file}")
        return report_file
    
    def run_complete_analysis(self):
        """Run complete performance and reliability analysis"""
        print("\n" + "="*80)
        print("📊 MIGRATION PERFORMANCE & RELIABILITY ANALYSIS")
        print("📅 Phase 1 Week 4 Day 4 - Task 4H")
        print("🎯 Comprehensive evaluation of high-risk migrations")
        print("="*80)
        
        # Step 1: Analyze migration sequence
        migration_success = self.analyze_migration_sequence()
        
        # Step 2: Assess system performance
        performance_metrics = self.assess_system_performance()
        
        # Step 3: Evaluate system reliability
        reliability_success = self.evaluate_system_reliability()
        
        # Step 4: Generate recommendations
        recommendations = self.generate_recommendations()
        
        # Step 5: Save comprehensive report
        report_file = self.save_analysis_report()
        
        print("\n" + "="*80)
        print("📊 ANALYSIS SUMMARY")
        print("="*80)
        
        migration_rate = self.analysis_results["migration_summary"]["success_rate_percent"]
        reliability_score = self.analysis_results["reliability_assessment"]["total_score"]
        phase_ready = recommendations["phase_completion_readiness"]["ready_for_completion"]
        
        print(f"🎯 Migration Success Rate: {migration_rate:.1f}%")
        print(f"🛡️ System Reliability Score: {reliability_score:.1f}/100")
        print(f"✅ Phase 1 Completion Ready: {phase_ready}")
        print(f"📋 Recommendation: {recommendations['phase_completion_readiness']['recommendation']}")
        print("="*80)
        
        return {
            "migration_success": migration_success,
            "reliability_success": reliability_success,
            "phase_completion_ready": phase_ready,
            "analysis_report": report_file
        }

def main():
    analyzer = MigrationPerformanceAnalyzer()
    results = analyzer.run_complete_analysis()
    
    print(f"\n🚀 Analysis Results:")
    print(f"  🎯 Migration success: {results['migration_success']}")
    print(f"  🛡️ Reliability success: {results['reliability_success']}")
    print(f"  ✅ Phase completion ready: {results['phase_completion_ready']}")
    print(f"  📋 Analysis report: {results['analysis_report']}")

if __name__ == "__main__":
    main() 