# 🔧 PHASE 2 & 3 EXECUTION PLAN
## MainPC Dockerization - Remaining Work

### 📊 **CURRENT STATUS ASSESSMENT**
- ✅ **Phase 1 COMPLETED**: 54/54 agents compile (100% success)
- ✅ **CodeGenerator**: Functional and preserved
- ❌ **Phase 2**: Infrastructure standardization pending
- ❌ **Phase 3**: Docker readiness pending

---

## 🎯 **PHASE 2: INFRASTRUCTURE STANDARDIZATION**

### **P2.1: Error Reporting Cleanup**
**TARGET**: Remove old error bus code from agents

**PRIORITY**: Medium (system works, but cleanup needed)

**EXECUTION STEPS**:
```bash
# Step 1: Identify agents with old error bus code
find main_pc_code/agents -name "*.py" -exec grep -l "error_bus_port\|error_bus_host\|error_bus_pub" {} \;

# Step 2: Remove old error bus setup (bulk operation)
find main_pc_code/agents -name "*.py" -exec sed -i '/self\.error_bus_port/d' {} \;
find main_pc_code/agents -name "*.py" -exec sed -i '/self\.error_bus_host/d' {} \;
find main_pc_code/agents -name "*.py" -exec sed -i '/self\.error_bus_pub/d' {} \;
find main_pc_code/agents -name "*.py" -exec sed -i '/error_bus_pub\.bind/d' {} \;

# Step 3: Test compilation after cleanup
python3 -c "
import subprocess
failed = []
for agent in ['main_pc_code/agents/chitchat_agent.py', 'main_pc_code/agents/executor.py']:
    result = subprocess.run(['python3', '-m', 'py_compile', agent], capture_output=True)
    if result.returncode != 0:
        failed.append(agent)
print(f'Failed agents: {failed}')
"
```

**ESTIMATED TIME**: 1-2 hours

---

### **P2.2: Health Check Validation** 
**TARGET**: Verify StandardizedHealthChecker is working across agents

**PRIORITY**: Low (empirical testing showed auto-creation works)

**EXECUTION STEPS**:
```bash
# Step 1: Validate health checker exists in sample agents
python3 -c "
import sys, os
sys.path.insert(0, os.path.abspath('.'))
test_agents = ['nlu_agent', 'executor', 'chitchat_agent']
for agent_name in test_agents:
    try:
        module = __import__(f'main_pc_code.agents.{agent_name}', fromlist=[agent_name])
        # Test agent creation and health checker
        print(f'✅ {agent_name}: Health check validation needed')
    except Exception as e:
        print(f'❌ {agent_name}: {e}')
"

# Step 2: Create health check validation script
# (Manual verification of auto-created health checkers)
```

**ESTIMATED TIME**: 30 minutes

---

### **P2.3: Configuration Unification**
**TARGET**: Standardize config loading patterns

**PRIORITY**: High (many agents need config)

**EXECUTION STEPS**:
```bash
# Step 1: Find agents using old load_config
grep -r "load_config" main_pc_code/agents/ | cut -d: -f1 | sort | uniq

# Step 2: Update to unified config loading (targeted replacement)
find main_pc_code/agents -name "*.py" -exec grep -l "load_config" {} \; | while read file; do
    # Replace import
    sed -i 's/from main_pc_code.utils.config_loader import load_config/from common.config_manager import load_unified_config/g' "$file"
    # Replace function call
    sed -i 's/load_config()/load_unified_config("main_pc_code\/config\/startup_config.yaml")/g' "$file"
    echo "Updated: $file"
done

# Step 3: Test configuration loading
python3 -c "
from common.config_manager import load_unified_config
config = load_unified_config('main_pc_code/config/startup_config.yaml')
print(f'✅ Config loaded: {len(config.get(\"agent_groups\", {}))} groups')
"
```

**ESTIMATED TIME**: 2-3 hours

---

## 🐳 **PHASE 3: DOCKER READINESS**

### **P3.1: Environment Variable Standardization**
**TARGET**: Replace hardcoded IPs/ports with environment variables

**PRIORITY**: High (critical for Docker deployment)

**EXECUTION STEPS**:
```bash
# Step 1: Find hardcoded IP addresses
grep -r "192\.168\." main_pc_code/agents/ | head -10

# Step 2: Replace with environment-aware calls
find main_pc_code/agents -name "*.py" -exec sed -i 's/"192\.168\.100\.[0-9]*"/get_service_ip("mainpc")/g' {} \;

# Step 3: Add get_service_ip import where needed
find main_pc_code/agents -name "*.py" -exec grep -l "get_service_ip" {} \; | while read file; do
    if ! grep -q "from common.config_manager import.*get_service_ip" "$file"; then
        sed -i '1i from common.config_manager import get_service_ip' "$file"
    fi
done

# Step 4: Test environment variable usage
python3 -c "
from common.config_manager import get_service_ip
print(f'MainPC IP: {get_service_ip(\"mainpc\")}')
print(f'PC2 IP: {get_service_ip(\"pc2\")}')
"
```

**ESTIMATED TIME**: 2-3 hours

---

### **P3.2: File Path Dockerization**
**TARGET**: Ensure all paths work in Docker containers

**PRIORITY**: Medium (important for production)

**EXECUTION STEPS**:
```bash
# Step 1: Find hardcoded file paths
grep -r "/home/\|/tmp/\|C:\\\\" main_pc_code/agents/ | head -10

# Step 2: Create Docker-safe path patterns
python3 -c "
import os
from pathlib import Path

# Define Docker-safe paths
docker_paths = {
    'logs': '/app/logs',
    'models': '/app/models', 
    'config': '/app/config',
    'data': '/app/data'
}

print('Docker path mappings:')
for key, path in docker_paths.items():
    Path(path).mkdir(parents=True, exist_ok=True)
    print(f'{key}: {path}')
"

# Step 3: Update agents to use Docker-safe paths
# (Manual review and targeted updates needed)
```

**ESTIMATED TIME**: 3-4 hours

---

### **P3.3: Dependency Verification & Docker Compose**
**TARGET**: Generate dependency map and Docker compose file

**PRIORITY**: High (required for deployment)

**EXECUTION STEPS**:
```bash
# Step 1: Generate agent dependency map
python3 -c "
import yaml
import json
from pathlib import Path

with open('main_pc_code/config/startup_config.yaml') as f:
    config = yaml.safe_load(f)

agents = {}
for group_name, group_agents in config['agent_groups'].items():
    for agent_name, agent_config in group_agents.items():
        agents[agent_name] = {
            'script': agent_config.get('script_path'),
            'port': agent_config.get('port'),
            'dependencies': agent_config.get('dependencies', []),
            'group': group_name,
            'docker_ready': True  # All agents now compile
        }

with open('mainpc_agent_dependencies.json', 'w') as f:
    json.dump(agents, f, indent=2)
    
print(f'Generated dependency map for {len(agents)} agents')
"

# Step 2: Create Docker Compose template
cat > docker-compose.mainpc.yml << 'EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - mainpc-network

  nats:
    image: nats:2.10-alpine
    ports:
      - "4222:4222"
    networks:
      - mainpc-network

  mainpc-core:
    build:
      context: .
      dockerfile: docker/Dockerfile.mainpc
    ports:
      - "5500-5600:5500-5600"
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
      - ./config:/app/config
    environment:
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
      - MAINPC_IP=mainpc-core
    networks:
      - mainpc-network
    depends_on:
      - redis
      - nats

networks:
  mainpc-network:
    driver: bridge
EOF

echo "Created docker-compose.mainpc.yml"

# Step 3: Create Dockerfile template
mkdir -p docker
cat > docker/Dockerfile.mainpc << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/models /app/data

# Expose ports (will be configured per agent)
EXPOSE 5500-5600

# Default command (will be overridden per agent)
CMD ["python3", "main_pc_code/scripts/start_system_v2.py"]
EOF

echo "Created docker/Dockerfile.mainpc"
```

**ESTIMATED TIME**: 4-5 hours

---

## 📅 **EXECUTION SCHEDULE**

### **Day 1: Phase 2 Infrastructure (4-6 hours)**
- Morning: P2.1 Error reporting cleanup
- Afternoon: P2.3 Configuration unification 
- Evening: P2.2 Health check validation

### **Day 2: Phase 3 Docker Prep (8-10 hours)**
- Morning: P3.1 Environment variables
- Afternoon: P3.2 File path dockerization
- Evening: P3.3 Dependency mapping & Docker compose

### **Day 3: Testing & Validation (2-4 hours)**
- Docker compose validation
- End-to-end testing
- Documentation updates

---

## 🎯 **SUCCESS CRITERIA**

### **Phase 2 Complete:**
- [ ] No custom error bus code in agents
- [ ] All agents use unified config loading
- [ ] Health checkers validated across sample agents

### **Phase 3 Complete:**
- [ ] No hardcoded IP addresses
- [ ] Docker-safe file paths implemented
- [ ] `mainpc_agent_dependencies.json` generated
- [ ] `docker-compose.mainpc.yml` working
- [ ] `docker/Dockerfile.mainpc` functional

### **Deployment Ready:**
- [ ] `docker-compose up` works without errors
- [ ] All 54 agents start successfully in containers
- [ ] Health checks pass for all agents
- [ ] Inter-agent communication working

---

## ⚠️ **RISK MITIGATION**

1. **Backup before bulk operations**
2. **Test after each phase**
3. **Incremental validation**
4. **Keep original Phase 1 success intact**

**TOTAL ESTIMATED TIME**: 2-3 days (16-20 hours)
**PRIORITY ORDER**: P2.3 → P3.1 → P3.3 → P2.1 → P3.2 → P2.2 