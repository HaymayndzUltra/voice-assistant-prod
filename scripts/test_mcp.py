#!/usr/bin/env python3
"""
Simple test script for MCP tools
"""

import json
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_ai_system_monitor():
    """Test the AI system monitor"""
    try:
        from scripts.ai_system_monitor import AISystemMonitor
        
        monitor = AISystemMonitor()
        
        # Test system status
        print("🔍 Testing system status...")
        status = await monitor.get_system_status()
        print(json.dumps(status, indent=2))
        
        print("\n✅ MCP tools are working!")
        
    except Exception as e:
        print(f"❌ Error testing MCP tools: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_system_monitor())
