#!/usr/bin/env python3
"""
WP-03 Graceful Shutdown Migration Script
Identifies agents without proper graceful shutdown and updates them to use BaseAgent
Target: All agent files that don't inherit from BaseAgent or implement graceful shutdown
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set
import subprocess

class GracefulShutdownAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect graceful shutdown patterns in agent files"""
    
    def __init__(self):
        self.has_signal_import = False
        self.has_signal_handlers = False
        self.has_cleanup_method = False
        self.inherits_from_base_agent = False
        self.class_names = []
        self.imports = []
        self.has_atexit = False
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
            if alias.name == 'signal':
                self.has_signal_import = True
            elif alias.name == 'atexit':
                self.has_atexit = True
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(f"from {node.module}")
            if 'base_agent' in node.module.lower() or 'BaseAgent' in str(node.names):
                self.inherits_from_base_agent = True
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        self.class_names.append(node.name)
        
        # Check if inherits from BaseAgent
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseAgent':
                self.inherits_from_base_agent = True
            elif isinstance(base, ast.Attribute) and base.attr == 'BaseAgent':
                self.inherits_from_base_agent = True
        
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node):
        if node.name == 'cleanup' or node.name == 'shutdown':
            self.has_cleanup_method = True
        elif 'signal' in node.name.lower() or 'handler' in node.name.lower():
            self.has_signal_handlers = True
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Check for signal.signal() calls
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr == 'signal' and
            isinstance(node.func.value, ast.Name) and 
            node.func.value.id == 'signal'):
            self.has_signal_handlers = True
        self.generic_visit(node)

def find_agent_files() -> List[Path]:
    """Find all Python files that appear to be agents"""
    root = Path.cwd()
    agent_files = []
    
    # Search patterns for agent files
    search_dirs = [
        "main_pc_code/agents",
        "pc2_code/agents", 
        "common/core",
        "phase0_implementation",
        "phase1_implementation",
        "phase2_implementation"
    ]
    
    for search_dir in search_dirs:
        search_path = root / search_dir
        if search_path.exists():
            for python_file in search_path.rglob("*.py"):
                # Skip __init__.py and test files
                if (python_file.name != "__init__.py" and 
                    not python_file.name.startswith("test_") and
                    "_test" not in python_file.name):
                    
                    # Check if file contains agent-like patterns
                    try:
                        with open(python_file, 'r', encoding='utf-8') as f:
                            content = f.read().lower()
                            if any(pattern in content for pattern in [
                                'class ', 'agent', 'zmq', 'socket', 'port', 'run', 'main'
                            ]):
                                agent_files.append(python_file)
                    except Exception:
                        continue
    
    return agent_files

def analyze_agent_file(file_path: Path) -> Dict:
    """Analyze a single agent file for graceful shutdown patterns"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = GracefulShutdownAnalyzer()
        analyzer.visit(tree)
        
        # Additional text-based checks
        content_lower = content.lower()
        has_main_loop = any(pattern in content_lower for pattern in [
            'while true:', 'while self.running:', 'for event in', 'while not'
        ])
        
        has_threading = 'threading' in content_lower or 'thread' in content_lower
        
        # Risk assessment
        risk_score = 0
        if has_main_loop:
            risk_score += 3
        if has_threading:
            risk_score += 2
        if 'zmq' in content_lower:
            risk_score += 2
        if not analyzer.has_cleanup_method:
            risk_score += 3
        if not analyzer.inherits_from_base_agent:
            risk_score += 2
        if not analyzer.has_signal_handlers:
            risk_score += 3
        
        return {
            'file_path': file_path,
            'has_signal_import': analyzer.has_signal_import,
            'has_signal_handlers': analyzer.has_signal_handlers,
            'has_cleanup_method': analyzer.has_cleanup_method,
            'inherits_from_base_agent': analyzer.inherits_from_base_agent,
            'class_names': analyzer.class_names,
            'imports': analyzer.imports,
            'has_atexit': analyzer.has_atexit,
            'has_main_loop': has_main_loop,
            'has_threading': has_threading,
            'risk_score': risk_score,
            'needs_migration': not analyzer.inherits_from_base_agent and risk_score >= 5
        }
    
    except Exception as e:
        return {
            'file_path': file_path,
            'error': str(e),
            'needs_migration': False,
            'risk_score': 0
        }

def update_agent_to_inherit_base_agent(file_path: Path) -> bool:
    """Update an agent file to inherit from BaseAgent and use graceful shutdown"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Add BaseAgent import if not present
        if 'from common.core.base_agent import BaseAgent' not in content:
            # Find import section
            lines = content.split('\n')
            import_insert_line = 0
            
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    import_insert_line = i + 1
                elif line.strip() and not line.strip().startswith('#'):
                    break
            
            # Insert BaseAgent import
            lines.insert(import_insert_line, 'from common.core.base_agent import BaseAgent')
            content = '\n'.join(lines)
            changes.append("Added BaseAgent import")
        
        # Update class definitions to inherit from BaseAgent
        class_pattern = r'class\s+(\w+Agent\w*)\s*(\([^)]*\))?\s*:'
        
        def replace_class_def(match):
            class_name = match.group(1)
            current_inheritance = match.group(2)
            
            if current_inheritance and 'BaseAgent' not in current_inheritance:
                # Add BaseAgent to existing inheritance
                inheritance = current_inheritance.strip('()').strip()
                if inheritance:
                    new_inheritance = f"({inheritance}, BaseAgent)"
                else:
                    new_inheritance = "(BaseAgent)"
            elif not current_inheritance:
                # Add BaseAgent inheritance
                new_inheritance = "(BaseAgent)"
            else:
                # Already has BaseAgent
                return match.group(0)
            
            changes.append(f"Updated {class_name} to inherit from BaseAgent")
            return f"class {class_name}{new_inheritance}:"
        
        content = re.sub(class_pattern, replace_class_def, content)
        
        # Remove manual signal handling if BaseAgent is now inherited
        if 'from common.core.base_agent import BaseAgent' in content:
            # Remove manual signal imports if they exist
            signal_import_patterns = [
                r'import signal\s*\n',
                r'from signal import.*\n',
                r'import atexit\s*\n'
            ]
            
            for pattern in signal_import_patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, '', content)
                    changes.append("Removed manual signal imports (handled by BaseAgent)")
            
            # Remove manual signal handlers
            signal_handler_patterns = [
                r'signal\.signal\([^)]+\)[^\n]*\n',
                r'def signal_handler[^:]*:.*?(?=\n\s*def|\n\s*class|\n\s*if|\Z)',
                r'atexit\.register[^)]*\)[^\n]*\n'
            ]
            
            for pattern in signal_handler_patterns:
                if re.search(pattern, content, re.DOTALL):
                    content = re.sub(pattern, '', content, flags=re.DOTALL)
                    changes.append("Removed manual signal handlers (handled by BaseAgent)")
        
        # Add super() call to __init__ if needed
        init_pattern = r'def __init__\(self[^)]*\):\s*\n'
        if re.search(init_pattern, content):
            def add_super_call(match):
                init_def = match.group(0)
                # Check if super() is already called
                method_start = match.end()
                method_body = content[method_start:]
                
                # Find the end of the __init__ method
                indent_level = None
                lines = method_body.split('\n')
                method_lines = []
                
                for line in lines:
                    if line.strip():
                        if indent_level is None:
                            indent_level = len(line) - len(line.lstrip())
                        current_indent = len(line) - len(line.lstrip())
                        
                        if current_indent < indent_level and line.strip():
                            break
                    method_lines.append(line)
                
                method_content = '\n'.join(method_lines)
                
                if 'super().__init__' not in method_content and 'super().' not in method_content:
                    # Add super() call at the beginning of the method
                    spaces = ' ' * (indent_level or 8)
                    super_call = f"\n{spaces}super().__init__(*args, **kwargs)"
                    changes.append("Added super().__init__() call")
                    return init_def + super_call
                
                return init_def
            
            content = re.sub(init_pattern, add_super_call, content)
        
        if content != original_content and changes:
            print(f"\n📝 {file_path}:")
            for change in changes:
                print(f"  ✅ {change}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        
        return False
    
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False

def generate_shutdown_test_script():
    """Generate a test script to validate graceful shutdown"""
    test_script_content = '''#!/usr/bin/env python3
"""
WP-03 Graceful Shutdown Test Script
Tests graceful shutdown functionality across all agents
"""

import os
import signal
import time
import subprocess
import threading
from pathlib import Path

def test_agent_graceful_shutdown(agent_module: str, timeout: int = 30) -> bool:
    """Test graceful shutdown for a specific agent"""
    try:
        print(f"🧪 Testing graceful shutdown for {agent_module}...")
        
        # Start the agent
        process = subprocess.Popen(
            ['python', '-m', agent_module],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path.cwd()
        )
        
        # Give it time to start
        time.sleep(5)
        
        if process.poll() is not None:
            print(f"❌ {agent_module} failed to start")
            return False
        
        # Send SIGTERM for graceful shutdown
        print(f"📡 Sending SIGTERM to {agent_module}...")
        process.send_signal(signal.SIGTERM)
        
        # Wait for graceful shutdown
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            if process.returncode == 0:
                print(f"✅ {agent_module} shut down gracefully")
                return True
            else:
                print(f"⚠️  {agent_module} shut down with code {process.returncode}")
                if stderr:
                    print(f"   Error: {stderr.decode()[:200]}...")
                return False
        
        except subprocess.TimeoutExpired:
            print(f"❌ {agent_module} did not respond to SIGTERM within {timeout}s")
            process.kill()
            return False
    
    except Exception as e:
        print(f"❌ Error testing {agent_module}: {e}")
        return False

def test_all_agents():
    """Test graceful shutdown for all known agents"""
    agent_modules = [
        'main_pc_code.agents.service_registry_agent',
        'main_pc_code.agents.system_digital_twin',
        'main_pc_code.agents.request_coordinator',
        'main_pc_code.11',  # ModelManagerSuite
        'main_pc_code.agents.streaming_interrupt_handler',
        'main_pc_code.agents.model_orchestrator',
        'pc2_code.agents.advanced_router',
        'phase0_implementation.group_01_core_observability.observability_hub.observability_hub'
    ]
    
    print("🚀 WP-03 Graceful Shutdown Test Suite")
    print("=" * 50)
    
    results = {}
    for agent_module in agent_modules:
        results[agent_module] = test_agent_graceful_shutdown(agent_module)
    
    # Summary
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} agents passed graceful shutdown test")
    
    if passed == total:
        print("🎉 All agents support graceful shutdown!")
    else:
        print("⚠️  Some agents need graceful shutdown improvements:")
        for agent, result in results.items():
            if not result:
                print(f"  ❌ {agent}")

if __name__ == "__main__":
    test_all_agents()
'''
    
    test_script_path = Path("scripts/test_graceful_shutdown.py")
    test_script_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(test_script_path, 'w') as f:
        f.write(test_script_content)
    
    # Make executable
    os.chmod(test_script_path, 0o755)
    print(f"✅ Created graceful shutdown test script: {test_script_path}")

def main():
    print("🚀 WP-03: GRACEFUL SHUTDOWN MIGRATION")
    print("=" * 50)
    
    # Find and analyze agent files
    agent_files = find_agent_files()
    print(f"📁 Found {len(agent_files)} potential agent files")
    
    analysis_results = []
    for agent_file in agent_files:
        result = analyze_agent_file(agent_file)
        analysis_results.append(result)
    
    # Categorize results
    needs_migration = [r for r in analysis_results if r.get('needs_migration', False)]
    already_compliant = [r for r in analysis_results if r.get('inherits_from_base_agent', False)]
    low_risk = [r for r in analysis_results if r.get('risk_score', 0) < 5 and not r.get('needs_migration', False)]
    
    print(f"\n📊 ANALYSIS RESULTS:")
    print(f"✅ Already compliant (inherits BaseAgent): {len(already_compliant)}")
    print(f"🔧 Needs migration: {len(needs_migration)}")
    print(f"📊 Low risk: {len(low_risk)}")
    
    # Show detailed results for high-risk files
    if needs_migration:
        print(f"\n🔧 HIGH-RISK FILES NEEDING MIGRATION:")
        for result in sorted(needs_migration, key=lambda x: x.get('risk_score', 0), reverse=True):
            file_path = result['file_path']
            risk_score = result.get('risk_score', 0)
            print(f"\n📄 {file_path} (Risk Score: {risk_score})")
            print(f"   Classes: {', '.join(result.get('class_names', []))}")
            print(f"   ❌ Inherits BaseAgent: {result.get('inherits_from_base_agent', False)}")
            print(f"   ❌ Has cleanup method: {result.get('has_cleanup_method', False)}")
            print(f"   ❌ Has signal handlers: {result.get('has_signal_handlers', False)}")
            print(f"   ⚠️  Has main loop: {result.get('has_main_loop', False)}")
            print(f"   ⚠️  Has threading: {result.get('has_threading', False)}")
    
    # Perform migration
    if needs_migration:
        print(f"\n🔧 PERFORMING MIGRATION...")
        migration_count = 0
        
        for result in needs_migration:
            if update_agent_to_inherit_base_agent(result['file_path']):
                migration_count += 1
        
        print(f"\n✅ MIGRATION COMPLETE!")
        print(f"📊 Migrated {migration_count} agents to use BaseAgent graceful shutdown")
    
    # Generate test script
    generate_shutdown_test_script()
    
    # Generate summary report
    print(f"\n📋 WP-03 GRACEFUL SHUTDOWN SUMMARY:")
    print(f"🔧 BaseAgent enhanced with SIGTERM/SIGINT handlers")
    print(f"🔧 Atexit cleanup registration added")
    print(f"🔧 Multiple cleanup call prevention implemented")
    print(f"📊 {migration_count if needs_migration else 0} agents migrated to graceful shutdown")
    print(f"🧪 Test script created: scripts/test_graceful_shutdown.py")
    
    print(f"\n🚀 Next Steps:")
    print(f"1. Run tests: python scripts/test_graceful_shutdown.py")
    print(f"2. Test Docker graceful shutdown: docker-compose stop (should be graceful)")
    print(f"3. Test Kubernetes rolling updates: kubectl rollout restart deployment/agent-name")
    print(f"4. Validate zero-downtime deployment capabilities")

if __name__ == "__main__":
    main() 