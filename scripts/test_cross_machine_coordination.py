#!/usr/bin/env python3
"""
Test Cross-Machine Coordination - Phase 1 Week 3 Day 5
Tests enhanced cross-machine coordination between Central and Edge ObservabilityHubs
"""

import sys
import time
import requests
from typing import Dict, Any

CENTRAL_HUB_URL = "http://localhost:9000"
EDGE_HUB_URL = "http://localhost:9100"

class CrossMachineCoordinationTester:
    """Test enhanced cross-machine coordination between hubs"""
    
    def __init__(self):
        self.central_url = CENTRAL_HUB_URL
        self.edge_url = EDGE_HUB_URL
        self.results = {
            "central_to_edge": None,
            "edge_to_central": None,
            "failover": None,
            "sync_status": None,
            "alerts": []
        }
    
    def test_coordination(self):
        print("\n🔄 TESTING CROSS-MACHINE COORDINATION")
        print("=" * 50)
        
        # Test Central Hub can reach Edge Hub
        self.results["central_to_edge"] = self._test_peer_status(self.central_url, self.edge_url)
        print(f"✅ Central Hub → Edge Hub: {self.results['central_to_edge']}")
        
        # Test Edge Hub can reach Central Hub
        self.results["edge_to_central"] = self._test_peer_status(self.edge_url, self.central_url)
        print(f"✅ Edge Hub → Central Hub: {self.results['edge_to_central']}")
        
        # Test failover status
        self.results["failover"] = self._test_failover_status()
        print(f"✅ Failover Status: {self.results['failover']}")
        
        # Test sync status
        self.results["sync_status"] = self._test_sync_status()
        print(f"✅ Sync Status: {self.results['sync_status']}")
        
        # Print alerts if any
        if self.results["alerts"]:
            print(f"⚠️  Alerts: {self.results['alerts']}")
        else:
            print("🎉 Cross-machine coordination test passed!")
        
        return self.results
    
    def _test_peer_status(self, source_url: str, peer_url: str) -> str:
        try:
            response = requests.get(f"{source_url}/api/v1/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                peer_status = data.get('peer_coordination', {}).get('peer_status', 'unknown')
                return peer_status
            else:
                self.results['alerts'].append(f"Peer status check failed: {source_url}")
                return "unreachable"
        except Exception as e:
            self.results['alerts'].append(f"Peer status error: {e}")
            return "error"
    
    def _test_failover_status(self) -> str:
        try:
            response = requests.get(f"{CENTRAL_HUB_URL}/api/v1/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                failover = data.get('peer_coordination', {}).get('failover_active', False)
                return "active" if failover else "inactive"
            else:
                return "unknown"
        except Exception as e:
            self.results['alerts'].append(f"Failover status error: {e}")
            return "error"
    
    def _test_sync_status(self) -> str:
        try:
            response = requests.get(f"{CENTRAL_HUB_URL}/api/v1/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                last_sync = data.get('peer_coordination', {}).get('last_successful_sync', None)
                if last_sync:
                    return f"last sync at {time.ctime(last_sync)}"
                else:
                    return "no recent sync"
            else:
                return "unknown"
        except Exception as e:
            self.results['alerts'].append(f"Sync status error: {e}")
            return "error"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test cross-machine coordination between hubs")
    parser.add_argument("--full-validation", action="store_true", help="Run full validation")
    args = parser.parse_args()
    tester = CrossMachineCoordinationTester()
    tester.test_coordination()

if __name__ == "__main__":
    main() 