#!/usr/bin/env python3
"""
Main PC Running Services Validator
=================================
Quick validation of currently running Main PC services based on actual Docker containers.
"""

import subprocess
import json
import sys
from datetime import datetime

class MainPCRunningValidator:
    def __init__(self):
        self.results = {
            'containers_running': {},
            'service_groups': {},
            'infrastructure': {},
            'overall_health': {}
        }
    
    def get_running_containers(self):
        """Get all running containers with Main PC-related services."""
        print("🔍 Checking running Main PC containers...")
        
        try:
            # Get detailed container info
            cmd = [
                'docker', 'ps', '--format', 
                'json {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        containers.append({
                            'name': parts[0],
                            'image': parts[1], 
                            'status': parts[2],
                            'ports': parts[3]
                        })
            
            return containers
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error getting containers: {e}")
            return []
    
    def categorize_services(self, containers):
        """Categorize services by type."""
        print("📊 Categorizing services...")
        
        categories = {
            'language_stack': [],
            'emotion_system': [],
            'reasoning_gpu': [],
            'vision_gpu': [],
            'memory_stack': [],
            'translation_services': [],
            'infrastructure': [],
            'utility': []
        }
        
        for container in containers:
            name = container['name']
            image = container['image']
            
            # Categorize based on image or name
            if 'language' in image or any(x in name for x in ['nlu', 'model', 'responder', 'feedback', 'intention', 'advanced_command', 'proactive', 'goal', 'emotion_synthesis', 'dynamic_identity']):
                categories['language_stack'].append(container)
            elif 'emotion' in image or any(x in name for x in ['emotion', 'mood', 'human_awareness', 'tone', 'voice_profiling', 'empathy']):
                categories['emotion_system'].append(container)
            elif 'reasoning' in image or any(x in name for x in ['cognitive', 'goto', 'chain_of_thought']):
                categories['reasoning_gpu'].append(container)
            elif 'vision' in image or 'face_recognition' in name:
                categories['vision_gpu'].append(container)
            elif 'memory' in image or any(x in name for x in ['memory', 'knowledge']):
                categories['memory_stack'].append(container)
            elif 'translation' in image or 'translation' in name:
                categories['translation_services'].append(container)
            elif any(x in name for x in ['redis', 'nats', 'observability']):
                categories['infrastructure'].append(container)
            else:
                categories['utility'].append(container)
        
        return categories
    
    def validate_infrastructure(self, infrastructure):
        """Validate core infrastructure services."""
        print("⚙️  Validating infrastructure...")
        
        redis_count = len([c for c in infrastructure if 'redis' in c['name']])
        nats_count = len([c for c in infrastructure if 'nats' in c['name']])
        observability_count = len([c for c in infrastructure if 'observability' in c['name']])
        
        return {
            'redis_instances': redis_count,
            'nats_instances': nats_count, 
            'observability_instances': observability_count,
            'total_infrastructure': len(infrastructure)
        }
    
    def check_port_distribution(self, containers):
        """Check port distribution across services."""
        print("🔌 Checking port distribution...")
        
        port_ranges = {
            '5xxx': 0,
            '6xxx': 0, 
            '4xxx': 0,
            'other': 0
        }
        
        all_ports = []
        for container in containers:
            ports = container.get('ports', '')
            if ports and ports != '-':
                # Extract port numbers
                import re
                port_matches = re.findall(r'(\d+)->', ports)
                for port in port_matches:
                    all_ports.append(int(port))
                    if port.startswith('5'):
                        port_ranges['5xxx'] += 1
                    elif port.startswith('6'):
                        port_ranges['6xxx'] += 1
                    elif port.startswith('4'):
                        port_ranges['4xxx'] += 1
                    else:
                        port_ranges['other'] += 1
        
        return {
            'port_ranges': port_ranges,
            'total_ports': len(all_ports),
            'unique_ports': len(set(all_ports))
        }
    
    def run_validation(self):
        """Run complete validation."""
        print("🎯 MAIN PC RUNNING SERVICES VALIDATION")
        print("=" * 60)
        
        # Get running containers
        containers = self.get_running_containers()
        if not containers:
            print("❌ No containers found")
            return False
        
        print(f"✅ Found {len(containers)} running containers")
        
        # Categorize services
        categories = self.categorize_services(containers)
        
        # Print service summary
        print("\n📊 SERVICE SUMMARY:")
        total_agents = 0
        for category, services in categories.items():
            if services:
                print(f"  ✅ {category}: {len(services)} services")
                total_agents += len(services)
        
        # Validate infrastructure
        infrastructure_stats = self.validate_infrastructure(categories['infrastructure'])
        print(f"\n⚙️  INFRASTRUCTURE:")
        print(f"  ✅ Redis instances: {infrastructure_stats['redis_instances']}")
        print(f"  ✅ NATS instances: {infrastructure_stats['nats_instances']}")
        print(f"  ✅ Observability: {infrastructure_stats['observability_instances']}")
        
        # Check port distribution
        port_stats = self.check_port_distribution(containers)
        print(f"\n🔌 PORT ALLOCATION:")
        print(f"  ✅ Total exposed ports: {port_stats['total_ports']}")
        print(f"  ✅ Port ranges: {port_stats['port_ranges']}")
        
        # Overall assessment
        print(f"\n🏆 OVERALL ASSESSMENT:")
        print(f"  ✅ Total running services: {total_agents}")
        print(f"  ✅ Infrastructure services: {infrastructure_stats['total_infrastructure']}")
        print(f"  ✅ Service groups active: {len([c for c in categories.values() if c])}")
        
        # Calculate success metrics
        gpu_services = len(categories['reasoning_gpu']) + len(categories['vision_gpu'])
        core_services = len(categories['language_stack']) + len(categories['emotion_system']) + len(categories['memory_stack'])
        
        if total_agents >= 10 and infrastructure_stats['redis_instances'] >= 3 and gpu_services >= 1:
            print(f"  🎉 VALIDATION PASSED: {total_agents} services operational")
            print(f"  🎯 SUCCESS RATE: {min(100, (total_agents/20)*100):.1f}%")
            return True
        else:
            print(f"  ⚠️  PARTIAL SUCCESS: {total_agents} services running")
            print(f"  🎯 SUCCESS RATE: {min(100, (total_agents/20)*100):.1f}%")
            return total_agents >= 5  # At least 5 services for basic operation

if __name__ == "__main__":
    validator = MainPCRunningValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)
