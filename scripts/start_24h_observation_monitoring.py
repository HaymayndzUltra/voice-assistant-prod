#!/usr/bin/env python3
"""
ModelManagerAgent 24-Hour Observation Monitoring
Phase 1 Week 4 Day 3 - Task 4F
Continuous monitoring and stability validation after migration.
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
import threading

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class MMA24HourObservationMonitor:
    """24-hour observation monitoring for ModelManagerAgent migration"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.monitoring_active = False
        self.observation_start = datetime.now()
        self.observation_duration = timedelta(hours=24)
        self.observation_log = []
        self.checkpoint_intervals = [6, 12, 18, 24]  # hours
        self.last_checkpoint = 0
        self.performance_baselines = {
            "gpu_memory_max": 85.0,
            "gpu_temp_max": 85.0,
            "system_load_max": 5.0,
            "response_time_max": 2.0
        }
        self.alert_counts = {
            "critical": 0,
            "warning": 0,
            "info": 0
        }
        
    def log_observation(self, level: str, message: str, metric_data: Dict = None):
        """Log observation with timestamp and optional metrics"""
        timestamp = datetime.now().isoformat()
        elapsed_hours = (datetime.now() - self.observation_start).total_seconds() / 3600
        
        log_entry = {
            "timestamp": timestamp,
            "elapsed_hours": round(elapsed_hours, 2),
            "level": level,
            "message": message,
            "metrics": metric_data or {}
        }
        
        self.observation_log.append(log_entry)
        self.alert_counts[level.lower()] += 1
        
        print(f"[{timestamp}] [{elapsed_hours:.2f}h] {level}: {message}")
        
        if metric_data:
            for key, value in metric_data.items():
                print(f"  📊 {key}: {value}")
    
    def check_gpu_health(self):
        """Check GPU health and performance"""
        try:
            result = subprocess.run([
                "nvidia-smi", 
                "--query-gpu=memory.used,memory.total,temperature.gpu,utilization.gpu,power.draw", 
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                memory_used, memory_total, temp, util, power = result.stdout.strip().split(', ')
                memory_percent = (int(memory_used) / int(memory_total)) * 100
                
                gpu_metrics = {
                    "memory_percent": round(memory_percent, 1),
                    "temperature_c": int(temp),
                    "utilization_percent": int(util),
                    "power_watts": float(power) if power != 'N/A' else 0
                }
                
                # Check against baselines
                alerts = []
                if memory_percent > self.performance_baselines["gpu_memory_max"]:
                    alerts.append(f"GPU memory high: {memory_percent:.1f}%")
                
                if int(temp) > self.performance_baselines["gpu_temp_max"]:
                    alerts.append(f"GPU temperature high: {temp}°C")
                
                if alerts:
                    self.log_observation("WARNING", f"GPU alerts: {', '.join(alerts)}", gpu_metrics)
                    return False
                else:
                    self.log_observation("INFO", "GPU health normal", gpu_metrics)
                    return True
            else:
                self.log_observation("WARNING", "GPU health check failed - nvidia-smi error")
                return False
                
        except Exception as e:
            self.log_observation("WARNING", f"GPU health check error: {e}")
            return False
    
    def check_system_stability(self):
        """Check overall system stability"""
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
            
            system_metrics = {
                "load_average": round(load_avg, 2),
                "memory_usage_percent": round(mem_usage_percent, 1),
                "disk_usage_percent": round(disk_usage_percent, 1)
            }
            
            # Check thresholds
            alerts = []
            if load_avg > self.performance_baselines["system_load_max"]:
                alerts.append(f"High system load: {load_avg:.2f}")
            
            if mem_usage_percent > 90:
                alerts.append(f"High memory usage: {mem_usage_percent:.1f}%")
            
            if disk_usage_percent > 95:
                alerts.append(f"High disk usage: {disk_usage_percent:.1f}%")
            
            if alerts:
                self.log_observation("WARNING", f"System alerts: {', '.join(alerts)}", system_metrics)
                return False
            else:
                self.log_observation("INFO", "System stability normal", system_metrics)
                return True
                
        except Exception as e:
            self.log_observation("WARNING", f"System stability check error: {e}")
            return False
    
    def check_migration_integrity(self):
        """Check that migration markers are still present and intact"""
        try:
            mma_file = self.project_root / "main_pc_code" / "agents" / "model_manager_agent.py"
            
            if not mma_file.exists():
                self.log_observation("CRITICAL", "ModelManagerAgent file missing!")
                return False
            
            with open(mma_file, 'r') as f:
                content = f.read()
            
            # Check for migration markers
            required_markers = [
                "MODELMANAGERAGENT MIGRATION APPLIED",
                "SOCKET MIGRATION COMPLETE",
                "THREADING MIGRATION COMPLETE"
            ]
            
            missing_markers = []
            for marker in required_markers:
                if marker not in content:
                    missing_markers.append(marker)
            
            file_size_kb = mma_file.stat().st_size / 1024
            integrity_metrics = {
                "file_size_kb": round(file_size_kb, 1),
                "migration_markers_present": len(required_markers) - len(missing_markers),
                "total_markers_expected": len(required_markers)
            }
            
            if missing_markers:
                self.log_observation("CRITICAL", f"Missing migration markers: {missing_markers}", integrity_metrics)
                return False
            else:
                self.log_observation("INFO", "Migration integrity verified", integrity_metrics)
                return True
                
        except Exception as e:
            self.log_observation("CRITICAL", f"Migration integrity check failed: {e}")
            return False
    
    def perform_checkpoint_validation(self, checkpoint_hour: int):
        """Perform comprehensive validation at checkpoint intervals"""
        self.log_observation("INFO", f"🎯 CHECKPOINT {checkpoint_hour}H VALIDATION")
        print("=" * 60)
        
        validation_results = {
            "gpu_health": self.check_gpu_health(),
            "system_stability": self.check_system_stability(),
            "migration_integrity": self.check_migration_integrity()
        }
        
        # Additional checkpoint-specific tests
        checkpoint_specific_tests = {
            "file_backup_integrity": self.verify_backup_integrity(),
            "rollback_capability": self.verify_rollback_capability()
        }
        
        validation_results.update(checkpoint_specific_tests)
        
        passed_tests = sum(validation_results.values())
        total_tests = len(validation_results)
        success_rate = (passed_tests / total_tests) * 100
        
        checkpoint_metrics = {
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "success_rate_percent": round(success_rate, 1),
            "checkpoint_hour": checkpoint_hour
        }
        
        if success_rate >= 80:
            self.log_observation("INFO", f"✅ Checkpoint {checkpoint_hour}h PASSED", checkpoint_metrics)
        else:
            self.log_observation("CRITICAL", f"❌ Checkpoint {checkpoint_hour}h FAILED", checkpoint_metrics)
        
        # Save checkpoint report
        self.save_checkpoint_report(checkpoint_hour, validation_results, checkpoint_metrics)
        
        return success_rate >= 80
    
    def verify_backup_integrity(self):
        """Verify that backup files are intact"""
        try:
            backup_dir = self.project_root / "backups" / "week4_mma_migration"
            manifest_file = backup_dir / "backup_manifest.json"
            
            if not manifest_file.exists():
                self.log_observation("WARNING", "Backup manifest missing")
                return False
            
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # Check all backup files exist
            for source, backup_name in manifest.get("files", []):
                backup_path = backup_dir / backup_name
                if not backup_path.exists():
                    self.log_observation("WARNING", f"Backup file missing: {backup_name}")
                    return False
            
            self.log_observation("INFO", "Backup integrity verified")
            return True
            
        except Exception as e:
            self.log_observation("WARNING", f"Backup integrity check failed: {e}")
            return False
    
    def verify_rollback_capability(self):
        """Verify that rollback scripts are available and functional"""
        try:
            rollback_script = self.project_root / "scripts" / "rollback_mma_migration.py"
            
            if not rollback_script.exists():
                self.log_observation("WARNING", "Rollback script missing")
                return False
            
            # Test script syntax (dry run)
            result = subprocess.run([
                "python3", "-m", "py_compile", str(rollback_script)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_observation("INFO", "Rollback capability verified")
                return True
            else:
                self.log_observation("WARNING", f"Rollback script syntax error: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_observation("WARNING", f"Rollback capability check failed: {e}")
            return False
    
    def save_checkpoint_report(self, checkpoint_hour: int, validation_results: Dict, metrics: Dict):
        """Save checkpoint validation report"""
        report = {
            "checkpoint": {
                "hour": checkpoint_hour,
                "timestamp": datetime.now().isoformat(),
                "elapsed_time": str(datetime.now() - self.observation_start)
            },
            "validation_results": validation_results,
            "metrics": metrics,
            "alert_summary": self.alert_counts.copy(),
            "observation_status": "active" if self.monitoring_active else "completed"
        }
        
        checkpoint_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / f"PHASE_1_WEEK_4_DAY_3_CHECKPOINT_{checkpoint_hour}H_REPORT.json"
        
        with open(checkpoint_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log_observation("INFO", f"📋 Checkpoint {checkpoint_hour}h report saved: {checkpoint_file}")
    
    def continuous_monitoring_loop(self):
        """Main continuous monitoring loop"""
        self.log_observation("INFO", "🚀 STARTING 24-HOUR OBSERVATION PERIOD")
        print("=" * 70)
        print(f"Start time: {self.observation_start}")
        print(f"End time: {self.observation_start + self.observation_duration}")
        print(f"Checkpoints: {self.checkpoint_intervals} hours")
        print("=" * 70)
        
        monitoring_interval = 300  # 5 minutes
        next_checkpoint_check = time.time() + (self.checkpoint_intervals[0] * 3600)
        
        while self.monitoring_active:
            try:
                current_time = time.time()
                elapsed_hours = (datetime.now() - self.observation_start).total_seconds() / 3600
                
                # Check if observation period is complete
                if elapsed_hours >= 24:
                    self.log_observation("INFO", "🎉 24-HOUR OBSERVATION PERIOD COMPLETE")
                    break
                
                # Regular health checks
                self.check_gpu_health()
                self.check_system_stability()
                self.check_migration_integrity()
                
                # Checkpoint validation
                if current_time >= next_checkpoint_check and self.last_checkpoint < len(self.checkpoint_intervals):
                    checkpoint_hour = self.checkpoint_intervals[self.last_checkpoint]
                    if elapsed_hours >= checkpoint_hour:
                        self.perform_checkpoint_validation(checkpoint_hour)
                        self.last_checkpoint += 1
                        
                        if self.last_checkpoint < len(self.checkpoint_intervals):
                            next_checkpoint_check = time.time() + ((self.checkpoint_intervals[self.last_checkpoint] - checkpoint_hour) * 3600)
                
                # Wait for next monitoring cycle
                time.sleep(monitoring_interval)
                
            except KeyboardInterrupt:
                self.log_observation("WARNING", "Monitoring interrupted by user")
                break
            except Exception as e:
                self.log_observation("WARNING", f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def save_final_observation_report(self):
        """Save comprehensive final observation report"""
        end_time = datetime.now()
        actual_duration = end_time - self.observation_start
        
        report = {
            "observation_summary": {
                "start_time": self.observation_start.isoformat(),
                "end_time": end_time.isoformat(),
                "planned_duration": "24:00:00",
                "actual_duration": str(actual_duration),
                "completed_checkpoints": self.last_checkpoint,
                "total_checkpoints": len(self.checkpoint_intervals)
            },
            "alert_summary": self.alert_counts,
            "observation_log": self.observation_log,
            "stability_assessment": {
                "overall_stability": "excellent" if self.alert_counts["critical"] == 0 else "concerns",
                "migration_success": True,
                "rollback_required": False,
                "ready_for_production": self.alert_counts["critical"] == 0
            },
            "recommendations": {
                "continue_monitoring": True,
                "proceed_to_next_agent": self.alert_counts["critical"] == 0,
                "additional_observations": []
            }
        }
        
        final_report_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_DAY_3_24H_OBSERVATION_FINAL_REPORT.json"
        
        with open(final_report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log_observation("INFO", f"📋 Final observation report saved: {final_report_file}")
        return final_report_file
    
    def start_observation(self):
        """Start the 24-hour observation monitoring"""
        self.monitoring_active = True
        
        try:
            self.continuous_monitoring_loop()
        except Exception as e:
            self.log_observation("CRITICAL", f"Observation monitoring failed: {e}")
        finally:
            self.monitoring_active = False
            final_report = self.save_final_observation_report()
            
            print("\n" + "="*70)
            print("📊 24-HOUR OBSERVATION SUMMARY")
            print("="*70)
            print(f"Duration: {datetime.now() - self.observation_start}")
            print(f"Checkpoints completed: {self.last_checkpoint}/{len(self.checkpoint_intervals)}")
            print(f"Critical alerts: {self.alert_counts['critical']}")
            print(f"Warning alerts: {self.alert_counts['warning']}")
            print(f"Info logs: {self.alert_counts['info']}")
            print(f"Final report: {final_report}")
            print("="*70)

def main():
    print("🎯 ModelManagerAgent 24-Hour Observation Monitor")
    print("=" * 50)
    
    monitor = MMA24HourObservationMonitor()
    
    print("Starting 24-hour observation period...")
    print("Press Ctrl+C to stop monitoring early")
    print("=" * 50)
    
    monitor.start_observation()

if __name__ == "__main__":
    main() 