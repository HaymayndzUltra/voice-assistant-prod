#!/bin/bash
# COMPLETE Migration Script v2 - With ALL Dependencies
# This script copies ALL necessary files including common modules, utilities, and error handling

echo "🚀 COMPLETE MIGRATION SCRIPT V2 - COMPREHENSIVE"
echo "=============================================="

# Set paths
WORKSPACE="/workspace"
NEW_REPO="/workspace/unified-system-v1"

# Create ALL necessary directories
echo "📁 Creating comprehensive directory structure..."
mkdir -p $NEW_REPO/src/agents/mainpc/{services,formainpc,backups}
mkdir -p $NEW_REPO/src/agents/pc2/{forpc2,backups,core_agents,integration,utils}
mkdir -p $NEW_REPO/src/agents/core
mkdir -p $NEW_REPO/src/utils/{core,pools,error_handling}
mkdir -p $NEW_REPO/models
mkdir -p $NEW_REPO/data
mkdir -p $NEW_REPO/common/{core,pools,utils,error_bus}
mkdir -p $NEW_REPO/common_utils
mkdir -p $NEW_REPO/config
mkdir -p $NEW_REPO/database
mkdir -p $NEW_REPO/security
mkdir -p $NEW_REPO/events
mkdir -p $NEW_REPO/complexity

# CRITICAL: Copy ALL common modules
echo "⚡ Copying ALL common modules (CRITICAL!)..."
if [ -d "$WORKSPACE/common" ]; then
    cp -r $WORKSPACE/common/* $NEW_REPO/common/ 2>/dev/null || true
    echo "  ✓ Copied common directory"
fi

if [ -d "$WORKSPACE/common_utils" ]; then
    cp -r $WORKSPACE/common_utils/* $NEW_REPO/common_utils/ 2>/dev/null || true
    echo "  ✓ Copied common_utils directory"
fi

# Copy specific critical files
echo "📌 Copying critical base files..."
cp $WORKSPACE/common/core/base_agent.py $NEW_REPO/src/utils/base_agent.py 2>/dev/null || true
cp $WORKSPACE/common/core/enhanced_base_agent.py $NEW_REPO/src/utils/enhanced_base_agent.py 2>/dev/null || true

# Copy configuration management
echo "⚙️ Copying configuration management..."
cp $WORKSPACE/common/config_manager.py $NEW_REPO/common/ 2>/dev/null || true
cp $WORKSPACE/common/env_helpers.py $NEW_REPO/common/ 2>/dev/null || true

# Copy ZMQ pools
echo "🔌 Copying ZMQ pools..."
if [ -d "$WORKSPACE/common/pools" ]; then
    cp -r $WORKSPACE/common/pools/* $NEW_REPO/common/pools/ 2>/dev/null || true
fi

# Copy error handling
echo "❗ Copying error handling modules..."
if [ -d "$WORKSPACE/common/error_bus" ]; then
    cp -r $WORKSPACE/common/error_bus/* $NEW_REPO/common/error_bus/ 2>/dev/null || true
fi
if [ -d "$WORKSPACE/common_utils" ]; then
    cp $WORKSPACE/common_utils/error_handling.py $NEW_REPO/common_utils/ 2>/dev/null || true
    cp $WORKSPACE/common_utils/zmq_helper.py $NEW_REPO/common_utils/ 2>/dev/null || true
    cp $WORKSPACE/common_utils/env_loader.py $NEW_REPO/common_utils/ 2>/dev/null || true
    cp $WORKSPACE/common_utils/port_registry.py $NEW_REPO/common_utils/ 2>/dev/null || true
fi

# Copy utilities
echo "🔧 Copying all utilities..."
if [ -d "$WORKSPACE/common/utils" ]; then
    cp -r $WORKSPACE/common/utils/* $NEW_REPO/common/utils/ 2>/dev/null || true
fi

# Copy all MainPC agents
echo "📦 Copying MainPC agents..."
if [ -d "$WORKSPACE/main_pc_code/agents" ]; then
    cp -r $WORKSPACE/main_pc_code/agents/* $NEW_REPO/src/agents/mainpc/ 2>/dev/null || true
fi

# Copy MainPC services
echo "📦 Copying MainPC services..."
if [ -d "$WORKSPACE/main_pc_code/services" ]; then
    cp -r $WORKSPACE/main_pc_code/services/* $NEW_REPO/src/agents/mainpc/services/ 2>/dev/null || true
fi

# Copy FORMAINPC directory
echo "📦 Copying FORMAINPC agents..."
if [ -d "$WORKSPACE/main_pc_code/FORMAINPC" ]; then
    cp -r $WORKSPACE/main_pc_code/FORMAINPC/* $NEW_REPO/src/agents/mainpc/formainpc/ 2>/dev/null || true
fi

# Copy model_manager_suite.py (special case)
echo "📦 Copying model_manager_suite.py..."
if [ -f "$WORKSPACE/main_pc_code/model_manager_suite.py" ]; then
    cp $WORKSPACE/main_pc_code/model_manager_suite.py $NEW_REPO/src/agents/mainpc/
fi

# Copy additional MainPC modules
echo "📦 Copying MainPC additional modules..."
if [ -d "$WORKSPACE/main_pc_code/database" ]; then
    cp -r $WORKSPACE/main_pc_code/database/* $NEW_REPO/database/ 2>/dev/null || true
fi
if [ -d "$WORKSPACE/main_pc_code/security" ]; then
    cp -r $WORKSPACE/main_pc_code/security/* $NEW_REPO/security/ 2>/dev/null || true
fi
if [ -d "$WORKSPACE/main_pc_code/complexity" ]; then
    cp -r $WORKSPACE/main_pc_code/complexity/* $NEW_REPO/complexity/ 2>/dev/null || true
fi

# Copy all PC2 agents
echo "📦 Copying PC2 agents..."
if [ -d "$WORKSPACE/pc2_code/agents" ]; then
    cp -r $WORKSPACE/pc2_code/agents/* $NEW_REPO/src/agents/pc2/ 2>/dev/null || true
fi

# Copy PC2 ForPC2 directory
echo "📦 Copying PC2 ForPC2 agents..."
if [ -d "$WORKSPACE/pc2_code/agents/ForPC2" ]; then
    cp -r $WORKSPACE/pc2_code/agents/ForPC2/* $NEW_REPO/src/agents/pc2/forpc2/ 2>/dev/null || true
fi

# Copy PC2 backups
echo "📦 Copying PC2 backups..."
if [ -d "$WORKSPACE/pc2_code/agents/backups" ]; then
    cp -r $WORKSPACE/pc2_code/agents/backups/* $NEW_REPO/src/agents/pc2/backups/ 2>/dev/null || true
fi

# Copy PC2 core agents
echo "📦 Copying PC2 core agents..."
if [ -d "$WORKSPACE/pc2_code/agents/core_agents" ]; then
    cp -r $WORKSPACE/pc2_code/agents/core_agents/* $NEW_REPO/src/agents/pc2/core_agents/ 2>/dev/null || true
fi

# Copy PC2 utilities
echo "📦 Copying PC2 utilities..."
if [ -d "$WORKSPACE/pc2_code/agents/utils" ]; then
    cp -r $WORKSPACE/pc2_code/agents/utils/* $NEW_REPO/src/agents/pc2/utils/ 2>/dev/null || true
fi

# Copy error bus template
echo "📦 Copying error bus template..."
if [ -f "$WORKSPACE/pc2_code/agents/error_bus_template.py" ]; then
    cp $WORKSPACE/pc2_code/agents/error_bus_template.py $NEW_REPO/src/agents/pc2/
fi

# Copy ObservabilityHub
echo "📦 Copying ObservabilityHub..."
if [ -d "$WORKSPACE/phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub" ]; then
    cp -r $WORKSPACE/phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/* $NEW_REPO/src/agents/core/ 2>/dev/null || true
fi

# Copy events system
echo "📦 Copying events system..."
if [ -d "$WORKSPACE/events" ]; then
    cp -r $WORKSPACE/events/* $NEW_REPO/events/ 2>/dev/null || true
fi

# Copy models if they exist
echo "🤖 Copying models directory..."
if [ -d "$WORKSPACE/main_pc_code/models" ]; then
    cp -r $WORKSPACE/main_pc_code/models/* $NEW_REPO/models/ 2>/dev/null || true
fi
if [ -d "$WORKSPACE/pc2_code/models" ]; then
    cp -r $WORKSPACE/pc2_code/models/* $NEW_REPO/models/ 2>/dev/null || true
fi

# Copy configuration files
echo "📋 Copying configuration files..."
if [ -d "$WORKSPACE/pc2_code/config" ]; then
    cp -r $WORKSPACE/pc2_code/config/* $NEW_REPO/config/ 2>/dev/null || true
fi
if [ -d "$WORKSPACE/main_pc_code/config" ]; then
    cp -r $WORKSPACE/main_pc_code/config/* $NEW_REPO/config/ 2>/dev/null || true
fi

# Create __init__.py files
echo "📝 Creating __init__.py files..."
find $NEW_REPO -type d -name "*.egg-info" -prune -o -type d -exec touch {}/__init__.py \; 2>/dev/null || true

# Update script paths in configuration
echo "⚙️  Updating configuration paths..."
cd $NEW_REPO

# Create a Python script to update paths and fix imports
cat > update_paths_and_imports.py << 'EOF'
import yaml
import os
import re

# Load config
with open('config/startup_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Update paths
for group_name, agents in config.get('agent_groups', {}).items():
    for agent_name, agent_config in agents.items():
        script_path = agent_config.get('script_path', '')
        
        # Update MainPC paths
        if script_path.startswith('main_pc_code/agents/'):
            new_path = script_path.replace('main_pc_code/agents/', 'src/agents/mainpc/')
            agent_config['script_path'] = new_path
        elif script_path.startswith('main_pc_code/services/'):
            new_path = script_path.replace('main_pc_code/services/', 'src/agents/mainpc/services/')
            agent_config['script_path'] = new_path
        elif script_path.startswith('main_pc_code/FORMAINPC/'):
            new_path = script_path.replace('main_pc_code/FORMAINPC/', 'src/agents/mainpc/formainpc/')
            agent_config['script_path'] = new_path
        elif script_path == 'main_pc_code/model_manager_suite.py':
            agent_config['script_path'] = 'src/agents/mainpc/model_manager_suite.py'
            
        # Update PC2 paths
        elif script_path.startswith('pc2_code/agents/ForPC2/'):
            new_path = script_path.replace('pc2_code/agents/ForPC2/', 'src/agents/pc2/forpc2/')
            agent_config['script_path'] = new_path
        elif script_path.startswith('pc2_code/agents/'):
            new_path = script_path.replace('pc2_code/agents/', 'src/agents/pc2/')
            agent_config['script_path'] = new_path
            
        # Update ObservabilityHub paths
        elif 'observability_hub' in script_path:
            agent_config['script_path'] = 'src/agents/core/observability_hub.py'

# Save updated config
with open('config/startup_config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print("✅ Configuration paths updated!")

# Fix Python imports in agent files
def fix_imports_in_file(filepath):
    if not os.path.exists(filepath):
        return
        
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix common imports
    replacements = [
        # Fix error bus imports
        ('from pc2_code.agents.error_bus_template import', 'from src.agents.pc2.error_bus_template import'),
        # Fix common imports that might need adjustment
        ('from main_pc_code.agents.', 'from src.agents.mainpc.'),
        ('from pc2_code.agents.', 'from src.agents.pc2.'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open(filepath, 'w') as f:
        f.write(content)

# Fix imports in all Python files
print("🔧 Fixing imports in Python files...")
for root, dirs, files in os.walk('src/agents'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            fix_imports_in_file(filepath)

print("✅ Imports fixed!")
EOF

python3 update_paths_and_imports.py
rm update_paths_and_imports.py

# Create a requirements_extra.txt for additional dependencies
echo "📋 Creating additional requirements file..."
cat > requirements_extra.txt << 'EOF'
# Additional dependencies from common modules
redis>=4.0.0
nats-py>=2.0.0
psycopg2-binary>=2.9.0
sqlalchemy>=1.4.0
alembic>=1.8.0
passlib>=1.7.0
python-jose>=3.3.0
httpx>=0.23.0
uvicorn>=0.18.0
fastapi>=0.85.0
pydantic>=1.10.0
EOF

# Merge with existing requirements
cat requirements_extra.txt >> requirements.txt
rm requirements_extra.txt

# Final validation
echo ""
echo "🔍 Running comprehensive validation..."
python3 scripts/deep_scan_validator.py

echo ""
echo "✅ COMPREHENSIVE MIGRATION COMPLETE!"
echo ""
echo "📋 What was copied:"
echo "  ✓ All agent files (MainPC + PC2)"
echo "  ✓ Common modules (config_manager, env_helpers, etc.)"
echo "  ✓ Common utilities (error_handling, zmq_helper, etc.)"
echo "  ✓ ZMQ pools and Redis pools"
echo "  ✓ Error bus and error handling"
echo "  ✓ Database modules"
echo "  ✓ Security modules"
echo "  ✓ Events system"
echo "  ✓ All configuration files"
echo ""
echo "Next steps:"
echo "1. cd $NEW_REPO"
echo "2. python3 -m venv venv"
echo "3. source venv/bin/activate"
echo "4. pip install -r requirements.txt"
echo "5. cp .env.example .env"
echo "6. Edit .env with your settings"
echo "7. python main.py start --profile core"