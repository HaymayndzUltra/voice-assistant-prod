#!/usr/bin/env python3
"""
Path Refactoring Script

This script refactors hardcoded file paths in the codebase to use the centralized
path management system. It replaces hardcoded paths with references to the path_env module.
"""

import os
import re
import sys
from pathlib import Path
import argparse
import logging
from typing import List, Dict, Tuple, Optional
from common.utils.log_setup import configure_logging

# Setup logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import the path manager to ensure it's working
from common.utils.path_env import get_path, join_path, get_file_path

# Define patterns to search for
PATH_PATTERNS = [
    # os.path.join with hardcoded paths
    r'os\.path\.join\((.*?)"(main_pc_code|pc2_code|config|logs|data|models|cache)"(.*?)\)',
    
    # Direct string paths
    r'"(main_pc_code|pc2_code)/([^"]*)"',
    r'"(logs|config|data|models|cache)/([^"]*)"',
    r'\'(logs|config|data|models|cache)/([^\']*)\'',
    
    # Path with os.path.dirname(__file__)
    r'os\.path\.join\(os\.path\.dirname\(__file__\), ["\']\.\.(?:/|\\\\)([^"\']*)["\']',
    r'os\.path\.join\(os\.path\.dirname\(__file__\), ["\']\.\.["\'](.*?)\)',
    
    # Absolute Windows paths
    r'"[C-Z]:\\\\[^"]*"',
    r'"[C-Z]:/[^"]*"',
    
    # Absolute Linux paths
    r'"/home/[^"]*"',
    
    # Path constructor with string concatenation
    r'"(logs|config|data|models|cache)/" \+ ([^+]+)',
    
    # Path objects
    r'Path\("(main_pc_code|pc2_code|config|logs|data|models|cache)/([^"]*)"\)',
    r'Path\(\'(main_pc_code|pc2_code|config|logs|data|models|cache)/([^\']*)\'\)',
]

# Define replacement templates
REPLACEMENT_TEMPLATES = {
    "main_pc_code": "get_path(\"main_pc_code\")",
    "pc2_code": "get_path(\"pc2_code\")",
    "config": "get_path(\"config\")",
    "logs": "get_path(\"logs\")",
    "data": "get_path(\"data\")",
    "models": "get_path(\"models\")",
    "cache": "get_path(\"cache\")",
    "main_pc_code/config": "get_path(\"main_pc_config\")",
    "pc2_code/config": "get_path(\"pc2_config\")",
    "main_pc_code/logs": "get_path(\"main_pc_logs\")",
    "pc2_code/logs": "get_path(\"pc2_logs\")",
}

# Files to prioritize for refactoring
PRIORITY_FILES = [
    "main_pc_code/agents/model_manager_agent.py",
    "main_pc_code/agents/streaming_tts_agent.py",
    "main_pc_code/agents/fixed_streaming_translation.py",
    "main_pc_code/agents/face_recognition_agent.py",
    "main_pc_code/agents/request_coordinator.py",
    "main_pc_code/agents/unified_system_agent.py",
    "main_pc_code/agents/streaming_whisper_asr.py",
    "main_pc_code/agents/tone_detector.py",
    "main_pc_code/agents/gguf_model_manager.py",
    "main_pc_code/agents/predictive_loader.py",
    "main_pc_code/config/config_manager.py",
    "main_pc_code/utils/config_loader.py",
    "main_pc_code/utils/path_manager.py",
    "main_pc_code/utils/network_utils.py",
    "main_pc_code/utils/service_discovery_client.py",
    "main_pc_code/agents/llm_runtime_tools.py",
    "main_pc_code/agents/voicemeeter_control_agent.py",
    "main_pc_code/agents/human_awareness_agent.py",
    "main_pc_code/agents/IntentionValidatorAgent.py",
    "main_pc_code/agents/EmpathyAgent.py"
]

# Import statement to add at the top of refactored files
PATH_ENV_IMPORT = """
# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from common.utils.path_env import get_path, join_path, get_file_path, get_project_root
"""

def find_files_to_refactor(directory: str, extensions: List[str] = ['.py']) -> List[str]:
    """Find all files with the given extensions in the directory."""
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                files.append(os.path.join(root, filename))
    return files

def analyze_file(file_path: str) -> Dict[str, int]:
    """Analyze a file for hardcoded paths."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    matches = {}
    for pattern in PATH_PATTERNS:
        found = re.findall(pattern, content)
        if found:
            matches[pattern] = len(found)
    
    return matches

def refactor_file(file_path: str, dry_run: bool = False) -> Tuple[int, List[str]]:
    """
    Refactor hardcoded paths in a file.
    
    Args:
        file_path: Path to the file to refactor
        dry_run: If True, don't actually modify the file
        
    Returns:
        Tuple of (number of replacements, list of replacements made)
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        replacements = []
        total_replacements = 0
        
        # Check if path_env is already imported
        path_env_imported = re.search(r'from common\.utils\.path_env import', content) is not None
        
        # First, handle specific file path patterns
        
        # Replace Path objects with hardcoded paths
        for match in re.finditer(r'Path\("(main_pc_code|pc2_code|config|logs|data|models|cache)/([^"]*)"\)', content):
            full_match = match.group(0)
            path_type = match.group(1)
            subpath = match.group(2)
            
            if path_type == "main_pc_code" and subpath.startswith("config/"):
                subpath_parts = subpath[len("config/"):].split("/")
                replacement = f'Path(get_file_path("main_pc_config", "{"/".join(subpath_parts)}"))'
            elif path_type == "pc2_code" and subpath.startswith("config/"):
                subpath_parts = subpath[len("config/"):].split("/")
                replacement = f'Path(get_file_path("pc2_config", "{"/".join(subpath_parts)}"))'
            else:
                replacement = f'Path(join_path("{path_type}", "{subpath}"))'
                
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Replace Path objects with hardcoded paths (single quotes)
        for match in re.finditer(r'Path\(\'(main_pc_code|pc2_code|config|logs|data|models|cache)/([^\']*)\'\)', content):
            full_match = match.group(0)
            path_type = match.group(1)
            subpath = match.group(2)
            
            if path_type == "main_pc_code" and subpath.startswith("config/"):
                subpath_parts = subpath[len("config/"):].split("/")
                replacement = f'Path(get_file_path("main_pc_config", "{"/".join(subpath_parts)}"))'
            elif path_type == "pc2_code" and subpath.startswith("config/"):
                subpath_parts = subpath[len("config/"):].split("/")
                replacement = f'Path(get_file_path("pc2_config", "{"/".join(subpath_parts)}"))'
            else:
                replacement = f'Path(join_path("{path_type}", "{subpath}"))'
                
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Replace os.path.join with hardcoded paths
        for match in re.finditer(r'os\.path\.join\((.*?)"(main_pc_code|pc2_code|config|logs|data|models|cache)"(.*?)\)', content):
            full_match = match.group(0)
            path_type = match.group(2)
            
            if "config" in path_type and "llm_config.yaml" in full_match:
                replacement = 'get_file_path("main_pc_config", "llm_config.yaml")'
                content = content.replace(full_match, replacement)
                replacements.append(f"{full_match} -> {replacement}")
                total_replacements += 1
            elif "config" in path_type and "startup_config.yaml" in full_match:
                replacement = 'get_file_path("main_pc_config", "startup_config.yaml")'
                content = content.replace(full_match, replacement)
                replacements.append(f"{full_match} -> {replacement}")
                total_replacements += 1
            elif "config" in path_type and "gguf_models.json" in full_match:
                replacement = 'get_file_path("main_pc_config", "gguf_models.json")'
                content = content.replace(full_match, replacement)
                replacements.append(f"{full_match} -> {replacement}")
                total_replacements += 1
            elif "logs" in path_type and ".log" in full_match:
                # Extract the log filename
                log_file_match = re.search(r'"([^"]+\.log)"', full_match)
                if log_file_match:
                    log_filename = log_file_match.group(1)
                    replacement = f'join_path("logs", "{log_filename}")'
                    content = content.replace(full_match, replacement)
                    replacements.append(f"{full_match} -> {replacement}")
                    total_replacements += 1
            else:
                # Generic fallback for other path types (models, data, cache, etc.)
                # Extract all quoted path components in the os.path.join call
                sub_parts = re.findall(r'"([^"\\]+)"', full_match)
                # The first part is the path_type itself; any additional parts form the subpath
                if len(sub_parts) > 1:
                    subpath = "/".join(sub_parts[1:])
                    replacement = f'join_path("{path_type}", "{subpath}")'
                else:
                    # No additional components – refer to the directory root
                    replacement = f'get_path("{path_type}")'
                content = content.replace(full_match, replacement)
                replacements.append(f"{full_match} -> {replacement}")
                total_replacements += 1
        
        # Replace direct string paths
        for match in re.finditer(r'"(main_pc_code|pc2_code|logs|config|data|models|cache)/([^"]*)"', content):
            full_match = match.group(0)
            path_type = match.group(1)
            subpath = match.group(2)
            
            if path_type == "main_pc_code" and subpath.startswith("config/"):
                subpath_parts = subpath[len("config/"):].split("/")
                replacement = f'get_file_path("main_pc_config", "{"/".join(subpath_parts)}")'
            elif path_type == "pc2_code" and subpath.startswith("config/"):
                subpath_parts = subpath[len("config/"):].split("/")
                replacement = f'get_file_path("pc2_config", "{"/".join(subpath_parts)}")'
            else:
                replacement = f'join_path("{path_type}", "{subpath}")'
                
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Replace direct string paths (single quotes)
        for match in re.finditer(r'\'(main_pc_code|pc2_code|logs|config|data|models|cache)/([^\']*)\'', content):
            full_match = match.group(0)
            path_type = match.group(1)
            subpath = match.group(2)
            
            if path_type == "main_pc_code" and subpath.startswith("config/"):
                subpath_parts = subpath[len("config/"):].split("/")
                replacement = f'get_file_path("main_pc_config", "{"/".join(subpath_parts)}")'
            elif path_type == "pc2_code" and subpath.startswith("config/"):
                subpath_parts = subpath[len("config/"):].split("/")
                replacement = f'get_file_path("pc2_config", "{"/".join(subpath_parts)}")'
            else:
                replacement = f'join_path("{path_type}", "{subpath}")'
                
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Replace paths with os.path.dirname(__file__)
        for match in re.finditer(r'os\.path\.join\(os\.path\.dirname\(__file__\), ["\']\.\.(?:/|\\\\)([^"\']*)["\']', content):
            full_match = match.group(0)
            subpath = match.group(1)
            
            # Determine the path type based on the file location
            if "main_pc_code/agents" in file_path:
                replacement = f'join_path("main_pc_code", "{subpath}")'
            elif "pc2_code/agents" in file_path:
                replacement = f'join_path("pc2_code", "{subpath}")'
            else:
                # Use a generic replacement if we can't determine the specific path type
                replacement = f'join_path("logs", "{subpath}")' if "logs" in subpath else f'join_path("config", "{subpath}")' if "config" in subpath else f'join_path("data", "{subpath}")' if "data" in subpath else f'join_path("models", "{subpath}")' if "models" in subpath else f'join_path("cache", "{subpath}")' if "cache" in subpath else None
                
            if replacement:
                content = content.replace(full_match, replacement)
                replacements.append(f"{full_match} -> {replacement}")
                total_replacements += 1

        # Replace sys.path insertions that manually navigate to project root
        for match in re.finditer(r'sys\.path\.insert\(\s*0\s*,\s*os\.path\.abspath\(os\.path\.join\(os\.path\.dirname\(__file__\),\s*[\'\"\.]\.\./\.\.[\'\"\)]\)\)\s*\)', content):
            full_match = match.group(0)
            replacement = 'sys.path.insert(0, get_project_root())'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Add import if needed and if changes were made
        if total_replacements > 0 and not path_env_imported:
            # Find the right spot to insert the import
            import_match = re.search(r'import\s+[^\n]+\n\n', content)
            if import_match:
                insert_pos = import_match.end()
                content = content[:insert_pos] + PATH_ENV_IMPORT + content[insert_pos:]
                replacements.append("Added path_env import")
                total_replacements += 1
        
        # Replace absolute Windows or Linux paths inside double quotes
        for match in re.finditer(r'"([A-Za-z]):\\([^\"]*)"', content):
            full_match = match.group(0)
            drive = match.group(1)
            path_rest = match.group(2).replace('\\', '/')  # normalize
            # Heuristic mapping
            if 'xtts' in path_rest.lower():
                replacement = 'join_path("models", "xtts_local")'
            elif 'voice assistant' in path_rest.lower() or 'voice_samples' in path_rest.lower():
                filename = os.path.basename(path_rest)
                replacement = f'get_file_path("data", "voice_samples/{filename}")'
            elif path_rest.lower().endswith('.exe'):
                filename = os.path.basename(path_rest)
                replacement = f'get_file_path("config", "voicemeeter/{filename}")'
            else:
                filename = os.path.basename(path_rest)
                replacement = f'get_file_path("data", "{filename}")'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        # Replace absolute paths inside single quotes
        for match in re.finditer(r'\'([A-Za-z]):\\([^\']*)\'', content):
            full_match = match.group(0)
            drive = match.group(1)
            path_rest = match.group(2).replace('\\', '/')
            if 'xtts' in path_rest.lower():
                replacement = 'join_path("models", "xtts_local")'
            elif 'voice assistant' in path_rest.lower() or 'voice_samples' in path_rest.lower():
                filename = os.path.basename(path_rest)
                replacement = f'get_file_path("data", "voice_samples/{filename}")'
            elif path_rest.lower().endswith('.exe'):
                filename = os.path.basename(path_rest)
                replacement = f'get_file_path("config", "voicemeeter/{filename}")'
            else:
                filename = os.path.basename(path_rest)
                replacement = f'get_file_path("data", "{filename}")'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1

        # Replace os.path.join(dirname(__file__), '..', 'logs', <file>) patterns
        for match in re.finditer(r'os\.path\.join\(os\.path\.dirname\(__file__\)(?:,\s*[\'\"]\.\.\"?\"?\])*\s*,\s*[\'\"]logs[\'\"]\s*(?:,\s*[\'\"][^\'\"]+[\'\"])*\)', content):
            full_match = match.group(0)
            # extract quoted pieces after 'logs'
            subparts = re.findall(r'\"([^\"]+)\"|\'([^\']+)\'', full_match)
            filenames = [p[0] or p[1] for p in subparts if (p[0] or p[1]) and (p[0] or p[1]) != '..' and (p[0] or p[1]).lower() != 'logs']
            if filenames:
                subpath = '/'.join(filenames)
                replacement = f'join_path("logs", "{subpath}")'
            else:
                replacement = 'get_path("logs")'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Replace dirname(__file__) '../../..' style project-root discovery
        for match in re.finditer(r'os\.path\.abspath\(os\.path\.join\(os\.path\.dirname\(__file__\)\s*,\s*((?:["\"][.]{2}["\"],?\s*){2,})\)\)', content, flags=re.MULTILINE):
            full_match = match.group(0)
            segments = re.findall(r'["\"][.]{2}["\"]', match.group(1))
            depth = len(segments)
            # Heuristic: depth 2 => main_pc_code relative file usually, use get_main_pc_code(); else use get_project_root()
            if depth == 2:
                replacement = 'get_main_pc_code()'
            else:
                replacement = 'get_project_root()'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
 
        # Replace LOGS_DIR assignments built via dirname(__file__)
        for match in re.finditer(r'([A-Za-z_]*LOGS_DIR[\s]*=[\s]*)(os\.path\.join\(os\.path\.dirname\(__file__\)[^\n]+)', content):
            full_match = match.group(2)
            replacement = 'join_path("logs")'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Replace variable assignments of PROJECT_ROOT/MAIN_PC_CODE, etc.
        for match in re.finditer(r'^\s*(\w+)\s*=\s*os\.path\.abspath\(os\.path\.join\(os\.path\.dirname\(__file__\)[^)]*\)\)', content, flags=re.MULTILINE):
            var_name = match.group(1)
            full_match = match.group(0)
            if var_name.upper() == 'MAIN_PC_CODE':
                replacement = f'{var_name} = get_main_pc_code()'
            else:
                replacement = f'{var_name} = get_project_root()'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Replace Path(__file__).resolve().parent.parent patterns
        for match in re.finditer(r'([A-Z_]+)_DIR\s*=\s*Path\(__file__\)\.resolve\(\)\.parent(?:\.parent)+', content):
            full_match = match.group(0)
            var_name = match.group(1) + "_DIR"
            if '.parent.parent' in full_match:
                replacement = f'{var_name} = get_main_pc_code()'
            else:
                replacement = f'{var_name} = get_project_root()'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1
        
        # Replace os.path.join(os.path.dirname(__file__), '..', 'file.txt') patterns
        for match in re.finditer(r'os\.path\.join\(os\.path\.dirname\(__file__\),\s*[\'"]\.\.[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)', content):
            full_match = match.group(0)
            file_path = match.group(1)
            
            # Determine the appropriate path type
            if 'log' in file_path.lower():
                path_type = 'logs'
            elif 'user_profile' in file_path.lower() or 'active_user' in file_path.lower():
                path_type = 'data'
            else:
                path_type = 'data'  # Default to data directory
                
            replacement = f'join_path("{path_type}", "{file_path}")'
            content = content.replace(full_match, replacement)
            replacements.append(f"{full_match} -> {replacement}")
            total_replacements += 1

        # Write changes back to the file if not a dry run and changes were made
        if not dry_run and content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return total_replacements, replacements
    
    except Exception as e:
        logger.error(f"Error refactoring {file_path}: {e}")
        return 0, []

def main():
    parser = argparse.ArgumentParser(description="Refactor hardcoded paths in the codebase")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually modify files")
    parser.add_argument("--analyze-only", action="store_true", help="Only analyze files, don't refactor")
    parser.add_argument("--priority-only", action="store_true", help="Only refactor priority files")
    parser.add_argument("--file", help="Refactor a specific file")
    parser.add_argument("--aggressive", action="store_true", help="Use more aggressive pattern matching")
    args = parser.parse_args()
    
    if args.file:
        files_to_refactor = [args.file]
    elif args.priority_only:
        files_to_refactor = [os.path.join(PROJECT_ROOT, f) for f in PRIORITY_FILES]
    else:
        files_to_refactor = find_files_to_refactor(os.path.join(PROJECT_ROOT, "main_pc_code"))
        files_to_refactor += find_files_to_refactor(os.path.join(PROJECT_ROOT, "pc2_code"))
    
    logger.info(f"Found {len(files_to_refactor)} files to process")
    
    # Filter to only existing files
    files_to_refactor = [f for f in files_to_refactor if os.path.exists(f)]
    
    if args.analyze_only:
        total_matches = 0
        files_with_paths = 0
        
        for file_path in files_to_refactor:
            matches = analyze_file(file_path)
            if matches:
                files_with_paths += 1
                file_matches = sum(matches.values())
                total_matches += file_matches
                logger.info(f"{file_path}: {file_matches} hardcoded paths")
                for pattern, count in matches.items():
                    logger.debug(f"  - {pattern}: {count}")
        
        logger.info(f"Analysis complete: {total_matches} hardcoded paths found in {files_with_paths} files")
    else:
        total_replacements = 0
        files_modified = 0
        
        for file_path in files_to_refactor:
            replacements, changes = refactor_file(file_path, args.dry_run)
            if replacements > 0:
                files_modified += 1
                total_replacements += replacements
                logger.info(f"{file_path}: {replacements} replacements made")
                for change in changes:
                    logger.debug(f"  - {change}")
        
        action = "Would modify" if args.dry_run else "Modified"
        logger.info(f"Refactoring complete: {total_replacements} replacements in {files_modified} files")
        logger.info(f"{action} {files_modified} files")

if __name__ == "__main__":
    main() 