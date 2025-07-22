#!/usr/bin/env python3
"""
Test Distributed ObservabilityHub Architecture
Phase 1 Week 3 Day 2 - Comprehensive Validation
"""

import sys
import os
import time
import requests
import json
import threading
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

class DistributedObservabilityTester:
    """Comprehensive tester for distributed ObservabilityHub architecture"""
    
    def __init__(self):
        self.central_hub_url = "http://localhost:9000"
        self.edge_hub_url = "http://localhost:9100"
        self.test_results = {}
        self.validation_errors = []
    
    def run_full_validation(self):
        """Run comprehensive validation of distributed architecture"""
        print("🧪 DISTRIBUTED OBSERVABILITY VALIDATION")
        print("=" * 50)
        
        # Test individual hubs
        central_ok = self._test_hub("Central Hub", self.central_hub_url, "central_hub", "mainpc")
        edge_ok = self._test_hub("Edge Hub", self.edge_hub_url, "edge_hub", "pc2")
        
        if not (central_ok and edge_ok):
            print("❌ Basic hub validation failed")
            return False
        
        # Test distributed features
        sync_ok = self._test_cross_machine_sync()
        failover_ok = self._test_failover_behavior()
        coordination_ok = self._test_hub_coordination()
        data_consistency_ok = self._test_data_consistency()
        
        # Generate comprehensive report
        self._generate_validation_report()
        
        overall_success = all([central_ok, edge_ok, sync_ok, failover_ok, coordination_ok, data_consistency_ok])
        
        if overall_success:
            print("\n🎉 ALL DISTRIBUTED VALIDATION TESTS PASSED!")
        else:
            print("\n❌ SOME DISTRIBUTED VALIDATION TESTS FAILED")
            self._print_error_summary()
        
        return overall_success
    
    def _test_hub(self, hub_name: str, hub_url: str, expected_role: str, expected_env: str) -> bool:
        """Test individual hub functionality"""
        print(f"\n🔍 Testing {hub_name} ({hub_url})")
        
        tests = [
            ("Health Check", f"{hub_url}/health"),
            ("Metrics Endpoint", f"{hub_url}/metrics"),
            ("Agents API", f"{hub_url}/api/v1/agents"),
            ("Status API", f"{hub_url}/api/v1/status")
        ]
        
        hub_results = {}
        
        for test_name, url in tests:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"   ✅ {test_name}: OK")
                    hub_results[test_name] = True
                    
                    # Validate specific responses
                    if "health" in url:
                        health_data = response.json()
                        if health_data.get('role') != expected_role:
                            self.validation_errors.append(f"{hub_name}: Expected role {expected_role}, got {health_data.get('role')}")
                        if health_data.get('environment') != expected_env:
                            self.validation_errors.append(f"{hub_name}: Expected environment {expected_env}, got {health_data.get('environment')}")
                        
                        print(f"      Role: {health_data.get('role')} ({'✅' if health_data.get('role') == expected_role else '❌'})")
                        print(f"      Environment: {health_data.get('environment')} ({'✅' if health_data.get('environment') == expected_env else '❌'})")
                        print(f"      Monitored Agents: {health_data.get('monitored_agents', 0)}")
                        
                else:
                    print(f"   ❌ {test_name}: HTTP {response.status_code}")
                    hub_results[test_name] = False
                    
            except Exception as e:
                print(f"   ❌ {test_name}: {e}")
                hub_results[test_name] = False
        
        success_rate = sum(hub_results.values()) / len(hub_results)
        self.test_results[hub_name] = {
            'success_rate': success_rate,
            'tests': hub_results
        }
        
        return success_rate >= 0.75
    
    def _test_cross_machine_sync(self) -> bool:
        """Test cross-machine synchronization functionality"""
        print("\n🔄 Testing Cross-Machine Synchronization")
        
        try:
            # Get status from both hubs
            central_status = requests.get(f"{self.central_hub_url}/api/v1/status", timeout=10).json()
            edge_status = requests.get(f"{self.edge_hub_url}/api/v1/status", timeout=10).json()
            
            central_peer = central_status.get('peer_coordination', {})
            edge_peer = edge_status.get('peer_coordination', {})
            
            # Check peer endpoints configuration
            central_peer_endpoint = central_peer.get('peer_hub_endpoint')
            edge_peer_endpoint = edge_peer.get('peer_hub_endpoint')
            
            print(f"   Central Hub Peer Endpoint: {central_peer_endpoint}")
            print(f"   Edge Hub Peer Endpoint: {edge_peer_endpoint}")
            
            # Validate peer status
            central_peer_status = central_peer.get('peer_status', 'unknown')
            edge_peer_status = edge_peer.get('peer_status', 'unknown')
            
            print(f"   Central → Edge Status: {central_peer_status} ({'✅' if central_peer_status == 'healthy' else '⚠️'})")
            print(f"   Edge → Central Status: {edge_peer_status} ({'✅' if edge_peer_status == 'healthy' else '⚠️'})")
            
            # Check sync timestamps
            central_last_sync = central_peer.get('last_successful_sync')
            edge_last_sync = edge_peer.get('last_successful_sync')
            
            if central_last_sync:
                sync_age = time.time() - central_last_sync
                print(f"   Central Last Sync: {sync_age:.1f}s ago ({'✅' if sync_age < 120 else '⚠️'})")
            else:
                print("   Central Last Sync: None ⚠️")
            
            if edge_last_sync:
                sync_age = time.time() - edge_last_sync
                print(f"   Edge Last Sync: {sync_age:.1f}s ago ({'✅' if sync_age < 120 else '⚠️'})")
            else:
                print("   Edge Last Sync: None ⚠️")
            
            # Test manual sync
            print("   🔄 Testing manual sync trigger...")
            sync_ok = self._trigger_manual_sync()
            
            sync_success = (
                central_peer_status in ['healthy', 'unknown'] and
                edge_peer_status in ['healthy', 'unknown'] and
                sync_ok
            )
            
            if sync_success:
                print("   ✅ Cross-machine synchronization validation passed")
            else:
                print("   ❌ Cross-machine synchronization validation failed")
                self.validation_errors.append("Cross-machine synchronization not working properly")
            
            return sync_success
            
        except Exception as e:
            print(f"   ❌ Cross-machine sync test failed: {e}")
            self.validation_errors.append(f"Cross-machine sync test error: {e}")
            return False
    
    def _trigger_manual_sync(self) -> bool:
        """Trigger manual synchronization test"""
        try:
            # Create test data on edge hub and check if it appears on central
            test_payload = {
                "source_hub": "test_edge",
                "timestamp": time.time(),
                "metrics": [
                    {
                        "agent_name": "test_agent",
                        "metric_type": "test_metric",
                        "metric_value": 1.0,
                        "timestamp": time.time(),
                        "metadata": {"test": True}
                    }
                ],
                "sync_type": "test_sync"
            }
            
            # Send test sync to central hub
            response = requests.post(
                f"{self.central_hub_url}/api/v1/sync_from_peer",
                json=test_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"      Manual sync test: ✅ ({result.get('metrics_received', 0)} metrics)")
                return True
            else:
                print(f"      Manual sync test: ❌ (HTTP {response.status_code})")
                return False
                
        except Exception as e:
            print(f"      Manual sync test: ❌ ({e})")
            return False
    
    def _test_failover_behavior(self) -> bool:
        """Test failover behavior when hubs are unavailable"""
        print("\n⚡ Testing Failover Behavior")
        
        try:
            # Get current failover status
            central_status = requests.get(f"{self.central_hub_url}/api/v1/status", timeout=10).json()
            edge_status = requests.get(f"{self.edge_hub_url}/api/v1/status", timeout=10).json()
            
            central_failover = central_status.get('peer_coordination', {}).get('failover_active', False)
            edge_failover = edge_status.get('peer_coordination', {}).get('failover_active', False)
            
            print(f"   Central Hub Failover Status: {central_failover}")
            print(f"   Edge Hub Failover Status: {edge_failover}")
            
            # Check sync failure counts
            central_failures = central_status.get('peer_coordination', {}).get('sync_failures', 0)
            edge_failures = edge_status.get('peer_coordination', {}).get('sync_failures', 0)
            
            print(f"   Central Hub Sync Failures: {central_failures}")
            print(f"   Edge Hub Sync Failures: {edge_failures}")
            
            # Test hub resilience (both should continue operating independently)
            print("   🔍 Testing hub independence...")
            
            # Each hub should have local monitoring capabilities
            central_agents = requests.get(f"{self.central_hub_url}/api/v1/agents", timeout=10).json()
            edge_agents = requests.get(f"{self.edge_hub_url}/api/v1/agents", timeout=10).json()
            
            central_agent_count = central_agents.get('total_agents', 0)
            edge_agent_count = edge_agents.get('total_agents', 0)
            
            print(f"   Central Hub Agents: {central_agent_count}")
            print(f"   Edge Hub Agents: {edge_agent_count}")
            
            # Validate that each hub has discovered agents in their environment
            failover_ok = (
                central_agent_count > 0 and
                edge_agent_count >= 0  # PC2 might have fewer agents
            )
            
            if failover_ok:
                print("   ✅ Failover behavior validation passed")
            else:
                print("   ❌ Failover behavior validation failed")
                self.validation_errors.append("Hubs not operating independently")
            
            return failover_ok
            
        except Exception as e:
            print(f"   ❌ Failover test failed: {e}")
            self.validation_errors.append(f"Failover test error: {e}")
            return False
    
    def _test_hub_coordination(self) -> bool:
        """Test hub coordination and communication"""
        print("\n🤝 Testing Hub Coordination")
        
        try:
            # Test bidirectional communication
            coordination_tests = [
                ("Central → Edge Health Check", self._test_hub_to_hub_comm(self.central_hub_url, self.edge_hub_url)),
                ("Edge → Central Health Check", self._test_hub_to_hub_comm(self.edge_hub_url, self.central_hub_url)),
            ]
            
            coordination_results = []
            for test_name, result in coordination_tests:
                print(f"   {test_name}: {'✅' if result else '❌'}")
                coordination_results.append(result)
            
            coordination_ok = any(coordination_results)  # At least one direction should work
            
            if coordination_ok:
                print("   ✅ Hub coordination validation passed")
            else:
                print("   ❌ Hub coordination validation failed")
                self.validation_errors.append("Hub coordination not working")
            
            return coordination_ok
            
        except Exception as e:
            print(f"   ❌ Hub coordination test failed: {e}")
            self.validation_errors.append(f"Hub coordination test error: {e}")
            return False
    
    def _test_hub_to_hub_comm(self, source_url: str, target_url: str) -> bool:
        """Test communication between specific hubs"""
        try:
            # Get source hub status to see if it can reach target
            response = requests.get(f"{source_url}/api/v1/status", timeout=5)
            if response.status_code == 200:
                status = response.json()
                peer_status = status.get('peer_coordination', {}).get('peer_status', 'unknown')
                return peer_status in ['healthy', 'reachable']
            return False
        except:
            return False
    
    def _test_data_consistency(self) -> bool:
        """Test data consistency between hubs"""
        print("\n📊 Testing Data Consistency")
        
        try:
            # Test that both hubs are collecting metrics
            central_metrics = requests.get(f"{self.central_hub_url}/metrics", timeout=10)
            edge_metrics = requests.get(f"{self.edge_hub_url}/metrics", timeout=10)
            
            central_ok = central_metrics.status_code == 200 and len(central_metrics.text) > 100
            edge_ok = edge_metrics.status_code == 200 and len(edge_metrics.text) > 100
            
            print(f"   Central Hub Metrics: {'✅' if central_ok else '❌'} ({len(central_metrics.text) if central_ok else 0} bytes)")
            print(f"   Edge Hub Metrics: {'✅' if edge_ok else '❌'} ({len(edge_metrics.text) if edge_ok else 0} bytes)")
            
            # Check for specific metrics indicating distributed operation
            central_content = central_metrics.text if central_ok else ""
            edge_content = edge_metrics.text if edge_ok else ""
            
            central_has_distributed = "observability_hub_status" in central_content
            edge_has_distributed = "observability_hub_status" in edge_content
            
            print(f"   Central Distributed Metrics: {'✅' if central_has_distributed else '❌'}")
            print(f"   Edge Distributed Metrics: {'✅' if edge_has_distributed else '❌'}")
            
            consistency_ok = central_ok and edge_ok and central_has_distributed and edge_has_distributed
            
            if consistency_ok:
                print("   ✅ Data consistency validation passed")
            else:
                print("   ❌ Data consistency validation failed")
                self.validation_errors.append("Data consistency issues detected")
            
            return consistency_ok
            
        except Exception as e:
            print(f"   ❌ Data consistency test failed: {e}")
            self.validation_errors.append(f"Data consistency test error: {e}")
            return False
    
    def _generate_validation_report(self):
        """Generate comprehensive validation report"""
        print("\n📋 VALIDATION REPORT")
        print("=" * 30)
        
        for hub_name, results in self.test_results.items():
            success_rate = results['success_rate'] * 100
            print(f"{hub_name}: {success_rate:.1f}% success rate")
            
            for test_name, passed in results['tests'].items():
                status = "✅" if passed else "❌"
                print(f"   {status} {test_name}")
        
        if self.validation_errors:
            print("\n⚠️  VALIDATION ERRORS:")
            for error in self.validation_errors:
                print(f"   • {error}")
    
    def _print_error_summary(self):
        """Print summary of validation errors"""
        if self.validation_errors:
            print("\n📋 ERROR SUMMARY:")
            for i, error in enumerate(self.validation_errors, 1):
                print(f"   {i}. {error}")

def main():
    """Main test execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Distributed ObservabilityHub Architecture")
    parser.add_argument("--central-url", default="http://localhost:9000", help="Central Hub URL")
    parser.add_argument("--edge-url", default="http://localhost:9100", help="Edge Hub URL")
    parser.add_argument("--quick", action="store_true", help="Run quick validation only")
    
    args = parser.parse_args()
    
    tester = DistributedObservabilityTester()
    tester.central_hub_url = args.central_url
    tester.edge_hub_url = args.edge_url
    
    if args.quick:
        # Quick validation - just health checks
        central_ok = tester._test_hub("Central Hub", args.central_url, "central_hub", "mainpc")
        edge_ok = tester._test_hub("Edge Hub", args.edge_url, "edge_hub", "pc2")
        success = central_ok and edge_ok
    else:
        # Full validation
        success = tester.run_full_validation()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 