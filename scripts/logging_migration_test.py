#!/usr/bin/env python3
"""
Logging Infrastructure Migration Test Script
Phase 0 Day 4 - Task 4C & 4D

This script helps manage the gradual deployment of rotating file handlers
to low-risk test agents and monitors disk usage during the transition.
"""

import sys
import os
import time
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager


class LoggingMigrationTester:
    """Manages logging infrastructure migration testing."""
    
    def __init__(self):
        self.project_root = Path(PathManager.get_project_root())
        self.logs_dir = self.project_root / "logs"
        self.test_results = {}
        
        # Low-risk test agents selected for gradual deployment
        self.test_agents = [
            {
                "name": "MemoryOrchestratorService",
                "script_path": "pc2_code/agents/memory_orchestrator_service.py",
                "system": "PC2",
                "risk_level": "low",
                "critical": False,
                "estimated_log_volume": "medium"
            },
            {
                "name": "SystemDigitalTwin", 
                "script_path": "main_pc_code/agents/system_digital_twin.py",
                "system": "MainPC",
                "risk_level": "medium",  # Higher traffic but well-tested
                "critical": True,
                "estimated_log_volume": "high"
            },
            {
                "name": "MoodTrackerAgent",
                "script_path": "main_pc_code/agents/mood_tracker_agent.py", 
                "system": "MainPC",
                "risk_level": "low",
                "critical": False,
                "estimated_log_volume": "low"
            },
            {
                "name": "UnifiedWebAgent",
                "script_path": "pc2_code/agents/unified_web_agent.py",
                "system": "PC2", 
                "risk_level": "low",
                "critical": False,
                "estimated_log_volume": "medium"
            },
            {
                "name": "FaceRecognitionAgent",
                "script_path": "main_pc_code/agents/face_recognition_agent.py",
                "system": "MainPC",
                "risk_level": "low", 
                "critical": False,
                "estimated_log_volume": "low"
            }
        ]
        
        print(f"🧪 Logging Migration Tester initialized")
        print(f"📁 Project root: {self.project_root}")
        print(f"📊 Logs directory: {self.logs_dir}")
        print(f"🤖 Test agents: {len(self.test_agents)}")
    
    def check_agent_exists(self, agent: Dict) -> bool:
        """Check if agent script file exists."""
        script_path = self.project_root / agent["script_path"]
        exists = script_path.exists()
        
        if not exists:
            print(f"⚠️  Agent script not found: {script_path}")
        
        return exists
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Get current disk usage statistics."""
        try:
            # Get logs directory usage
            logs_usage = shutil.disk_usage(self.logs_dir)
            
            # Get total disk usage
            total_usage = shutil.disk_usage(self.project_root)
            
            return {
                "logs_dir_free_gb": logs_usage.free / (1024**3),
                "logs_dir_total_gb": logs_usage.total / (1024**3),
                "logs_dir_used_gb": (logs_usage.total - logs_usage.free) / (1024**3),
                "total_free_gb": total_usage.free / (1024**3),
                "total_used_gb": (total_usage.total - total_usage.free) / (1024**3),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ Error getting disk usage: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_log_file_sizes(self) -> Dict[str, Dict]:
        """Get current log file sizes for all agents."""
        log_files = {}
        
        if not self.logs_dir.exists():
            return log_files
        
        for log_file in self.logs_dir.glob("*.log"):
            try:
                stat = log_file.stat()
                log_files[log_file.name] = {
                    "size_bytes": stat.st_size,
                    "size_mb": stat.st_size / (1024**2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "has_rotation_files": len(list(self.logs_dir.glob(f"{log_file.stem}.log.*"))) > 0
                }
            except Exception as e:
                log_files[log_file.name] = {"error": str(e)}
        
        return log_files
    
    def check_baseagent_inheritance(self, agent: Dict) -> bool:
        """Check if agent inherits from BaseAgent (supports rotating logger)."""
        script_path = self.project_root / agent["script_path"]
        
        if not script_path.exists():
            return False
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for BaseAgent import and inheritance
            has_import = "from common.core.base_agent import BaseAgent" in content
            has_inheritance = "class" in content and "BaseAgent" in content and ":" in content
            
            return has_import and has_inheritance
            
        except Exception as e:
            print(f"❌ Error checking {script_path}: {e}")
            return False
    
    def validate_test_agents(self) -> Dict[str, bool]:
        """Validate all test agents are ready for migration."""
        results = {}
        
        print(f"\n🔍 VALIDATING TEST AGENTS")
        print(f"=" * 50)
        
        for agent in self.test_agents:
            agent_name = agent["name"]
            print(f"\n📝 Testing: {agent_name}")
            
            # Check script exists
            exists = self.check_agent_exists(agent)
            print(f"  📄 Script exists: {'✅' if exists else '❌'}")
            
            # Check BaseAgent inheritance
            if exists:
                inherits = self.check_baseagent_inheritance(agent)
                print(f"  🏗️  BaseAgent inheritance: {'✅' if inherits else '❌'}")
            else:
                inherits = False
            
            # Overall readiness
            ready = exists and inherits
            print(f"  🎯 Migration ready: {'✅' if ready else '❌'}")
            
            results[agent_name] = {
                "script_exists": exists,
                "inherits_baseagent": inherits,
                "migration_ready": ready,
                "agent_config": agent
            }
        
        return results
    
    def generate_migration_plan(self, validation_results: Dict) -> List[Dict]:
        """Generate migration plan based on validation results."""
        migration_plan = []
        
        # Sort agents by risk level and readiness
        ready_agents = [
            (name, data) for name, data in validation_results.items() 
            if data["migration_ready"]
        ]
        
        # Sort by risk level (low risk first)
        risk_order = {"low": 1, "medium": 2, "high": 3}
        ready_agents.sort(key=lambda x: (
            risk_order.get(x[1]["agent_config"]["risk_level"], 4),
            x[1]["agent_config"]["critical"]  # Non-critical first
        ))
        
        for i, (agent_name, data) in enumerate(ready_agents):
            agent_config = data["agent_config"]
            migration_plan.append({
                "order": i + 1,
                "agent_name": agent_name,
                "system": agent_config["system"],
                "risk_level": agent_config["risk_level"],
                "critical": agent_config["critical"],
                "estimated_log_volume": agent_config["estimated_log_volume"],
                "script_path": agent_config["script_path"],
                "migration_ready": True
            })
        
        # Add non-ready agents at the end
        not_ready_agents = [
            (name, data) for name, data in validation_results.items() 
            if not data["migration_ready"]
        ]
        
        for agent_name, data in not_ready_agents:
            agent_config = data["agent_config"]
            migration_plan.append({
                "order": len(ready_agents) + 1,
                "agent_name": agent_name,
                "system": agent_config["system"],
                "risk_level": agent_config["risk_level"],
                "critical": agent_config["critical"],
                "estimated_log_volume": agent_config["estimated_log_volume"],
                "script_path": agent_config["script_path"],
                "migration_ready": False,
                "blocking_issues": [
                    "Script not found" if not data["script_exists"] else None,
                    "No BaseAgent inheritance" if not data["inherits_baseagent"] else None
                ]
            })
        
        return migration_plan
    
    def monitor_disk_usage(self, duration_minutes: int = 10, interval_seconds: int = 30) -> List[Dict]:
        """Monitor disk usage over time."""
        print(f"\n📊 MONITORING DISK USAGE")
        print(f"⏱️  Duration: {duration_minutes} minutes")
        print(f"🔄 Interval: {interval_seconds} seconds")
        
        measurements = []
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            usage = self.get_disk_usage()
            log_sizes = self.get_log_file_sizes()
            
            measurement = {
                "timestamp": datetime.now().isoformat(),
                "disk_usage": usage,
                "log_files": log_sizes,
                "total_log_files": len(log_sizes),
                "total_log_size_mb": sum(
                    lf.get("size_mb", 0) for lf in log_sizes.values() 
                    if isinstance(lf, dict) and "size_mb" in lf
                )
            }
            
            measurements.append(measurement)
            
            # Print current status
            if "error" not in usage:
                print(f"📈 {datetime.now().strftime('%H:%M:%S')} - "
                      f"Free: {usage['total_free_gb']:.1f}GB, "
                      f"Logs: {measurement['total_log_size_mb']:.1f}MB "
                      f"({measurement['total_log_files']} files)")
            
            time.sleep(interval_seconds)
        
        return measurements
    
    def test_log_rotation_trigger(self, test_size_mb: float = 11.0) -> Dict:
        """Test log rotation by creating a large test log file."""
        test_log_path = self.logs_dir / "rotation_test.log"
        
        print(f"\n🧪 TESTING LOG ROTATION")
        print(f"📄 Test file: {test_log_path}")
        print(f"📏 Target size: {test_size_mb}MB")
        
        try:
            # Create test logger with rotation
            from common.utils.logger_util import get_rotating_json_logger
            
            test_logger = get_rotating_json_logger(
                name="rotation_test",
                log_file=str(test_log_path),
                max_bytes=10*1024*1024,  # 10MB limit
                backup_count=3,
                console_output=False
            )
            
            # Generate log entries until rotation triggers
            start_time = datetime.now()
            entry_count = 0
            rotation_triggered = False
            
            # Large message to speed up file growth
            large_message = "x" * 1000  # 1KB per message
            
            while test_log_path.stat().st_size < test_size_mb * 1024 * 1024:
                test_logger.info(f"Test log entry {entry_count}: {large_message}", extra={
                    "entry_number": entry_count,
                    "test_data": {"large_field": large_message}
                })
                entry_count += 1
                
                # Check for rotation files
                if not rotation_triggered:
                    rotation_files = list(self.logs_dir.glob("rotation_test.log.*"))
                    if rotation_files:
                        rotation_triggered = True
                        print(f"✅ Rotation triggered after {entry_count} entries")
                
                # Safety limit
                if entry_count > 50000:
                    print(f"⚠️  Safety limit reached at {entry_count} entries")
                    break
            
            end_time = datetime.now()
            
            # Check final state
            final_size = test_log_path.stat().st_size if test_log_path.exists() else 0
            rotation_files = list(self.logs_dir.glob("rotation_test.log.*"))
            
            result = {
                "success": rotation_triggered,
                "duration_seconds": (end_time - start_time).total_seconds(),
                "entries_generated": entry_count,
                "final_size_mb": final_size / (1024**2),
                "rotation_files_created": len(rotation_files),
                "rotation_files": [f.name for f in rotation_files],
                "rotation_triggered": rotation_triggered
            }
            
            print(f"📊 Test results: {json.dumps(result, indent=2)}")
            
            # Cleanup test files
            try:
                if test_log_path.exists():
                    test_log_path.unlink()
                for rf in rotation_files:
                    rf.unlink()
                print(f"🧹 Cleaned up test files")
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
            
            return result
            
        except Exception as e:
            print(f"❌ Log rotation test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_report(self, validation_results: Dict, migration_plan: List[Dict], 
                       disk_monitoring: List[Dict], rotation_test: Dict) -> Dict:
        """Generate comprehensive migration test report."""
        report = {
            "test_timestamp": datetime.now().isoformat(),
            "phase": "Phase 0 Day 4 - Logging Infrastructure Upgrade",
            "summary": {
                "total_test_agents": len(self.test_agents),
                "migration_ready": sum(1 for r in validation_results.values() if r["migration_ready"]),
                "disk_monitoring_duration": len(disk_monitoring),
                "rotation_test_successful": rotation_test.get("success", False)
            },
            "validation_results": validation_results,
            "migration_plan": migration_plan,
            "disk_monitoring": disk_monitoring,
            "rotation_test": rotation_test,
            "recommendations": []
        }
        
        # Generate recommendations
        ready_count = report["summary"]["migration_ready"]
        if ready_count == len(self.test_agents):
            report["recommendations"].append("✅ All test agents ready for migration")
        elif ready_count > 0:
            report["recommendations"].append(f"🔄 {ready_count}/{len(self.test_agents)} agents ready - proceed with ready agents first")
        else:
            report["recommendations"].append("❌ No agents ready for migration - address blocking issues first")
        
        if rotation_test.get("success"):
            report["recommendations"].append("✅ Log rotation working correctly")
        else:
            report["recommendations"].append("❌ Log rotation needs investigation")
        
        # Disk usage recommendations
        if disk_monitoring:
            latest_usage = disk_monitoring[-1]["disk_usage"]
            if "total_free_gb" in latest_usage and latest_usage["total_free_gb"] < 5:
                report["recommendations"].append("⚠️  Low disk space - monitor closely during migration")
        
        return report


def main():
    """Main testing function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Logging Infrastructure Migration Test",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate agents without testing'
    )
    
    parser.add_argument(
        '--monitor-duration',
        type=int,
        default=5,
        help='Disk monitoring duration in minutes (default: 5)'
    )
    
    parser.add_argument(
        '--skip-rotation-test',
        action='store_true',
        help='Skip log rotation test'
    )
    
    parser.add_argument(
        '--output-file',
        help='Save report to JSON file'
    )
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = LoggingMigrationTester()
    
    # Validate test agents
    print(f"\n🚀 STARTING LOGGING MIGRATION TEST")
    validation_results = tester.validate_test_agents()
    
    # Generate migration plan
    migration_plan = tester.generate_migration_plan(validation_results)
    
    print(f"\n📋 MIGRATION PLAN")
    print(f"=" * 50)
    for item in migration_plan:
        status = "✅ READY" if item["migration_ready"] else "❌ BLOCKED"
        print(f"{item['order']}. {item['agent_name']} ({item['system']}) - {status}")
        if not item["migration_ready"] and "blocking_issues" in item:
            for issue in item["blocking_issues"]:
                if issue:
                    print(f"   ⚠️  {issue}")
    
    if args.validate_only:
        print(f"\n✅ Validation complete - use full test for migration readiness")
        return
    
    # Monitor disk usage
    disk_monitoring = tester.monitor_disk_usage(duration_minutes=args.monitor_duration)
    
    # Test log rotation
    if not args.skip_rotation_test:
        rotation_test = tester.test_log_rotation_trigger()
    else:
        rotation_test = {"skipped": True}
    
    # Generate report
    report = tester.generate_report(validation_results, migration_plan, disk_monitoring, rotation_test)
    
    print(f"\n📊 FINAL REPORT")
    print(f"=" * 50)
    for rec in report["recommendations"]:
        print(f"  {rec}")
    
    # Save report if requested
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report saved to: {args.output_file}")
    
    print(f"\n🎯 MIGRATION TEST COMPLETE")


if __name__ == "__main__":
    main() 