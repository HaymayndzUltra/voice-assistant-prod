#!/usr/bin/env python3
"""
Updated targeted fix for specific agent folders with correct file mappings
"""
import pathlib
import re
import ast
import json
from typing import Set, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Agent name to actual file mapping
AGENT_FILE_MAPPING = {
    # Standard agents
    "active_learning_monitor": "main_pc_code/agents/active_learning_monitor.py",
    "advanced_command_handler": "main_pc_code/agents/advanced_command_handler.py",
    "chitchat_agent": "main_pc_code/agents/chitchat_agent.py",
    "cloud_translation_service": "main_pc_code/agents/cloud_translation_service.py",
    "emotion_engine": "main_pc_code/agents/emotion_engine.py",
    "emotion_synthesis_agent": "main_pc_code/agents/emotion_synthesis_agent.py",
    "executor": "main_pc_code/agents/executor.py",
    "face_recognition_agent": "main_pc_code/agents/face_recognition_agent.py",
    "feedback_handler": "main_pc_code/agents/feedback_handler.py",
    "fused_audio_preprocessor": "main_pc_code/agents/fused_audio_preprocessor.py",
    "goal_manager": "main_pc_code/agents/goal_manager.py",
    "knowledge_base": "main_pc_code/agents/knowledge_base.py",
    "learning_manager": "main_pc_code/agents/learning_manager.py",
    "learning_opportunity_detector": "main_pc_code/agents/learning_opportunity_detector.py",
    "learning_orchestration_service": "main_pc_code/agents/learning_orchestration_service.py",
    "memory_client": "main_pc_code/agents/memory_client.py",
    "model_orchestrator": "main_pc_code/agents/model_orchestrator.py",
    "nlu_agent": "main_pc_code/agents/nlu_agent.py",
    "predictive_health_monitor": "main_pc_code/agents/predictive_health_monitor.py",
    "request_coordinator": "main_pc_code/agents/request_coordinator.py",
    "responder": "main_pc_code/agents/responder.py",
    "session_memory_agent": "main_pc_code/agents/session_memory_agent.py",
    "smart_home_agent": "main_pc_code/agents/smart_home_agent.py",
    "streaming_interrupt_handler": "main_pc_code/agents/streaming_interrupt_handler.py",
    "streaming_language_analyzer": "main_pc_code/agents/streaming_language_analyzer.py",
    "streaming_speech_recognition": "main_pc_code/agents/streaming_speech_recognition.py",
    "streaming_tts_agent": "main_pc_code/agents/streaming_tts_agent.py",
    "system_digital_twin": "main_pc_code/agents/system_digital_twin.py",
    "tone_detector": "main_pc_code/agents/tone_detector.py",
    "unified_system_agent": "main_pc_code/agents/unified_system_agent.py",
    "wake_word_detector": "main_pc_code/agents/wake_word_detector.py",
    
    # Agents with alternative file names
    "audio_capture": "main_pc_code/agents/streaming_audio_capture.py",
    "code_generator": "main_pc_code/agents/code_generator_agent.py",
    "dynamic_identity_agent": "main_pc_code/agents/DynamicIdentityAgent.py",
    "empathy_agent": "main_pc_code/agents/EmpathyAgent.py",
    "human_awareness": "main_pc_code/agents/human_awareness_agent.py",
    "intention_validator": "main_pc_code/agents/IntentionValidatorAgent.py",
    "mood_tracker": "main_pc_code/agents/mood_tracker_agent.py",
    "proactive_agent": "main_pc_code/agents/ProactiveAgent.py",
    "service_registry": "main_pc_code/agents/service_registry_agent.py",
    "translation_services": "main_pc_code/agents/translation_service.py",
    "voice_profiling": "main_pc_code/agents/voice_profiling_agent.py",
    "vram_optimizer": "main_pc_code/agents/vram_optimizer_agent.py",
    
    # Services (might not have direct agent files)
    "chain_of_thought_agent": "main_pc_code/FORMAINPC/chain_of_thought_agent.py",
    "cognitive_model_agent": "main_pc_code/FORMAINPC/cognitive_model_agent.py",
    "model_manager_suite": "main_pc_code/agents/model_manager_agent.py",
    "observability_hub": "phase1_implementation/consolidated_agents/observability_hub/enhanced_observability_hub.py",
    "stt_service": "main_pc_code/services/stt_service.py",
    "tts_service": "main_pc_code/services/tts_service.py",
}

def fix_forbidden_patterns(file_path: pathlib.Path) -> bool:
    """Remove forbidden patterns from a file"""
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    original_content = content
    
    # Remove sys.path.insert lines
    content = re.sub(r'sys\.path\.insert.*?\n', '', content)
    
    # Replace logging.basicConfig with proper log_setup
    if "logging.basicConfig" in content:
        # Add log_setup import if not present
        if "from common.utils.log_setup import configure_logging" not in content:
            lines = content.split('\n')
            import_line_idx = -1
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_line_idx = i
            
            if import_line_idx >= 0:
                lines.insert(import_line_idx + 1, "from common.utils.log_setup import configure_logging")
                content = '\n'.join(lines)
        
        # Replace logging.basicConfig calls
        content = re.sub(
            r'logging\.basicConfig\([^)]*\)',
            'logger = configure_logging(__name__)',
            content
        )
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False

def check_missing_imports(file_path: pathlib.Path) -> List[str]:
    """Check which required imports are missing"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []
    
    # Get all imports
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    
    missing = []
    
    # Required imports
    required_imports = {
        "common.utils.env_standardizer": "from common.utils.env_standardizer import get_env",
        "common.core.base_agent": "from common.core.base_agent import BaseAgent", 
        "common.utils.log_setup": "from common.utils.log_setup import configure_logging",
    }
    
    for module, import_stmt in required_imports.items():
        if module not in imports:
            missing.append(import_stmt)
    
    # Error publisher (main PC only for these agents)
    if "main_pc_code.agents.error_publisher" not in imports:
        missing.append("from main_pc_code.agents.error_publisher import ErrorPublisher")
    
    return missing

def add_missing_imports(file_path: pathlib.Path, missing_imports: List[str]) -> bool:
    """Add missing imports to a file"""
    if not missing_imports:
        return False
        
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    lines = content.split('\n')
    
    # Find insertion point
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line.strip() and not line.startswith('#') and insert_idx > 0:
            break
    
    # Insert missing imports
    for import_stmt in missing_imports:
        lines.insert(insert_idx, import_stmt)
        insert_idx += 1
    
    file_path.write_text('\n'.join(lines), encoding='utf-8')
    return True

def fix_agent(agent_name: str) -> Dict:
    """Fix a specific agent"""
    print(f"\n🔧 Fixing agent: {agent_name}")
    
    # Get the actual file path
    file_path_str = AGENT_FILE_MAPPING.get(agent_name)
    if not file_path_str:
        print(f"  ❌ No file mapping found for {agent_name}")
        return {"agent": agent_name, "exists": False, "error": "no_mapping"}
    
    py_file = ROOT / file_path_str
    
    result = {
        "agent": agent_name,
        "python_file": str(py_file),
        "exists": py_file.exists(),
        "patterns_fixed": False,
        "imports_added": False,
        "missing_imports": []
    }
    
    if not py_file.exists():
        print(f"  ❌ Python file not found: {py_file}")
        return result
    
    # Fix forbidden patterns
    patterns_fixed = fix_forbidden_patterns(py_file)
    result["patterns_fixed"] = patterns_fixed
    
    # Check and add missing imports
    missing_imports = check_missing_imports(py_file)
    result["missing_imports"] = missing_imports
    
    if missing_imports:
        imports_added = add_missing_imports(py_file, missing_imports)
        result["imports_added"] = imports_added
        print(f"  ✅ Added {len(missing_imports)} missing imports")
    
    if patterns_fixed:
        print(f"  ✅ Fixed forbidden patterns")
    
    if not patterns_fixed and not missing_imports:
        print(f"  ✨ Already compliant")
    
    return result

def main():
    """Main function to fix specific agents"""
    print("🎯 TARGETED AGENT COMPLIANCE FIX v2")
    print(f"📋 Fixing {len(AGENT_FILE_MAPPING)} specific agents")
    print("=" * 50)
    
    results = []
    fixed_count = 0
    compliant_count = 0
    missing_count = 0
    
    for agent_name in AGENT_FILE_MAPPING.keys():
        result = fix_agent(agent_name)
        results.append(result)
        
        if not result["exists"]:
            missing_count += 1
        elif result["patterns_fixed"] or result["imports_added"]:
            fixed_count += 1
        else:
            compliant_count += 1
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    print(f"✅ Fixed: {fixed_count} agents")
    print(f"✨ Already compliant: {compliant_count} agents") 
    print(f"❌ Missing files: {missing_count} agents")
    print(f"📦 Total processed: {len(AGENT_FILE_MAPPING)} agents")
    
    # Save detailed results
    results_file = ROOT / "scripts" / "specific_agents_fix_v2_results.json"
    with results_file.open('w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    print("\n🎉 TARGETED AGENT FIX v2 COMPLETE!")

if __name__ == "__main__":
    main()