#!/usr/bin/env python3
"""
Auto-detect Python package requirements for PC2 Infra Core group.
Uses AST parsing to find all import statements in PC2 agent source files.
Canonical helper stack ensures no sys.path manipulation needed.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Set, Dict, List

# Mapping of import names to PyPI package names
IMPORT_TO_PACKAGE = {
    'zmq': 'pyzmq',
    'redis': 'redis',
    'yaml': 'PyYAML',
    'requests': 'requests',
    'nats': 'nats-py',
    'psutil': 'psutil',
    'pydantic': 'pydantic',
    'fastapi': 'fastapi',
    'uvicorn': 'uvicorn',
    'prometheus_client': 'prometheus-client',
    'aiohttp': 'aiohttp',
    'asyncio_mqtt': 'asyncio-mqtt',
    'dotenv': 'python-dotenv',
    'jwt': 'PyJWT',
    'httpx': 'httpx',
    'aiofiles': 'aiofiles',
    'starlette': 'starlette',
    'numpy': 'numpy',
    'scipy': 'scipy',
    'sklearn': 'scikit-learn',
    'torch': 'torch==2.1.0',
    'transformers': 'transformers',
    'datasets': 'datasets',
    'huggingface_hub': 'huggingface-hub',
    'chromadb': 'chromadb',
    'sentence_transformers': 'sentence-transformers',
    'openai': 'openai',
    'elevenlabs': 'elevenlabs',
    'google.cloud': 'google-cloud-translate',
    'azure.cognitiveservices': 'azure-cognitiveservices-speech',
    'tweepy': 'tweepy',
    'discord': 'discord.py',
    'flask': 'flask'
}

# Standard library modules (don't need to be installed)
STDLIB_MODULES = {
    'os', 'sys', 'json', 'time', 'datetime', 'threading', 'logging', 'pathlib',
    'typing', 'asyncio', 'collections', 'functools', 'itertools', 'math',
    'random', 'string', 'uuid', 'traceback', 'warnings', 'socket', 'urllib',
    'http', 'ssl', 'hashlib', 'base64', 'tempfile', 'shutil', 'subprocess',
    'signal', 'copy', 'pickle', 'gzip', 'zipfile', 'tarfile', 'configparser',
    'argparse', 're', 'glob', 'fnmatch', 'csv', 'xml', 'html', 'email',
    'multiprocessing', 'concurrent', 'queue', 'weakref', 'gc', 'inspect',
    'dis', 'ast', 'tokenize', 'keyword', 'builtins', 'io', 'codecs',
    'locale', 'calendar', 'heapq', 'bisect', 'array', 'struct', 'enum',
    'decimal', 'fractions', 'statistics', 'zlib', 'bz2', 'lzma', 'contextvars'
}

def extract_imports_from_file(file_path: Path) -> Set[str]:
    """Extract all import statements from a Python file using AST."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
                    
        return imports
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return set()

def main():
    # PC2 Infra Core agents
    agent_files = [
        Path("../../phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py"),
        Path("../../pc2_code/agents/resource_manager.py")
    ]
    
    all_imports = set()
    
    print("Analyzing PC2 Infra Core agents...")
    for agent_file in agent_files:
        if agent_file.exists():
            print(f"  - {agent_file}")
            imports = extract_imports_from_file(agent_file)
            all_imports.update(imports)
        else:
            print(f"  ⚠️  Missing: {agent_file}")
    
    # Filter out stdlib modules and 'common' modules
    external_imports = set()
    for imp in all_imports:
        if imp not in STDLIB_MODULES and not imp.startswith('common'):
            external_imports.add(imp)
    
    # Convert to package names
    packages = set()
    for imp in sorted(external_imports):
        if imp in IMPORT_TO_PACKAGE:
            packages.add(IMPORT_TO_PACKAGE[imp])
        else:
            packages.add(imp)  # Use import name as package name
    
    # Write requirements
    requirements_content = "\n".join(sorted(packages))
    
    with open("requirements.auto.txt", "w") as f:
        f.write(requirements_content)
    
    print(f"\n✅ Generated requirements.auto.txt with {len(packages)} packages:")
    for pkg in sorted(packages):
        print(f"  - {pkg}")
    
    print(f"\nFound {len(external_imports)} external imports:")
    for imp in sorted(external_imports):
        print(f"  - {imp}")

if __name__ == "__main__":
    main()
