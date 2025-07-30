#!/usr/bin/env python3
"""
Docker Setup Validation Script
Validates the dual-hub Docker architecture for MainPC-PC2 communication
"""

import sys
import subprocess
import requests
import time
import json
from pathlib import Path

class DockerValidator:
    def __init__(self):
        self.results = {
            'docker': False,
            'docker_compose': False,
            'nvidia_runtime': False,
            'network_connectivity': False,
            'mainpc_services': {},
            'pc2_services': {},
            'cross_machine_communication': False,
            'observability_sync': False
        }
    
    def check_prerequisites(self):
        """Check Docker prerequisites"""
        print("🔍 Checking prerequisites...")
        
        # Check Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Docker installed:", result.stdout.strip())
                self.results['docker'] = True
            else:
                print("❌ Docker not found")
        except FileNotFoundError:
            print("❌ Docker command not found")
        
        # Check Docker Compose
        try:
            result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Docker Compose installed:", result.stdout.strip())
                self.results['docker_compose'] = True
            else:
                print("❌ Docker Compose not found")
        except FileNotFoundError:
            print("❌ Docker Compose command not found")
        
        # Check NVIDIA Docker runtime
        try:
            result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
            if 'nvidia' in result.stdout.lower():
                print("✅ NVIDIA Docker runtime detected")
                self.results['nvidia_runtime'] = True
            else:
                print("⚠️  NVIDIA Docker runtime not detected")
        except:
            print("⚠️  Could not check NVIDIA runtime")
    
    def check_network_connectivity(self):
        """Check network connectivity between machines"""
        print("\n🌐 Checking network connectivity...")
        
        mainpc_ip = "192.168.100.16"
        pc2_ip = "192.168.100.17"
        
        # Test ping connectivity
        try:
            result = subprocess.run(['ping', '-c', '1', mainpc_ip], capture_output=True)
            if result.returncode == 0:
                print(f"✅ MainPC ({mainpc_ip}) is reachable")
                self.results['network_connectivity'] = True
            else:
                print(f"❌ MainPC ({mainpc_ip}) is not reachable")
        except:
            print(f"❌ Could not test connectivity to MainPC")
        
        try:
            result = subprocess.run(['ping', '-c', '1', pc2_ip], capture_output=True)
            if result.returncode == 0:
                print(f"✅ PC2 ({pc2_ip}) is reachable")
            else:
                print(f"❌ PC2 ({pc2_ip}) is not reachable")
        except:
            print(f"❌ Could not test connectivity to PC2")
    
    def check_docker_services(self, machine_type):
        """Check Docker services for a specific machine"""
        print(f"\n🐳 Checking {machine_type.upper()} Docker services...")
        
        if machine_type == 'mainpc':
            services = [
                'mainpc-redis',
                'mainpc-observability-hub', 
                'mainpc-service-registry',
                'mainpc-system-digital-twin'
            ]
        else:  # pc2
            services = [
                'pc2-redis',
                'pc2-observability-hub',
                'pc2-resource-manager',
                'pc2-memory-orchestrator'
            ]
        
        for service in services:
            try:
                result = subprocess.run(
                    ['docker', 'ps', '--filter', f'name={service}', '--filter', 'status=running'],
                    capture_output=True, text=True
                )
                if service in result.stdout:
                    print(f"✅ {service}: Running")
                    self.results[f'{machine_type}_services'][service] = True
                else:
                    print(f"❌ {service}: Not running")
                    self.results[f'{machine_type}_services'][service] = False
            except:
                print(f"❌ Could not check {service}")
                self.results[f'{machine_type}_services'][service] = False
    
    def check_observability_endpoints(self):
        """Check ObservabilityHub endpoints"""
        print("\n📊 Checking ObservabilityHub endpoints...")
        
        endpoints = [
            ('MainPC Hub', 'http://192.168.100.16:9000/health'),
            ('MainPC Prometheus', 'http://192.168.100.16:9090'),
            ('PC2 Hub', 'http://192.168.100.17:9000/health'),
        ]
        
        for name, url in endpoints:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {name}: Responding")
                    if 'health' in url:
                        try:
                            data = response.json()
                            status = data.get('status', 'unknown')
                            print(f"   Status: {status}")
                        except:
                            pass
                else:
                    print(f"❌ {name}: HTTP {response.status_code}")
            except requests.exceptions.ConnectionError:
                print(f"❌ {name}: Connection refused")
            except requests.exceptions.Timeout:
                print(f"❌ {name}: Timeout")
            except Exception as e:
                print(f"❌ {name}: Error - {e}")
    
    def check_cross_machine_sync(self):
        """Check cross-machine synchronization"""
        print("\n🔗 Checking cross-machine synchronization...")
        
        try:
            # Check if PC2 can reach MainPC hub
            response = requests.get('http://192.168.100.17:9000/health', timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Look for cross-machine sync indicators
                if 'mainpc_hub_endpoint' in str(data) or 'cross_machine_sync' in str(data):
                    print("✅ Cross-machine sync configured")
                    self.results['cross_machine_communication'] = True
                else:
                    print("⚠️  Cross-machine sync configuration not detected")
            
            # Test metrics forwarding
            print("📈 Testing metrics forwarding...")
            time.sleep(2)  # Wait for metrics to sync
            
            mainpc_response = requests.get('http://192.168.100.16:9000/health_summary', timeout=5)
            if mainpc_response.status_code == 200:
                data = mainpc_response.json()
                total_agents = data.get('total_agents', 0)
                if total_agents > 0:
                    print(f"✅ MainPC monitoring {total_agents} agents (including PC2)")
                    self.results['observability_sync'] = True
                else:
                    print("⚠️  No agents detected in MainPC monitoring")
            
        except Exception as e:
            print(f"❌ Cross-machine sync check failed: {e}")
    
    def validate_docker_paths(self):
        """Validate Docker path utilities"""
        print("\n📂 Validating Docker path utilities...")
        
        try:
            # Test docker_paths module
            sys.path.insert(0, str(Path.cwd()))
            from common.utils.docker_paths import get_logs_dir, get_data_dir, is_docker_environment
            
            print("✅ docker_paths module imported successfully")
            print(f"   Docker environment: {is_docker_environment()}")
            print(f"   Logs dir: {get_logs_dir()}")
            print(f"   Data dir: {get_data_dir()}")
            
        except Exception as e:
            print(f"❌ Docker paths validation failed: {e}")
    
    def generate_report(self):
        """Generate validation report"""
        print("\n" + "="*60)
        print("📋 VALIDATION REPORT")
        print("="*60)
        
        total_checks = 0
        passed_checks = 0
        
        # Prerequisites
        print("\n🔧 Prerequisites:")
        for check in ['docker', 'docker_compose', 'nvidia_runtime']:
            status = "✅ PASS" if self.results[check] else "❌ FAIL"
            print(f"  {check}: {status}")
            total_checks += 1
            if self.results[check]:
                passed_checks += 1
        
        # Network
        print("\n🌐 Network:")
        status = "✅ PASS" if self.results['network_connectivity'] else "❌ FAIL"
        print(f"  connectivity: {status}")
        total_checks += 1
        if self.results['network_connectivity']:
            passed_checks += 1
        
        # Services
        for machine in ['mainpc', 'pc2']:
            print(f"\n🐳 {machine.upper()} Services:")
            services = self.results[f'{machine}_services']
            for service, status in services.items():
                status_str = "✅ PASS" if status else "❌ FAIL"
                print(f"  {service}: {status_str}")
                total_checks += 1
                if status:
                    passed_checks += 1
        
        # Cross-machine communication
        print("\n🔗 Cross-machine Communication:")
        status = "✅ PASS" if self.results['cross_machine_communication'] else "❌ FAIL"
        print(f"  sync: {status}")
        total_checks += 1
        if self.results['cross_machine_communication']:
            passed_checks += 1
        
        # Summary
        print(f"\n📊 SUMMARY: {passed_checks}/{total_checks} checks passed")
        success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 DUAL-HUB ARCHITECTURE VALIDATION: SUCCESS!")
        elif success_rate >= 60:
            print("⚠️  DUAL-HUB ARCHITECTURE VALIDATION: PARTIAL SUCCESS")
        else:
            print("❌ DUAL-HUB ARCHITECTURE VALIDATION: NEEDS ATTENTION")
        
        return success_rate

def main():
    print("🚀 Docker Dual-Hub Architecture Validator")
    print("==========================================")
    
    validator = DockerValidator()
    
    validator.check_prerequisites()
    validator.check_network_connectivity() 
    validator.check_docker_services('mainpc')
    validator.check_docker_services('pc2')
    validator.check_observability_endpoints()
    validator.check_cross_machine_sync()
    validator.validate_docker_paths()
    
    success_rate = validator.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if success_rate >= 80 else 1)

if __name__ == "__main__":
    main() 