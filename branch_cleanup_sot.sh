#!/bin/bash

# SOT Branch Cleanup Script
# Purpose: Clean up all branches and create fresh SOT branch for background agent

echo "🔥 Starting SOT Branch Cleanup..."

# Step 1: Save current work
echo "📝 Saving current work..."
git add .
git commit -m "SOT-PREP: Comprehensive audit setup and config corrections

- Updated audit.md with comprehensive MainPC+PC2 requirements
- Added startup_config_corrected.yaml for PC2
- Enhanced audit instructions with security and dependency mapping
- Ready for background agent comprehensive audit execution
- Includes Phase 1 consolidation context and cleanup recommendations"

# Step 2: Create new SOT branch
echo "🌟 Creating new SOT branch..."
git checkout -b "sot/comprehensive-audit-cleanup-2025"

# Step 3: Push new SOT branch
echo "📤 Pushing SOT branch to origin..."
git push -u origin sot/comprehensive-audit-cleanup-2025

# Step 4: List all branches for cleanup
echo "📋 Current branches:"
git branch -a

# Step 5: Delete old local branches (excluding current SOT)
echo "🗑️ Cleaning up old local branches..."
git branch | grep -v "sot/comprehensive-audit-cleanup-2025" | grep -v "main" | grep -v "master" | xargs -r git branch -D

# Step 6: Delete old remote tracking branches
echo "🌐 Cleaning up remote tracking branches..."
git remote prune origin

# Step 7: Verification
echo "✅ Branch cleanup complete!"
echo "📊 Current status:"
git status
echo ""
echo "🌿 Active branches:"
git branch -a

echo ""
echo "🎯 SOT Branch Created: sot/comprehensive-audit-cleanup-2025"
echo "📋 This branch contains:"
echo "   ✅ Updated comprehensive audit instructions"
echo "   ✅ PC2 configuration corrections"
echo "   ✅ MainPC agent analysis"
echo "   ✅ Phase 1 consolidation context"
echo "   ✅ Ready for background agent execution"
echo ""
echo "🔄 Background agent can now access latest state for audit execution" 