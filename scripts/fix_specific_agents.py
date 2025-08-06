#!/usr/bin/env python3
"""
Targeted fix for specific agent folders only
Focuses on the exact agents listed by the user
"""
import pathlib
import re
import ast
import json
from typing import Set, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Specific agents to fix (from user's list)
TARGET_AGENTS = [
    "active_learning_monitor",
    "advanced_command_handler", 
    "audio_capture",
    "chain_of_thought_agent",
    "chitchat_agent",
    "cloud_translation_service",
    "code_generator",
    "cognitive_model_agent",
    "dynamic_identity_agent",
    "emotion_engine",
    "emotion_synthesis_agent",
    "empathy_agent",
    "executor",
    "face_recognition_agent",
    "feedback_handler",
    "fused_audio_preprocessor",
    "goal_manager",
    "human_awareness",
    "intention_validator",
    "knowledge_base",
    "learning_manager",
    "learning_opportunity_detector",
    "learning_orchestration_service",
    "memory_client",
    "model_manager_suite",
    "model_orchestrator",
    "mood_tracker",
    "nlu_agent",
    "observability_hub",
    "predictive_health_monitor",
    "proactive_agent",
    "request_coordinator",
    "responder",
    "service_registry",
    "session_memory_agent",
    "smart_home_agent",
    "streaming_interrupt_handler",
    "streaming_language_analyzer",
    "streaming_speech_recognition",
    "streaming_tts_agent",
    "stt_service",
    "system_digital_twin",
    "tone_detector",
    "translation_services",
    "tts_service",
    "unified_system_agent",
    "voice_profiling",
    "vram_optimizer",
    "wake_word_detector"
]

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

def check_missing_imports(file_path: pathlib.Path, agent_side: str) -> List[str]:
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
    
    # Error publisher
    if agent_side == "main":
        if "main_pc_code.agents.error_publisher" not in imports:
            missing.append("from main_pc_code.agents.error_publisher import ErrorPublisher")
    else:
        if "pc2_code.utils.pc2_error_publisher" not in imports:
            missing.append("from pc2_code.utils.pc2_error_publisher import PC2ErrorPublisher")
    
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
    
    # Determine agent side and find Python file
    if agent_name.startswith('pc2_'):
        py_name = agent_name[4:]  # Remove pc2_ prefix
        py_file = ROOT / "pc2_code" / "agents" / f"{py_name}.py"
        agent_side = "pc2"
    else:
        py_file = ROOT / "main_pc_code" / "agents" / f"{agent_name}.py"
        agent_side = "main"
    
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
    missing_imports = check_missing_imports(py_file, agent_side)
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
    print("🎯 TARGETED AGENT COMPLIANCE FIX")
    print(f"📋 Fixing {len(TARGET_AGENTS)} specific agents")
    print("=" * 50)
    
    results = []
    fixed_count = 0
    compliant_count = 0
    missing_count = 0
    
    for agent_name in TARGET_AGENTS:
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
    print(f"📦 Total processed: {len(TARGET_AGENTS)} agents")
    
    # Save detailed results
    results_file = ROOT / "scripts" / "specific_agents_fix_results.json"
    with results_file.open('w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    print("\n🎉 TARGETED AGENT FIX COMPLETE!")

if __name__ == "__main__":
    main()