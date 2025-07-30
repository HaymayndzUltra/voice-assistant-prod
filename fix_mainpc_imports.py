#!/usr/bin/env python3
from typing import Union
"""
Batch fix script for MainPC agent import issues
Fixes get_main_pc_code() and get_project_root() import problems
"""

import os
import re
from pathlib import Path

def fix_get_main_pc_code_import(file_path):
    """Fix get_main_pc_code() import in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file has get_main_pc_code() usage but no import
        if 'get_main_pc_code()' in content and 'from common.utils.path_env import' not in content:
            # Find the first import block
            lines = content.split('\n')
            insert_line = 0
            
            # Find where to insert the import (after first imports)
            for i, line in enumerate(lines):
                if line.strip().startswith('from ') or line.strip().startswith('import '):
                    insert_line = i + 1
            
            # Insert the import
            import_line = "from common.utils.path_env import get_main_pc_code, get_project_root"
            lines.insert(insert_line, import_line)
            
            # Write back the file
            new_content = '\n'.join(lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True, "Added get_main_pc_code import"
        
        return False, "No fix needed"
    
    except Exception as e:
        return False, f"Error: {e}"

def fix_project_root_import(file_path):
    """Fix get_project_root() import in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if file has PROJECT_ROOT = get_project_root() but no import
        if 'PROJECT_ROOT = get_project_root()' in content and 'from common.utils.path_env import' not in content:
            # Find the first import block
            lines = content.split('\n')
            insert_line = 0
            
            # Find where to insert the import
            for i, line in enumerate(lines):
                if line.strip().startswith('from ') or line.strip().startswith('import '):
                    insert_line = i + 1
            
            # Insert the import
            import_line = "from common.utils.path_env import get_project_root"
            lines.insert(insert_line, import_line)
            
            # Write back the file
            new_content = '\n'.join(lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True, "Added get_project_root import"
        
        return False, "No fix needed"
    
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Main batch fix function"""
    # List of agents with get_main_pc_code issues (from grep results)
    agents_with_issues = [
        'main_pc_code/agents/streaming_translation.py',
        'main_pc_code/agents/remote_connector_agent.py', 
        'main_pc_code/agents/llm_runtime_tools.py',
        'main_pc_code/agents/voice_controller.py',
        'main_pc_code/agents/system_digital_twin_launcher.py',
        'main_pc_code/agents/streaming_interrupt.py',
        'main_pc_code/agents/streaming_language_to_llm.py',
        'main_pc_code/agents/streaming_interrupt_handler.py',
        'main_pc_code/agents/face_recognition_agent.py',
        'main_pc_code/agents/mood_tracker_agent.py',
        'main_pc_code/agents/emotion_engine.py',
        'main_pc_code/agents/streaming_partial_transcripts.py',
        'main_pc_code/agents/voicemeeter_control_agent.py',
        'main_pc_code/agents/responder.py',
        'main_pc_code/agents/learning_manager.py',
        'main_pc_code/agents/noise_reduction_agent.py',
        'main_pc_code/agents/streaming_whisper_asr.py',
        'main_pc_code/agents/HumanAwarenessAgent.py',
        'main_pc_code/agents/code_generator_agent.py',
        'main_pc_code/agents/trigger_word_detector.py',
        'main_pc_code/agents/tone_detector.py',
        'main_pc_code/agents/advanced_command_handler.py',
        'main_pc_code/agents/fused_audio_preprocessor.py',
        'main_pc_code/agents/vram_optimizer_agent.py',
        'main_pc_code/agents/nlu_agent.py',
        'main_pc_code/agents/predictive_health_monitor.py',
        'main_pc_code/agents/chitchat_agent.py',
        'main_pc_code/agents/advanced_suggestion_system.py',
        'main_pc_code/agents/human_awareness_agent.py',
        'main_pc_code/FORMAINPC/NLLBAdapter.py',
        'main_pc_code/FORMAINPC/GOT_TOTAgent.py',
        'main_pc_code/FORMAINPC/LearningAdjusterAgent.py',
        'main_pc_code/FORMAINPC/LocalFineTunerAgent.py',
        'main_pc_code/FORMAINPC/ChainOfThoughtAgent.py'
    ]
    
    print("🔧 BATCH FIXING MAINPC IMPORT ISSUES")
    print("=" * 50)
    
    fixed_count = 0
    failed_count = 0
    
    for agent_path in agents_with_issues:
        if os.path.exists(agent_path):
            success, message = fix_get_main_pc_code_import(agent_path)
            if success:
                print(f"✅ {agent_path}: {message}")
                fixed_count += 1
            else:
                print(f"⚠️  {agent_path}: {message}")
                if "Error:" in message:
                    failed_count += 1
        else:
            print(f"❌ {agent_path}: File not found")
            failed_count += 1
    
    # Also fix PROJECT_ROOT issues
    project_root_agents = [
        'main_pc_code/FORMAINPC/ConsolidatedTranslator.py',
        'main_pc_code/FORMAINPC/GOT_TOTAgent.py',
        'main_pc_code/utils/service_discovery_client.py',
        'main_pc_code/utils/network_utils.py'
    ]
    
    print(f"\n🔧 FIXING PROJECT_ROOT ISSUES:")
    for agent_path in project_root_agents:
        if os.path.exists(agent_path):
            success, message = fix_project_root_import(agent_path)
            if success:
                print(f"✅ {agent_path}: {message}")
                fixed_count += 1
            else:
                print(f"⚠️  {agent_path}: {message}")
    
    print(f"\n📊 BATCH FIX SUMMARY:")
    print(f"✅ Fixed: {fixed_count} files")
    print(f"❌ Failed: {failed_count} files")
    print(f"🎯 Success Rate: {fixed_count}/{fixed_count + failed_count} ({(fixed_count/(fixed_count + failed_count)*100):.1f}%)")

if __name__ == "__main__":
    main()