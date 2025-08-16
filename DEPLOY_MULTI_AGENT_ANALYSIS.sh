#!/bin/bash
# Multi-Agent Docker Architecture Analysis Deployment Script
# Purpose: Deploy the problem to multiple Background Agents for comprehensive analysis

set -e

echo "=========================================="
echo "Multi-Agent Docker Architecture Analysis"
echo "=========================================="

# Configuration
SESSION_ID="DOCKER_ANALYSIS_$(date +%Y%m%d_%H%M%S)"
AGENTS=("ALPHA_SECURITY" "BETA_OPERATIONS" "GAMMA_ARCHITECTURE")
PROBLEM_FILE="MASTER_PROBLEM_DOCKER_ARCHITECTURE.md"
BASE_PATH="/memory-bank/multi-agent/${SESSION_ID}"

# Create session directory
echo "Creating session directory: ${BASE_PATH}"
mkdir -p "${BASE_PATH}"

# Generate problem hash
PROBLEM_HASH=$(sha256sum "${PROBLEM_FILE}" | cut -d' ' -f1)
echo "Problem hash: ${PROBLEM_HASH}"

# Copy problem statement
cp "${PROBLEM_FILE}" "${BASE_PATH}/MASTER_PROBLEM.md"

# Create agent-specific prompts
for AGENT in "${AGENTS[@]}"; do
    AGENT_PATH="${BASE_PATH}/${AGENT}"
    mkdir -p "${AGENT_PATH}/input"
    mkdir -p "${AGENT_PATH}/output"
    
    # Create agent-specific instructions
    cat > "${AGENT_PATH}/input/instructions.md" << EOF
# Agent: ${AGENT}
# Session: ${SESSION_ID}
# Problem Hash: ${PROBLEM_HASH}

## Your Focus Area

EOF
    
    case "${AGENT}" in
        "ALPHA_SECURITY")
            cat >> "${AGENT_PATH}/input/instructions.md" << 'EOF'
You are ALPHA_SECURITY. Focus your analysis on:
- Security vulnerabilities (docker.sock and beyond)
- Secrets management and credential exposure
- Network security between machines
- Container escape risks
- RBAC and access control
- Supply chain security (base images)
- CVE scanning and vulnerability management
EOF
            ;;
            
        "BETA_OPERATIONS")
            cat >> "${AGENT_PATH}/input/instructions.md" << 'EOF'
You are BETA_OPERATIONS. Focus your analysis on:
- Deployment readiness and procedures
- Service discovery mechanisms
- Health checks and monitoring
- Log aggregation and metrics
- Failure scenarios and recovery
- Database and state management
- Backup and disaster recovery
- Rolling updates and zero-downtime deployment
EOF
            ;;
            
        "GAMMA_ARCHITECTURE")
            cat >> "${AGENT_PATH}/input/instructions.md" << 'EOF'
You are GAMMA_ARCHITECTURE. Focus your analysis on:
- Base image hierarchy optimization
- Service dependencies and circular references
- Port allocation and conflicts
- Machine assignment optimization (GPU/CPU)
- Build pipeline and CI/CD
- Performance and caching strategy
- Network topology and latency
- Microservices patterns and anti-patterns
EOF
            ;;
    esac
    
    # Copy the main problem
    cp "${BASE_PATH}/MASTER_PROBLEM.md" "${AGENT_PATH}/input/problem.md"
    
    # Create status file
    cat > "${AGENT_PATH}/status.txt" << EOF
AGENT: ${AGENT}
STATUS: READY
CREATED: $(date -Iseconds)
SESSION: ${SESSION_ID}
EOF
    
    echo "✓ Agent ${AGENT} initialized"
done

# Create orchestration config
cat > "${BASE_PATH}/orchestration.json" << EOF
{
  "session_id": "${SESSION_ID}",
  "problem_hash": "${PROBLEM_HASH}",
  "agents": [
    "ALPHA_SECURITY",
    "BETA_OPERATIONS", 
    "GAMMA_ARCHITECTURE"
  ],
  "created_at": "$(date -Iseconds)",
  "timeout_minutes": 60,
  "resolution_strategy": "EVIDENCE_BASED",
  "expected_outputs": {
    "phase1": "Independent analysis from each agent",
    "phase2": "Synthesis and CCC matrix",
    "phase3": "Conflict resolution",
    "phase4": "Final consolidated Blueprint v1.1"
  }
}
EOF

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Session ID: ${SESSION_ID}"
echo "Base Path: ${BASE_PATH}"
echo ""
echo "Next Steps:"
echo "1. Deploy to Background Agents:"
echo ""

for AGENT in "${AGENTS[@]}"; do
    echo "   cursor-agent --background \\"
    echo "     --name \"${AGENT}\" \\"
    echo "     --task \"Analyze ${BASE_PATH}/${AGENT}/input/problem.md per instructions\" \\"
    echo "     --output \"${BASE_PATH}/${AGENT}/output/\" \\"
    echo "     --timeout 60"
    echo ""
done

echo "2. After all agents complete, run synthesis:"
echo "   python3 multi-agent-orchestrator.py \\"
echo "     --session ${SESSION_ID} \\"
echo "     --synthesize"
echo ""
echo "3. Review final consolidated plan:"
echo "   cat ${BASE_PATH}/FINAL_BLUEPRINT_V1.1.md"
echo ""
echo "=========================================="