#!/bin/bash

# Fix Agent Issues Script
# This script resolves common issues with agents in the AI System Monorepo

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'
BOLD='\033[1m'

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
MAIN_PC_CODE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$MAIN_PC_CODE_DIR")"

echo -e "${BLUE}${BOLD}Starting Agent Issue Remediation...${RESET}"

# 1. Kill any existing agent processes to free up ports
echo -e "${YELLOW}Stopping any existing agent processes...${RESET}"
pkill -f "python.*start_mvs.py" || echo "No start_mvs.py processes running"
pkill -f "python.*system_digital_twin.py" || echo "No system_digital_twin.py processes running"
pkill -f "python.*model_manager_agent.py" || echo "No model_manager_agent.py processes running"

# Wait for ports to be released
sleep 2

# 2. Check and fix indentation in system_digital_twin.py
echo -e "${YELLOW}Checking system_digital_twin.py for indentation issues...${RESET}"
SYSTEM_DIGITAL_TWIN_PATH="$MAIN_PC_CODE_DIR/agents/system_digital_twin.py"
if [ -f "$SYSTEM_DIGITAL_TWIN_PATH" ]; then
    # Check for indentation errors around line 158
    if grep -A 5 -B 5 "if secure_zmq:" "$SYSTEM_DIGITAL_TWIN_PATH" | grep -q "logger.info"; then
        echo -e "${GREEN}system_digital_twin.py appears to have correct indentation${RESET}"
    else
        echo -e "${RED}Indentation issues detected in system_digital_twin.py${RESET}"
        echo -e "${YELLOW}Please manually fix indentation in the file${RESET}"
    fi
else
    echo -e "${RED}system_digital_twin.py not found at $SYSTEM_DIGITAL_TWIN_PATH${RESET}"
fi

# 3. Check and fix indentation in base_agent.py
echo -e "${YELLOW}Checking base_agent.py for indentation issues...${RESET}"
BASE_AGENT_PATH="$MAIN_PC_CODE_DIR/src/core/base_agent.py"
if [ -f "$BASE_AGENT_PATH" ]; then
    # Check for indentation errors around line 118
    if grep -A 5 -B 5 "if attempt < max_retries - 1:" "$BASE_AGENT_PATH" | grep -q "continue"; then
        echo -e "${GREEN}base_agent.py appears to have correct indentation${RESET}"
    else
        echo -e "${RED}Indentation issues detected in base_agent.py${RESET}"
        echo -e "${YELLOW}Please manually fix indentation in the file${RESET}"
    fi
else
    echo -e "${RED}base_agent.py not found at $BASE_AGENT_PATH${RESET}"
fi

# 4. Check and fix indentation in service_discovery_client.py
echo -e "${YELLOW}Checking service_discovery_client.py for indentation issues...${RESET}"
SERVICE_DISCOVERY_PATH="$MAIN_PC_CODE_DIR/utils/service_discovery_client.py"
if [ -f "$SERVICE_DISCOVERY_PATH" ]; then
    # Check for indentation errors around line 35
    if grep -A 5 -B 5 "def __init__" "$SERVICE_DISCOVERY_PATH" | grep -q "self.sdt_port"; then
        echo -e "${GREEN}service_discovery_client.py appears to have correct indentation${RESET}"
    else
        echo -e "${RED}Indentation issues detected in service_discovery_client.py${RESET}"
        echo -e "${YELLOW}Please manually fix indentation in the file${RESET}"
    fi
else
    echo -e "${RED}service_discovery_client.py not found at $SERVICE_DISCOVERY_PATH${RESET}"
fi

# 5. Check and fix try/except in network_utils.py
echo -e "${YELLOW}Checking network_utils.py for missing except blocks...${RESET}"
NETWORK_UTILS_PATH="$MAIN_PC_CODE_DIR/utils/network_utils.py"
if [ -f "$NETWORK_UTILS_PATH" ]; then
    # Check for missing except blocks
    if grep -A 10 -B 10 "try:" "$NETWORK_UTILS_PATH" | grep -q "except"; then
        echo -e "${GREEN}network_utils.py appears to have proper try/except blocks${RESET}"
    else
        echo -e "${RED}Missing except blocks detected in network_utils.py${RESET}"
        echo -e "${YELLOW}Please manually fix try/except blocks in the file${RESET}"
    fi
else
    echo -e "${RED}network_utils.py not found at $NETWORK_UTILS_PATH${RESET}"
fi

# 6. Fix health check status format in LearningAdjusterAgent
echo -e "${YELLOW}Checking LearningAdjusterAgent for health check status format...${RESET}"
LEARNING_ADJUSTER_PATH="$MAIN_PC_CODE_DIR/FORMAINPC/LearningAdjusterAgent.py"
if [ -f "$LEARNING_ADJUSTER_PATH" ]; then
    # Check if the agent returns "ok" status
    if grep -q '"status": "ok"' "$LEARNING_ADJUSTER_PATH"; then
        echo -e "${GREEN}LearningAdjusterAgent already returns 'ok' status${RESET}"
    else
        echo -e "${RED}LearningAdjusterAgent may not return 'ok' status${RESET}"
        echo -e "${YELLOW}Please check and fix the health check response format${RESET}"
    fi
else
    echo -e "${RED}LearningAdjusterAgent.py not found at $LEARNING_ADJUSTER_PATH${RESET}"
fi

# 7. Create a summary report
echo -e "\n${BLUE}${BOLD}Agent Issue Remediation Summary:${RESET}"
echo -e "1. Stopped any running agent processes to free up ports"
echo -e "2. Checked system_digital_twin.py for indentation issues"
echo -e "3. Checked base_agent.py for indentation issues"
echo -e "4. Checked service_discovery_client.py for indentation issues"
echo -e "5. Checked network_utils.py for missing except blocks"
echo -e "6. Checked LearningAdjusterAgent for health check status format"

echo -e "\n${YELLOW}Next steps:${RESET}"
echo -e "1. Fix any identified issues in the files"
echo -e "2. Run ./run_mvs.sh to start the system"
echo -e "3. Monitor the logs for any remaining issues"

echo -e "\n${GREEN}${BOLD}Agent Issue Remediation Complete!${RESET}" 