#!/usr/bin/env python3
"""
Comprehensive script to fix all syntax errors in the MainPC codebase.
This script will fix:
1. Incomplete self. statements (mostly self.context.term())
2. Socket close() calls
3. Import errors and syntax issues
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

class SyntaxErrorFixer:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.fixes_applied = 0
        self.files_fixed = 0
        
    def fix_incomplete_self_statements(self, file_path: Path) -> bool:
        """Fix incomplete self. statements in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                original_content = content
                
            lines = content.splitlines()
            fixed_lines = []
            modified = False
            
            for i, line in enumerate(lines):
                if line.strip() == 'self.':
                    # Analyze context to determine the correct completion
                    context_start = max(0, i - 10)
                    context_end = min(len(lines), i + 5)
                    context_lines = lines[context_start:i+1]
                    context = '\n'.join(context_lines)
                    
                    indent = len(line) - len(line.lstrip())
                    
                    # Determine the fix based on context
                    if 'context' in context and ('cleanup' in context.lower() or 
                                                'close' in context.lower() or 
                                                'stop' in context.lower() or
                                                'terminate' in context.lower()):
                        # Most likely self.context.term()
                        fixed_line = ' ' * indent + 'self.context.term()'
                        print(f"  Fixed line {i+1}: 'self.' -> 'self.context.term()'")
                    elif 'socket' in lines[i-1] if i > 0 else False:
                        # Likely a socket.close() call
                        # Look for socket name in previous line
                        prev_line = lines[i-1] if i > 0 else ""
                        socket_match = re.search(r'self\.(\w+_?socket)', prev_line)
                        if socket_match:
                            socket_name = socket_match.group(1)
                            fixed_line = ' ' * indent + f'self.{socket_name}.close()'
                            print(f"  Fixed line {i+1}: 'self.' -> 'self.{socket_name}.close()'")
                        else:
                            fixed_line = ' ' * indent + 'self.socket.close()'
                            print(f"  Fixed line {i+1}: 'self.' -> 'self.socket.close()'")
                    else:
                        # Default to self.close() for other contexts
                        fixed_line = ' ' * indent + 'self.close()'
                        print(f"  Fixed line {i+1}: 'self.' -> 'self.close()'")
                    
                    fixed_lines.append(fixed_line)
                    modified = True
                    self.fixes_applied += 1
                else:
                    fixed_lines.append(line)
            
            if modified and not self.dry_run:
                # Backup original file
                backup_path = file_path.with_suffix('.bak')
                shutil.copy2(file_path, backup_path)
                
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(fixed_lines))
                
                self.files_fixed += 1
                return True
                
        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
            
        return False
    
    def fix_specific_syntax_errors(self, file_path: Path) -> bool:
        """Fix specific known syntax errors in certain files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                original_content = content
                
            modified = False
            
            # Fix specific files with known issues
            if file_path.name == 'data_optimizer.py':
                # Fix the super().__init__ line issue
                pattern = r'super\(\).__init__\(\*args, \*\*kwargs\)\s*self\.compression_level = 9'
                replacement = 'super().__init__(*args, **kwargs)\n        self.compression_level = 9'
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
                    print(f"  Fixed super().__init__ syntax error")
                    
            elif file_path.name == 'validate_pc2_zmq_services.py':
                # Fix extra parenthesis
                pattern = r'sys\.path\.insert\(0, os\.path\.abspath\(join_path\("main_pc_code", "\.\."\)\)\)\)'
                replacement = 'sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))'
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
                    print(f"  Fixed extra parenthesis error")
                    
            elif file_path.name == 'vision_capture_agent.py':
                # Fix extra parenthesis
                pattern = r'sys\.path\.insert\(0, os\.path\.abspath\(join_path\("main_pc_code", "\.\."\)\)\)\)'
                replacement = 'sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))'
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
                    print(f"  Fixed extra parenthesis error")
                    
            elif file_path.name == 'vram_optimizer_agent.py':
                # Fix extra parenthesis in get_zmq_connection_string
                pattern = r'self\.sdt_socket\.connect\(get_zmq_connection_string\(5585, "localhost"\)\)\)'
                replacement = 'self.sdt_socket.connect(get_zmq_connection_string(5585, "localhost"))'
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
                    print(f"  Fixed extra parenthesis in get_zmq_connection_string")
                    
            elif file_path.name == 'test_voice_command_flow.py':
                # Fix double f-string prefix
                pattern = r'ff"tcp://'
                replacement = r'f"tcp://'
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
                    print(f"  Fixed double f-string prefix")
            
            # Fix import indentation issues
            if 'except ImportError as e:' in content:
                lines = content.splitlines()
                fixed_lines = []
                for i, line in enumerate(lines):
                    if line.strip() == 'except ImportError as e:' and i > 0:
                        # Check if previous line has proper indentation
                        prev_line = lines[i-1]
                        if not prev_line.strip().startswith('from ') and not prev_line.strip().startswith('import '):
                            # This except is misplaced, needs proper try block
                            fixed_lines.append(line)
                        else:
                            # Add proper indentation
                            fixed_lines.append('    ' + line)
                            modified = True
                            print(f"  Fixed except block indentation at line {i+1}")
                    else:
                        fixed_lines.append(line)
                        
                if modified:
                    content = '\n'.join(fixed_lines)
                    
            if modified and not self.dry_run:
                # Backup original file
                backup_path = file_path.with_suffix('.bak')
                shutil.copy2(file_path, backup_path)
                
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                self.files_fixed += 1
                return True
                
        except Exception as e:
            print(f"  Error processing {file_path}: {e}")
            
        return False
    
    def process_directory(self, directory: Path):
        """Process all Python files in a directory."""
        print(f"\nProcessing directory: {directory}")
        
        # List of files with known issues from the analysis
        files_with_incomplete_self = [
            "voice_profiling_agent.py", "face_recognition_agent.py", 
            "streaming_language_analyzer.py", "nlu_agent.py", "emotion_engine.py",
            "responder.py", "active_learning_monitor.py", "memory_client.py",
            "MetaCognitionAgent.py", "knowledge_base.py", "request_coordinator.py",
            "predictive_health_monitor.py", "feedback_handler.py", "learning_manager.py",
            "learning_opportunity_detector.py", "human_awareness_agent.py",
            "ProactiveAgent.py", "tone_detector.py", "executor.py",
            "streaming_whisper_asr.py", "voicemeeter_control_agent.py",
            "translation_service.py", "unified_system_agent.py", "chitchat_agent.py",
            "trigger_word_detector.py", "remote_connector_agent.py", "EmpathyAgent.py"
        ]
        
        files_with_syntax_errors = [
            "data_optimizer.py", "validate_pc2_zmq_services.py", "vision_capture_agent.py",
            "vram_optimizer_agent.py", "auto_fix_health_checks.py", "fix_agent_health_issues.py",
            "validate_agents.py", "system_launcher.py", "end_to_end_test.py",
            "test_voice_command_flow.py", "working_agent_health_test.py"
        ]
        
        # Process files with incomplete self statements
        for filename in files_with_incomplete_self:
            file_path = directory / "agents" / filename
            if not file_path.exists():
                # Try other locations
                file_path = directory / filename
                if not file_path.exists():
                    file_path = directory / "scripts" / filename
                    if not file_path.exists():
                        file_path = directory / "tests" / filename
                        
            if file_path.exists():
                print(f"\nFixing incomplete self statements in: {file_path.name}")
                self.fix_incomplete_self_statements(file_path)
                
        # Process files with other syntax errors
        for filename in files_with_syntax_errors:
            # Search in multiple locations
            possible_paths = [
                directory / "agents" / filename,
                directory / "agents" / "utils" / filename,
                directory / "scripts" / filename,
                directory / "tests" / filename,
                directory / filename
            ]
            
            for file_path in possible_paths:
                if file_path.exists():
                    print(f"\nFixing syntax errors in: {file_path.name}")
                    self.fix_specific_syntax_errors(file_path)
                    break


def main():
    parser = argparse.ArgumentParser(description='Fix syntax errors in MainPC codebase')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be fixed without making changes')
    parser.add_argument('--path', type=str, default='/workspace/main_pc_code',
                       help='Path to MainPC code directory')
    
    args = parser.parse_args()
    
    fixer = SyntaxErrorFixer(dry_run=args.dry_run)
    
    print("=" * 80)
    print("MAINPC SYNTAX ERROR FIXER")
    print("=" * 80)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***\n")
    
    # Process the MainPC directory
    fixer.process_directory(Path(args.path))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total fixes applied: {fixer.fixes_applied}")
    print(f"Total files fixed: {fixer.files_fixed}")
    
    if args.dry_run:
        print("\nTo apply these fixes, run without --dry-run flag")
    else:
        print("\nBackup files created with .bak extension")
        print("Review the changes and test the system")


if __name__ == "__main__":
    main()