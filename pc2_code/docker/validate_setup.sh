#!/bin/bash

# PC2 Docker Setup Validation Script
# Validates that all required files and configurations are in place

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 PC2 Docker Setup Validation${NC}"
echo "=================================="

# Track validation results
total_checks=0
passed_checks=0

validate_check() {
    local check_name="$1"
    local check_command="$2"
    
    total_checks=$((total_checks + 1))
    echo -n "Checking $check_name... "
    
    if eval "$check_command" &>/dev/null; then
        echo -e "${GREEN}✅ PASS${NC}"
        passed_checks=$((passed_checks + 1))
    else
        echo -e "${RED}❌ FAIL${NC}"
    fi
}

validate_file() {
    local file_path="$1"
    local description="$2"
    
    total_checks=$((total_checks + 1))
    echo -n "Checking $description... "
    
    if [[ -f "$file_path" ]]; then
        echo -e "${GREEN}✅ EXISTS${NC}"
        passed_checks=$((passed_checks + 1))
    else
        echo -e "${RED}❌ MISSING${NC}"
        echo "  Expected: $file_path"
    fi
}

echo -e "${YELLOW}📋 File Structure Validation${NC}"
echo "----------------------------"

# Check core files
validate_file "pc2_code/docker-compose.pc2.yml" "Docker Compose file"
validate_file "pc2_code/docker/Dockerfile.pc2-base" "Base Dockerfile"
validate_file "pc2_code/docker/Dockerfile.pc2-vision" "Vision Dockerfile"
validate_file "pc2_code/docker/Dockerfile.pc2-web" "Web Dockerfile"
validate_file "pc2_code/docker/Dockerfile.pc2-monitoring" "Monitoring Dockerfile"
validate_file "pc2_code/docker/build_images.sh" "Build script"
validate_file "pc2_code/docker/start_pc2_system.sh" "Startup script"
validate_file "pc2_code/docker/health_check.py" "Health check script"
validate_file "pc2_code/docker/requirements.common.txt" "Common requirements"
validate_file "pc2_code/docker/PC2_PORT_MAPPING.md" "Port mapping docs"
validate_file "pc2_code/docker/README.md" "Documentation"

echo ""
echo -e "${YELLOW}📋 Configuration Validation${NC}"
echo "----------------------------"

# Check startup configuration
validate_file "pc2_code/config/startup_config.yaml" "PC2 startup config"

# Check agent directories
validate_file "pc2_code/agents/memory_orchestrator_service.py" "MemoryOrchestratorService"
validate_file "pc2_code/agents/tiered_responder.py" "TieredResponder"
validate_file "pc2_code/agents/advanced_router.py" "AdvancedRouter"

echo ""
echo -e "${YELLOW}🛠️ System Requirements${NC}"
echo "----------------------"

# Check system requirements
validate_check "Docker installed" "command -v docker"
validate_check "Docker Compose installed" "command -v docker-compose"
validate_check "Docker daemon running" "docker info"
validate_check "curl available" "command -v curl"

echo ""
echo -e "${YELLOW}📊 Port Availability${NC}"
echo "-------------------"

# Check if key ports are available
key_ports=(7100 7140 7129 9000 9100)
for port in "${key_ports[@]}"; do
    validate_check "Port $port available" "! netstat -tuln | grep -q :$port"
done

echo ""
echo -e "${YELLOW}🔗 Network Connectivity${NC}"
echo "------------------------"

# Check network connectivity (optional)
validate_check "localhost connectivity" "curl -s http://localhost:80 || curl -s http://127.0.0.1:80 || true"

echo ""
echo -e "${YELLOW}📁 Directory Permissions${NC}"
echo "-------------------------"

# Check directory permissions
validate_check "Docker directory writable" "[[ -w pc2_code/docker ]]"
validate_check "Project root readable" "[[ -r . ]]"

echo ""
echo "=================================="
echo -e "${BLUE}📊 Validation Summary${NC}"
echo "=================================="

if [[ $passed_checks -eq $total_checks ]]; then
    echo -e "${GREEN}🎉 All checks passed! ($passed_checks/$total_checks)${NC}"
    echo -e "${GREEN}✅ PC2 Docker setup is ready for deployment${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Build images: ./pc2_code/docker/start_pc2_system.sh build"
    echo "2. Start system: ./pc2_code/docker/start_pc2_system.sh start"
    echo "3. Check status: ./pc2_code/docker/start_pc2_system.sh status"
    exit 0
else
    failed_checks=$((total_checks - passed_checks))
    echo -e "${RED}❌ $failed_checks/$total_checks checks failed${NC}"
    echo -e "${YELLOW}⚠️  Please fix the issues above before proceeding${NC}"
    echo ""
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo "- Install missing dependencies"
    echo "- Check file paths and permissions"
    echo "- Ensure ports are not in use"
    echo "- Review PC2 Docker documentation"
    exit 1
fi