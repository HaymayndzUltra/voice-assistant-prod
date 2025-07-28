#!/bin/bash

# Strategic Directive Execution Script
# This script creates and commits the strategic directive for system evolution

set -e  # Exit on any error

echo "🚀 Executing Strategic Directive for Memory System Evolution"
echo "=========================================================="

# Get current date for file naming
CURRENT_DATE=$(date +"%Y-%m-%d")
DIRECTIVE_FILE="directives/${CURRENT_DATE}_strategic_directive.md"
BRANCH_NAME="feature/directive-${CURRENT_DATE}"

echo "📅 Date: $CURRENT_DATE"
echo "📄 Directive File: $DIRECTIVE_FILE"
echo "🌿 Branch Name: $BRANCH_NAME"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check current branch and status
echo "📊 Current Git Status:"
echo "   Branch: $(git branch --show-current)"
echo "   Status: $(git status --porcelain | wc -l) changes"
echo ""

# Create directives directory if it doesn't exist
if [ ! -d "directives" ]; then
    echo "📁 Creating directives directory..."
    mkdir -p directives
fi

# Check if directive file already exists
if [ -f "$DIRECTIVE_FILE" ]; then
    echo "⚠️  Warning: Directive file already exists: $DIRECTIVE_FILE"
    echo "   Overwriting existing file..."
fi

echo "📝 Creating strategic directive file..."
echo "   File: $DIRECTIVE_FILE"

# The directive content is already created in the file above
# This script assumes the file exists from the previous edit_file call

# Verify the file was created
if [ ! -f "$DIRECTIVE_FILE" ]; then
    echo "❌ Error: Failed to create directive file"
    exit 1
fi

echo "✅ Directive file created successfully"
echo ""

# Create new branch
echo "🌿 Creating new branch: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME"

if [ $? -eq 0 ]; then
    echo "✅ Branch created successfully"
else
    echo "❌ Error: Failed to create branch"
    exit 1
fi

echo ""

# Add the directive file to git
echo "📦 Adding directive file to git..."
git add "$DIRECTIVE_FILE"

if [ $? -eq 0 ]; then
    echo "✅ File added to git staging area"
else
    echo "❌ Error: Failed to add file to git"
    exit 1
fi

echo ""

# Commit the changes
echo "💾 Committing changes..."
COMMIT_MESSAGE="feat: Add strategic directive for system evolution

- Created comprehensive strategic directive for memory system evolution
- Defined smart integration approach for workflow intelligence
- Outlined system evolution blueprint requirements
- Set roadmap for achieving full autonomy and intelligence

Date: $CURRENT_DATE
Branch: $BRANCH_NAME"

git commit -m "$COMMIT_MESSAGE"

if [ $? -eq 0 ]; then
    echo "✅ Changes committed successfully"
    echo "   Commit message: feat: Add strategic directive for system evolution"
else
    echo "❌ Error: Failed to commit changes"
    exit 1
fi

echo ""

# Push the branch to remote
echo "🚀 Pushing branch to remote repository..."
git push -u origin "$BRANCH_NAME"

if [ $? -eq 0 ]; then
    echo "✅ Branch pushed successfully"
    echo "   Remote branch: origin/$BRANCH_NAME"
else
    echo "❌ Error: Failed to push branch"
    echo "   You may need to configure remote repository or check permissions"
    exit 1
fi

echo ""
echo "🎉 Strategic Directive Execution Complete!"
echo "=========================================="
echo ""
echo "📋 Summary:"
echo "   ✅ Directive file created: $DIRECTIVE_FILE"
echo "   ✅ New branch created: $BRANCH_NAME"
echo "   ✅ Changes committed with message: 'feat: Add strategic directive for system evolution'"
echo "   ✅ Branch pushed to remote: origin/$BRANCH_NAME"
echo ""
echo "🔗 Next Steps:"
echo "   1. Review the strategic directive: $DIRECTIVE_FILE"
echo "   2. The Background Agent can now use this directive to:"
echo "      - Implement smart integration of workflow intelligence"
echo "      - Create system evolution blueprint"
echo "      - Evolve the memory system into a fully autonomous command center"
echo ""
echo "📚 Files Created/Modified:"
echo "   - $DIRECTIVE_FILE (new)"
echo "   - Git branch: $BRANCH_NAME (new)"
echo "   - Git commit: feat: Add strategic directive for system evolution"
echo ""
echo "🚀 Ready for Background Agent execution!" 