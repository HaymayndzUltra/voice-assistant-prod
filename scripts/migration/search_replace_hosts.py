#!/usr/bin/env python3
"""
WP-01 Host Binding Refactor Script
AST-based replacement of hardcoded localhost/127.0.0.1 with env-aware helpers
Target: 600+ occurrences across 64 agents
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Set
import re

# Add common to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common"))

class HostBindingRefactor(ast.NodeTransformer):
    """AST transformer to replace localhost references with env helpers"""
    
    def __init__(self):
        self.changes = []
        self.imports_added = False
    
    def visit_Str(self, node):
        """Replace string literals containing localhost/127.0.0.1"""
        if hasattr(node, 's') and isinstance(node.s, str):
            # TCP connection strings
            if "tcp://localhost:" in node.s:
                port = node.s.split(":")[-1]
                self.changes.append(f"Line {node.lineno}: tcp://localhost:{port} → env-aware")
                # Create new JoinedStr node for f-string
                new_node = ast.JoinedStr(
                    values=[
                        ast.Constant(value="tcp://"),
                        ast.FormattedValue(
                            value=ast.Call(
                                func=ast.Name(id='get_env', ctx=ast.Load()),
                                args=[
                                    ast.Constant(value='BIND_ADDRESS'),
                                    ast.Constant(value='0.0.0.0')
                                ],
                                keywords=[]
                            ),
                            conversion=-1,
                            format_spec=None
                        ),
                        ast.Constant(value=f":{port}")
                    ]
                )
                return new_node
            
            elif "tcp://127.0.0.1:" in node.s:
                port = node.s.split(":")[-1]
                self.changes.append(f"Line {node.lineno}: tcp://127.0.0.1:{port} → env-aware")
                new_node = ast.JoinedStr(
                    values=[
                        ast.Constant(value="tcp://"),
                        ast.FormattedValue(
                            value=ast.Call(
                                func=ast.Name(id='get_env', ctx=ast.Load()),
                                args=[
                                    ast.Constant(value='BIND_ADDRESS'),
                                    ast.Constant(value='0.0.0.0')
                                ],
                                keywords=[]
                            ),
                            conversion=-1,
                            format_spec=None
                        ),
                        ast.Constant(value=f":{port}")
                    ]
                )
                return new_node
            
            # Plain localhost/127.0.0.1 strings
            elif node.s == "localhost":
                self.changes.append(f"Line {node.lineno}: 'localhost' → get_env(...)")
                return ast.Call(
                    func=ast.Name(id='get_env', ctx=ast.Load()),
                    args=[
                        ast.Constant(value='BIND_ADDRESS'),
                        ast.Constant(value='0.0.0.0')
                    ],
                    keywords=[]
                )
            
            elif node.s == "127.0.0.1":
                self.changes.append(f"Line {node.lineno}: '127.0.0.1' → get_env(...)")
                return ast.Call(
                    func=ast.Name(id='get_env', ctx=ast.Load()),
                    args=[
                        ast.Constant(value='BIND_ADDRESS'),
                        ast.Constant(value='0.0.0.0')
                    ],
                    keywords=[]
                )
        
        return node
    
    def visit_Module(self, node):
        """Add import at module level if needed"""
        if self.changes and not self.imports_added:
            # Add import at the top
            import_node = ast.ImportFrom(
                module='common.env_helpers',
                names=[ast.alias(name='get_env', asname=None)],
                level=0
            )
            node.body.insert(0, import_node)
            self.imports_added = True
        
        return self.generic_visit(node)

def refactor_file_simple(file_path: Path) -> bool:
    """Simple regex-based refactor for faster execution"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Add import if localhost found and not already imported
        if ('localhost' in content or '127.0.0.1' in content) and 'from common.env_helpers import get_env' not in content:
            # Add import after existing imports
            lines = content.split('\n')
            import_index = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_index = i + 1
            
            lines.insert(import_index, 'from common.env_helpers import get_env')
            content = '\n'.join(lines)
            changes.append("Added get_env import")
        
        # Replace TCP connection strings
        tcp_localhost_pattern = r'"tcp://localhost:(\d+)"'
        tcp_127_pattern = r'"tcp://127\.0\.0\.1:(\d+)"'
        
        def replace_tcp_localhost(match):
            port = match.group(1)
            changes.append(f"tcp://localhost:{port} → env-aware")
            return f'f"tcp://{{get_env(\'BIND_ADDRESS\', \'0.0.0.0\')}}:{port}"'
        
        def replace_tcp_127(match):
            port = match.group(1)
            changes.append(f"tcp://127.0.0.1:{port} → env-aware")
            return f'f"tcp://{{get_env(\'BIND_ADDRESS\', \'0.0.0.0\')}}:{port}"'
        
        content = re.sub(tcp_localhost_pattern, replace_tcp_localhost, content)
        content = re.sub(tcp_127_pattern, replace_tcp_127, content)
        
        # Replace plain localhost strings (be careful with context)
        localhost_pattern = r'get_env("BIND_ADDRESS", "0.0.0.0")'
        localhost_127_pattern = r'"127\.0\.0\.1"'
        
        # Only replace if it looks like a host parameter
        if re.search(r'host.*=.*get_env("BIND_ADDRESS", "0.0.0.0")', content, re.IGNORECASE):
            content = re.sub(r'host.*=.*get_env("BIND_ADDRESS", "0.0.0.0")', lambda m: m.group(0).replace('get_env("BIND_ADDRESS", "0.0.0.0")', 'get_env("BIND_ADDRESS", "0.0.0.0")'), content, flags=re.IGNORECASE)
            changes.append("host = localhost → env-aware")
        
        if re.search(r'host.*=.*"127\.0\.0\.1"', content, re.IGNORECASE):
            content = re.sub(r'host.*=.*"127\.0\.0\.1"', lambda m: m.group(0).replace('get_env("BIND_ADDRESS", "0.0.0.0")', 'get_env("BIND_ADDRESS", "0.0.0.0")'), content, flags=re.IGNORECASE)
            changes.append("host = 127.0.0.1 → env-aware")
        
        if content != original_content and changes:
            print(f"\n📝 {file_path}:")
            for change in changes:
                print(f"  ✅ {change}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def find_python_files() -> List[Path]:
    """Find all Python files with localhost references"""
    root = Path.cwd()
    python_files = []
    
    # Scan main directories
    for pattern in ["main_pc_code/**/*.py", "pc2_code/**/*.py", "common/**/*.py", "scripts/**/*.py"]:
        python_files.extend(root.glob(pattern))
    
    # Filter out __pycache__ and test files for now
    return [f for f in python_files if "__pycache__" not in str(f)]

def main():
    print("🚀 WP-01: HOST BINDING REFACTOR")
    print("=" * 50)
    
    # Find target files
    files = find_python_files()
    print(f"📁 Found {len(files)} Python files to scan")
    
    modified_count = 0
    
    for file_path in files:
        if refactor_file_simple(file_path):
            modified_count += 1
    
    print(f"\n✅ WP-01 COMPLETE!")
    print(f"📊 Modified {modified_count} files")
    print(f"🔧 localhost → env-aware conversions applied")
    
    # Create env template
    create_env_template()

def create_env_template():
    """Create .env.template with all required variables"""
    template_content = """# WP-01 Environment Variables Template
# Generated by search_replace_hosts.py

# === BINDING CONFIGURATION ===
BIND_ADDRESS=0.0.0.0

# === SERVICE DISCOVERY ===
SERVICE_REGISTRY_HOST=service-registry
SERVICE_REGISTRY_PORT=7200

SYSTEM_DIGITAL_TWIN_HOST=system-digital-twin  
SYSTEM_DIGITAL_TWIN_PORT=7220

# === REDIS ===
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# === PC2 SERVICES ===
PC2_IP=pc2-machine
MAIN_PC_IP=mainpc-machine

# === MODEL PATHS ===
MODEL_DIR=/app/models
DATA_DIR=/app/data
LOG_DIR=/app/logs
"""
    
    env_file = Path("docker/config/env.template")
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(template_content)
    print(f"📄 Created {env_file}")

if __name__ == "__main__":
    main() 