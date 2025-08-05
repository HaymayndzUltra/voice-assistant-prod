#!/usr/bin/env python3
"""
Requirements Extraction Script for Agent Migration

This script scans an agent's source file and extracts Python import statements
to generate a minimal requirements.txt file for that specific agent.

Usage:
    python extract_individual_requirements.py <agent_name>
    
Example:
    python extract_individual_requirements.py service_registry_agent
"""

import ast
import os
import re
import sys
import argparse
from pathlib import Path
from typing import Set, List, Optional


class RequirementsExtractor:
    """Extracts Python dependencies from agent source files."""
    
    # Standard library modules that should not be included in requirements.txt
    STDLIB_MODULES = {
        'os', 'sys', 'json', 'time', 'datetime', 'asyncio', 'logging', 'pathlib',
        'typing', 'collections', 'itertools', 'functools', 'operator', 'copy',
        'threading', 'multiprocessing', 'subprocess', 'socket', 'http', 'urllib',
        'xml', 'html', 'email', 'base64', 'hashlib', 'hmac', 'secrets', 'uuid',
        'random', 'math', 'statistics', 'decimal', 'fractions', 'cmath', 'pickle',
        'sqlite3', 'csv', 'configparser', 'argparse', 'getpass', 'tempfile',
        'shutil', 'glob', 'fnmatch', 'linecache', 'fileinput', 'gzip', 'tarfile',
        'zipfile', 'mimetypes', 'calendar', 'timeit', 'profile', 'pstats',
        'traceback', 'warnings', 'contextlib', 'abc', 'atexit', 'gc', 'inspect',
        'code', 'dis', 'ast', 'keyword', 'token', 'tokenize', 'py_compile',
        'compileall', 'zipapp', 'runpy', 'importlib', 'pkgutil', 'modulefinder',
        'unittest', 'doctest', 'test', 'builtins', '__builtin__', '__future__'
    }
    
    # Common third-party packages with their PyPI names
    PACKAGE_MAPPINGS = {
        'redis': 'redis',
        'nats': 'nats-py',
        'zmq': 'pyzmq',
        'cv2': 'opencv-python',
        'PIL': 'Pillow',
        'yaml': 'PyYAML',
        'requests': 'requests',
        'flask': 'Flask',
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'pydantic': 'pydantic',
        'sqlalchemy': 'SQLAlchemy',
        'psycopg2': 'psycopg2-binary',
        'pymongo': 'pymongo',
        'torch': 'torch',
        'transformers': 'transformers',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'scipy': 'scipy',
        'sklearn': 'scikit-learn',
        'matplotlib': 'matplotlib',
        'seaborn': 'seaborn',
        'openai': 'openai',
        'anthropic': 'anthropic',
        'google': 'google-cloud',
        'azure': 'azure',
        'boto3': 'boto3',
        'pvporcupine': 'pvporcupine',
        'sounddevice': 'sounddevice',
        'librosa': 'librosa',
        'speech_recognition': 'SpeechRecognition',
        'gtts': 'gTTS',
        'pyttsx3': 'pyttsx3'
    }
    
    def __init__(self, workspace_root: str = "/workspace"):
        self.workspace_root = Path(workspace_root)
        self.agent_dir = self.workspace_root / "main_pc_code" / "agents"
        
    def find_agent_files(self, agent_name: str) -> List[Path]:
        """Find all Python files related to an agent."""
        agent_files = []
        
        # Primary agent file
        primary_file = self.agent_dir / f"{agent_name}.py"
        if primary_file.exists():
            agent_files.append(primary_file)
        
        # Check for agent directory with multiple files
        agent_subdir = self.agent_dir / agent_name
        if agent_subdir.exists() and agent_subdir.is_dir():
            for py_file in agent_subdir.rglob("*.py"):
                agent_files.append(py_file)
        
        # Check for common variations
        variations = [
            f"{agent_name}_agent.py",
            f"{agent_name.replace('_agent', '')}.py",
            f"{agent_name.replace('_service', '')}.py"
        ]
        
        for variation in variations:
            var_file = self.agent_dir / variation
            if var_file.exists() and var_file not in agent_files:
                agent_files.append(var_file)
                
        return agent_files
    
    def extract_imports_from_file(self, file_path: Path) -> Set[str]:
        """Extract import statements from a Python file."""
        imports = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to extract imports
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        imports.add(module_name)
                        
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        imports.add(module_name)
                        
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            
            # Fallback: regex-based extraction
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract from import statements
                import_pattern = r'^(?:from\s+(\w+)|import\s+(\w+))'
                matches = re.findall(import_pattern, content, re.MULTILINE)
                for match in matches:
                    module = match[0] or match[1]
                    if module:
                        imports.add(module.split('.')[0])
                        
            except Exception as fallback_e:
                print(f"Error: Could not extract imports from {file_path}: {fallback_e}")
        
        return imports
    
    def filter_third_party_packages(self, imports: Set[str]) -> Set[str]:
        """Filter out standard library modules and return only third-party packages."""
        third_party = set()
        
        for module in imports:
            # Skip standard library modules
            if module in self.STDLIB_MODULES:
                continue
                
            # Skip local/project modules (starting with main_pc_code, common, etc.)
            if module.startswith(('main_pc_code', 'common', 'common_utils', 'phase1_implementation')):
                continue
                
            # Map to PyPI package name if known
            package_name = self.PACKAGE_MAPPINGS.get(module, module)
            third_party.add(package_name)
            
        return third_party
    
    def generate_requirements(self, agent_name: str) -> List[str]:
        """Generate requirements.txt content for a specific agent."""
        print(f"Extracting requirements for agent: {agent_name}")
        
        # Find agent files
        agent_files = self.find_agent_files(agent_name)
        if not agent_files:
            print(f"Warning: No files found for agent '{agent_name}'")
            return []
        
        print(f"Found {len(agent_files)} files to analyze:")
        for file_path in agent_files:
            print(f"  - {file_path}")
        
        # Extract imports from all agent files
        all_imports = set()
        for file_path in agent_files:
            file_imports = self.extract_imports_from_file(file_path)
            all_imports.update(file_imports)
        
        print(f"Raw imports found: {sorted(all_imports)}")
        
        # Filter to third-party packages only
        third_party_packages = self.filter_third_party_packages(all_imports)
        
        print(f"Third-party packages: {sorted(third_party_packages)}")
        
        # Convert to sorted list for consistent output
        requirements = sorted(list(third_party_packages))
        
        return requirements
    
    def save_requirements(self, requirements: List[str], output_path: Path) -> None:
        """Save requirements to a file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for req in requirements:
                f.write(f"{req}\n")
        
        print(f"Requirements saved to: {output_path}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Extract requirements for an agent")
    parser.add_argument("agent_name", help="Name of the agent to extract requirements for")
    parser.add_argument("--output", "-o", help="Output file path for requirements.txt")
    parser.add_argument("--workspace", default="/workspace", help="Workspace root directory")
    
    args = parser.parse_args()
    
    extractor = RequirementsExtractor(args.workspace)
    requirements = extractor.generate_requirements(args.agent_name)
    
    if not requirements:
        print("No third-party requirements found.")
        requirements = ["# No third-party requirements detected"]
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"requirements_{args.agent_name}.txt")
    
    extractor.save_requirements(requirements, output_path)
    
    print(f"\nExtraction complete for agent '{args.agent_name}'")
    print(f"Found {len([r for r in requirements if not r.startswith('#')])} third-party packages")


if __name__ == "__main__":
    main()