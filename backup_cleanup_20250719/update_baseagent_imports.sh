#!/bin/bash

AGENT_FILES=(
$(cat agent_paths_cleaned.txt)
)

for file in "${AGENT_FILES[@]}"; do
    if [ -f "$file" ]; then
        sed -i 's/from \(main_pc_code\.\)\?src\.core\.base_agent import BaseAgent/from common.core.base_agent import BaseAgent/g' "$file"
        echo "Checked and updated: $file"
    else
        echo "Warning: File not found, skipping: $file"
    fi
done

echo "---"
echo "Import update process completed for all active agents." 