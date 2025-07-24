#!/usr/bin/env python3
"""
PC2 Validation Script
Tests all 5 container groups and their agents for proper functionality
"""

import requests
import time
import json
import yaml
from typing import Dict, List, Tuple

# PC2 Container Groups and their agents
PC2_GROUPS = {
    "memory-services": {
        "container": "pc2-memory-services",
        "agents": [
            {"name": "MemoryOrchestratorService", "port": 7140, "health_port": 8140},
            {"name": "CacheManager", "port": 7102, "health_port": 8102},
            {"name": "UnifiedMemoryReasoningAgent", "port": 7105, "health_port": 8105},
            {"name": "ContextManager", "port": 7111, "health_port": 8111},
            {"name": "ExperienceTracker", "port": 7112, "health_port": 8112},
        ]
    },
    "ai-reasoning": {
        "container": "pc2-ai-reasoning", 
        "agents": [
            {"name": "DreamWorldAgent", "port": 7104, "health_port": 8104},
            {"name": "DreamingModeAgent", "port": 7127, "health_port": 8127},
            {"name": "TutorAgent", "port": 7108, "health_port": 8108},
            {"name": "TutoringAgent", "port": 7131, "health_port": 8131},
            {"name": "VisionProcessingAgent", "port": 7150, "health_port": 8150},
        ]
    },
    "web-services": {
        "container": "pc2-web-services",
        "agents": [
            {"name": "FileSystemAssistantAgent", "port": 7123, "health_port": 8123},
            {"name": "RemoteConnectorAgent", "port": 7124, "health_port": 8124},
            {"name": "UnifiedWebAgent", "port": 7126, "health_port": 8126},
        ]
    },
    "infrastructure": {
        "container": "pc2-infrastructure",
        "agents": [
            {"name": "TieredResponder", "port": 7100, "health_port": 8100},
            {"name": "AsyncProcessor", "port": 7101, "health_port": 8101},
            {"name": "ResourceManager", "port": 7113, "health_port": 8113},
            {"name": "TaskScheduler", "port": 7115, "health_port": 8115},
            {"name": "AdvancedRouter", "port": 7129, "health_port": 8129},
            {"name": "AuthenticationAgent", "port": 7116, "health_port": 8116},
            {"name": "UnifiedUtilsAgent", "port": 7118, "health_port": 8118},
            {"name": "ProactiveContextMonitor", "port": 7119, "health_port": 8119},
            {"name": "AgentTrustScorer", "port": 7122, "health_port": 8122},
        ]
    },
    "observability-hub-forwarder": {
        "container": "pc2-observability-forwarder",
        "agents": [
            {"name": "ObservabilityHub", "port": 9000, "health_port": 9100},
        ]
    }
}

PC2_HOST = "localhost"  # When running from PC2
TIMEOUT = 5  # seconds


def test_agent_health(agent: Dict, group_name: str) -> Tuple[bool, str]:
    """Test individual agent health check"""
    try:
        health_url = f"http://{PC2_HOST}:{agent['health_port']}/health"
        response = requests.get(health_url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok':
                return True, "✅ Healthy"
            else:
                return False, f"❌ Unhealthy: {data.get('message', 'Unknown error')}"
        else:
            return False, f"❌ HTTP {response.status_code}"
            
    except requests.exceptions.ConnectRefused:
        return False, "❌ Connection refused"
    except requests.exceptions.Timeout:
        return False, "❌ Timeout"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def test_group_functionality(group_name: str, group_data: Dict) -> Dict:
    """Test entire container group"""
    print(f"\n🔍 Testing {group_name} group...")
    print("=" * 50)
    
    results = {
        "group": group_name,
        "container": group_data["container"],
        "total_agents": len(group_data["agents"]),
        "healthy_agents": 0,
        "unhealthy_agents": 0,
        "agent_results": []
    }
    
    for agent in group_data["agents"]:
        healthy, status = test_agent_health(agent, group_name)
        
        agent_result = {
            "name": agent["name"],
            "port": agent["port"],
            "health_port": agent["health_port"],
            "healthy": healthy,
            "status": status
        }
        
        results["agent_results"].append(agent_result)
        
        if healthy:
            results["healthy_agents"] += 1
        else:
            results["unhealthy_agents"] += 1
            
        print(f"  {agent['name']:25} (:{agent['port']}) {status}")
    
    success_rate = (results["healthy_agents"] / results["total_agents"]) * 100
    print(f"\n📊 {group_name} Summary: {results['healthy_agents']}/{results['total_agents']} healthy ({success_rate:.1f}%)")
    
    return results


def test_cross_machine_communication():
    """Test PC2 → MainPC communication"""
    print(f"\n🌐 Testing Cross-Machine Communication...")
    print("=" * 50)
    
    # Test ObservabilityHub forwarding
    try:
        pc2_obs_url = f"http://{PC2_HOST}:9000/health"
        response = requests.get(pc2_obs_url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            print("✅ PC2 ObservabilityHub: Accessible")
            
            # Test if it can reach MainPC (this would be configured in the hub)
            data = response.json()
            if data.get('mainpc_connection'):
                print("✅ PC2 → MainPC: Connected")
            else:
                print("⚠️  PC2 → MainPC: Not configured or unreachable")
        else:
            print(f"❌ PC2 ObservabilityHub: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Cross-machine communication: {str(e)}")


def main():
    """Main validation function"""
    print("🧪 PC2 AI System Validation")
    print("============================")
    print(f"Testing 5 container groups with {sum(len(g['agents']) for g in PC2_GROUPS.values())} total agents")
    
    all_results = []
    total_agents = 0
    total_healthy = 0
    
    # Test each container group
    for group_name, group_data in PC2_GROUPS.items():
        results = test_group_functionality(group_name, group_data)
        all_results.append(results)
        
        total_agents += results["total_agents"]
        total_healthy += results["healthy_agents"]
    
    # Test cross-machine communication
    test_cross_machine_communication()
    
    # Final summary
    print(f"\n🎯 FINAL VALIDATION SUMMARY")
    print("=" * 50)
    
    overall_success_rate = (total_healthy / total_agents) * 100
    print(f"📊 Overall Health: {total_healthy}/{total_agents} agents healthy ({overall_success_rate:.1f}%)")
    
    for result in all_results:
        status = "✅" if result["unhealthy_agents"] == 0 else "⚠️" if result["healthy_agents"] > 0 else "❌"
        print(f"{status} {result['group']:25} {result['healthy_agents']}/{result['total_agents']}")
    
    print()
    if overall_success_rate >= 90:
        print("🎉 PC2 AI System: VALIDATION PASSED!")
        print("Ready for production use.")
    elif overall_success_rate >= 75:
        print("⚠️  PC2 AI System: VALIDATION PARTIAL")
        print("Some issues detected, but system is functional.")
    else:
        print("❌ PC2 AI System: VALIDATION FAILED")
        print("Major issues detected, troubleshooting required.")
    
    return overall_success_rate >= 75


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 