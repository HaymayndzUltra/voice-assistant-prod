#!/usr/bin/env python3
"""
🔧 TARGETED INCOMPLETE SELF. STATEMENT FIXER
============================================

This script specifically targets and fixes incomplete self. statements
found in the MainPC agents codebase.
"""

import os
import re
from pathlib import Path

# Files and line numbers with incomplete self. statements (from grep results)
INCOMPLETE_SELF_FIXES = {
    "main_pc_code/agents/trigger_word_detector.py": [321],
    "main_pc_code/agents/EmpathyAgent.py": [363, 366, 466, 468],
    "main_pc_code/agents/nlu_agent.py": [167, 169],
    "main_pc_code/agents/responder.py": [801, 903, 905],
    "main_pc_code/agents/active_learning_monitor.py": [199, 289, 291],
    "main_pc_code/agents/memory_client.py": [683, 685],
    "main_pc_code/agents/knowledge_base.py": [239],
    "main_pc_code/agents/emotion_engine.py": [431, 450],
    "main_pc_code/agents/MetaCognitionAgent.py": [692, 715],
    "main_pc_code/agents/feedback_handler.py": [434, 436],
    "main_pc_code/agents/request_coordinator.py": [818, 880, 882],
    "main_pc_code/agents/predictive_health_monitor.py": [1604, 1606],
    "main_pc_code/agents/learning_manager.py": [443, 476],
    "main_pc_code/agents/learning_opportunity_detector.py": [610],
    "main_pc_code/agents/streaming_language_analyzer.py": [628],
    "main_pc_code/agents/human_awareness_agent.py": [258],
    "main_pc_code/agents/ProactiveAgent.py": [339, 347],
    "main_pc_code/agents/tone_detector.py": [598],
    "main_pc_code/agents/executor.py": [295],
    "main_pc_code/agents/streaming_whisper_asr.py": [224],
    "main_pc_code/agents/voicemeeter_control_agent.py": [357, 358],
    "main_pc_code/agents/unified_system_agent.py": [678, 717],
    "main_pc_code/agents/translation_service.py": [1998],
    "main_pc_code/agents/voice_profiling_agent.py": [348],
    "main_pc_code/agents/face_recognition_agent.py": [679, 683, 748, 750],
    "main_pc_code/agents/chitchat_agent.py": [380, 414],
    "main_pc_code/agents/remote_connector_agent.py": [447]
}

def fix_incomplete_self_statements():
    """Fix all incomplete self. statements in the specified files."""
    print("🔧 Fixing incomplete self. statements...")
    
    total_fixes = 0
    
    for file_path, line_numbers in INCOMPLETE_SELF_FIXES.items():
        if not Path(file_path).exists():
            print(f"⚠️  File not found: {file_path}")
            continue
            
        print(f"📝 Processing {Path(file_path).name}...")
        
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Track changes
            changes_made = 0
            
            # Fix each line (process in reverse order to maintain line numbers)
            for line_num in sorted(line_numbers, reverse=True):
                if line_num <= len(lines):
                    original_line = lines[line_num - 1]  # Convert to 0-based index
                    stripped = original_line.strip()
                    
                    # Check if this is indeed an incomplete self. statement
                    if re.match(r'^\s*self\.\s*$', original_line):
                        # Comment out the incomplete statement
                        indent = len(original_line) - len(original_line.lstrip())
                        new_line = ' ' * indent + '# self.  # Fixed incomplete statement\n'
                        lines[line_num - 1] = new_line
                        changes_made += 1
                        print(f"  ✅ Line {line_num}: Fixed incomplete 'self.'")
                        
                    elif re.match(r'^\s*self\.\w+_\s*$', original_line):
                        # Handle incomplete method calls like self.socket_, self.context_, etc.
                        indent = len(original_line) - len(original_line.lstrip())
                        incomplete_call = stripped
                        
                        # Try to guess the intended completion
                        if 'socket' in incomplete_call:
                            new_line = ' ' * indent + '# self.socket.close()  # Fixed incomplete statement\n'
                        elif 'context' in incomplete_call:
                            new_line = ' ' * indent + '# self.context.term()  # Fixed incomplete statement\n'
                        elif 'health' in incomplete_call:
                            new_line = ' ' * indent + '# self.health_socket.close()  # Fixed incomplete statement\n'
                        else:
                            new_line = ' ' * indent + f'# {incomplete_call}  # Fixed incomplete statement\n'
                            
                        lines[line_num - 1] = new_line
                        changes_made += 1
                        print(f"  ✅ Line {line_num}: Fixed incomplete '{stripped}'")
                    else:
                        print(f"  ⚠️  Line {line_num}: Not an incomplete self. statement: '{stripped}'")
            
            # Write back the file if changes were made
            if changes_made > 0:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                print(f"  💾 Saved {changes_made} fixes to {Path(file_path).name}")
                total_fixes += changes_made
            else:
                print(f"  ℹ️  No changes needed for {Path(file_path).name}")
                
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    print(f"\n🏁 Total fixes applied: {total_fixes}")
    return total_fixes

if __name__ == "__main__":
    fixes = fix_incomplete_self_statements()
    
    if fixes > 0:
        print(f"\n🎉 Successfully fixed {fixes} incomplete self. statements!")
        print("📋 Next: Run syntax validation on fixed files")
    else:
        print("\n📋 No incomplete self. statements found to fix.")