# Docker Deployment Plan - Known Agents Only

**Date:** 2025-01-16  
**Goal:** Docker deployment ng verified, known agents lang  
**Total Known Agents:** 77 agents (54 MainPC + 23 PC2)

## 📊 **CORRECTED AGENT COUNT**

| **Machine** | **Known Agents** | **Config File** |
|-------------|------------------|-----------------|
| **MainPC** | 54 agents | `main_pc_code/config/startup_config.yaml` |
| **PC2** | 23 agents | `pc2_code/config/startup_config.yaml` |
| **TOTAL** | **77 agents** | Legacy configs (verified) |

**Note:** PC2 may 4 commented agents na hindi kasama sa count.

---

## 🎯 **DEPLOYMENT STRATEGY**

### **Option 1: Pure Legacy Docker (SAFEST)**
Gumamit ng legacy configs directly sa Docker, walang V3.

### **Option 2: Minimal V3 Docker** 
I-clean ang V3 config, keep lang ang known agents mo.

### **Option 3: Separate Legacy + V3**
Docker deployment ng legacy, then separate testing ng V3.

---

## 🐳 **DOCKER PLAN - LEGACY CONFIGS**

### **1. MainPC Docker Setup**
```yaml
# docker-compose.mainpc.yml
version: '3.8'
services:
  mainpc-system:
    build: 
      context: .
      dockerfile: docker/mainpc/Dockerfile
    environment:
      - MACHINE_TYPE=mainpc
      - CONFIG_FILE=main_pc_code/config/startup_config.yaml
    volumes:
      - ./main_pc_code:/app/main_pc_code:ro
      - ./common:/app/common:ro
    command: python3 main_pc_code/system_launcher.py --config main_pc_code/config/startup_config.yaml
```

### **2. PC2 Docker Setup**
```yaml
# docker-compose.pc2.yml  
version: '3.8'
services:
  pc2-system:
    build:
      context: .
      dockerfile: docker/pc2/Dockerfile
    environment:
      - MACHINE_TYPE=pc2
      - CONFIG_FILE=pc2_code/config/startup_config.yaml
    volumes:
      - ./pc2_code:/app/pc2_code:ro
      - ./common:/app/common:ro
    command: python3 main_pc_code/system_launcher.py --config pc2_code/config/startup_config.yaml
```

---

## ✅ **VERIFICATION COMMANDS**

### **Pre-Docker Verification**
```bash
# Test MainPC Legacy (54 agents)
export MACHINE_TYPE=mainpc
python3 main_pc_code/system_launcher.py --dry-run --config main_pc_code/config/startup_config.yaml

# Test PC2 Legacy (23 agents)  
export MACHINE_TYPE=pc2
python3 main_pc_code/system_launcher.py --dry-run --config pc2_code/config/startup_config.yaml
```

### **File Existence Check**
```bash
# Check MainPC agent files
python3 -c "
import yaml
with open('main_pc_code/config/startup_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    
missing = []
for group_name, group in config.get('agent_groups', {}).items():
    for agent_name, agent_config in group.items():
        script_path = agent_config.get('script_path', '')
        if not os.path.exists(script_path):
            missing.append(f'{agent_name}: {script_path}')

if missing:
    print('MISSING FILES:')
    for m in missing: print(f'❌ {m}')
else:
    print('✅ ALL MAINPC FILES EXIST')
"

# Check PC2 agent files  
python3 -c "
import yaml, os
with open('pc2_code/config/startup_config.yaml', 'r') as f:
    content = f.read()
    
# Parse PC2 services
missing = []
for line in content.split('\n'):
    if 'script_path:' in line and not line.strip().startswith('#'):
        script_path = line.split('script_path: ')[1].rstrip(',')
        if not os.path.exists(script_path):
            missing.append(script_path)

if missing:
    print('MISSING PC2 FILES:')
    for m in missing: print(f'❌ {m}')
else:
    print('✅ ALL PC2 FILES EXIST')
"
```

### **Port Conflict Check**
```bash
# Check for port conflicts
python3 -c "
import yaml, re

# Get MainPC ports
with open('main_pc_code/config/startup_config.yaml', 'r') as f:
    mainpc_config = yaml.safe_load(f)

mainpc_ports = set()
for group in mainpc_config.get('agent_groups', {}).values():
    for agent_config in group.values():
        port = agent_config.get('port', '')
        if port:
            # Extract numeric port
            port_num = re.sub(r'[^0-9]', '', str(port))
            if port_num: mainpc_ports.add(int(port_num))

# Get PC2 ports
with open('pc2_code/config/startup_config.yaml', 'r') as f:
    pc2_content = f.read()

pc2_ports = set()
for line in pc2_content.split('\n'):
    if 'port:' in line and not line.strip().startswith('#'):
        port_match = re.search(r'port: [^,\s]+', line)
        if port_match:
            port = port_match.group().split(': ')[1].rstrip(',')
            port_num = re.sub(r'[^0-9]', '', port)
            if port_num: pc2_ports.add(int(port_num))

conflicts = mainpc_ports & pc2_ports
if conflicts:
    print(f'⚠️ PORT CONFLICTS: {sorted(conflicts)}')
else:
    print('✅ NO PORT CONFLICTS')

print(f'MainPC ports: {len(mainpc_ports)}')
print(f'PC2 ports: {len(pc2_ports)}')
"
```

---

## 🚀 **DEPLOYMENT STEPS**

### **1. Pre-Docker Testing**
```bash
# Test legacy configs locally first
./scripts/test_legacy_configs.sh
```

### **2. Docker Build & Test**
```bash
# Build MainPC
docker-compose -f docker-compose.mainpc.yml build

# Build PC2  
docker-compose -f docker-compose.pc2.yml build

# Test run (dry-run mode)
docker-compose -f docker-compose.mainpc.yml run --rm mainpc-system python3 main_pc_code/system_launcher.py --dry-run --config main_pc_code/config/startup_config.yaml

docker-compose -f docker-compose.pc2.yml run --rm pc2-system python3 main_pc_code/system_launcher.py --dry-run --config pc2_code/config/startup_config.yaml
```

### **3. Production Deploy**
```bash
# Deploy MainPC
docker-compose -f docker-compose.mainpc.yml up -d

# Deploy PC2
docker-compose -f docker-compose.pc2.yml up -d

# Monitor
docker-compose logs -f
```

---

## 📋 **IMMEDIATE NEXT STEPS**

1. ✅ **Verify Legacy Configs** - Run yung verification commands
2. ✅ **Test File Existence** - Make sure all 77 agents may files
3. ✅ **Check Port Conflicts** - Avoid conflicts between MainPC/PC2  
4. ✅ **Create Docker Configs** - Build Docker setup for legacy only
5. ✅ **Test Docker Build** - Dry run sa Docker environment
6. ✅ **Deploy** - Production deployment ng known agents

**Priority:** Safety first - legacy configs na working na, then optimize later.

---

## ❓ **TANONG SA USER**

1. **Anong Docker strategy mo prefer?** (Pure legacy o minimal V3?)
2. **May specific port range ba for Docker?** (Para avoid conflicts)
3. **Need mo ba cross-machine communication?** (MainPC ↔ PC2)
4. **Anong deployment environment?** (Single machine o separate containers?)

Ready na tayo mag-implement pagka-decide mo sa strategy! 🚀 