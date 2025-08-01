#!/usr/bin/env python3
"""
Test script for 5-minute periodic sync
"""

import time
from auto_sync_manager import get_sync_status, set_sync_interval, stop_periodic_sync

def test_periodic_sync():
    """Test the periodic sync functionality"""
    print("🧪 Testing 5-minute Periodic Sync")
    print("=" * 50)
    
    # Get initial status
    status = get_sync_status()
    print(f"📊 Initial Status:")
    print(f"   Periodic sync enabled: {status['periodic_sync_enabled']}")
    print(f"   Sync interval: {status['sync_interval_seconds']} seconds")
    print(f"   Thread alive: {status['periodic_thread_alive']}")
    print()
    
    # Test changing interval to 30 seconds for testing
    print("⏰ Setting sync interval to 30 seconds for testing...")
    set_sync_interval(30)
    
    # Wait and check status
    print("⏳ Waiting 35 seconds to see periodic sync in action...")
    for i in range(35):
        time.sleep(1)
        if i % 10 == 0:
            print(f"   {i} seconds elapsed...")
    
    # Check final status
    final_status = get_sync_status()
    print(f"📊 Final Status:")
    print(f"   Periodic sync enabled: {final_status['periodic_sync_enabled']}")
    print(f"   Sync interval: {final_status['sync_interval_seconds']} seconds")
    print(f"   Thread alive: {final_status['periodic_thread_alive']}")
    print(f"   Last sync: {final_status['last_sync']}")
    
    # Reset to 5 minutes
    print("⏰ Resetting sync interval to 5 minutes...")
    set_sync_interval(300)
    
    print("✅ Periodic sync test completed!")

if __name__ == "__main__":
    test_periodic_sync() 