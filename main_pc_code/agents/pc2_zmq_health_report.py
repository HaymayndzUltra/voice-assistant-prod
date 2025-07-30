#!/usr/bin/env python3
"""
PC2 ZMQ Health Report Agent - Migrated to BaseAgent
Cross-machine health monitoring and reporting service.

This agent provides continuous health monitoring of PC2 ZMQ services,
generating periodic health reports and maintaining system visibility
across the distributed MainPC-PC2 architecture.
"""
import sys
import json
import time
import re
import threading
from pathlib import Path
from datetime import datetime
import prettytable
from typing import Dict, Any, List, Optional

# BaseAgent import - REQUIRED for migration
from common.core.base_agent import BaseAgent

# Standardized utilities
from common.utils.path_manager import PathManager
from common.utils.logger_util import get_json_logger
from common.utils.path_manager import PathManager

# Constants for health reporting
DEFAULT_HEALTH_REPORT_PORT = 5640
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
REPORT_RETENTION_DAYS = 7
MAX_RETRIES = 2
DEFAULT_TIMEOUT_MS = 5000

class PC2HealthReportAgent(BaseAgent):
    """
    PC2 ZMQ Health Report Agent migrated to BaseAgent inheritance.
    
    Provides continuous health monitoring of PC2 ZMQ services with
    periodic reporting and alerting capabilities.
    """
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
        """
        Initialize the PC2 Health Report Agent with BaseAgent inheritance.
        
        Args:
            port: Main service port (optional, will use DEFAULT_HEALTH_REPORT_PORT if not provided)
            health_check_port: Health check port (optional, defaults to port+1)
            **kwargs: Additional configuration parameters
        """
        # CRITICAL: Call BaseAgent.__init__() FIRST
        super().__init__(
            name=kwargs.get('name', 'PC2HealthReportAgent'),
            port=port or DEFAULT_HEALTH_REPORT_PORT,
            health_check_port=health_check_port,
            **kwargs
        )
        
        # Get JSON logger for standardized logging
        self.logger = get_json_logger(self.name)
        
        # Health monitoring configuration
        self.check_interval = kwargs.get('check_interval', HEALTH_CHECK_INTERVAL)
        self.timeout_ms = kwargs.get('timeout_ms', DEFAULT_TIMEOUT_MS)
        self.max_retries = kwargs.get('max_retries', MAX_RETRIES)
        
        # Health monitoring state
        self.pc2_services = {}
        self.last_health_report = None
        self.health_history = []
        self.alert_thresholds = {
            'consecutive_failures': 3,
            'failure_rate_threshold': 0.5
        }
        
        # Statistics tracking
        self.stats = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'reports_generated': 0,
            'alerts_sent': 0,
            'start_time': time.time()
        }
        
        # Initialize PC2 services
        self._load_pc2_services()
        
        # Set up health monitoring
        self._setup_health_monitoring()
        
        self.logger.info(f"{self.name} initialized successfully", extra={
            "port": self.port,
            "health_check_port": self.health_check_port,
            "check_interval": self.check_interval,
            "pc2_services_count": len(self.pc2_services),
            "component": "initialization"
        })
    
    def _load_pc2_services(self):
        """Load all PC2 ZMQ remote services from system configuration"""
        try:
            project_root = PathManager.get_project_root()
            config_path = Path(project_root) / 'main_pc_code' / 'config' / 'system_config.py'
            
            if not config_path.exists():
                self.logger.warning(f"System config not found at {config_path}")
                return
            
            # Read the system_config.py file content
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Look for PC2 ZMQ service patterns using regex
            pattern = r'"([^"]+)"\s*:\s*{[^}]*"serving_method"\s*:\s*"zmq_service_remote"[^}]*}'
            model_ids = re.findall(pattern, content, re.DOTALL)
            
            self.logger.info(f"Found {len(model_ids)} PC2 ZMQ services in system_config.py")
            
            # Extract and prepare model info
            self.pc2_services = {}
            for model_id in model_ids:
                service_info = self._extract_service_info(content, model_id)
                if service_info:
                    self.pc2_services[model_id] = service_info
                    self.logger.debug(f"Loaded PC2 service: {model_id} at {service_info['zmq_address']}")
            
            self.logger.info(f"Successfully loaded {len(self.pc2_services)} PC2 ZMQ services", extra={
                "services": list(self.pc2_services.keys()),
                "component": "service_loading"
            })
            
        except Exception as e:
            self.logger.error(f"Error loading PC2 services: {e}")
            self.pc2_services = {}
    
    def _extract_service_info(self, content: str, model_id: str) -> Optional[Dict[str, Any]]:
        """Extract service information from config content"""
        try:
            # Extract ZMQ address
            zmq_address_match = re.search(
                fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_address"\s*:\s*"([^"]+)"', 
                content, re.DOTALL
            )
            zmq_address = zmq_address_match.group(1) if zmq_address_match else None
            
            if not zmq_address:
                self.logger.warning(f"No ZMQ address found for {model_id}")
                return None
            
            # Extract display name
            display_name_match = re.search(
                fr'"{model_id}"\s*:\s*{{[^}}]*"display_name"\s*:\s*"([^"]+)"', 
                content, re.DOTALL
            )
            display_name = display_name_match.group(1) if display_name_match else model_id
            
            # Extract health check action
            health_action_match = re.search(
                fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_actions"\s*:\s*{{\s*"health"\s*:\s*"([^"]+)"', 
                content, re.DOTALL
            )
            health_action = health_action_match.group(1) if health_action_match else "health_check"
            
            # Extract expected health response
            health_expect_pattern = fr'"{model_id}"\s*:\s*{{[^}}]*"expected_health_response_contains"\s*:\s*{{\s*"status"\s*:\s*"([^"]+)"'
            health_expect_match = re.search(health_expect_pattern, content, re.DOTALL)
            expected_status = health_expect_match.group(1) if health_expect_match else "ok"
            
            return {
                "model_id": model_id,
                "display_name": display_name,
                "zmq_address": zmq_address,
                "health_action": health_action,
                "expected_status": expected_status,
                "consecutive_failures": 0,
                "last_check_time": None,
                "last_check_status": "unknown"
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting service info for {model_id}: {e}")
            return None
    
    def _setup_health_monitoring(self):
        """Set up background health monitoring"""
        def health_monitor():
            self.logger.info("PC2 health monitoring thread started")
            while self.running:
                try:
                    # Perform health check cycle
                    self._perform_health_check_cycle()
                    
                    # Wait for next check interval
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in health monitoring: {e}")
                    time.sleep(30)  # Short delay on error
            
            self.logger.info("PC2 health monitoring thread stopped")
        
        self.health_monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        self.health_monitor_thread.start()
    
    def _perform_health_check_cycle(self):
        """Perform a complete health check cycle for all PC2 services"""
        if not self.pc2_services:
            self.logger.warning("No PC2 services configured for health checking")
            return
        
        self.logger.info(f"Starting health check cycle for {len(self.pc2_services)} services")
        
        results = []
        for model_id, service_info in self.pc2_services.items():
            try:
                result = self._check_zmq_service(service_info)
                results.append(result)
                
                # Update service state
                self.pc2_services[model_id]['last_check_time'] = time.time()
                self.pc2_services[model_id]['last_check_status'] = result['status']
                
                if result['status'] != 'healthy':
                    self.pc2_services[model_id]['consecutive_failures'] += 1
                else:
                    self.pc2_services[model_id]['consecutive_failures'] = 0
                
                self.stats['total_checks'] += 1
                if result['status'] == 'healthy':
                    self.stats['successful_checks'] += 1
                else:
                    self.stats['failed_checks'] += 1
                
            except Exception as e:
                self.logger.error(f"Error checking service {model_id}: {e}")
                self.stats['failed_checks'] += 1
        
        # Generate and process report
        report = self._generate_health_report(results)
        self._process_health_report(report, results)
        
        # Check for alerts
        self._check_alert_conditions(results)
        
        self.logger.info(f"Health check cycle completed", extra={
            "services_checked": len(results),
            "healthy_services": sum(1 for r in results if r['status'] == 'healthy'),
            "component": "health_monitoring"
        })
    
    def _check_zmq_service(self, service_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check the health of a ZMQ remote service with retries"""
        model_id = service_info["model_id"]
        zmq_address = service_info["zmq_address"]
        health_action = service_info["health_action"]
        expected_status = service_info["expected_status"]
        
        result = {
            "model_id": model_id,
            "display_name": service_info["display_name"],
            "zmq_address": zmq_address,
            "status": "unknown",
            "error": None,
            "response": None,
            "latency_ms": 0,
            "expected_status": expected_status,
            "timestamp": datetime.now().isoformat()
        }
        
        # Try with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                import zmq
                context = zmq.Context()
                socket = context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, self.timeout_ms)
                socket.setsockopt(zmq.SNDTIMEO, self.timeout_ms)
                
                start_time = time.time()
                
                # Connect to service
                socket.connect(zmq_address)
                
                # Send health check request
                payload = {"action": health_action}
                socket.send_json(payload)
                
                # Wait for response
                raw_response = socket.recv()
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                # Parse response
                response_text = raw_response.decode('utf-8', errors='replace')
                response = json.loads(response_text)
                
                # Analyze response
                if isinstance(response, dict):
                    service_status = response.get('status', '').lower()
                    is_alive = response.get('alive', None)
                    
                    if (service_status == expected_status or 
                        service_status in ['loaded', 'online', 'ok', 'success', 'available_not_loaded'] or 
                        is_alive is True):
                        result.update({
                            "status": "healthy",
                            "response": response,
                            "latency_ms": latency_ms
                        })
                        break
                    else:
                        result.update({
                            "status": "unhealthy",
                            "error": f"Unexpected status: {service_status}",
                            "response": response,
                            "latency_ms": latency_ms
                        })
                else:
                    result.update({
                        "status": "unhealthy",
                        "error": "Invalid response format",
                        "response": response_text,
                        "latency_ms": latency_ms
                    })
                
                socket.close()
                context.term()
                break
                
            except zmq.Again:
                result.update({
                    "status": "timeout",
                    "error": f"Timeout after {self.timeout_ms}ms (attempt {attempt}/{self.max_retries})"
                })
                if attempt < self.max_retries:
                    time.sleep(1)  # Brief delay before retry
            except Exception as e:
                result.update({
                    "status": "error",
                    "error": f"Connection error: {str(e)} (attempt {attempt}/{self.max_retries})"
                })
                if attempt < self.max_retries:
                    time.sleep(1)  # Brief delay before retry
            finally:
                try:
                    socket.close()
                    context.term()
                except:
                    pass
        
        return result
    
    def _generate_health_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate formatted health report"""
        try:
            # Create summary table
            table = prettytable.PrettyTable()
            table.field_names = ["Service", "Status", "Latency", "Error"]
            table.align = "l"
            
            healthy_count = 0
            for result in results:
                status_icon = "✅" if result["status"] == "healthy" else "❌"
                status_text = f"{status_icon} {result['status']}"
                latency_text = f"{result['latency_ms']}ms" if result['latency_ms'] > 0 else "N/A"
                error_text = result['error'][:50] + "..." if result['error'] and len(result['error']) > 50 else result['error'] or ""
                
                table.add_row([
                    result['display_name'][:20],
                    status_text,
                    latency_text,
                    error_text
                ])
                
                if result["status"] == "healthy":
                    healthy_count += 1
            
            # Generate report header
            total_services = len(results)
            health_percentage = (healthy_count / total_services * 100) if total_services > 0 else 0
            
            report = f"""
PC2 ZMQ HEALTH REPORT
====================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Agent: {self.name}

SUMMARY:
- Total Services: {total_services}
- Healthy: {healthy_count} ({health_percentage:.1f}%)
- Unhealthy: {total_services - healthy_count}

SERVICE DETAILS:
{table}

STATISTICS:
- Total Checks: {self.stats['total_checks']}
- Success Rate: {(self.stats['successful_checks'] / max(1, self.stats['total_checks']) * 100):.1f}%
- Failed Checks: {self.stats['failed_checks']}
- Reports Generated: {self.stats['reports_generated']}
"""
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating health report: {e}")
            return f"Error generating report: {e}"
    
    def _process_health_report(self, report: str, results: List[Dict[str, Any]]):
        """Process and store health report"""
        try:
            self.last_health_report = {
                'timestamp': datetime.now().isoformat(),
                'report': report,
                'results': results,
                'summary': {
                    'total_services': len(results),
                    'healthy_services': sum(1 for r in results if r['status'] == 'healthy'),
                    'unhealthy_services': sum(1 for r in results if r['status'] != 'healthy')
                }
            }
            
            # Add to history (keep last 24 reports)
            self.health_history.append(self.last_health_report)
            if len(self.health_history) > 24:
                self.health_history.pop(0)
            
            self.stats['reports_generated'] += 1
            
            # Save to file
            self._save_report_to_file(report, results)
            
            self.logger.info("Health report processed and saved", extra={
                "healthy_services": self.last_health_report['summary']['healthy_services'],
                "total_services": self.last_health_report['summary']['total_services'],
                "component": "health_reporting"
            })
            
        except Exception as e:
            self.logger.error(f"Error processing health report: {e}")
    
    def _save_report_to_file(self, report: str, results: List[Dict[str, Any]]):
        """Save health report to file"""
        try:
            # Create reports directory
            reports_dir = Path("reports/health")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"pc2_health_report_{timestamp}.txt"
            json_filename = f"pc2_health_report_{timestamp}.json"
            
            # Save text report
            report_path = reports_dir / report_filename
            with open(report_path, 'w') as f:
                f.write(report)
            
            # Save JSON data
            json_path = reports_dir / json_filename
            json_data = {
                'timestamp': datetime.now().isoformat(),
                'agent': self.name,
                'summary': {
                    'total_services': len(results),
                    'healthy_services': sum(1 for r in results if r['status'] == 'healthy'),
                    'unhealthy_services': sum(1 for r in results if r['status'] != 'healthy')
                },
                'results': results,
                'statistics': self.stats.copy()
            }
            
            with open(json_path, 'w') as f:
                json.dump(json_data, f, indent=2)
            
            self.logger.debug(f"Health report saved to {report_path} and {json_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving health report: {e}")
    
    def _check_alert_conditions(self, results: List[Dict[str, Any]]):
        """Check for alert conditions and send alerts if needed"""
        try:
            alerts = []
            
            # Check for consecutive failures
            for model_id, service_info in self.pc2_services.items():
                if service_info['consecutive_failures'] >= self.alert_thresholds['consecutive_failures']:
                    alerts.append({
                        'type': 'consecutive_failures',
                        'service': model_id,
                        'failure_count': service_info['consecutive_failures'],
                        'message': f"Service {model_id} has failed {service_info['consecutive_failures']} consecutive health checks"
                    })
            
            # Check overall failure rate
            total_services = len(results)
            failed_services = sum(1 for r in results if r['status'] != 'healthy')
            if total_services > 0:
                failure_rate = failed_services / total_services
                if failure_rate >= self.alert_thresholds['failure_rate_threshold']:
                    alerts.append({
                        'type': 'high_failure_rate',
                        'failure_rate': failure_rate,
                        'failed_services': failed_services,
                        'total_services': total_services,
                        'message': f"High failure rate: {failed_services}/{total_services} services unhealthy ({failure_rate*100:.1f}%)"
                    })
            
            # Process alerts
            for alert in alerts:
                self._send_alert(alert)
                self.stats['alerts_sent'] += 1
            
        except Exception as e:
            self.logger.error(f"Error checking alert conditions: {e}")
    
    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert notification"""
        self.logger.warning("PC2 Health Alert", extra={
            "alert_type": alert['type'],
            "alert_message": alert['message'],
            "alert_data": alert,
            "component": "health_alerting"
        })
        
        # TODO: Implement additional alert mechanisms (email, Slack, etc.)
    
    def get_current_health_status(self) -> Dict[str, Any]:
        """Get current health status of all PC2 services"""
        return {
            'timestamp': datetime.now().isoformat(),
            'agent': self.name,
            'services': self.pc2_services.copy(),
            'last_report': self.last_health_report,
            'statistics': self.stats.copy()
        }
    
    def run(self):
        """
        Main execution method using BaseAgent's run() framework.
        """
        try:
            self.logger.info(f"Starting {self.name}")
            
            # Perform initial health check
            if self.pc2_services:
                self.logger.info("Performing initial health check...")
                self._perform_health_check_cycle()
            
            # Call parent run() method for standard startup
            super().run()
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested via KeyboardInterrupt")
        except Exception as e:
            self.logger.error(f"Fatal error in {self.name}: {e}")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        """
        Cleanup method with custom cleanup logic for health reporting.
        """
        try:
            self.logger.info(f"Cleaning up {self.name}")
            
            # Generate final health report
            if self.pc2_services:
                self.logger.info("Generating final health report...")
                try:
                    results = []
                    for service_info in self.pc2_services.values():
                        results.append({
                            'model_id': service_info['model_id'],
                            'display_name': service_info['display_name'],
                            'status': service_info['last_check_status'],
                            'last_check_time': service_info['last_check_time']
                        })
                    
                    final_report = self._generate_health_report(results)
                    self._save_report_to_file(final_report, results)
                except Exception as e:
                    self.logger.error(f"Error generating final report: {e}")
            
            # Call parent cleanup
            super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# Backward compatibility functions
def load_pc2_zmq_services():
    """Legacy function for backward compatibility"""
    agent = PC2HealthReportAgent()
    return agent.pc2_services

def check_zmq_service(service_info, timeout_ms=5000, retries=2):
    """Legacy function for backward compatibility"""
    agent = PC2HealthReportAgent()
    return agent._check_zmq_service(service_info)

def generate_health_report(results):
    """Legacy function for backward compatibility"""
    agent = PC2HealthReportAgent()
    return agent._generate_health_report(results)

def main():
    """Main function for backward compatibility and standalone execution"""
    print("\nPC2 ZMQ HEALTH CHECK REPORTER (BaseAgent Version)")
    print("==================================================")
    
    # For one-shot mode, create a minimal instance without BaseAgent initialization
    # to avoid argument parsing conflicts
    try:
        # Load PC2 services directly
        project_root = PathManager.get_project_root()
        config_path = Path(project_root) / 'main_pc_code' / 'config' / 'system_config.py'
        
        if not config_path.exists():
            print(f"\n❌ System config not found at {config_path}")
            return 1
        
        # Read the system_config.py file content
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Look for PC2 ZMQ service patterns using regex
        pattern = r'"([^"]+)"\s*:\s*{[^}]*"serving_method"\s*:\s*"zmq_service_remote"[^}]*}'
        model_ids = re.findall(pattern, content, re.DOTALL)
        
        if not model_ids:
            print("\n❌ No PC2 ZMQ services found in system_config.py")
            return 1
        
        print(f"\nFound {len(model_ids)} PC2 ZMQ services to check")
        
        # Check each service using simplified approach
        results = []
        for model_id in model_ids:
            print(f"Checking {model_id}...")
            
            # Extract service info (simplified version)
            zmq_address_match = re.search(
                fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_address"\s*:\s*"([^"]+)"', 
                content, re.DOTALL
            )
            zmq_address = zmq_address_match.group(1) if zmq_address_match else None
            
            display_name_match = re.search(
                fr'"{model_id}"\s*:\s*{{[^}}]*"display_name"\s*:\s*"([^"]+)"', 
                content, re.DOTALL
            )
            display_name = display_name_match.group(1) if display_name_match else model_id
            
            if zmq_address:
                # Simplified health check
                result = {
                    "model_id": model_id,
                    "display_name": display_name,
                    "zmq_address": zmq_address,
                    "status": "skipped",
                    "error": "One-shot mode - simplified check",
                    "latency_ms": 0,
                    "timestamp": datetime.now().isoformat()
                }
                results.append(result)
                print(f"  ℹ️  {model_id} - one-shot mode (service discovery only)")
            else:
                print(f"  ❌ {model_id} - no ZMQ address found")
        
        # Generate simple report
        print(f"\n📊 PC2 ZMQ SERVICES DISCOVERY REPORT")
        print("=" * 50)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: One-shot discovery")
        print(f"\nSERVICES FOUND: {len(results)}")
        
        for result in results:
            print(f"- {result['display_name']} ({result['model_id']}) at {result['zmq_address']}")
        
        print(f"\n💡 NOTE: This was a service discovery run.")
        print(f"   For full health checks, run without --one-shot flag.")
        print(f"   Example: python3 main_pc_code/agents/pc2_zmq_health_report.py --port 5640")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error in one-shot health check: {e}")
        return 1

if __name__ == "__main__":
    import argparse
    
    # Parse arguments ourselves to avoid conflict with BaseAgent's parse_agent_args()
    parser = argparse.ArgumentParser(description="Run PC2 Health Report Agent")
    parser.add_argument('--port', type=int, help='Main service port')
    parser.add_argument('--health-port', type=int, help='Health check port')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--one-shot', action='store_true', help='Run one health check and exit')
    parser.add_argument('--interval', type=int, help='Health check interval in seconds')
    
    # Parse known args to avoid conflicts with BaseAgent's argument parser
    args, unknown = parser.parse_known_args()
    
    if args.one_shot:
        # Run one-time health check (legacy mode)
        sys.exit(main())
    else:
        # Run as continuous service
        # Temporarily clear sys.argv to avoid BaseAgent parsing conflicts
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]  # Keep only script name
        
        try:
            agent = PC2HealthReportAgent(
                port=args.port,
                health_check_port=args.health_port,
                check_interval=args.interval or HEALTH_CHECK_INTERVAL
            )
            
            agent.run()
        finally:
            # Restore original argv
            sys.argv = original_argv
