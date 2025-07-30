#!/usr/bin/env python3
"""
Run consistency fixes for the AI System Monorepo
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from session_continuity_manager import SessionContinuityManager

def main():
    """TODO: Add description for main."""
    print("🔧 AI System Monorepo - Consistency Fix")
    print("=" * 50)

    try:
        # Initialize manager
        manager = SessionContinuityManager()

        # Step 1: Clean up duplicate tasks
        print("\n1️⃣ Cleaning up duplicate tasks...")
        cleanup_result = manager.cleanup_duplicate_tasks()
        print(f"   ✅ Result: {cleanup_result}")

        # Step 2: Sync all state files
        print("\n2️⃣ Syncing all state files...")
        sync_result = manager.sync_all_states()
        print(f"   ✅ Result: {sync_result}")

        print("\n🎯 Consistency fixes completed successfully!")
        print("📊 All state files are now synchronized")

    except Exception as e:
        print(f"❌ Error during consistency fix: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())