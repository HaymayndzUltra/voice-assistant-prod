#!/usr/bin/env python3
"""
PRACTICAL CURRENT SYSTEM ANALYSIS
=================================
Focus on what's actually running and accessible RIGHT NOW
"""

import subprocess
import json
import yaml
import requests
from pathlib import Path
import socket
from datetime import datetime

class PracticalSystemAnalyzer:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "live_services": [],
            "accessible_ports": [],
            "active_configs": {},
            "real_blind_spots": [],
            "actionable_fixes": []
        }
    
    def analyze_current_state(self):
        """Analyze what's actually running RIGHT NOW"""
        print("🔍 ANALYZING CURRENT LIVE SYSTEM STATE...")
        
        # 1. Check what's actually running
        self.check_live_services()
        
        # 2. Test real accessibility
        self.test_accessible_endpoints()
        
        # 3. Validate current configs
        self.validate_current_configs()
        
        # 4. Find REAL gaps
        self.identify_real_gaps()
        
        return self.results
    
    def check_live_services(self):
        """Check what services are actually running"""
        print("🟢 Checking Live Services...")
        
        live_services = []
        
        # Check common AI service ports
        common_ports = [
            (5596, "Translation Proxy"),
            (7155, "GPU Scheduler"), 
            (8155, "GPU Scheduler Health"),
            (9000, "MainPC ObservabilityHub"),
            (9100, "PC2 ObservabilityHub"),
            (5600, "ZMQ Bridge"),
            (7220, "SystemDigitalTwin"),
            (8000, "Prometheus Metrics")
        ]
        
        for port, service_name in common_ports:
            if self.is_port_open('localhost', port):
                live_services.append({
                    "service": service_name,
                    "port": port,
                    "status": "RUNNING",
                    "accessible": True
                })
        
        # Check Docker containers
        try:
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        container = json.loads(line)
                        live_services.append({
                            "service": container.get('Names', 'Unknown'),
                            "type": "docker_container",
                            "status": container.get('State', 'Unknown'),
                            "image": container.get('Image', 'Unknown')
                        })
        except:
            live_services.append({
                "service": "Docker",
                "status": "NOT_ACCESSIBLE", 
                "note": "Docker commands not available"
            })
        
        self.results["live_services"] = live_services
    
    def test_accessible_endpoints(self):
        """Test which endpoints are actually accessible"""
        print("🌐 Testing Accessible Endpoints...")
        
        endpoints_to_test = [
            ("http://localhost:8000/health", "GPU Scheduler Health"),
            ("http://localhost:6596/health", "Translation Proxy Health"),
            ("http://localhost:9000/metrics", "MainPC Metrics"),
            ("http://localhost:9100/metrics", "PC2 Metrics"),
            ("http://localhost:7220/health", "SystemDigitalTwin"),
        ]
        
        accessible = []
        for url, name in endpoints_to_test:
            try:
                response = requests.get(url, timeout=3)
                accessible.append({
                    "endpoint": url,
                    "name": name,
                    "status": response.status_code,
                    "accessible": True,
                    "response_size": len(response.text) if response.text else 0
                })
            except Exception as e:
                accessible.append({
                    "endpoint": url,
                    "name": name,
                    "accessible": False,
                    "error": str(e)
                })
        
        self.results["accessible_ports"] = accessible
    
    def validate_current_configs(self):
        """Check which config files exist and are valid"""
        print("⚙️ Validating Current Configs...")
        
        config_files = [
            "main_pc_code/config/startup_config.yaml",
            "pc2_code/config/startup_config.yaml", 
            "services/cross_gpu_scheduler/requirements.txt",
            "services/streaming_translation_proxy/requirements.txt"
        ]
        
        configs = {}
        for config_path in config_files:
            path = Path(config_path)
            if path.exists():
                try:
                    if path.suffix == '.yaml':
                        with open(path) as f:
                            data = yaml.safe_load(f)
                        configs[config_path] = {
                            "exists": True,
                            "valid": True,
                            "size": len(str(data)),
                            "type": "yaml"
                        }
                    else:
                        configs[config_path] = {
                            "exists": True,
                            "valid": True,
                            "size": path.stat().st_size,
                            "type": "text"
                        }
                except Exception as e:
                    configs[config_path] = {
                        "exists": True,
                        "valid": False,
                        "error": str(e)
                    }
            else:
                configs[config_path] = {"exists": False}
        
        self.results["active_configs"] = configs
    
    def identify_real_gaps(self):
        """Identify REAL gaps based on current state"""
        print("🎯 Identifying Real Gaps...")
        
        real_gaps = []
        
        # Gap 1: Check if GPU Scheduler is actually working
        gpu_scheduler_running = any(
            service.get("port") == 7155 and service.get("status") == "RUNNING" 
            for service in self.results["live_services"]
        )
        
        if not gpu_scheduler_running:
            real_gaps.append({
                "gap": "GPU Scheduler Not Running",
                "impact": "HIGH",
                "description": "Cross-GPU coordination service not active",
                "fix_command": "cd services/cross_gpu_scheduler && python3 app.py"
            })
        
        # Gap 2: Check if Translation Proxy is working
        translation_proxy_accessible = any(
            endpoint.get("name") == "Translation Proxy Health" and endpoint.get("accessible")
            for endpoint in self.results["accessible_ports"]
        )
        
        if not translation_proxy_accessible:
            real_gaps.append({
                "gap": "Translation Proxy Not Accessible",
                "impact": "MEDIUM", 
                "description": "Real-time translation service not responding",
                "fix_command": "cd services/streaming_translation_proxy && uvicorn proxy:app --host 0.0.0.0 --port 5596"
            })
        
        # Gap 3: Check observability coverage
        mainpc_metrics = any(
            endpoint.get("name") == "MainPC Metrics" and endpoint.get("accessible")
            for endpoint in self.results["accessible_ports"]
        )
        
        pc2_metrics = any(
            endpoint.get("name") == "PC2 Metrics" and endpoint.get("accessible")
            for endpoint in self.results["accessible_ports"]
        )
        
        if not mainpc_metrics or not pc2_metrics:
            real_gaps.append({
                "gap": "Observability Coverage Incomplete",
                "impact": "MEDIUM",
                "description": f"MainPC metrics: {mainpc_metrics}, PC2 metrics: {pc2_metrics}",
                "fix_command": "Check ObservabilityHub deployment and health checks"
            })
        
        self.results["real_blind_spots"] = real_gaps
    
    def generate_actionable_fixes(self):
        """Generate immediate actionable fixes"""
        fixes = []
        
        for gap in self.results["real_blind_spots"]:
            if gap["impact"] == "HIGH":
                fixes.append({
                    "priority": 1,
                    "action": f"Fix {gap['gap']}",
                    "command": gap["fix_command"],
                    "timeline": "Execute immediately"
                })
            elif gap["impact"] == "MEDIUM":
                fixes.append({
                    "priority": 2, 
                    "action": f"Address {gap['gap']}",
                    "command": gap["fix_command"],
                    "timeline": "Execute within 24 hours"
                })
        
        # Add verification commands
        fixes.append({
            "priority": 0,
            "action": "Verify Current State",
            "command": "python3 PRACTICAL_CURRENT_ANALYSIS.py",
            "timeline": "Run now to re-check"
        })
        
        self.results["actionable_fixes"] = fixes
        return fixes
    
    def is_port_open(self, host, port):
        """Check if a port is open"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                return result == 0
        except:
            return False
    
    def save_results(self, filename="current_system_state.json"):
        """Save results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✅ Current state saved to {filename}")

def main():
    analyzer = PracticalSystemAnalyzer()
    results = analyzer.analyze_current_state()
    
    print(f"\n🔍 CURRENT SYSTEM STATE ANALYSIS")
    print(f"📊 Live Services Found: {len(results['live_services'])}")
    print(f"🌐 Accessible Endpoints: {sum(1 for e in results['accessible_ports'] if e.get('accessible'))}/{len(results['accessible_ports'])}")
    print(f"🎯 Real Gaps Identified: {len(results['real_blind_spots'])}")
    
    print("\n📋 LIVE SERVICES:")
    for service in results['live_services'][:5]:  # Show first 5
        status = service.get('status', 'Unknown')
        name = service.get('service', 'Unknown')
        print(f"   • {name}: {status}")
    
    print("\n🎯 REAL GAPS:")
    for gap in results['real_blind_spots']:
        impact = gap['impact']
        description = gap['description']
        print(f"   • {impact}: {description}")
    
    # Generate and show actionable fixes
    fixes = analyzer.generate_actionable_fixes()
    print("\n⚡ IMMEDIATE ACTIONS:")
    for fix in sorted(fixes, key=lambda x: x['priority'])[:3]:
        print(f"   {fix['priority']}. {fix['action']}")
        print(f"      Command: {fix['command']}")
    
    analyzer.save_results()
    
    print("\n🚀 NEXT STEPS:")
    print("1. Run the immediate action commands above")
    print("2. Re-run this script to verify fixes")
    print("3. Focus on HIGH impact gaps first")

if __name__ == "__main__":
    main()