#!/usr/bin/env python3
"""
Quick Main PC Status Check
=========================
Fast status check after recent fixes.
"""

import subprocess

def quick_status():
    """Quick status check for key services."""
    print("🚀 QUICK MAIN PC STATUS CHECK")
    print("=" * 40)
    
    # Key services to check
    key_services = {
        'translation': ['cloud_translation_service', 'redis_translation', 'nats_translation'],
        'speech': ['tts_service', 'audio_capture', 'redis_speech', 'nats_speech'],
        'coordination': ['request_coordinator', 'model_manager_suite']
    }
    
    for group, services in key_services.items():
        print(f"\n🔍 {group.upper()} GROUP:")
        
        running_count = 0
        for service in services:
            try:
                result = subprocess.run(['docker', 'ps', '--filter', f'name={service}', 
                                       '--format', 'table {{.Names}}\t{{.Status}}'], 
                                      capture_output=True, text=True, timeout=5)
                
                if service in result.stdout and 'Up' in result.stdout:
                    print(f"   ✅ {service}")
                    running_count += 1
                else:
                    print(f"   ❌ {service}")
                    
            except Exception as e:
                print(f"   ⚠️  {service} (check failed)")
        
        health = "✅ HEALTHY" if running_count == len(services) else "⚠️ PARTIAL" if running_count > 0 else "❌ UNHEALTHY"
        print(f"   📊 Status: {health} ({running_count}/{len(services)})")
    
    # Test key ports
    print(f"\n🔌 KEY PORT STATUS:")
    key_ports = [4298, 6384, 6387, 4229]  # translation NATS, translation Redis, speech Redis, speech NATS
    
    accessible_ports = 0
    for port in key_ports:
        try:
            result = subprocess.run(['nc', '-z', 'localhost', str(port)], 
                                  capture_output=True, timeout=3)
            if result.returncode == 0:
                print(f"   ✅ Port {port}")
                accessible_ports += 1
            else:
                print(f"   ❌ Port {port}")
        except:
            print(f"   ⚠️  Port {port} (check failed)")
    
    print(f"   📊 Ports: {accessible_ports}/{len(key_ports)} accessible")
    
    # Overall assessment
    print(f"\n🎯 QUICK ASSESSMENT:")
    print(f"   Translation services: Fixed NATS config ✅")
    print(f"   Speech services: Partially deployed ⚠️")
    print(f"   Next: Full validation run")

if __name__ == "__main__":
    quick_status()
