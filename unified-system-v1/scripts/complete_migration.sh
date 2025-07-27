#!/bin/bash
# Complete Migration Script for Unified System
# This script copies ALL necessary files from the original workspace

echo "🚀 COMPLETE MIGRATION SCRIPT FOR UNIFIED SYSTEM"
echo "=============================================="

# Set paths
WORKSPACE="/workspace"
NEW_REPO="/workspace/unified-system-v1"

# Create all necessary directories
echo "📁 Creating directory structure..."
mkdir -p $NEW_REPO/src/agents/mainpc/{services,formainpc}
mkdir -p $NEW_REPO/src/agents/pc2/{forpc2,backups}
mkdir -p $NEW_REPO/src/agents/core
mkdir -p $NEW_REPO/src/utils/core
mkdir -p $NEW_REPO/models
mkdir -p $NEW_REPO/data
mkdir -p $NEW_REPO/common/core

# Copy BaseAgent (CRITICAL!)
echo "⚡ Copying BaseAgent (critical component)..."
cp $WORKSPACE/common/core/base_agent.py $NEW_REPO/src/utils/
cp $WORKSPACE/common/core/base_agent.py $NEW_REPO/common/core/
cp $WORKSPACE/common/core/enhanced_base_agent.py $NEW_REPO/common/core/

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

# Copy ObservabilityHub
echo "📦 Copying ObservabilityHub..."
if [ -d "$WORKSPACE/phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub" ]; then
    cp -r $WORKSPACE/phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/* $NEW_REPO/src/agents/core/ 2>/dev/null || true
fi

# Copy utilities
echo "🔧 Copying utilities..."
if [ -d "$WORKSPACE/main_pc_code/utils" ]; then
    cp -r $WORKSPACE/main_pc_code/utils/* $NEW_REPO/src/utils/ 2>/dev/null || true
fi
if [ -d "$WORKSPACE/pc2_code/utils" ]; then
    cp -r $WORKSPACE/pc2_code/utils/* $NEW_REPO/src/utils/ 2>/dev/null || true
fi

# Copy common utilities
echo "🔧 Copying common utilities..."
if [ -d "$WORKSPACE/common" ]; then
    cp -r $WORKSPACE/common/* $NEW_REPO/common/ 2>/dev/null || true
fi

# Copy models if they exist
echo "🤖 Copying models directory..."
if [ -d "$WORKSPACE/main_pc_code/models" ]; then
    cp -r $WORKSPACE/main_pc_code/models/* $NEW_REPO/models/ 2>/dev/null || true
fi
if [ -d "$WORKSPACE/pc2_code/models" ]; then
    cp -r $WORKSPACE/pc2_code/models/* $NEW_REPO/models/ 2>/dev/null || true
fi

# Update script paths in configuration
echo "⚙️  Updating configuration paths..."
cd $NEW_REPO

# Create a Python script to update paths
cat > update_paths.py << 'EOF'
import yaml

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
EOF

python3 update_paths.py
rm update_paths.py

# Final checks
echo ""
echo "🔍 Running validation..."
python3 scripts/validate_repository.py

echo ""
echo "✅ MIGRATION COMPLETE!"
echo ""
echo "Next steps:"
echo "1. cd $NEW_REPO"
echo "2. python3 -m venv venv"
echo "3. source venv/bin/activate"
echo "4. pip install -r requirements.txt"
echo "5. cp .env.example .env"
echo "6. python main.py start --profile core"