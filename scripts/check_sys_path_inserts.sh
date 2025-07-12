#!/bin/bash

# Script to check if new sys.path.insert calls have been introduced
# This is a non-blocking check that should be run in CI

set -e

echo "Checking for new sys.path.insert calls..."

# Get count from main branch
echo "Counting sys.path.insert calls in main branch..."
git fetch origin main --quiet
MAIN_COUNT=$(git show origin/main: -- . | grep -c "sys.path.insert(0" || echo 0)

# Get count from current branch
echo "Counting sys.path.insert calls in current branch..."
CURRENT_COUNT=$(grep -r "sys.path.insert(0" --include="*.py" . | wc -l || echo 0)

echo "Main branch count: $MAIN_COUNT"
echo "Current branch count: $CURRENT_COUNT"

# Fail if count has increased
if [ "$CURRENT_COUNT" -gt "$MAIN_COUNT" ]; then
    echo "ERROR: New sys.path.insert calls detected!"
    echo "Please use proper imports instead of modifying sys.path."
    echo "See MainPcDocs/SYSTEM_DOCUMENTATION/DEV_GUIDE/01_package_layout.md for guidance."
    exit 1
else
    echo "No new sys.path.insert calls detected. Good job!"
    if [ "$CURRENT_COUNT" -lt "$MAIN_COUNT" ]; then
        echo "In fact, you've removed some sys.path.insert calls. Great progress!"
    fi
    exit 0
fi 