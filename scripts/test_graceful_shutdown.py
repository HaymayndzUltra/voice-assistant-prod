#!/usr/bin/env python3
"""
WP-03 Graceful Shutdown Test Script
Tests graceful shutdown functionality across all agents
"""

import os
import signal
import time
import subprocess
import threading
from pathlib import Path

def test_agent_graceful_shutdown(agent_module: str, timeout: int = 30) -> bool:
    """Test graceful shutdown for a specific agent"""
    try:
        print(f"🧪 Testing graceful shutdown for {agent_module}...")
        
        # Start the agent
        process = subprocess.Popen(
            ['python', '-m', agent_module],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path.cwd()
        )
        
        # Give it time to start
        time.sleep(5)
        
        if process.poll() is not None:
            print(f"❌ {agent_module} failed to start")
            return False
        
        # Send SIGTERM for graceful shutdown
        print(f"📡 Sending SIGTERM to {agent_module}...")
        process.send_signal(signal.SIGTERM)
        
        # Wait for graceful shutdown
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            if process.returncode == 0:
                print(f"✅ {agent_module} shut down gracefully")
                return True
            else:
                print(f"⚠️  {agent_module} shut down with code {process.returncode}")
                if stderr:
                    print(f"   Error: {stderr.decode()[:200]}...")
                return False
        
        except subprocess.TimeoutExpired:
            print(f"❌ {agent_module} did not respond to SIGTERM within {timeout}s")
            process.kill()
            return False
    
    except Exception as e:
        print(f"❌ Error testing {agent_module}: {e}")
        return False

def test_all_agents():
    """Test graceful shutdown for all known agents"""
    agent_modules = [
        'main_pc_code.agents.service_registry_agent',
        'main_pc_code.agents.system_digital_twin',
        'main_pc_code.agents.request_coordinator',
        'main_pc_code.11',  # ModelManagerSuite
        'main_pc_code.agents.streaming_interrupt_handler',
        'main_pc_code.agents.model_orchestrator',
        'pc2_code.agents.advanced_router',
        'phase0_implementation.group_01_core_observability.observability_hub.observability_hub'
    ]
    
    print("🚀 WP-03 Graceful Shutdown Test Suite")
    print("=" * 50)
    
    results = {}
    for agent_module in agent_modules:
        results[agent_module] = test_agent_graceful_shutdown(agent_module)
    
    # Summary
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"
📊 Test Results: {passed}/{total} agents passed graceful shutdown test")
    
    if passed == total:
        print("🎉 All agents support graceful shutdown!")
    else:
        print("⚠️  Some agents need graceful shutdown improvements:")
        for agent, result in results.items():
            if not result:
                print(f"  ❌ {agent}")

if __name__ == "__main__":
    test_all_agents()
