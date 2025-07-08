#!/bin/bash

# Agent Discovery and Reporting Script
# This script runs the agent discovery process and generates all reports

# Set variables
OUTPUT_DIR="./analysis_output"
JSON_REPORT="$OUTPUT_DIR/active_agents_report.json"
MD_REPORT="$OUTPUT_DIR/active_agents_report.md"
SOT_FILE="$OUTPUT_DIR/source_of_truth.yaml"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$OUTPUT_DIR/agent_discovery_${TIMESTAMP}.log"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "====================================================="
echo "      AI System Agent Discovery and Reporting"
echo "====================================================="
echo "Started at: $(date)"
echo "Log file: $LOG_FILE"
echo

# Function to log messages
log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1" | tee -a "$LOG_FILE"
}

# Make scripts executable
log "Making scripts executable..."
chmod +x scripts/discover_active_agents.py
chmod +x scripts/generate_agents_report.py
chmod +x scripts/rebuild_source_of_truth.py

# Step 1: Run the agent discovery script
log "Step 1: Discovering active agents..."
python scripts/discover_active_agents.py --output "$JSON_REPORT" 2>&1 | tee -a "$LOG_FILE"

# Check if the discovery was successful
if [ ! -f "$JSON_REPORT" ]; then
    log "ERROR: Agent discovery failed. JSON report not generated."
    exit 1
fi

# Step 2: Generate the markdown report
log "Step 2: Generating markdown report..."
python scripts/generate_agents_report.py --input "$JSON_REPORT" --output "$MD_REPORT" 2>&1 | tee -a "$LOG_FILE"

# Step 3: Rebuild the source of truth file
log "Step 3: Rebuilding source of truth file..."
python scripts/rebuild_source_of_truth.py --input "$JSON_REPORT" --output "$SOT_FILE" 2>&1 | tee -a "$LOG_FILE"

# Step 4: Create a backup of the current source of truth file if it exists
if [ -f "pc2_code/_pc2mainpcSOT.yaml" ]; then
    BACKUP_FILE="pc2_code/_pc2mainpcSOT.yaml.bak_${TIMESTAMP}"
    log "Creating backup of existing source of truth file: $BACKUP_FILE"
    cp "pc2_code/_pc2mainpcSOT.yaml" "$BACKUP_FILE"
fi

# Summary
log "====================================================="
log "Discovery and reporting complete!"
log "JSON Report: $JSON_REPORT"
log "Markdown Report: $MD_REPORT"
log "Source of Truth: $SOT_FILE"
log "====================================================="

# Open the markdown report if xdg-open is available
if command -v xdg-open &> /dev/null; then
    log "Opening markdown report..."
    xdg-open "$MD_REPORT" &
else
    log "Report generated. You can open it manually at: $MD_REPORT"
fi

echo
echo "To apply the new source of truth file, review it and then run:"
echo "cp $SOT_FILE pc2_code/_pc2mainpcSOT.yaml"
echo 