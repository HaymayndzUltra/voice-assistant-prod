#!/usr/bin/env python3
"""
Simple test to check if port 5576 is listening
"""

import socket
import time

def test_port_connection():
    print("Testing connection to port 5576...")
    
    try:
        # Create a socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        # Try to connect
        result = sock.connect_ex(('localhost', 5576))
        
        if result == 0:
            print("✅ Port 5576 is listening and accepting connections")
            sock.close()
            return True
        else:
            print(f"❌ Port 5576 is not accepting connections (error code: {result})")
            sock.close()
            return False
            
    except Exception as e:
        print(f"❌ Error testing port: {e}")
        return False

if __name__ == "__main__":
    test_port_connection() 