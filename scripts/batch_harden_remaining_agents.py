#!/usr/bin/env python3
"""
Batch Hardening Script for Remaining Agents
Fixes sys.path.insert and logging.basicConfig issues across all missing agents
"""

import os
import re
from pathlib import Path

def fix_sys_path_insert(file_path):
    """Remove sys.path.insert patterns from a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: Basic sys.path.insert removal
    content = re.sub(
        r'# Add.*?directory to.*?path.*?\n.*?sys\.path\.insert\(0,.*?\)\n',
        '# Removed sys.path.insert - rely on PYTHONPATH=/app in Docker environment\n',
        content, flags=re.DOTALL | re.MULTILINE
    )
    
    # Pattern 2: Project root setup
    content = re.sub(
        r'project_root = .*?\nif project_root not in sys\.path:\n\s*sys\.path\.insert\(0, project_root\)\n',
        '# Removed sys.path.insert - rely on PYTHONPATH=/app in Docker environment\n',
        content, flags=re.MULTILINE
    )
    
    # Pattern 3: Various sys.path.insert patterns
    content = re.sub(
        r'if.*?not in sys\.path:\n\s*sys\.path\.insert\(0,.*?\)\n',
        '# Removed sys.path.insert - rely on PYTHONPATH=/app in Docker environment\n',
        content, flags=re.MULTILINE
    )
    
    # Pattern 4: Direct sys.path.insert lines
    content = re.sub(
        r'^\s*sys\.path\.insert\(0,.*?\)\s*\n',
        '# Removed sys.path.insert - rely on PYTHONPATH=/app in Docker environment\n',
        content, flags=re.MULTILINE
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_logging_basicconfig(file_path):
    """Replace logging.basicConfig with canonical logging"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if canonical logging is already imported
    if 'from common.utils.log_setup import configure_logging' not in content:
        # Add canonical import after other imports (find good spot)
        import_section = content.find('import logging')
        if import_section != -1:
            # Find end of current line
            line_end = content.find('\n', import_section)
            # Insert canonical import
            content = (content[:line_end + 1] + 
                      'from common.utils.log_setup import configure_logging\n' + 
                      content[line_end + 1:])
    
    # Pattern 1: Basic logging.basicConfig replacement
    content = re.sub(
        r'logging\.basicConfig\([^)]*\)\s*\n(?:logger = logging\.getLogger.*?\n)?',
        'logger = configure_logging(__name__, log_to_file=True)\n',
        content, flags=re.DOTALL
    )
    
    # Pattern 2: Multi-line logging.basicConfig
    content = re.sub(
        r'logging\.basicConfig\(\s*\n(?:.*?\n)*?\s*\)\s*\n(?:logger = logging\.getLogger.*?\n)?',
        'logger = configure_logging(__name__, log_to_file=True)\n',
        content, flags=re.DOTALL
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def harden_agent_file(file_path):
    """Apply all hardening fixes to an agent file"""
    if not file_path.exists():
        print(f"⚠️ File not found: {file_path}")
        return False
    
    print(f"🔧 Hardening {file_path.name}...")
    
    try:
        # Apply fixes
        fix_sys_path_insert(file_path)
        fix_logging_basicconfig(file_path)
        
        # Test compilation
        import py_compile
        py_compile.compile(file_path, doraise=True)
        print(f"✅ {file_path.name} - SUCCESS")
        return True
    except Exception as e:
        print(f"❌ {file_path.name} - ERROR: {e}")
        return False

def main():
    """Main execution"""
    print("🚀 Batch Hardening Remaining Agents")
    print("=" * 50)
    
    workspace = Path("/workspace")
    
    # List of remaining agents to harden
    remaining_agents = [
        # language_stack (already partially done, finish the rest)
        "main_pc_code/agents/IntentionValidatorAgent.py",
        "main_pc_code/agents/feedback_handler.py", 
        "main_pc_code/agents/DynamicIdentityAgent.py",
        "main_pc_code/agents/ProactiveAgent.py",
        
        # speech_gpu (continue from where we left off)
        "main_pc_code/agents/fused_audio_preprocessor.py",
        "main_pc_code/agents/streaming_speech_recognition.py", 
        "main_pc_code/agents/wake_word_detector.py",
        "main_pc_code/agents/streaming_interrupt_handler.py",
        "main_pc_code/agents/streaming_language_analyzer.py",
        
        # learning_gpu 
        "main_pc_code/agents/learning_opportunity_detector.py",
        "main_pc_code/agents/active_learning_monitor.py",
        
        # emotion_system
        "main_pc_code/agents/human_awareness_agent.py",
        "main_pc_code/agents/tone_detector.py",
        "main_pc_code/agents/voice_profiling_agent.py",
        
        # utility_cpu
        "main_pc_code/agents/executor.py",
        "main_pc_code/agents/predictive_health_monitor.py",
        "main_pc_code/agents/translation_service.py",
        "main_pc_code/agents/smart_home_agent.py",
    ]
    
    # Also handle observability (different path)
    observability_agents = [
        "phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py"
    ]
    
    success_count = 0
    total_count = 0
    
    # Process main agents
    for agent_path in remaining_agents:
        total_count += 1
        full_path = workspace / agent_path
        if harden_agent_file(full_path):
            success_count += 1
    
    # Process observability agents
    for agent_path in observability_agents:
        total_count += 1
        full_path = workspace / agent_path
        if harden_agent_file(full_path):
            success_count += 1
    
    # Final report
    print(f"\n🎯 BATCH HARDENING RESULTS:")
    print(f"   Processed: {total_count} agents")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {total_count - success_count}")
    print(f"   Success Rate: {(success_count/total_count*100):.1f}%")
    
    if success_count == total_count:
        print(f"\n🎉 ALL AGENTS SUCCESSFULLY HARDENED!")
        return True
    else:
        print(f"\n⚠️ Some agents still need manual fixes")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)