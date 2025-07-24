#!/usr/bin/env python3
"""
Enhance Central ObservabilityHub (MainPC Port 9000)
Phase 1 Week 3 Day 2 - Distributed Architecture Enhancement
"""

import sys
import os
import time
import subprocess
import requests
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

def enhance_central_hub():
    """Enhance Central Hub on MainPC (Port 9000) with distributed capabilities"""
    print("🚀 ENHANCING CENTRAL OBSERVABILITYHUB (MAINPC PORT 9000)")
    print("=" * 65)
    
    try:
        # Check if we're on MainPC
        main_config_path = Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"
        if not main_config_path.exists():
            print("❌ MainPC startup config not found. Are you running on MainPC?")
            return False
        
        # Set environment variables for MainPC
        os.environ.pop('PC2_MODE', None)  # Ensure PC2 mode is disabled
        os.environ['MACHINE_TYPE'] = 'mainpc'
        os.environ['ENABLE_PROMETHEUS_METRICS'] = 'true'
        
        print("✅ Environment configured for MainPC")
        
        # Check for existing ObservabilityHub process
        print("🔍 Checking for existing ObservabilityHub...")
        try:
            response = requests.get("http://localhost:9000/health", timeout=2)
            if response.status_code == 200:
                print("⚠️  Existing ObservabilityHub detected on port 9000")
                print("🔄 This will be replaced with Enhanced version...")
                # Note: In production, we might want to gracefully shut down the old version
        except:
            print("✅ No existing ObservabilityHub detected")
        
        # Import and start Enhanced Central Hub
        enhanced_hub_path = Path(PathManager.get_project_root()) / "phase1_implementation" / "consolidated_agents" / "observability_hub" / "enhanced_observability_hub.py"
        
        if not enhanced_hub_path.exists():
            print(f"❌ Enhanced ObservabilityHub not found: {enhanced_hub_path}")
            return False
        
        print("✅ Enhanced ObservabilityHub found")
        
        # Update configuration for distributed mode
        _update_central_hub_config()
        
        # Start Enhanced Central Hub process
        print("🔄 Starting Enhanced Central Hub on port 9000...")
        
        cmd = [
            sys.executable,
            str(enhanced_hub_path),
            "--role", "central_hub",
            "--port", "9000",
            "--host", "0.0.0.0"
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            cwd=str(PathManager.get_project_root()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"✅ Enhanced Central Hub started with PID: {process.pid}")
        
        # Wait for startup
        print("⏳ Waiting for Enhanced Central Hub to initialize...")
        time.sleep(15)  # Central hub needs more time for agent discovery
        
        # Test connection and enhanced features
        try:
            response = requests.get("http://localhost:9000/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Enhanced Central Hub health check successful!")
                print(f"   Role: {health_data.get('role', 'unknown')}")
                print(f"   Environment: {health_data.get('environment', 'unknown')}")
                print(f"   Monitored Agents: {health_data.get('monitored_agents', 0)}")
                print(f"   Peer Hub Status: {health_data.get('peer_hub_status', 'unknown')}")
                print(f"   Failover Active: {health_data.get('failover_active', False)}")
                
                # Test enhanced endpoints
                _test_enhanced_endpoints()
                
                print("\n🎯 ENHANCED CENTRAL HUB DEPLOYMENT SUCCESSFUL!")
                print(f"   Central Hub URL: http://localhost:9000")
                print(f"   Health Check: http://localhost:9000/health")
                print(f"   Metrics: http://localhost:9000/metrics")
                print(f"   Agents API: http://localhost:9000/api/v1/agents")
                print(f"   Status API: http://localhost:9000/api/v1/status")
                print(f"   Process PID: {process.pid}")
                
                # Keep running until interrupted
                print("\n💡 Enhanced Central Hub is running. Press Ctrl+C to stop.")
                try:
                    process.wait()
                except KeyboardInterrupt:
                    print("\n🛑 Shutting down Enhanced Central Hub...")
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    print("✅ Enhanced Central Hub stopped")
                
                return True
                
            else:
                print(f"❌ Enhanced Central Hub health check failed: {response.status_code}")
                process.terminate()
                return False
                
        except Exception as e:
            print(f"❌ Enhanced Central Hub connection test failed: {e}")
            
            # Check process status and logs
            if process.poll() is None:
                print("🔄 Process still running, checking logs...")
                try:
                    stdout, stderr = process.communicate(timeout=5)
                    if stdout:
                        print("STDOUT:", stdout)
                    if stderr:
                        print("STDERR:", stderr)
                except subprocess.TimeoutExpired:
                    print("⚠️  Process still running but not responding")
                
                process.terminate()
            
            return False
            
    except Exception as e:
        print(f"❌ Enhanced Central Hub deployment failed: {e}")
        return False

def _update_central_hub_config():
    """Update MainPC configuration for distributed ObservabilityHub"""
    print("🔧 Updating Central Hub configuration for distributed mode...")
    
    try:
        config_path = Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"
        
        if not config_path.exists():
            print("⚠️  MainPC config not found, using defaults")
            return
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Update ObservabilityHub configuration
        agent_groups = config_data.setdefault('agent_groups', {})
        
        # Find or create observability group
        obs_group = None
        for group_name, group_data in agent_groups.items():
            if 'ObservabilityHub' in group_data.get('agents', {}):
                obs_group = group_data
                break
        
        if not obs_group:
            # Create new observability group
            agent_groups['observability_services'] = {
                'agents': {
                    'ObservabilityHub': {}
                }
            }
            obs_group = agent_groups['observability_services']
        
        # Update ObservabilityHub config
        obs_hub_config = obs_group['agents'].setdefault('ObservabilityHub', {})
        obs_hub_config.update({
            'port': 9000,
            'host': '0.0.0.0',
            'health_check_port': 9001,
            'config': {
                'prometheus_enabled': True,
                'cross_machine_sync': True,
                'peer_hub_endpoint': 'http://192.168.1.2:9100',  # PC2 Edge Hub
                'role': 'central_hub',
                'environment': 'mainpc',
                'parallel_health_checks': True,
                'prediction_enabled': True,
                'enable_failover': True
            }
        })
        
        # Write updated config (backup original first)
        backup_path = config_path.with_suffix('.yaml.backup')
        if not backup_path.exists():
            with open(backup_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            print(f"✅ Configuration backup created: {backup_path}")
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False)
        
        print("✅ Central Hub configuration updated for distributed mode")
        
    except Exception as e:
        print(f"⚠️  Error updating config: {e}")

def _test_enhanced_endpoints():
    """Test enhanced Central Hub endpoints"""
    print("\n🧪 Testing Enhanced Central Hub endpoints...")
    
    endpoints = [
        ("Metrics", "http://localhost:9000/metrics"),
        ("Agents API", "http://localhost:9000/api/v1/agents"),
        ("Status API", "http://localhost:9000/api/v1/status")
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {name}: OK")
                
                if "status" in url:
                    # Show status details
                    status_data = response.json()
                    hub_info = status_data.get('hub_info', {})
                    peer_info = status_data.get('peer_coordination', {})
                    print(f"      Hub Role: {hub_info.get('role', 'unknown')}")
                    print(f"      Peer Status: {peer_info.get('peer_status', 'unknown')}")
                    print(f"      Failover: {peer_info.get('failover_active', False)}")
                
                elif "agents" in url:
                    # Show agent count
                    agents_data = response.json()
                    agent_count = agents_data.get('total_agents', 0)
                    print(f"      Discovered Agents: {agent_count}")
                    
            else:
                print(f"   ❌ {name}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {name}: {e}")

def validate_central_hub():
    """Validate Enhanced Central Hub deployment"""
    print("\n🧪 VALIDATING ENHANCED CENTRAL HUB DEPLOYMENT")
    print("=" * 50)
    
    tests = [
        ("Health Endpoint", "http://localhost:9000/health"),
        ("Metrics Endpoint", "http://localhost:9000/metrics"),
        ("Agents API", "http://localhost:9000/api/v1/agents"),
        ("Status API", "http://localhost:9000/api/v1/status")
    ]
    
    results = {}
    
    for test_name, url in tests:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {test_name}: OK")
                results[test_name] = True
                
                # Additional validation for specific endpoints
                if "health" in url:
                    health_data = response.json()
                    if health_data.get('role') == 'central_hub':
                        print(f"   ✅ Role validation: {health_data.get('role')}")
                    else:
                        print(f"   ⚠️  Unexpected role: {health_data.get('role')}")
                
            else:
                print(f"❌ {test_name}: HTTP {response.status_code}")
                results[test_name] = False
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            results[test_name] = False
    
    success_rate = sum(results.values()) / len(results) * 100
    print(f"\n📊 VALIDATION RESULTS: {success_rate:.1f}% ({sum(results.values())}/{len(results)} tests passed)")
    
    return success_rate >= 75

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance Central ObservabilityHub")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation tests")
    parser.add_argument("--config-only", action="store_true", help="Only update configuration")
    
    args = parser.parse_args()
    
    if args.validate_only:
        success = validate_central_hub()
    elif args.config_only:
        _update_central_hub_config()
        success = True
    else:
        success = enhance_central_hub()
    
    sys.exit(0 if success else 1) 