#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Deployment Validation Script
Validates the entire AI System deployment across MainPC and PC2
"""

import sys
import time
import json
import argparse
import subprocess
import requests
import zmq
from typing import Dict, List, Optional
from pathlib import Path

class DeploymentValidator:
    def __init__(self):
        self.mainpc_host = get_service_ip("mainpc")  # Configure as needed
        self.pc2_host = get_service_ip("pc2")     # Configure as needed
        self.results = {"mainpc": {}, "pc2": {}, "cross_machine": {}}
    
    def check_docker_containers(self, host: str) -> Dict:
        """Check if Docker containers are running"""
        try:
            if host == "localhost":
                cmd = "docker ps --format '{{.Names}},{{.Status}}'"
            else:
                cmd = f"ssh {host} 'docker ps --format \"{{{{.Names}}}},{{{{.Status}}}}\"'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"status": "error", "message": result.stderr}
            
            containers = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    name, status = line.split(',', 1)
                    containers[name] = {"status": "healthy" if "Up" in status else "unhealthy", "details": status}
            
            return {"status": "success", "containers": containers}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def check_zmq_service(self, host: str, port: int, service_name: str) -> Dict:
        """Check individual ZMQ service health"""
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            socket.setsockopt(zmq.SNDTIMEO, 5000)
            socket.connect(f"tcp://{host}:{port}")
            
            socket.send_string("health_check")
            response = socket.recv_string()
            
            socket.close()
            context.term()
            
            healthy = response == "OK" or "healthy" in response.lower()
            return {
                "status": "healthy" if healthy else "unhealthy",
                "response": response,
                "service": service_name
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": service_name
            }
    
    def check_redis_nats(self, host: str) -> Dict:
        """Check Redis and NATS infrastructure"""
        results = {}
        
        # Check Redis
        try:
            import redis
            r = redis.Redis(host=host, port=6379, decode_responses=True)
            r.ping()
            results["redis"] = {"status": "healthy"}
        except Exception as e:
            results["redis"] = {"status": "unhealthy", "error": str(e)}
        
        # Check NATS
        try:
            response = requests.get(f"http://{host}:8222/healthz", timeout=5)
            results["nats"] = {"status": "healthy" if response.status_code == 200 else "unhealthy"}
        except Exception as e:
            results["nats"] = {"status": "unhealthy", "error": str(e)}
        
        return results
    
    def validate_mainpc(self) -> Dict:
        """Validate MainPC deployment"""
        print("🔍 Validating MainPC deployment...")
        
        # Check Docker containers
        containers = self.check_docker_containers("localhost")
        
        # Check core services
        core_services = [
            ("ServiceRegistry", 7200),
            ("SystemDigitalTwin", 7220),
            ("RequestCoordinator", 26002),
            ("ModelManagerSuite", 7211),
            ("ObservabilityHub", 9000)
        ]
        
        service_health = {}
        for service, port in core_services:
            health = self.check_zmq_service("localhost", port, service)
            service_health[service] = health
        
        # Check infrastructure
        infrastructure = self.check_redis_nats("localhost")
        
        return {
            "containers": containers,
            "services": service_health,
            "infrastructure": infrastructure
        }
    
    def validate_pc2(self) -> Dict:
        """Validate PC2 deployment"""
        print("🔍 Validating PC2 deployment...")
        
        # Check Docker containers
        containers = self.check_docker_containers("localhost")  # Run from PC2
        
        # Check core PC2 services
        pc2_services = [
            ("MemoryOrchestratorService", 7140),
            ("TieredResponder", 7100),
            ("TaskScheduler", 7115),
            ("ResourceManager", 7113)
        ]
        
        service_health = {}
        for service, port in pc2_services:
            health = self.check_zmq_service("localhost", port, service)
            service_health[service] = health
        
        return {
            "containers": containers,
            "services": service_health
        }
    
    def validate_cross_machine(self) -> Dict:
        """Validate cross-machine connectivity"""
        print("🔍 Validating cross-machine connectivity...")
        
        results = {}
        
        # Test network connectivity
        try:
            # Ping test
            ping_result = subprocess.run(
                f"ping -c 3 {self.pc2_host}", 
                shell=True, capture_output=True, text=True
            )
            results["network_ping"] = {
                "status": "healthy" if ping_result.returncode == 0 else "unhealthy",
                "output": ping_result.stdout
            }
        except Exception as e:
            results["network_ping"] = {"status": "error", "error": str(e)}
        
        # Test ServiceRegistry from PC2
        try:
            registry_health = self.check_zmq_service(self.mainpc_host, 7200, "ServiceRegistry")
            results["cross_service_registry"] = registry_health
        except Exception as e:
            results["cross_service_registry"] = {"status": "error", "error": str(e)}
        
        return results
    
    def generate_report(self) -> str:
        """Generate comprehensive validation report"""
        total_services = 0
        healthy_services = 0
        
        # Count MainPC services
        if "services" in self.results["mainpc"]:
            for service, health in self.results["mainpc"]["services"].items():
                total_services += 1
                if health.get("status") == "healthy":
                    healthy_services += 1
        
        # Count PC2 services
        if "services" in self.results["pc2"]:
            for service, health in self.results["pc2"]["services"].items():
                total_services += 1
                if health.get("status") == "healthy":
                    healthy_services += 1
        
        health_percentage = (healthy_services / total_services * 100) if total_services > 0 else 0
        
        # Overall status
        if health_percentage >= 95:
            status = "✅ ALL systems healthy"
        elif health_percentage >= 80:
            status = "⚠️  MOSTLY healthy with minor issues"
        elif health_percentage >= 50:
            status = "❌ DEGRADED - multiple issues detected"
        else:
            status = "🚨 CRITICAL - system failure"
        
        report = f"""
🚀 AI SYSTEM DEPLOYMENT VALIDATION REPORT
{'='*50}

Overall Status: {status}
Service Health: {healthy_services}/{total_services} ({health_percentage:.1f}%)

MAINPC (RTX 4090) STATUS:
{self._format_machine_status(self.results["mainpc"])}

PC2 (RTX 3060) STATUS:
{self._format_machine_status(self.results["pc2"])}

CROSS-MACHINE CONNECTIVITY:
{self._format_cross_machine_status(self.results["cross_machine"])}

Validation completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        return report
    
    def _format_machine_status(self, machine_data: Dict) -> str:
        """Format machine status for report"""
        lines = []
        
        if "containers" in machine_data and machine_data["containers"].get("status") == "success":
            containers = machine_data["containers"]["containers"]
            lines.append(f"  Containers: {len(containers)} running")
        
        if "services" in machine_data:
            for service, health in machine_data["services"].items():
                status_icon = "✅" if health.get("status") == "healthy" else "❌"
                lines.append(f"  {status_icon} {service}")
        
        if "infrastructure" in machine_data:
            for infra, health in machine_data["infrastructure"].items():
                status_icon = "✅" if health.get("status") == "healthy" else "❌"
                lines.append(f"  {status_icon} {infra}")
        
        return "\n".join(lines) if lines else "  No data available"
    
    def _format_cross_machine_status(self, cross_data: Dict) -> str:
        """Format cross-machine status for report"""
        lines = []
        
        for check, result in cross_data.items():
            status_icon = "✅" if result.get("status") == "healthy" else "❌"
            lines.append(f"  {status_icon} {check}")
        
        return "\n".join(lines) if lines else "  No connectivity tests performed"

def main():
    parser = argparse.ArgumentParser(description="Validate AI System Deployment")
    parser.add_argument("--machine", choices=["mainpc", "pc2", "all"], default="all",
                      help="Which machine to validate")
    parser.add_argument("--mainpc-host", default=get_service_ip("mainpc"),
                      help="MainPC host address")
    parser.add_argument("--pc2-host", default=get_service_ip("pc2"), 
                      help="PC2 host address")
    parser.add_argument("--output", help="Output file for report")
    
    args = parser.parse_args()
    
    validator = DeploymentValidator()
    validator.mainpc_host = args.mainpc_host
    validator.pc2_host = args.pc2_host
    
    # Run validations based on machine argument
    if args.machine in ["all", "mainpc"]:
        validator.results["mainpc"] = validator.validate_mainpc()
    
    if args.machine in ["all", "pc2"]:
        validator.results["pc2"] = validator.validate_pc2()
    
    if args.machine == "all":
        validator.results["cross_machine"] = validator.validate_cross_machine()
    
    # Generate and display report
    report = validator.generate_report()
    print(report)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {args.output}")
    
    # Exit with appropriate code
    total_issues = 0
    for machine_data in validator.results.values():
        if isinstance(machine_data, dict):
            if "services" in machine_data:
                for health in machine_data["services"].values():
                    if health.get("status") != "healthy":
                        total_issues += 1
    
    sys.exit(0 if total_issues == 0 else 1)

if __name__ == "__main__":
    main() 