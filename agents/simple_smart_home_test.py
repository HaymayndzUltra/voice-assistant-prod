#!/usr/bin/env python3
"""
Simple Smart Home Test - Direct approach without complex async
Let's prove the device control actually works first
"""

import sys
sys.path.append('/home/haymayndz/AI_System_Monorepo')

from PyP100.PyP100 import P100
import time

def test_direct_control():
    """Test direct device control without agent framework"""
    print("🔄 Testing direct Tapo device control...")
    
    try:
        # Create device
        device = P100("192.168.100.63", "dagsgarcia8@gmail.com", "Prof2025!")
        print("✅ Device object created")
        
        # Connect
        device.handshake()
        device.login()
        print("✅ Connected to device")
        
        # Get device info to confirm it's working
        info = device.getDeviceInfo()
        print(f"Device info: {info}")
        
        # Turn ON
        print("🔄 Turning ON...")
        device.turnOn()
        print("✅ Light should be ON!")
        
        time.sleep(3)
        
        # Turn OFF
        print("🔄 Turning OFF...")
        device.turnOff()
        print("✅ Light should be OFF!")
        
        print("\n🎉 DIRECT DEVICE CONTROL WORKS!")
        return True
        
    except Exception as e:
        print(f"❌ Direct control failed: {e}")
        return False

if __name__ == "__main__":
    success = test_direct_control()
    if success:
        print("\n✅ RESULT: Device control is working!")
        print("The issue is in the agent framework, not the device.")
    else:
        print("\n❌ RESULT: Device control is not working.")
        print("There's a fundamental issue with the device connection.")
