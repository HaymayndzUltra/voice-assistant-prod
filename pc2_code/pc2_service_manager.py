#!/usr/bin/env python3
"""
PC2 Service Manager
- Comprehensive tool for managing all PC2 services
- Ensures proper external binding (0.0.0.0) for Main PC connectivity
- Handles service startup, monitoring, and health checks
- Provides fallback mechanisms for critical services
"""
import os
import sys
import time
import json
import socket
import logging
import argparse
import subprocess
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/pc2_service_manager.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PC2ServiceManager")

# Define service configuration
PC2_SERVICES = [
    # Critical Translation Services
    {
        "name": "NLLB Translation Adapter",
        "script": "agents/nllb_translation_adapter.py",
        "port": 5581,
        "bind_address": "0.0.0.0",
        "critical": True,
        "dependencies": [],
        "startup_time": 20,
        "test_request": {
            "action": "translate",
            "text": "Magandang umaga po",
            "source_lang": "tgl_Latn",
            "target_lang": "eng_Latn"
        }
    },
    {
        "name": "TinyLlama Service",
        "script": "agents/tinyllama_service_enhanced.py",
        "port": 5615,
        "bind_address": "0.0.0.0",
        "critical": True,
        "dependencies": [],
        "startup_time": 10,
        "test_request": {
            "action": "health_check"
        }
    },
    {
        "name": "Translator Agent",
        "script": "quick_translator_fix.py",  # Using our reliable quick fix version
        "original_script": "agents/translator_agent_fixed.py",
        "port": 5563,
        "bind_address": "0.0.0.0",
        "critical": True,
        "dependencies": ["NLLB Translation Adapter", "TinyLlama Service"],
        "startup_time": 5,
        "test_request": {
            "action": "translate",
            "text": "Buksan mo ang file",
            "source_lang": "tl",
            "target_lang": "en",
            "session_id": "test_session"
        }
    },
    
    # Memory Services - non-critical for initial connectivity testing
    {
        "name": "Memory Agent",
        "script": "agents/memory.py",
        "port": 5590,
        "bind_address": "0.0.0.0",
        "critical": False,
        "dependencies": [],
        "startup_time": 5,
        "test_request": {
            "action": "health_check"
        }
    },
    {
        "name": "Contextual Memory Agent",
        "script": "agents/contextual_memory_agent.py",
        "port": 5596,
        "bind_address": "0.0.0.0",
        "critical": False,
        "dependencies": ["Memory Agent"],
        "startup_time": 5,
        "test_request": {
            "action": "health_check"
        }
    }
]

class PC2ServiceManager:
    def __init__(self):
        """Initialize the PC2 Service Manager"""
        self.services = PC2_SERVICES
        self.processes = {}
        self.health_status = {}
        self.base_dir = Path(__file__).resolve().parent
    
    def check_port_available(self, port):
        """Check if a port is available (not in use)"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = True
        try:
            sock.bind(("0.0.0.0", port))
        except:
            result = False
        finally:
            sock.close()
        return result
    
    def check_port_listening(self, port):
        """Check if a port has a service listening on it"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = False
        try:
            sock.connect(("localhost", port))
            result = True
        except:
            result = False
        finally:
            sock.close()
        return result
    
    def kill_process_on_port(self, port):
        """Attempt to kill any process using the specified port"""
        try:
            # This works on Windows
            result = subprocess.run(
                f"FOR /F \"tokens=5\" %a in ('netstat -ano ^| findstr :{port} ^| findstr LISTENING') do taskkill /F /PID %a",
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            logger.info(f"Attempted to kill process on port {port}: {result.stdout.decode()}")
            return True
        except Exception as e:
            logger.error(f"Failed to kill process on port {port}: {str(e)}")
            return False
    
    def ensure_port_available(self, port):
        """Ensure a port is available, killing any process using it if needed"""
        if not self.check_port_available(port):
            logger.warning(f"Port {port} is in use. Attempting to kill process...")
            if self.kill_process_on_port(port):
                time.sleep(1)  # Wait a moment for the port to be freed
                if self.check_port_available(port):
                    logger.info(f"Port {port} is now available")
                    return True
                else:
                    logger.error(f"Port {port} is still in use after kill attempt")
                    return False
            else:
                logger.error(f"Failed to free port {port}")
                return False
        return True
    
    def setup_firewall_rules(self):
        """Setup firewall rules for all PC2 service ports"""
        logger.info("Setting up firewall rules for PC2 services...")
        
        # Get all unique ports
        ports = [service["port"] for service in self.services]
        ports_str = ",".join(map(str, ports))
        
        try:
            # Create a PowerShell command to add firewall rules
            ps_command = f"""
            $existingRule = Get-NetFirewallRule -DisplayName 'PC2 Services' -ErrorAction SilentlyContinue
            if ($existingRule) {{
                Remove-NetFirewallRule -DisplayName 'PC2 Services'
            }}
            New-NetFirewallRule -DisplayName 'PC2 Services' -Direction Inbound -Protocol TCP -LocalPort {ports_str} -Action Allow
            """
            
            # Write to a temporary file
            with open("temp_firewall.ps1", "w") as f:
                f.write(ps_command)
            
            # Run the PowerShell script with admin privileges
            subprocess.run(
                ["powershell", "-Command", "Start-Process", "powershell", 
                 "-ArgumentList", "'-ExecutionPolicy Bypass -File temp_firewall.ps1'", 
                 "-Verb", "RunAs", "-Wait"],
                check=True
            )
            
            logger.info(f"Firewall rules successfully applied for ports: {ports_str}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup firewall rules: {str(e)}")
            return False
    
    def start_service(self, service):
        """Start a single PC2 service"""
        name = service["name"]
        script = service["script"]
        port = service["port"]
        
        logger.info(f"Starting {name} on port {port}...")
        
        # Check if the script exists
        script_path = self.base_dir / script
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return False
        
        # Ensure the port is available
        if not self.ensure_port_available(port):
            logger.error(f"Cannot start {name}: port {port} is unavailable")
            return False
        
        # Start the service in a new process
        try:
            cmd = f"start \"PC2 {name}\" cmd /k python {script}"
            subprocess.Popen(cmd, shell=True)
            
            # Wait for the service to start
            start_time = time.time()
            max_wait = service["startup_time"]
            
            logger.info(f"Waiting up to {max_wait}s for {name} to start...")
            
            while time.time() - start_time < max_wait:
                if self.check_port_listening(port):
                    logger.info(f"{name} successfully started on port {port}")
                    return True
                time.sleep(1)
            
            logger.warning(f"Timeout waiting for {name} to start")
            return False
            
        except Exception as e:
            logger.error(f"Error starting {name}: {str(e)}")
            return False
    
    def start_all_services(self, critical_only=False):
        """Start all PC2 services in the correct order"""
        logger.info(f"Starting {'critical' if critical_only else 'all'} PC2 services...")
        
        # Filter services based on critical flag if needed
        services_to_start = [s for s in self.services if not critical_only or s["critical"]]
        
        # Start services with no dependencies first
        started = []
        failures = []
        
        # First pass: services with no dependencies
        for service in services_to_start:
            if not service["dependencies"]:
                if self.start_service(service):
                    started.append(service["name"])
                else:
                    failures.append(service["name"])
        
        # Second pass: services with dependencies
        for service in services_to_start:
            if service["dependencies"]:
                # Check if all dependencies are started
                deps_met = all(dep in started for dep in service["dependencies"])
                
                if deps_met:
                    if self.start_service(service):
                        started.append(service["name"])
                    else:
                        failures.append(service["name"])
                else:
                    logger.error(f"Cannot start {service['name']}: dependencies not met")
                    failures.append(service["name"])
        
        # Report results
        if failures:
            logger.warning(f"Failed to start these services: {', '.join(failures)}")
        
        if started:
            logger.info(f"Successfully started these services: {', '.join(started)}")
        
        return started, failures
    
    def check_service_health(self, service):
        """Check the health of a single service"""
        import zmq
        
        name = service["name"]
        port = service["port"]
        test_request = service.get("test_request", {"action": "health_check"})
        
        logger.info(f"Checking health of {name} on port {port}...")
        
        # First check if the port is listening
        if not self.check_port_listening(port):
            logger.warning(f"{name} is not listening on port {port}")
            return False, "Port not listening"
        
        # Try to connect and send a request
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            socket.connect(f"tcp://localhost:{port}")
            
            # Send test request
            socket.send_string(json.dumps(test_request))
            
            # Wait for response
            response = socket.recv_string()
            response_data = json.loads(response)
            
            # Check response status
            if response_data.get("status") in ["success", "ok"]:
                logger.info(f"{name} is healthy: {response[:100]}...")
                return True, response_data
            else:
                logger.warning(f"{name} returned error status: {response[:100]}...")
                return False, response_data
                
        except Exception as e:
            logger.error(f"Error checking {name} health: {str(e)}")
            return False, str(e)
        finally:
            socket.close()
            context.term()
    
    def check_all_service_health(self):
        """Check the health of all PC2 services"""
        logger.info("Checking health of all PC2 services...")
        
        results = {}
        
        for service in self.services:
            name = service["name"]
            healthy, details = self.check_service_health(service)
            
            results[name] = {
                "healthy": healthy,
                "details": details,
                "port": service["port"],
                "critical": service["critical"]
            }
        
        # Update health status
        self.health_status = results
        
        # Summarize results
        healthy_services = [name for name, data in results.items() if data["healthy"]]
        unhealthy_services = [name for name, data in results.items() if not data["healthy"]]
        
        logger.info(f"Health check complete. Healthy: {len(healthy_services)}, Unhealthy: {len(unhealthy_services)}")
        
        if unhealthy_services:
            logger.warning(f"Unhealthy services: {', '.join(unhealthy_services)}")
        
        return results
    
    def print_health_report(self):
        """Print a detailed health report for all services"""
        if not self.health_status:
            self.check_all_service_health()
        
        print("\nPC2 SERVICES HEALTH REPORT")
        print("=" * 80)
        
        # Print a table header
        print(f"{'Service Name':<30} {'Port':<10} {'Status':<15} {'Details'}")
        print("-" * 80)
        
        for name, data in self.health_status.items():
            status = "✅ HEALTHY" if data["healthy"] else "❌ UNHEALTHY"
            details = str(data["details"])
            if len(details) > 30:
                details = details[:27] + "..."
            
            print(f"{name:<30} {data['port']:<10} {status:<15} {details}")
        
        # Print summary
        healthy_count = sum(1 for data in self.health_status.values() if data["healthy"])
        total_count = len(self.health_status)
        
        print("-" * 80)
        print(f"Summary: {healthy_count}/{total_count} services are healthy")
        
        # Check if all critical services are healthy
        critical_services = [name for name, data in self.health_status.items() 
                            if data["critical"] and not data["healthy"]]
        
        if critical_services:
            print(f"\n⚠️  WARNING: These critical services are unhealthy: {', '.join(critical_services)}")
        else:
            print("\n✅ All critical services are healthy")
    
    def restart_unhealthy_services(self):
        """Restart any unhealthy services"""
        if not self.health_status:
            self.check_all_service_health()
        
        unhealthy_services = [name for name, data in self.health_status.items() if not data["healthy"]]
        
        if not unhealthy_services:
            logger.info("No unhealthy services to restart")
            return
        
        logger.info(f"Restarting unhealthy services: {', '.join(unhealthy_services)}")
        
        for service in self.services:
            if service["name"] in unhealthy_services:
                # Kill any process on this port
                self.kill_process_on_port(service["port"])
                time.sleep(1)
                
                # Restart the service
                self.start_service(service)
    
    def monitor_services(self, interval=60):
        """Continuously monitor services and restart if needed"""
        logger.info(f"Starting service monitoring with {interval}s interval")
        
        try:
            while True:
                self.check_all_service_health()
                self.print_health_report()
                self.restart_unhealthy_services()
                
                logger.info(f"Next health check in {interval} seconds...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Service monitoring stopped by user")

def main():
    """Main entry point for the PC2 Service Manager"""
    parser = argparse.ArgumentParser(description="PC2 Service Manager")
    parser.add_argument("--start", action="store_true", help="Start all PC2 services")
    parser.add_argument("--critical", action="store_true", help="Only start critical services")
    parser.add_argument("--health", action="store_true", help="Check health of all services")
    parser.add_argument("--monitor", action="store_true", help="Monitor services and restart if needed")
    parser.add_argument("--restart", action="store_true", help="Restart unhealthy services")
    parser.add_argument("--firewall", action="store_true", help="Setup firewall rules")
    
    args = parser.parse_args()
    
    manager = PC2ServiceManager()
    
    if args.firewall:
        manager.setup_firewall_rules()
    
    if args.start:
        manager.start_all_services(critical_only=args.critical)
    
    if args.health or args.restart:
        manager.check_all_service_health()
        manager.print_health_report()
    
    if args.restart:
        manager.restart_unhealthy_services()
    
    if args.monitor:
        manager.monitor_services()
    
    # If no arguments, show help
    if not any(vars(args).values()):
        parser.print_help()
        print("\nExamples:")
        print("  python pc2_service_manager.py --firewall --start  # Setup firewall and start all services")
        print("  python pc2_service_manager.py --critical --health  # Start critical services and check health")
        print("  python pc2_service_manager.py --monitor  # Continuously monitor and restart services")

if __name__ == "__main__":
    main()
