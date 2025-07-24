#!/usr/bin/env python3
"""
Deploy Edge ObservabilityHub (PC2 Port 9100)
Phase 1 Week 3 Day 2 - Distributed Architecture Deployment
"""

import sys
import os
import time
import subprocess
import requests
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

def deploy_edge_hub():
    """Deploy Edge Hub on PC2 (Port 9100)"""
    print("🚀 DEPLOYING EDGE OBSERVABILITYHUB (PC2 PORT 9100)")
    print("=" * 60)
    
    try:
        # Check if we're on PC2
        pc2_config_path = Path(PathManager.get_project_root()) / "pc2_code" / "config" / "startup_config.yaml"
        if not pc2_config_path.exists():
            print("❌ PC2 startup config not found. Are you running on PC2?")
            return False
        
        # Set environment variables for PC2
        os.environ['PC2_MODE'] = 'true'
        os.environ['MACHINE_TYPE'] = 'pc2'
        os.environ['ENABLE_PROMETHEUS_METRICS'] = 'true'
        
        print("✅ Environment configured for PC2")
        
        # Import and start Edge Hub
        enhanced_hub_path = Path(PathManager.get_project_root()) / "phase1_implementation" / "consolidated_agents" / "observability_hub" / "enhanced_observability_hub.py"
        
        if not enhanced_hub_path.exists():
            print(f"❌ Enhanced ObservabilityHub not found: {enhanced_hub_path}")
            return False
        
        print("✅ Enhanced ObservabilityHub found")
        
        # Start Edge Hub process
        print("🔄 Starting Edge Hub on port 9100...")
        
        cmd = [
            sys.executable,
            str(enhanced_hub_path),
            "--role", "edge_hub",
            "--port", "9100",
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
        
        print(f"✅ Edge Hub started with PID: {process.pid}")
        
        # Wait for startup
        print("⏳ Waiting for Edge Hub to initialize...")
        time.sleep(10)
        
        # Test connection
        try:
            response = requests.get("http://localhost:9100/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Edge Hub health check successful!")
                print(f"   Role: {health_data.get('role', 'unknown')}")
                print(f"   Environment: {health_data.get('environment', 'unknown')}")
                print(f"   Monitored Agents: {health_data.get('monitored_agents', 0)}")
                
                # Test metrics endpoint
                metrics_response = requests.get("http://localhost:9100/metrics", timeout=5)
                if metrics_response.status_code == 200:
                    print("✅ Prometheus metrics endpoint accessible")
                else:
                    print("⚠️  Prometheus metrics endpoint not accessible")
                
                print("\n🎯 EDGE HUB DEPLOYMENT SUCCESSFUL!")
                print(f"   Edge Hub URL: http://localhost:9100")
                print(f"   Health Check: http://localhost:9100/health")
                print(f"   Metrics: http://localhost:9100/metrics")
                print(f"   Process PID: {process.pid}")
                
                # Keep running until interrupted
                print("\n💡 Edge Hub is running. Press Ctrl+C to stop.")
                try:
                    process.wait()
                except KeyboardInterrupt:
                    print("\n🛑 Shutting down Edge Hub...")
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    print("✅ Edge Hub stopped")
                
                return True
                
            else:
                print(f"❌ Edge Hub health check failed: {response.status_code}")
                process.terminate()
                return False
                
        except Exception as e:
            print(f"❌ Edge Hub connection test failed: {e}")
            
            # Check if process is still running
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
        print(f"❌ Edge Hub deployment failed: {e}")
        return False

def validate_edge_hub():
    """Validate Edge Hub deployment"""
    print("\n🧪 VALIDATING EDGE HUB DEPLOYMENT")
    print("=" * 40)
    
    tests = [
        ("Health Endpoint", "http://localhost:9100/health"),
        ("Metrics Endpoint", "http://localhost:9100/metrics"),
        ("Agents API", "http://localhost:9100/api/v1/agents"),
        ("Status API", "http://localhost:9100/api/v1/status")
    ]
    
    results = {}
    
    for test_name, url in tests:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {test_name}: OK")
                results[test_name] = True
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
    
    parser = argparse.ArgumentParser(description="Deploy Edge ObservabilityHub")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation tests")
    
    args = parser.parse_args()
    
    if args.validate_only:
        success = validate_edge_hub()
    else:
        success = deploy_edge_hub()
    
    sys.exit(0 if success else 1) 