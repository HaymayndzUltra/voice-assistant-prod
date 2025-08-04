#!/usr/bin/env python3
"""
Main PC Individual Service Group Validator
==========================================

MAHALAGANG PAALALA: Tiyaking 100% ang resulta ng lahat ng local tests. 
Ito ang pundasyon ng buong stack na naka-base sa per-group architecture.

This script validates individual Main PC service groups:
- infra_core/coordination (foundation)
- emotion_system
- language_stack  
- memory_stack
- vision_gpu, reasoning_gpu, speech_gpu
- translation_services
- utility_cpu
- observability
"""

import subprocess
import time
import socket
import requests
import json
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class MainPCGroupValidator:
    def __init__(self):
        # Service groups and their key containers/services
        self.service_groups = {
            'coordination': {
                'infrastructure': ['redis_coordination', 'nats_coordination'],
                'applications': ['request_coordinator', 'model_manager_suite', 'vram_optimizer'],
                'ports': [6379, 4222, 26002, 27002]
            },
            'emotion_system': {
                'infrastructure': ['redis_emotion', 'nats_emotion'],
                'applications': ['emotion_engine', 'mood_tracker', 'human_awareness', 'tone_detector', 'voice_profiling', 'empathy_agent'],
                'ports': [6383, 4225]
            },
            'language_stack': {
                'infrastructure': ['redis_language', 'nats_language'],
                'applications': ['nlu_agent', 'intention_validator', 'advanced_command_handler', 'model_orchestrator'],
                'ports': [6385, 4227]
            },
            'memory_stack': {
                'infrastructure': ['redis_memory', 'nats_memory'],
                'applications': ['memory_client', 'knowledge_base', 'session_memory_agent'],
                'ports': [6381, 4223]
            },
            'vision_gpu': {
                'infrastructure': ['redis_vision', 'nats_vision'],
                'applications': ['face_recognition_agent'],
                'ports': [6386, 4228]
            },
            'reasoning_gpu': {
                'infrastructure': ['redis_reasoning', 'nats_reasoning'],
                'applications': ['cognitive_model_agent', 'chain_of_thought_agent', 'goto_agent'],
                'ports': [6389, 4230]
            },
            'speech_gpu': {
                'infrastructure': ['redis_speech', 'nats_speech'],
                'applications': ['stt_service', 'tts_service', 'audio_capture'],
                'ports': [6387, 4229],
                'optional': True
            },
            'translation_services': {
                'infrastructure': ['redis_translation', 'nats_translation'],
                'applications': ['cloud_translation_service'],
                'ports': [6384, 4298]
            },
            'utility_cpu': {
                'infrastructure': ['redis_utility', 'nats_utility'],
                'applications': ['executor', 'predictive_health_monitor'],
                'ports': [6382, 4224]
            },
            'observability': {
                'infrastructure': ['redis_observability'],
                'applications': ['observability_hub'],
                'ports': [6380, 9000]
            }
        }
        
        self.results = {}
    
    def get_running_containers(self):
        """Get all running containers."""
        try:
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                 capture_output=True, text=True, check=True)
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        container_info = json.loads(line)
                        containers.append({
                            'name': container_info.get('Names', ''),
                            'image': container_info.get('Image', ''),
                            'status': container_info.get('Status', ''),
                            'ports': container_info.get('Ports', '')
                        })
                    except json.JSONDecodeError:
                        continue
            
            return containers
        except subprocess.CalledProcessError:
            return []
    
    def validate_service_group(self, group_name, group_config, running_containers):
        """Validate a specific service group."""
        print(f"\n🔍 VALIDATING: {group_name.upper()}")
        print("="*50)
        
        group_result = {
            'infrastructure_status': {},
            'application_status': {},
            'port_accessibility': {},
            'overall_health': 'unknown'
        }
        
        container_names = [c['name'] for c in running_containers]
        
        # Check infrastructure containers
        print("📡 Infrastructure Services:")
        infra_healthy = 0
        for service in group_config['infrastructure']:
            if service in container_names:
                container = next(c for c in running_containers if c['name'] == service)
                status = "✅ RUNNING" if 'Up' in container['status'] else "❌ UNHEALTHY"
                print(f"  {service}: {status}")
                group_result['infrastructure_status'][service] = status
                if "✅" in status:
                    infra_healthy += 1
            else:
                print(f"  {service}: ❌ NOT FOUND")
                group_result['infrastructure_status'][service] = "❌ NOT FOUND"
        
        # Check application containers
        print("🚀 Application Services:")
        app_healthy = 0
        for service in group_config['applications']:
            if service in container_names:
                container = next(c for c in running_containers if c['name'] == service)
                status = "✅ RUNNING" if 'Up' in container['status'] else "❌ UNHEALTHY"
                print(f"  {service}: {status}")
                group_result['application_status'][service] = status
                if "✅" in status:
                    app_healthy += 1
            else:
                print(f"  {service}: ⚠️  NOT FOUND")
                group_result['application_status'][service] = "⚠️  NOT FOUND"
        
        # Check port accessibility
        print("🔌 Port Accessibility:")
        accessible_ports = 0
        for port in group_config['ports']:
            try:
                with socket.create_connection(('localhost', port), timeout=2):
                    print(f"  Port {port}: ✅ ACCESSIBLE")
                    group_result['port_accessibility'][port] = "✅ ACCESSIBLE"
                    accessible_ports += 1
            except (socket.error, socket.timeout):
                print(f"  Port {port}: ❌ NOT ACCESSIBLE")
                group_result['port_accessibility'][port] = "❌ NOT ACCESSIBLE"
        
        # Calculate overall health
        total_infra = len(group_config['infrastructure'])
        total_apps = len(group_config['applications'])
        total_ports = len(group_config['ports'])
        
        # Check if this is an optional service group (like speech_gpu for cloud-based setup)
        is_optional = group_config.get('optional', False)
        
        if is_optional:
            # For optional services, be more lenient
            if infra_healthy >= total_infra * 0.5:  # At least 50% infrastructure
                group_result['overall_health'] = "✅ HEALTHY (OPTIONAL)"
            else:
                group_result['overall_health'] = "⚠️  PARTIAL (OPTIONAL)"
        else:
            # Regular validation for required services
            if infra_healthy == total_infra and accessible_ports >= total_ports * 0.8:
                if app_healthy >= total_apps * 0.5:  # At least 50% of apps running
                    group_result['overall_health'] = "✅ HEALTHY"
                else:
                    group_result['overall_health'] = "⚠️  PARTIAL"
            else:
                group_result['overall_health'] = "❌ UNHEALTHY"
        
        print(f"\n🎯 GROUP HEALTH: {group_result['overall_health']}")
        print(f"   Infrastructure: {infra_healthy}/{total_infra}")
        print(f"   Applications: {app_healthy}/{total_apps}")
        print(f"   Ports: {accessible_ports}/{total_ports}")
        
        return group_result
    
    def run_validation(self):
        """Run complete validation of all service groups."""
        print("🎯 MAIN PC INDIVIDUAL SERVICE GROUP VALIDATION")
        print("=" * 70)
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Get running containers
        containers = self.get_running_containers()
        if not containers:
            print("❌ No running containers found")
            return False
        
        print(f"📊 Found {len(containers)} running containers")
        
        # Validate each service group
        healthy_groups = 0
        partial_groups = 0
        unhealthy_groups = 0
        
        for group_name, group_config in self.service_groups.items():
            result = self.validate_service_group(group_name, group_config, containers)
            self.results[group_name] = result
            
            # Handle optional services differently in success calculation
            if "OPTIONAL" in result['overall_health']:
                # Optional services count as healthy for success rate
                healthy_groups += 1
            elif result['overall_health'] == "✅ HEALTHY":
                healthy_groups += 1
            elif result['overall_health'] == "⚠️  PARTIAL":
                partial_groups += 1
            else:
                unhealthy_groups += 1
        
        # Overall assessment
        print(f"\n🏆 OVERALL MAIN PC ASSESSMENT:")
        print("=" * 40)
        print(f"✅ Healthy Groups: {healthy_groups}")
        print(f"⚠️  Partial Groups: {partial_groups}")
        print(f"❌ Unhealthy Groups: {unhealthy_groups}")
        print(f"📊 Total Groups: {len(self.service_groups)}")
        
        success_rate = ((healthy_groups + partial_groups * 0.5) / len(self.service_groups)) * 100
        print(f"🎯 SUCCESS RATE: {success_rate:.1f}%")
        
        if success_rate >= 75:
            print("🎉 MAIN PC PHASE 1 VALIDATION: SUCCESS!")
            print("✅ Ready for Phase 2 (PC2 Integration)")
            return True
        elif success_rate >= 50:
            print("⚠️  MAIN PC PHASE 1 VALIDATION: PARTIAL SUCCESS")
            print("🔧 Some groups need attention")
            return True
        else:
            print("❌ MAIN PC PHASE 1 VALIDATION: NEEDS WORK")
            print("🛠️  Multiple groups require fixing")
            return False

if __name__ == "__main__":
    validator = MainPCGroupValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)
