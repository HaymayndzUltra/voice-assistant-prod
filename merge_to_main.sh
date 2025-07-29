#!/bin/bash

# Merge feature/memory-system-evolution to main branch
# This script will safely merge the current feature branch to main

echo "🔄 Starting merge process..."
echo "Current branch: $(git branch --show-current)"
echo ""

# Check if we have uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo "❌ Error: You have uncommitted changes. Please commit or stash them first."
    git status
    exit 1
fi

# Store current branch name
CURRENT_BRANCH=$(git branch --show-current)
echo "📋 Current branch: $CURRENT_BRANCH"

# Switch to main branch
echo "🔄 Switching to main branch..."
git checkout main
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to switch to main branch"
    exit 1
fi

# Pull latest changes from main
echo "📥 Pulling latest changes from main..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to pull latest changes from main"
    exit 1
fi

# Merge the feature branch
echo "🔀 Merging $CURRENT_BRANCH into main..."
git merge $CURRENT_BRANCH
if [ $? -ne 0 ]; then
    echo "❌ Error: Merge conflict detected. Please resolve conflicts manually."
    echo "You can:"
    echo "  1. Resolve conflicts in the files"
    echo "  2. git add ."
    echo "  3. git commit"
    echo "  4. Run this script again"
    exit 1
fi

# Push the merged changes
echo "📤 Pushing merged changes to main..."
git push origin main
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to push to main"
    exit 1
fi

echo ""
echo "✅ SUCCESS: $CURRENT_BRANCH has been successfully merged to main!"
echo ""
echo "📊 Summary:"
echo "  - Source branch: $CURRENT_BRANCH"
echo "  - Target branch: main"
echo "  - Status: Merged and pushed"
echo ""
echo "🔄 You can now switch back to your feature branch:"
echo "  git checkout $CURRENT_BRANCH" 