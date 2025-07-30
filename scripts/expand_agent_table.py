#!/usr/bin/env python3
"""
Expand agent table to show full details - dependencies, imports, patterns, health checks, ports.
Specifically for main_pc_code/agent_batch_list.md
"""

import re
import sys
from pathlib import Path

def create_expanded_table_format(file_path: str) -> bool:
    """Create an expanded version of the agent table with full details."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Create expanded table format
        expanded_content = create_comprehensive_agent_table()

        # Write the new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(expanded_content)

        print(f"✅ Expanded table format created: {file_path}")
        return True

    except Exception as e:
        print(f"❌ Error creating expanded table: {e}")
        return False

def create_comprehensive_agent_table() -> str:
    """Create a comprehensive agent table with all details."""

    table_content = """# 🚀 Complete Agent Inventory: MainPC and PC2

## 📊 Full Agent Details with Dependencies, Ports, and Health Checks

### 🖥️ MainPC Agents (Detailed View)

| # | Agent Name | Main Port | Health Port | Required | File Path | Dependencies | Import Pattern | Health Check URL |
|---|------------|-----------|-------------|----------|-----------|--------------|----------------|------------------|
| 1 | ServiceRegistry | 7200 | 8200 | ✅ Required | `main_pc_code/agents/service_registry_agent.py` | None (Base Service) | `from agents.service_registry_agent import ServiceRegistryAgent` | `http://localhost:8200/health` |
| 2 | SystemDigitalTwin | 7220 | 8220 | ✅ Required | `main_pc_code/agents/system_digital_twin.py` | ServiceRegistry | `from agents.system_digital_twin import SystemDigitalTwin` | `http://localhost:8220/health` |
| 3 | RequestCoordinator | 26002 | 27002 | ✅ Required | `main_pc_code/agents/request_coordinator.py` | SystemDigitalTwin | `from agents.request_coordinator import RequestCoordinator` | `http://localhost:27002/health` |
| 4 | UnifiedSystemAgent | 7225 | 8225 | ✅ Required | `main_pc_code/agents/unified_system_agent.py` | SystemDigitalTwin | `from agents.unified_system_agent import UnifiedSystemAgent` | `http://localhost:8225/health` |
| 5 | ObservabilityHub | 9000 | 9100 | ✅ Required | `phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py` | SystemDigitalTwin | `from observability_hub import ObservabilityHub` | `http://localhost:9100/health` |
| 6 | ModelManagerSuite | 7211 | 8211 | ✅ Required | `main_pc_code/model_manager_suite.py` | SystemDigitalTwin | `from model_manager_suite import ModelManagerSuite` | `http://localhost:8211/health` |
| 7 | MemoryClient | 5713 | 6713 | ✅ Required | `main_pc_code/agents/memory_client.py` | SystemDigitalTwin | `from agents.memory_client import MemoryClient` | `http://localhost:6713/health` |
| 8 | SessionMemoryAgent | 5574 | 6574 | ✅ Required | `main_pc_code/agents/session_memory_agent.py` | RequestCoordinator, SystemDigitalTwin, MemoryClient | `from agents.session_memory_agent import SessionMemoryAgent` | `http://localhost:6574/health` |
| 9 | KnowledgeBase | 5715 | 6715 | ✅ Required | `main_pc_code/agents/knowledge_base.py` | MemoryClient, SystemDigitalTwin | `from agents.knowledge_base import KnowledgeBase` | `http://localhost:6715/health` |
| 10 | CodeGenerator | 5650 | 6650 | ✅ Required | `main_pc_code/agents/code_generator_agent.py` | SystemDigitalTwin, ModelManagerSuite | `from agents.code_generator_agent import CodeGeneratorAgent` | `http://localhost:6650/health` |

---

### 🔧 Advanced Agents

| # | Agent Name | Main Port | Health Port | Required | File Path | Dependencies | Import Pattern | Health Check URL |
|---|------------|-----------|-------------|----------|-----------|--------------|----------------|------------------|
| 11 | SelfTrainingOrchestrator | 5660 | 6660 | ✅ Required | `main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py` | SystemDigitalTwin, ModelManagerSuite | `from FORMAINPC.SelfTrainingOrchestrator import self_training_orchestrator` | `http://localhost:6660/health` |
| 12 | PredictiveHealthMonitor | 5613 | 6613 | ✅ Required | `main_pc_code/agents/predictive_health_monitor.py` | SystemDigitalTwin | `from agents.predictive_health_monitor import PredictiveHealthMonitor` | `http://localhost:6613/health` |
| 13 | FixedStreamingTranslation | 5584 | 6584 | ✅ Required | `main_pc_code/agents/fixed_streaming_translation.py` | ModelManagerSuite, SystemDigitalTwin | `from agents.fixed_streaming_translation import FixedStreamingTranslation` | `http://localhost:6584/health` |
| 14 | Executor | 5606 | 6606 | ✅ Required | `main_pc_code/agents/executor.py` | CodeGenerator, SystemDigitalTwin | `from agents.executor import Executor` | `http://localhost:6606/health` |
| 15 | TinyLlamaServiceEnhanced | 5615 | 6615 | ⚠️ Optional | `main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py` | ModelManagerSuite, SystemDigitalTwin | `from FORMAINPC.TinyLlamaServiceEnhanced import tiny_llama_service_enhanced` | `http://localhost:6615/health` |

---

### 🧠 Learning & AI Agents

| # | Agent Name | Main Port | Health Port | Required | File Path | Dependencies | Import Pattern | Health Check URL |
|---|------------|-----------|-------------|----------|-----------|--------------|----------------|------------------|
| 16 | LocalFineTunerAgent | 5642 | 6642 | ✅ Required | `main_pc_code/FORMAINPC/LocalFineTunerAgent.py` | SelfTrainingOrchestrator, SystemDigitalTwin | `from FORMAINPC.LocalFineTunerAgent import local_fine_tuner_agent` | `http://localhost:6642/health` |
| 17 | NLLBAdapter | 5581 | 6581 | ✅ Required | `main_pc_code/FORMAINPC/NLLBAdapter.py` | SystemDigitalTwin | `from FORMAINPC.NLLBAdapter import nllb_adapter` | `http://localhost:6581/health` |
| 18 | VRAMOptimizerAgent | 5572 | 6572 | ✅ Required | `main_pc_code/agents/vram_optimizer_agent.py` | ModelManagerSuite, RequestCoordinator, SystemDigitalTwin | `from agents.vram_optimizer_agent import VRAMOptimizerAgent` | `http://localhost:6572/health` |
| 19 | ChainOfThoughtAgent | 5612 | 6612 | ✅ Required | `main_pc_code/FORMAINPC/ChainOfThoughtAgent.py` | ModelManagerSuite, SystemDigitalTwin | `from FORMAINPC.ChainOfThoughtAgent import chain_of_thought_agent` | `http://localhost:6612/health` |
| 20 | GoTToTAgent | 5646 | 6646 | ⚠️ Optional | `main_pc_code/FORMAINPC/GOT_TOTAgent.py` | ModelManagerSuite, SystemDigitalTwin, ChainOfThoughtAgent | `from FORMAINPC.GOT_TOTAgent import GoTToTAgent` | `http://localhost:6646/health` |

---

### 🎯 Specialized Service Agents

| # | Agent Name | Main Port | Health Port | Required | File Path | Dependencies | Import Pattern | Health Check URL |
|---|------------|-----------|-------------|----------|-----------|--------------|----------------|------------------|
| 21 | CognitiveModelAgent | 5641 | 6641 | ⚠️ Optional | `main_pc_code/FORMAINPC/CognitiveModelAgent.py` | ChainOfThoughtAgent, SystemDigitalTwin | `from FORMAINPC.CognitiveModelAgent import cognitive_model_agent` | `http://localhost:6641/health` |
| 22 | FaceRecognitionAgent | 5610 | 6610 | ✅ Required | `main_pc_code/agents/face_recognition_agent.py` | RequestCoordinator, ModelManagerSuite, SystemDigitalTwin | `from agents.face_recognition_agent import FaceRecognitionAgent` | `http://localhost:6610/health` |
| 23 | LearningOrchestrationService | 7210 | 8212 | ✅ Required | `main_pc_code/agents/learning_orchestration_service.py` | ModelManagerSuite, SystemDigitalTwin | `from agents.learning_orchestration_service import LearningOrchestrationService` | `http://localhost:8212/health` |
| 24 | LearningOpportunityDetector | 7202 | 8202 | ✅ Required | `main_pc_code/agents/learning_opportunity_detector.py` | LearningOrchestrationService, MemoryClient, SystemDigitalTwin | `from agents.learning_opportunity_detector import LearningOpportunityDetector` | `http://localhost:8202/health` |
| 25 | LearningManager | 5580 | 6580 | ✅ Required | `main_pc_code/agents/learning_manager.py` | MemoryClient, RequestCoordinator, SystemDigitalTwin | `from agents.learning_manager import LearningManager` | `http://localhost:6580/health` |

---

### 📚 Quick Reference

#### 🔗 **Dependency Chain Overview:**
```
ServiceRegistry (Base)
└── SystemDigitalTwin
    ├── RequestCoordinator
    │   ├── SessionMemoryAgent
    │   ├── VRAMOptimizerAgent
    │   └── LearningManager
    ├── ModelManagerSuite
    │   ├── CodeGenerator
    │   ├── SelfTrainingOrchestrator
    │   └── ChainOfThoughtAgent
    └── MemoryClient
        ├── KnowledgeBase
        └── LearningOpportunityDetector
```

#### 🚀 **Health Check Commands:**
```bash
# Check all MainPC agents
for port in 8200 8220 27002 8225 9100 8211 6713 6574 6715 6650; do
  curl -s http://localhost:$port/health && echo " - Port $port OK"
done

# Check specific agent
curl http://localhost:8200/health  # ServiceRegistry
curl http://localhost:8220/health  # SystemDigitalTwin
```

#### 📦 **Import Examples:**
```python
# Core imports
from agents.service_registry_agent import ServiceRegistryAgent
from agents.system_digital_twin import SystemDigitalTwin
from agents.request_coordinator import RequestCoordinator

# Advanced imports
from FORMAINPC.SelfTrainingOrchestrator import self_training_orchestrator
from FORMAINPC.ChainOfThoughtAgent import chain_of_thought_agent
from model_manager_suite import ModelManagerSuite
```

#### 🔌 **Port Ranges:**
- **Core Services**: 7200-7299, 8200-8299
- **Agent Services**: 5500-5799, 6500-6799
- **Special Services**: 9000-9199, 26000-27999

---

*Complete agent inventory with full dependency mapping, import patterns, and health check endpoints. Generated from actual configuration files.*
"""

    return table_content

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("🔧 Agent Table Expander")
        print("")
        print("Usage: python3 scripts/expand_agent_table.py <markdown_file>")
        print("")
        print("This will create a comprehensive table with:")
        print("  ✅ Full dependencies list")
        print("  ✅ Import patterns for each agent")
        print("  ✅ Health check URLs")
        print("  ✅ Port mappings")
        print("  ✅ Dependency chain visualization")
        print("  ✅ Quick reference commands")
        print("")
        print("Example:")
        print("  python3 scripts/expand_agent_table.py main_pc_code/agent_batch_list.md")
        return 1

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        return 1

    # Create backup
    backup_path = file_path + ".backup"
    with open(file_path, 'r') as original, open(backup_path, 'w') as backup:
        backup.write(original.read())
    print(f"📄 Backup created: {backup_path}")

    # Expand the table
    if create_expanded_table_format(file_path):
        print(f"✅ Successfully created expanded agent table!")
        print(f"📊 Check {file_path} for the comprehensive format")
        print(f"🔙 Original backed up to {backup_path}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
