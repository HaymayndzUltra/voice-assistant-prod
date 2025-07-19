#!/usr/bin/env python3
"""
Cleanup Rogue Methods Script

This script identifies and removes rogue health_check methods that were incorrectly
placed at the top of files by the fix_indentation.py script.
"""

import os
import sys
import ast
import re
import logging
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# List of files with syntax errors from the health check audit report
TARGET_FILES = [
    "main_pc_code/src/core/task_router.py",
    "main_pc_code/FORMAINPC/GOT_TOTAgent.py",
    "main_pc_code/agents/vram_optimizer_agent.py",
    "main_pc_code/agents/coordinator_agent.py",
    "main_pc_code/agents/GoalOrchestratorAgent.py",
    "main_pc_code/agents/IntentionValidatorAgent.py",
    "main_pc_code/agents/DynamicIdentityAgent.py",
    "main_pc_code/agents/EmpathyAgent.py",
    "main_pc_code/agents/ProactiveAgent.py",
    "main_pc_code/agents/predictive_loader.py",
    "main_pc_code/FORMAINPC/EnhancedModelRouter.py",
    "main_pc_code/FORMAINPC/NLLBAdapter.py",
    "main_pc_code/FORMAINPC/LearningAdjusterAgent.py",
    "main_pc_code/FORMAINPC/LocalFineTunerAgent.py",
    "main_pc_code/FORMAINPC/CognitiveModelAgent.py",
    "main_pc_code/FORMAINPC/consolidated_translator.py",
    "main_pc_code/agents/emotion_engine.py",
    "main_pc_code/agents/human_awareness_agent.py",
    "main_pc_code/agents/emotion_synthesis_agent.py",
    "main_pc_code/agents/tone_detector.py",
    "main_pc_code/agents/voice_profiling_agent.py",
    "main_pc_code/agents/nlu_agent.py",
    "main_pc_code/agents/advanced_command_handler.py",
    "main_pc_code/agents/chitchat_agent.py",
    "main_pc_code/agents/feedback_handler.py",
    "main_pc_code/agents/streaming_language_analyzer.py",
    "main_pc_code/agents/session_memory_agent.py",
    "main_pc_code/agents/memory_manager.py",
    "main_pc_code/src/memory/memory_orchestrator.py",
    "main_pc_code/src/memory/memory_client.py",
    "main_pc_code/agents/learning_manager.py",
    "main_pc_code/agents/knowledge_base.py",
    "main_pc_code/agents/MetaCognitionAgent.py",
    "main_pc_code/agents/active_learning_monitor.py",
    "main_pc_code/agents/MultiAgentSwarmManager.py",
    "main_pc_code/agents/unified_system_agent.py",
    "main_pc_code/agents/tts_connector.py",
    "main_pc_code/agents/tts_cache.py",
    "main_pc_code/agents/streaming_tts_agent.py",
    "main_pc_code/agents/tts_agent.py",
    "main_pc_code/agents/streaming_interrupt_handler.py",
    "main_pc_code/agents/code_generator_agent.py",
    "main_pc_code/agents/streaming_audio_capture.py",
    "main_pc_code/src/audio/fused_audio_preprocessor.py",
    "main_pc_code/agents/streaming_speech_recognition.py",
    "main_pc_code/agents/language_and_translation_coordinator.py",
    "main_pc_code/src/vision/vision_capture_agent.py",
    "main_pc_code/agents/face_recognition_agent.py",
    "main_pc_code/agents/system_digital_twin.py",
]


def cleanup_rogue_method(file_path: str, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Clean up a rogue health_check method from a file.
    
    Args:
        file_path: Path to the file to clean up
        dry_run: If True, don't actually modify the file
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # First, try to parse the file with AST to see if it's valid Python
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            # Try to parse the file with AST
            ast.parse(content)
            # If we get here, the file is valid Python, so no need to clean up
            return False, f"SKIPPED: No syntax errors in {file_path}"
        except SyntaxError:
            # File has syntax errors, proceed with cleanup
            pass
        
        # Look for patterns that indicate a rogue health_check method at the top of the file
        lines = content.split('\n')
        
        # Check if there's a health_check method at the top of the file
        rogue_method_start = -1
        rogue_method_end = -1
        
        # Find the start of the rogue method
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('def health_check(self):'):
                # Check if this is at the top level (minimal indentation)
                if len(line) - len(line.lstrip()) <= 4:  # 4 spaces or less indentation
                    rogue_method_start = i
                    break
        
        if rogue_method_start == -1:
            # No rogue method found, try another approach
            # Look for the first import or class statement
            first_import_or_class = -1
            for i, line in enumerate(lines):
                stripped = line.strip()
                if (stripped.startswith('import ') or 
                    stripped.startswith('from ') or 
                    stripped.startswith('class ')):
                    first_import_or_class = i
                    break
            
            if first_import_or_class > 0:
                # Found an import or class statement, remove everything before it
                lines = lines[first_import_or_class:]
                if not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                return True, f"SUCCESS: Removed content before first import/class in {file_path}"
            
            return False, f"SKIPPED: No rogue method or clear structure found in {file_path}"
        
        # Find the end of the rogue method
        # We'll look for the first line after the start that has the same or less indentation
        # or the first line that looks like the start of a new section (import, class, etc.)
        start_indent = len(lines[rogue_method_start]) - len(lines[rogue_method_start].lstrip())
        
        for i in range(rogue_method_start + 1, len(lines)):
            if not lines[i].strip():  # Skip empty lines
                continue
                
            line_indent = len(lines[i]) - len(lines[i].lstrip())
            stripped = lines[i].strip()
            
            # If we find a line with same or less indentation, or a new section marker
            if (line_indent <= start_indent or 
                stripped.startswith('import ') or 
                stripped.startswith('from ') or 
                stripped.startswith('class ') or
                stripped.startswith('"""')):
                rogue_method_end = i
                break
        
        if rogue_method_end == -1:
            # If we couldn't find the end, assume it goes to the end of the file
            rogue_method_end = len(lines)
        
        # Remove the rogue method
        cleaned_lines = lines[:rogue_method_start] + lines[rogue_method_end:]
        
        # Write the cleaned content back to the file
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cleaned_lines))
        
        return True, f"SUCCESS: Removed rogue method from {file_path}"
    
    except Exception as e:
        return False, f"ERROR: Failed to clean up {file_path}: {str(e)}"


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up rogue health_check methods.')
    parser.add_argument('--dry-run', action='store_true', help='Do not modify files, just report what would be changed.')
    parser.add_argument('--files', nargs='+', help='Specific files to process.')
    args = parser.parse_args()
    
    if args.files:
        target_files = args.files
    else:
        target_files = TARGET_FILES
    
    # Ensure all paths are absolute
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    target_files = [os.path.join(base_dir, f) if not os.path.isabs(f) else f for f in target_files]
    
    # Filter out files that don't exist
    existing_files = [f for f in target_files if os.path.isfile(f)]
    if len(existing_files) != len(target_files):
        print(f"WARNING: {len(target_files) - len(existing_files)} files not found.")
    
    # Process each file
    cleaned_count = 0
    skipped_count = 0
    error_count = 0
    
    for file_path in existing_files:
        success, message = cleanup_rogue_method(file_path, args.dry_run)
        print(message)
        
        if "SUCCESS" in message:
            cleaned_count += 1
        elif "SKIPPED" in message:
            skipped_count += 1
        else:
            error_count += 1
    
    # Print summary
    print(f"\nSUMMARY: Processed {len(existing_files)} files")
    print(f"  Cleaned: {cleaned_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")


if __name__ == "__main__":
    main() 