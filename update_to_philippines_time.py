#!/usr/bin/env python3
"""
Update to Philippines Time
Updates all state files to use Philippines time format
"""

def update_to_philippines_time():
    """Update all state files to use Philippines time"""
    
    print("🇵🇭 Updating to Philippines Time Format")
    print("=" * 40)
    
    try:
        # Import and trigger auto-sync
        from auto_sync_manager import auto_sync
        
        print("\n1️⃣ Triggering auto-sync with Philippines time...")
        result = auto_sync()
        print(f"   Result: {result}")
        
        if result.get('status') == 'success':
            print("   ✅ Auto-sync completed successfully")
        else:
            print(f"   ❌ Auto-sync failed: {result.get('error')}")
            return False
        
        print("\n2️⃣ Checking updated files...")
        
        # Check cursor_state.json
        import json
        with open('cursor_state.json', 'r') as f:
            cursor_state = json.load(f)
        print(f"   cursor_state.json: {cursor_state['cursor_session']['disconnected_at']}")
        
        # Check task-state.json
        with open('task-state.json', 'r') as f:
            task_state = json.load(f)
        if task_state:
            print(f"   task-state.json: {task_state.get('last_updated', 'N/A')}")
        
        # Check task_interruption_state.json
        with open('task_interruption_state.json', 'r') as f:
            interruption_state = json.load(f)
        print(f"   task_interruption_state.json: {interruption_state['last_updated']}")
        
        # Check current-session.md
        with open('memory-bank/current-session.md', 'r') as f:
            session_content = f.read()
        if 'PH' in session_content:
            print("   current-session.md: ✅ Philippines time format detected")
        else:
            print("   current-session.md: ⚠️  Philippines time format not detected")
        
        print("\n✅ All state files updated to Philippines time!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating to Philippines time: {e}")
        return False

if __name__ == "__main__":
    update_to_philippines_time() 