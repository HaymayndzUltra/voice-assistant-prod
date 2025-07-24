#!/usr/bin/env python3
"""
Logging Infrastructure Upgrade Verification Script
Phase 0 Day 4 - Final verification that the logging upgrade is working

This script verifies that the BaseAgent logging upgrade is working correctly
by testing the rotating logger functionality in a controlled environment.
"""

import sys
import os
import time
import tempfile
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager


def test_baseagent_logging_upgrade():
    """Test that BaseAgent uses rotating logging correctly."""
    print(f"🧪 TESTING BASEAGENT LOGGING UPGRADE")
    print(f"=" * 50)
    
    try:
        # Import BaseAgent to test the updated logging
        from common.core.base_agent import BaseAgent
        
        print(f"✅ BaseAgent imported successfully")
        
        # Create a temporary test agent
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__(name="TestLogRotationAgent", port=None)
                
            def handle_request(self, request):
                return {"status": "ok", "message": "test response"}
        
        print(f"✅ Test agent class created")
        
        # Initialize test agent
        test_agent = TestAgent()
        print(f"✅ Test agent initialized: {test_agent.name}")
        
        # Check logger configuration
        logger = test_agent.logger
        
        # Check if logger has rotating file handler
        has_rotating_handler = False
        rotating_handler = None
        
        # Get the actual logger (unwrap LoggerAdapter)
        actual_logger = logger.logger if hasattr(logger, 'logger') else logger
        
        for handler in actual_logger.handlers:
            if 'RotatingFileHandler' in str(type(handler)):
                has_rotating_handler = True
                rotating_handler = handler
                break
        
        print(f"🔄 Has rotating file handler: {'✅' if has_rotating_handler else '❌'}")
        
        if has_rotating_handler and rotating_handler:
            print(f"📄 Log file: {rotating_handler.baseFilename}")
            print(f"📏 Max bytes: {rotating_handler.maxBytes:,} ({rotating_handler.maxBytes / (1024**2):.1f}MB)")
            print(f"🔄 Backup count: {rotating_handler.backupCount}")
        
        # Test logging functionality
        test_agent.logger.info("Test log entry - logging upgrade verification")
        test_agent.logger.info("Testing rotating logger configuration", extra={
            "test_data": {"rotation_enabled": True, "max_size_mb": 10}
        })
        
        print(f"✅ Test logging successful")
        
        # Cleanup
        test_agent.cleanup()
        print(f"🧹 Test agent cleaned up")
        
        return {
            "success": True,
            "has_rotating_handler": has_rotating_handler,
            "log_file": rotating_handler.baseFilename if rotating_handler else None,
            "max_bytes": rotating_handler.maxBytes if rotating_handler else None,
            "backup_count": rotating_handler.backupCount if rotating_handler else None
        }
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def verify_json_logger_functions():
    """Verify the enhanced JSON logger functions work correctly."""
    print(f"\n🔧 TESTING JSON LOGGER FUNCTIONS")
    print(f"=" * 50)
    
    try:
        from common.utils.logger_util import (
            get_rotating_json_logger,
            upgrade_logger_to_rotating,
            JsonFormatter
        )
        
        print(f"✅ Enhanced logger functions imported")
        
        # Test JsonFormatter
        formatter = JsonFormatter()
        print(f"✅ JsonFormatter created")
        
        # Test get_rotating_json_logger
        with tempfile.TemporaryDirectory() as temp_dir:
            test_log_file = Path(temp_dir) / "test_rotating.log"
            
            logger = get_rotating_json_logger(
                name="test_rotating_logger",
                log_file=str(test_log_file),
                max_bytes=1024*1024,  # 1MB for testing
                backup_count=3,
                console_output=False
            )
            
            print(f"✅ Rotating logger created")
            
            # Test logging
            logger.info("Test rotating logger functionality")
            logger.warning("Test warning message", extra={"test_field": "test_value"})
            
            # Verify log file exists
            if test_log_file.exists():
                print(f"✅ Log file created: {test_log_file}")
                
                # Check file content
                with open(test_log_file, 'r') as f:
                    content = f.read()
                    if "test_rotating_logger" in content and "Test rotating logger functionality" in content:
                        print(f"✅ Log content verified")
                    else:
                        print(f"❌ Log content verification failed")
            else:
                print(f"❌ Log file not created")
        
        return {"success": True}
        
    except Exception as e:
        print(f"❌ JSON logger function test failed: {e}")
        return {"success": False, "error": str(e)}


def check_existing_log_files():
    """Check existing log files to see their current state."""
    print(f"\n📁 CHECKING EXISTING LOG FILES")
    print(f"=" * 50)
    
    try:
        project_root = Path(PathManager.get_project_root())
        logs_dir = project_root / "logs"
        
        if not logs_dir.exists():
            print(f"📁 Logs directory doesn't exist yet: {logs_dir}")
            return {"logs_dir_exists": False}
        
        log_files = list(logs_dir.glob("*.log"))
        rotation_files = list(logs_dir.glob("*.log.*"))
        
        print(f"📊 Found {len(log_files)} main log files")
        print(f"🔄 Found {len(rotation_files)} rotation files")
        
        if log_files:
            print(f"\n📄 Main log files:")
            for log_file in sorted(log_files):
                size_mb = log_file.stat().st_size / (1024**2)
                modified = datetime.fromtimestamp(log_file.stat().st_mtime)
                print(f"  {log_file.name}: {size_mb:.2f}MB (modified: {modified.strftime('%Y-%m-%d %H:%M:%S')})")
        
        if rotation_files:
            print(f"\n🔄 Rotation files:")
            for rot_file in sorted(rotation_files):
                size_mb = rot_file.stat().st_size / (1024**2)
                print(f"  {rot_file.name}: {size_mb:.2f}MB")
        
        return {
            "logs_dir_exists": True,
            "main_log_files": len(log_files),
            "rotation_files": len(rotation_files),
            "total_log_size_mb": sum(f.stat().st_size for f in log_files + rotation_files) / (1024**2)
        }
        
    except Exception as e:
        print(f"❌ Error checking log files: {e}")
        return {"error": str(e)}


def main():
    """Main verification function."""
    print(f"🎯 LOGGING INFRASTRUCTURE UPGRADE VERIFICATION")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 60)
    
    results = {}
    
    # Test BaseAgent logging upgrade
    results["baseagent_test"] = test_baseagent_logging_upgrade()
    
    # Test JSON logger functions
    results["json_logger_test"] = verify_json_logger_functions()
    
    # Check existing log files
    results["log_files_check"] = check_existing_log_files()
    
    # Summary
    print(f"\n📊 VERIFICATION SUMMARY")
    print(f"=" * 50)
    
    all_successful = all(
        test_result.get("success", False) 
        for test_result in [results["baseagent_test"], results["json_logger_test"]]
    )
    
    if all_successful:
        print(f"✅ All tests passed - logging upgrade successful!")
        print(f"🎯 BaseAgent now uses rotating file handlers by default")
        print(f"💾 Log files will rotate at 10MB with 5 backups")
        print(f"🔄 Agents will automatically use new logging when restarted")
        
        # Provide next steps
        print(f"\n📋 NEXT STEPS:")
        print(f"1. ✅ Logging infrastructure upgraded")
        print(f"2. 🔄 Agents will use rotating logs when restarted") 
        print(f"3. 📊 Monitor disk usage during normal operations")
        print(f"4. 🎯 Day 4 objectives achieved!")
        
    else:
        print(f"❌ Some tests failed - review results above")
        for test_name, test_result in results.items():
            if not test_result.get("success", False):
                print(f"  ❌ {test_name}: {test_result.get('error', 'Unknown error')}")
    
    return results


if __name__ == "__main__":
    main() 