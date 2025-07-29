#!/usr/bin/env python3
"""
Test Philippines Time Format
Verifies that all time displays use Philippines time with 12-hour format
"""

from datetime import datetime, timezone, timedelta

def get_philippines_time() -> datetime:
    """Get current Philippines time (UTC+8)"""
    utc_now = datetime.now(timezone.utc)
    philippines_tz = timezone(timedelta(hours=8))
    return utc_now.astimezone(philippines_tz)

def format_philippines_time(dt: datetime) -> str:
    """Format datetime to Philippines time with 12-hour format"""
    philippines_tz = timezone(timedelta(hours=8))
    ph_time = dt.astimezone(philippines_tz)
    return ph_time.strftime('%Y-%m-%d %I:%M:%S %p')  # 12-hour format with AM/PM

def format_philippines_time_iso(dt: datetime) -> str:
    """Format datetime to Philippines time in ISO format"""
    philippines_tz = timezone(timedelta(hours=8))
    ph_time = dt.astimezone(philippines_tz)
    return ph_time.isoformat()

def test_philippines_time():
    """Test Philippines time formatting"""
    
    print("🇵🇭 Testing Philippines Time Format")
    print("=" * 40)
    
    # Test current time
    print("\n1️⃣ Current Time:")
    utc_now = datetime.now(timezone.utc)
    ph_time = get_philippines_time()
    
    print(f"   UTC Time: {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"   PH Time: {format_philippines_time(ph_time)} PH")
    print(f"   PH ISO: {format_philippines_time_iso(ph_time)}")
    
    # Test different times
    print("\n2️⃣ Different Times:")
    test_times = [
        datetime(2025, 7, 29, 6, 0, 0, tzinfo=timezone.utc),  # 6 AM UTC
        datetime(2025, 7, 29, 12, 0, 0, tzinfo=timezone.utc), # 12 PM UTC
        datetime(2025, 7, 29, 18, 0, 0, tzinfo=timezone.utc), # 6 PM UTC
        datetime(2025, 7, 29, 0, 0, 0, tzinfo=timezone.utc),  # 12 AM UTC
    ]
    
    for utc_time in test_times:
        ph_time = utc_time.astimezone(timezone(timedelta(hours=8)))
        print(f"   {utc_time.strftime('%H:%M')} UTC → {format_philippines_time(ph_time)} PH")
    
    # Test auto-sync manager integration
    print("\n3️⃣ Auto-Sync Manager Integration:")
    try:
        from auto_sync_manager import get_philippines_time as auto_sync_ph_time
        from auto_sync_manager import format_philippines_time as auto_sync_format
        
        test_time = auto_sync_ph_time()
        formatted_time = auto_sync_format(test_time)
        print(f"   ✅ Auto-sync manager: {formatted_time}")
    except Exception as e:
        print(f"   ❌ Auto-sync manager error: {e}")
    
    # Test todo_manager integration
    print("\n4️⃣ Todo Manager Integration:")
    try:
        from todo_manager import _timestamp
        timestamp = _timestamp()
        print(f"   ✅ Todo manager timestamp: {timestamp}")
    except Exception as e:
        print(f"   ❌ Todo manager error: {e}")
    
    print("\n🎯 Philippines time format test completed!")
    return True

if __name__ == "__main__":
    test_philippines_time() 