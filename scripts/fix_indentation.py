#!/usr/bin/env python3
"""
Fix indentation of health_check methods that are incorrectly nested inside other methods.

This script identifies Python files with health_check methods that have incorrect indentation
(nested inside other methods) and moves them to the class level with proper indentation.
"""

import os
import sys
import re
import logging
import argparse
from typing import List, Tuple, Optional, Dict, Any
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# List of files with indentation issues from the audit report
DEFAULT_TARGET_FILES = [
    "main_pc_code/agents/DynamicIdentityAgent.py",
    "main_pc_code/agents/EmpathyAgent.py",
    "main_pc_code/FORMAINPC/LearningAdjusterAgent.py",
    "main_pc_code/FORMAINPC/CognitiveModelAgent.py",
    "main_pc_code/agents/emotion_engine.py",
    "main_pc_code/agents/mood_tracker_agent.py",
    "main_pc_code/agents/human_awareness_agent.py",
    "main_pc_code/agents/emotion_synthesis_agent.py",
    "main_pc_code/agents/tone_detector.py",
    "main_pc_code/agents/advanced_command_handler.py",
    "main_pc_code/agents/memory_manager.py",
    "main_pc_code/agents/learning_manager.py",
    "main_pc_code/agents/knowledge_base.py",
    "main_pc_code/agents/active_learning_monitor.py",
    "main_pc_code/agents/code_generator_agent.py",
    "main_pc_code/agents/face_recognition_agent.py",
    "main_pc_code/src/core/task_router.py",
    "main_pc_code/FORMAINPC/GOT_TOTAgent.py",
    "main_pc_code/agents/vram_optimizer_agent.py",
    "main_pc_code/agents/coordinator_agent.py",
    "main_pc_code/agents/GoalOrchestratorAgent.py",
    "main_pc_code/agents/IntentionValidatorAgent.py",
    "main_pc_code/agents/ProactiveAgent.py",
    "main_pc_code/agents/predictive_loader.py",
    "main_pc_code/FORMAINPC/EnhancedModelRouter.py",
    "main_pc_code/FORMAINPC/NLLBAdapter.py",
    "main_pc_code/FORMAINPC/LocalFineTunerAgent.py",
    "main_pc_code/FORMAINPC/consolidated_translator.py",
    "main_pc_code/agents/voice_profiling_agent.py",
    "main_pc_code/agents/nlu_agent.py",
    "main_pc_code/agents/chitchat_agent.py",
    "main_pc_code/agents/feedback_handler.py",
    "main_pc_code/agents/streaming_language_analyzer.py",
    "main_pc_code/agents/session_memory_agent.py",
    "main_pc_code/src/memory/memory_orchestrator.py",
    "main_pc_code/src/memory/memory_client.py",
    "main_pc_code/agents/MetaCognitionAgent.py",
    "main_pc_code/agents/MultiAgentSwarmManager.py",
    "main_pc_code/agents/unified_system_agent.py",
    "main_pc_code/agents/tts_connector.py",
    "main_pc_code/agents/tts_cache.py",
    "main_pc_code/agents/streaming_tts_agent.py",
    "main_pc_code/agents/tts_agent.py",
    "main_pc_code/agents/streaming_interrupt_handler.py",
    "main_pc_code/agents/streaming_audio_capture.py",
    "main_pc_code/src/audio/fused_audio_preprocessor.py",
    "main_pc_code/agents/streaming_speech_recognition.py",
    "main_pc_code/agents/language_and_translation_coordinator.py",
    "main_pc_code/src/vision/vision_capture_agent.py",
    "main_pc_code/agents/system_digital_twin.py",
]


def detect_nested_health_check(content: str) -> List[Tuple[int, str, int]]:
    """
    Detect nested health_check methods in the content.
    
    Args:
        content: The file content to analyze
        
    Returns:
        List of tuples (line_number, indent_level, parent_method_line)
    """
    # Find all method definitions
    method_pattern = re.compile(r'^(\s+)def\s+(\w+)\s*\(\s*self\s*(?:,.*?)?\)\s*:', re.MULTILINE)
    methods = []
    
    for match in method_pattern.finditer(content):
        indent = match.group(1)
        method_name = match.group(2)
        line_num = content[:match.start()].count('\n')
        methods.append((line_num, indent, method_name))
    
    # Sort methods by line number
    methods.sort()
    
    # Find health_check methods that are nested inside other methods
    nested_health_checks = []
    
    for i, (line_num, indent, method_name) in enumerate(methods):
        if method_name == 'health_check':
            # Check if this health_check is nested inside another method
            parent_method = None
            parent_indent = ''
            
            for prev_line, prev_indent, prev_name in reversed(methods[:i]):
                if len(prev_indent) < len(indent):
                    parent_method = prev_name
                    parent_indent = prev_indent
                    break
            
            if parent_method and parent_method != 'health_check':
                nested_health_checks.append((line_num, indent, prev_line))
    
    return nested_health_checks


def fix_indentation_issue(file_path: str, dry_run: bool = False, verbose: bool = False) -> Tuple[bool, str]:
    """
    Fix the indentation issue in a file by moving the health_check method
    from being nested inside another method to being a proper class method.
    
    Args:
        file_path: Path to the Python file to process
        dry_run: If True, don't actually modify the file
        verbose: If True, print more detailed information
        
    Returns:
        Tuple of (success, message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            content = ''.join(lines)
            original_content = content  # Keep original for comparison
        
        # First, check for nested health_check methods
        nested_health_checks = detect_nested_health_check(content)
        
        if verbose:
            print(f"File: {file_path}")
            print(f"  Found {len(nested_health_checks)} nested health_check methods")
            
            # Print the first few lines of the file to help with debugging
            print("  First 10 lines:")
            for i, line in enumerate(lines[:10]):
                print(f"    {i+1}: {line.rstrip()}")
        
        if not nested_health_checks:
            # Try the traditional approach with regex
            health_check_pattern = re.compile(r'^(\s+)def\s+health_check\s*\(\s*self\s*(?:,.*?)?\)\s*:', re.MULTILINE)
            match = health_check_pattern.search(content)
            
            if match:
                # Get the line number of the health_check method
                line_num = content[:match.start()].count('\n')
                indent_level = match.group(1)
                
                # Check if this is at class level or nested
                class_indent = '    '  # Default to 4 spaces
                
                # Look for other method definitions at class level to determine indentation
                class_method_pattern = re.compile(r'^(\s+)def\s+\w+\s*\(\s*self\s*', re.MULTILINE)
                class_methods = class_method_pattern.findall(content)
                if class_methods:
                    class_indent = min(class_methods, key=len)
                
                if verbose:
                    print(f"  Found health_check at line {line_num} with indent '{indent_level}'")
                    print(f"  Class indent level: '{class_indent}'")
                
                # If health_check is already at class level, no need to fix
                if indent_level == class_indent:
                    return False, f"SKIPPED: health_check already at correct indentation in {file_path}"
                
                # Extract the health_check method
                method_lines = []
                method_lines.append(lines[line_num])
                
                i = line_num + 1
                while i < len(lines):
                    # If we find a line that has less indentation than our method, we've reached the end
                    if lines[i].strip() and not lines[i].startswith(indent_level):
                        break
                    method_lines.append(lines[i])
                    i += 1
                
                # Remove the health_check method from the original lines
                del lines[line_num:i]
                
                # Fix the indentation of the health_check method
                fixed_method_lines = []
                for line in method_lines:
                    if line.startswith(indent_level):
                        fixed_line = class_indent + line[len(indent_level):]
                    else:
                        fixed_line = line
                    fixed_method_lines.append(fixed_line)
                
                # Find a good position to insert the fixed method
                # Look for the end of a method or the end of the class
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith(class_indent + "def "):
                        # Found a method definition at class level
                        insert_pos = i
                
                if insert_pos > 0:
                    # Find the end of this method
                    for i in range(insert_pos + 1, len(lines)):
                        if lines[i].startswith(class_indent + "def ") or not lines[i].strip().startswith(' '):
                            insert_pos = i
                            break
                
                # Insert the fixed method at the appropriate position
                lines[insert_pos:insert_pos] = ['\n'] + fixed_method_lines
                
                new_content = ''.join(lines)
                
                # Check if we actually made changes
                if new_content == original_content:
                    return False, f"SKIPPED: No changes needed in {file_path}"
                
                if not dry_run:
                    # Write the modified content back to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                return True, f"SUCCESS: Corrected health_check indentation in {file_path}"
            
            return False, f"SKIPPED: No health_check method found in {file_path}"
        else:
            # Process each nested health_check
            for line_num, indent_level, parent_line in nested_health_checks:
                if verbose:
                    print(f"  Processing nested health_check at line {line_num} with indent '{indent_level}'")
                
                # Find the class-level indentation
                class_indent = '    '  # Default to 4 spaces
                
                # Look for other method definitions at class level to determine indentation
                class_method_pattern = re.compile(r'^(\s+)def\s+\w+\s*\(\s*self\s*', re.MULTILINE)
                class_methods = class_method_pattern.findall(content)
                if class_methods:
                    class_indent = min(class_methods, key=len)
                
                # Extract the health_check method
                method_lines = []
                method_lines.append(lines[line_num])
                
                i = line_num + 1
                while i < len(lines):
                    # If we find a line that has less indentation than our method, we've reached the end
                    if lines[i].strip() and not lines[i].startswith(indent_level):
                        break
                    method_lines.append(lines[i])
                    i += 1
                
                # Remove the health_check method from the original lines
                del lines[line_num:i]
                
                # Fix the indentation of the health_check method
                fixed_method_lines = []
                for line in method_lines:
                    if line.startswith(indent_level):
                        fixed_line = class_indent + line[len(indent_level):]
                    else:
                        fixed_line = line
                    fixed_method_lines.append(fixed_line)
                
                # Find a good position to insert the fixed method
                # Look for the end of a method or the end of the class
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith(class_indent + "def "):
                        # Found a method definition at class level
                        insert_pos = i
                
                if insert_pos > 0:
                    # Find the end of this method
                    for i in range(insert_pos + 1, len(lines)):
                        if lines[i].startswith(class_indent + "def ") or not lines[i].strip().startswith(' '):
                            insert_pos = i
                            break
                
                # Insert the fixed method at the appropriate position
                lines[insert_pos:insert_pos] = ['\n'] + fixed_method_lines
            
            new_content = ''.join(lines)
            
            # Check if we actually made changes
            if new_content == original_content:
                return False, f"SKIPPED: No changes needed in {file_path}"
            
            if not dry_run:
                # Write the modified content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
            return True, f"SUCCESS: Corrected {len(nested_health_checks)} nested health_check methods in {file_path}"
    
    except Exception as e:
        return False, f"ERROR: Failed to process health_check in {file_path}: {str(e)}"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Fix indentation of health_check methods.')
    parser.add_argument('--dry-run', action='store_true', help='Do not modify files, just report what would be changed.')
    parser.add_argument('--files', nargs='+', help='Specific files to process.')
    parser.add_argument('--from-file', help='Read list of files from a file, one per line.')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print more detailed information.')
    args = parser.parse_args()
    
    if args.files:
        target_files = args.files
    elif args.from_file:
        with open(args.from_file, 'r') as f:
            target_files = [line.strip() for line in f if line.strip()]
    else:
        target_files = DEFAULT_TARGET_FILES
    
    # Ensure all paths are absolute
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    target_files = [os.path.join(base_dir, f) if not os.path.isabs(f) else f for f in target_files]
    
    # Filter out files that don't exist
    existing_files = [f for f in target_files if os.path.isfile(f)]
    if len(existing_files) != len(target_files):
        print(f"WARNING: {len(target_files) - len(existing_files)} files not found.")
    
    # Process each file
    fixed_count = 0
    skipped_count = 0
    error_count = 0
    
    for file_path in existing_files:
        success, message = fix_indentation_issue(file_path, args.dry_run, args.verbose)
        print(message)
        
        if "SUCCESS" in message:
            fixed_count += 1
        elif "SKIPPED" in message:
            skipped_count += 1
        else:
            error_count += 1
    
    # Print summary
    print(f"\nSUMMARY: Processed {len(existing_files)} files")
    print(f"  Fixed: {fixed_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")


if __name__ == "__main__":
    main() 