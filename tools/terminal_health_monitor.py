#!/usr/bin/env python3
"""
Terminal Health Monitor
Prevents terminal session failures and provides recovery mechanisms
"""

import os
import time
import psutil
import subprocess
import signal
from pathlib import Path
from typing import Dict, Any

class TerminalHealthMonitor:
    def __init__(self, max_memory_mb: int = 1024, max_cpu_percent: float = 80.0):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.session_start_time = time.time()
        self.last_health_check = time.time()
        
    def check_system_resources(self) -> Dict[str, Any]:
        """Check current system resource usage"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            return {
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024*1024),
                "cpu_percent": cpu_percent,
                "healthy": memory.percent < 90 and cpu_percent < self.max_cpu_percent
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}
    
    def check_wsl_health(self) -> bool:
        """Check WSL2 subsystem health"""
        try:
            # Check if we're in WSL
            if not os.path.exists('/proc/version'):
                return True
                
            with open('/proc/version', 'r') as f:
                version_info = f.read()
                
            # Check for WSL indicators
            if 'Microsoft' in version_info or 'WSL' in version_info:
                # Test basic WSL operations
                result = subprocess.run(['uname', '-r'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                return result.returncode == 0
            return True
            
        except Exception:
            return False
    
    def cleanup_zombie_processes(self) -> int:
        """Clean up zombie processes that might be causing issues"""
        cleaned = 0
        try:
            for proc in psutil.process_iter(['pid', 'status', 'name']):
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    try:
                        parent = psutil.Process(proc.info['pid']).parent()
                        if parent and 'python' in parent.name().lower():
                            os.kill(proc.info['pid'], signal.SIGKILL)
                            cleaned += 1
                    except (psutil.NoSuchProcess, PermissionError):
                        pass
        except Exception:
            pass
        return cleaned
    
    def test_terminal_responsiveness(self, timeout: float = 5.0) -> bool:
        """Test if terminal can execute basic commands"""
        try:
            result = subprocess.run(['echo', 'test'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=timeout)
            return result.returncode == 0 and result.stdout.strip() == 'test'
        except (subprocess.TimeoutExpired, Exception):
            return False
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        uptime = time.time() - self.session_start_time
        return {
            "session_uptime_seconds": uptime,
            "session_uptime_minutes": uptime / 60,
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "shell": os.environ.get('SHELL', 'unknown'),
            "terminal": os.environ.get('TERM', 'unknown')
        }
    
    def force_session_cleanup(self) -> bool:
        """Force cleanup of current session"""
        try:
            # Clean up Python cache
            for root, dirs, files in os.walk('.'):
                for dir_name in dirs[:]:
                    if dir_name == '__pycache__':
                        import shutil
                        shutil.rmtree(os.path.join(root, dir_name))
                        dirs.remove(dir_name)
            
            # Clear temporary files
            temp_patterns = ['*.tmp', '*.temp', '*.log~', '.*.swp']
            for pattern in temp_patterns:
                for temp_file in Path('.').glob(f'**/{pattern}'):
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
            
            return True
        except Exception:
            return False
    
    def health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        resources = self.check_system_resources()
        wsl_healthy = self.check_wsl_health()
        terminal_responsive = self.test_terminal_responsiveness()
        session_info = self.get_session_info()
        
        overall_health = (
            resources.get("healthy", False) and 
            wsl_healthy and 
            terminal_responsive
        )
        
        return {
            "overall_healthy": overall_health,
            "timestamp": time.time(),
            "resources": resources,
            "wsl_healthy": wsl_healthy,
            "terminal_responsive": terminal_responsive,
            "session_info": session_info,
            "recommendations": self._get_recommendations(resources, wsl_healthy, terminal_responsive)
        }
    
    def _get_recommendations(self, resources: Dict, wsl_healthy: bool, terminal_responsive: bool) -> list:
        """Get health improvement recommendations"""
        recommendations = []
        
        if not resources.get("healthy", False):
            if resources.get("memory_percent", 0) > 80:
                recommendations.append("High memory usage - consider restarting processes")
            if resources.get("cpu_percent", 0) > 80:
                recommendations.append("High CPU usage - wait for operations to complete")
        
        if not wsl_healthy:
            recommendations.append("WSL subsystem issues - consider 'wsl --restart'")
        
        if not terminal_responsive:
            recommendations.append("Terminal not responsive - force new session needed")
        
        return recommendations

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Terminal Health Monitor")
    parser.add_argument("--check", action="store_true", help="Run health check")
    parser.add_argument("--cleanup", action="store_true", help="Clean up session")
    parser.add_argument("--monitor", action="store_true", help="Continuous monitoring")
    parser.add_argument("--interval", type=int, default=30, help="Monitor interval in seconds")
    
    args = parser.parse_args()
    
    monitor = TerminalHealthMonitor()
    
    if args.check:
        report = monitor.health_report()
        print(f"🏥 Terminal Health Report")
        print(f"Overall Health: {'✅ HEALTHY' if report['overall_healthy'] else '❌ UNHEALTHY'}")
        print(f"WSL Status: {'✅' if report['wsl_healthy'] else '❌'}")
        print(f"Terminal Responsive: {'✅' if report['terminal_responsive'] else '❌'}")
        print(f"Memory Usage: {report['resources'].get('memory_percent', 0):.1f}%")
        print(f"CPU Usage: {report['resources'].get('cpu_percent', 0):.1f}%")
        
        if report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"  • {rec}")
    
    elif args.cleanup:
        print("🧹 Cleaning up session...")
        zombies = monitor.cleanup_zombie_processes()
        cleanup_success = monitor.force_session_cleanup()
        print(f"Cleaned {zombies} zombie processes")
        print(f"Session cleanup: {'✅' if cleanup_success else '❌'}")
    
    elif args.monitor:
        print(f"📊 Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")
        try:
            while True:
                report = monitor.health_report()
                status = "✅ HEALTHY" if report['overall_healthy'] else "❌ UNHEALTHY"
                print(f"{time.strftime('%H:%M:%S')} - {status} | "
                      f"Mem: {report['resources'].get('memory_percent', 0):.1f}% | "
                      f"CPU: {report['resources'].get('cpu_percent', 0):.1f}%")
                
                if not report['overall_healthy']:
                    print("  ⚠️ Issues detected:")
                    for rec in report['recommendations']:
                        print(f"    • {rec}")
                
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n📊 Monitoring stopped")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 