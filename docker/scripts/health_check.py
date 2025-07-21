#!/usr/bin/env python3
"""Basic health check script for containers"""
import sys
import time

def health_check():
    """Simple health check that always passes"""
    try:
        # Basic system check
        print(f"Health check passed at {time.ctime()}")
        return True
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if health_check() else 1)
