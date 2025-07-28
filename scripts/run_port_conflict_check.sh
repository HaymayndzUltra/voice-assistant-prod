#!/bin/bash
# Port conflict detection script for CI/CD pipeline

set -e

echo "=== Port Conflict Detection ==="

# Configuration files to check
CONFIG_FILES=(
    "main_pc_code/config/startup_config.yaml"
    "pc2_code/config/startup_config.yaml"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to extract ports from YAML config
extract_ports() {
    local config_file="$1"
    local prefix="$2"
    
    if [[ ! -f "$config_file" ]]; then
        echo -e "${YELLOW}Warning: Config file not found: $config_file${NC}"
        return 0
    fi
    
    echo "Extracting ports from: $config_file"
    
    # Extract main ports and health check ports
    grep -E "(port:|health_check_port:)" "$config_file" | \
    sed 's/.*PORT_OFFSET.*+//' | \
    sed 's/[^0-9]*//g' | \
    grep -v '^$' | \
    sort -n | \
    while read port; do
        echo "${prefix}_${port}"
    done
}

# Function to check for duplicates
check_duplicates() {
    local all_ports_file="$1"
    
    echo "Checking for duplicate port assignments..."
    
    duplicates=$(sort "$all_ports_file" | uniq -d)
    
    if [[ -n "$duplicates" ]]; then
        echo -e "${RED}❌ DUPLICATE PORTS FOUND:${NC}"
        echo "$duplicates" | while read duplicate; do
            echo -e "${RED}  - Port $duplicate is assigned multiple times${NC}"
        done
        return 1
    else
        echo -e "${GREEN}✅ No duplicate ports found${NC}"
        return 0
    fi
}

# Function to check for port conflicts between services
check_conflicts() {
    local all_ports_file="$1"
    
    echo "Checking for potential port range conflicts..."
    
    # Check for ports that are too close together (might conflict with +1 offsets)
    sort -n "$all_ports_file" | \
    awk '{
        if (prev != "" && $1 - prev <= 1) {
            print "WARNING: Ports " prev " and " $1 " are very close together"
            conflicts++
        }
        prev = $1
    } 
    END {
        if (conflicts > 0) {
            print "Found " conflicts " potential conflicts"
            exit 1
        }
    }'
}

# Main execution
main() {
    local temp_file=$(mktemp)
    local exit_code=0
    
    echo "Starting port conflict check..."
    
    # Extract all ports from all config files
    for config in "${CONFIG_FILES[@]}"; do
        if [[ -f "$config" ]]; then
            extract_ports "$config" "$(basename $config .yaml)" >> "$temp_file"
        fi
    done
    
    # Check for duplicates
    if ! check_duplicates "$temp_file"; then
        exit_code=1
    fi
    
    # Check for conflicts
    if ! check_conflicts "$temp_file"; then
        exit_code=1
    fi
    
    # Summary
    echo ""
    echo "=== Summary ==="
    total_ports=$(wc -l < "$temp_file")
    unique_ports=$(sort "$temp_file" | uniq | wc -l)
    
    echo "Total port assignments: $total_ports"
    echo "Unique ports: $unique_ports"
    
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}✅ Port conflict check PASSED${NC}"
    else
        echo -e "${RED}❌ Port conflict check FAILED${NC}"
    fi
    
    # Cleanup
    rm -f "$temp_file"
    
    exit $exit_code
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
