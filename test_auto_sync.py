#!/usr/bin/env python3
"""
Test script to trigger auto-sync and verify it works
"""

try:
    from auto_sync_manager import auto_sync
    print("🔄 Triggering auto-sync...")
    result = auto_sync()
    print(f"✅ Auto-sync result: {result}")
    
    # Check if cursor_state.json was created at root level
    import os
    if os.path.exists('cursor_state.json'):
        import json
        with open('cursor_state.json', 'r') as f:
            data = json.load(f)
        print(f"✅ Root cursor_state.json updated with task: {data['cursor_session']['current_task']}")
    else:
        print("ℹ️ No root cursor_state.json created (as expected)")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc() 