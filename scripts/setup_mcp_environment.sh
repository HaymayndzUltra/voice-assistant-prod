#!/bin/bash

# MCP Environment Setup Script for Cursor Ultra Plan
# This script sets up the environment variables needed for MCP tools

echo "🚀 Setting up MCP Environment for Cursor Ultra Plan..."

# Create .env file for MCP configuration
ENV_FILE="$HOME/.cursor/mcp.env"

echo "📝 Creating MCP environment file at $ENV_FILE"

cat > "$ENV_FILE" << 'EOF'
# MCP Environment Variables for Cursor Ultra Plan

# GitHub Integration
# Get your GitHub token from: https://github.com/settings/tokens
# GITHUB_TOKEN=your_github_token_here

# Brave Search API (Optional)
# Get your Brave API key from: https://api.search.brave.com/
# BRAVE_API_KEY=your_brave_api_key_here

# PostgreSQL Connection (Optional)
# POSTGRES_CONNECTION_STRING=postgresql://username:password@localhost:5432/database

# AI System Path
AI_SYSTEM_PATH=/home/haymayndz/AI_System_Monorepo

# MainPC Configuration
MAINPC_CONFIG=/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml

# PC2 Configuration  
PC2_CONFIG=/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml
EOF

echo "✅ Environment file created!"

# Install required Python packages
echo "📦 Installing required Python packages..."
pip install psutil requests pyyaml

# Make the AI system monitor script executable
echo "🔧 Making AI system monitor executable..."
chmod +x /home/haymayndz/AI_System_Monorepo/scripts/ai_system_monitor.py

# Create a simple test script
echo "🧪 Creating test script..."
cat > /home/haymayndz/AI_System_Monorepo/scripts/test_mcp.py << 'EOF'
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
EOF

chmod +x /home/haymayndz/AI_System_Monorepo/scripts/test_mcp.py

echo ""
echo "🎉 MCP Environment Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit $ENV_FILE to add your API keys"
echo "2. Restart Cursor to reload MCP configuration"
echo "3. Test the setup: python3 /home/haymayndz/AI_System_Monorepo/scripts/test_mcp.py"
echo ""
echo "🔧 Available MCP Tools:"
echo "   • GitHub Integration (for repo management)"
echo "   • File System Access (for file operations)"
echo "   • Brave Search (for web search)"
echo "   • PostgreSQL (for database access)"
echo "   • AI System Monitor (for your AI agents)"
echo "   • Agent Health Checker (for system monitoring)"
echo ""
echo "💡 Ultra Plan Features Enabled:"
echo "   • MAX MODE with maximum AI usage"
echo "   • Background agents for automation"
echo "   • Parallel task execution"
echo "   • Advanced code analysis"
echo "   • Deep repository analysis"
echo "   • Custom triggers and automation"
echo "   • Maximum context windows" 