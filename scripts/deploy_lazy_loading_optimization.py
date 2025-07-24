#!/usr/bin/env python3
"""
Deploy Lazy Loading Optimization - Phase 1 Week 3 Day 3
Apply proven optimization patterns to Batch 1 agents
Based on face_recognition_agent pattern that achieved 93.6% improvement
"""

import sys
import os
import time
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any
import re
import ast

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

class LazyLoadingOptimizer:
    """Deploy lazy loading optimization patterns to agents"""
    
    def __init__(self):
        self.optimization_patterns = {
            "lazy_loading": self._apply_lazy_loading_pattern,
            "cache_optimization": self._apply_cache_optimization_pattern,
            "dependency_reduction": self._apply_dependency_reduction_pattern,
            "async_initialization": self._apply_async_initialization_pattern
        }
        
        # Proven optimization templates from Week 2
        self.lazy_loading_template = '''
    def _lazy_import_dependencies(self):
        """Lazy import heavy dependencies only when needed"""
        if not hasattr(self, '_dependencies_loaded'):
            try:
                # Import heavy dependencies here
{import_statements}
                self._dependencies_loaded = True
                self.logger.info(f"{{self.name}}: Dependencies loaded successfully")
            except ImportError as e:
                self.logger.error(f"{{self.name}}: Failed to load dependencies: {{e}}")
                self._dependencies_loaded = False
        
        return self._dependencies_loaded
    
    def _ensure_dependencies_loaded(self):
        """Ensure dependencies are loaded before use"""
        if not self._lazy_import_dependencies():
            raise ImportError(f"{{self.name}}: Required dependencies not available")
'''
        
        self.optimization_stats = {
            "agents_processed": 0,
            "optimizations_applied": 0,
            "estimated_improvements": {},
            "backup_files": [],
            "errors": []
        }
    
    def deploy_optimizations(self, agents_file: str, pattern: str = "face_recognition_proven", batch_size: int = 5):
        """Deploy optimizations to agents from file"""
        print(f"🚀 DEPLOYING LAZY LOADING OPTIMIZATIONS")
        print("=" * 50)
        
        # Load candidate agents
        candidates = self._load_candidates(agents_file)
        print(f"✅ Loaded {len(candidates)} optimization candidates")
        
        # Process in batches for safety
        successful_optimizations = 0
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            print(f"\n🔧 PROCESSING BATCH {batch_num} ({len(batch)} agents):")
            
            batch_success = 0
            for agent_name in batch:
                try:
                    if self._optimize_agent(agent_name):
                        batch_success += 1
                        successful_optimizations += 1
                        print(f"   ✅ {agent_name}: Optimization applied successfully")
                    else:
                        print(f"   ❌ {agent_name}: Optimization failed")
                        
                except Exception as e:
                    print(f"   ❌ {agent_name}: Error during optimization - {e}")
                    self.optimization_stats["errors"].append(f"{agent_name}: {str(e)}")
            
            print(f"   📊 Batch {batch_num} Results: {batch_success}/{len(batch)} successful")
            
            # Brief pause between batches
            if i + batch_size < len(candidates):
                print(f"   ⏳ Waiting 30 seconds before next batch...")
                time.sleep(30)
        
        # Generate optimization report
        self._generate_optimization_report(successful_optimizations, len(candidates))
        
        return successful_optimizations >= len(candidates) * 0.75  # 75% success threshold
    
    def _load_candidates(self, agents_file: str) -> List[str]:
        """Load optimization candidates from file"""
        try:
            # Try JSON file first
            if agents_file.endswith('.json'):
                candidates_path = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / agents_file
                with open(candidates_path, 'r') as f:
                    data = json.load(f)
                return [candidate['name'] for candidate in data.get('candidates', [])]
            
            # Try text file
            elif agents_file.endswith('.txt'):
                candidates_path = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / agents_file
                with open(candidates_path, 'r') as f:
                    return [line.strip() for line in f if line.strip()]
            
            else:
                # Direct file path
                candidates_path = Path(agents_file)
                if candidates_path.exists():
                    with open(candidates_path, 'r') as f:
                        return [line.strip() for line in f if line.strip()]
        
        except Exception as e:
            print(f"❌ Error loading candidates from {agents_file}: {e}")
            return []
        
        return []
    
    def _optimize_agent(self, agent_name: str) -> bool:
        """Apply optimization to a specific agent"""
        try:
            # Find agent script path
            script_path = self._find_agent_script(agent_name)
            if not script_path:
                print(f"   ⚠️  {agent_name}: Script not found")
                return False
            
            print(f"   🔧 {agent_name}: Analyzing {script_path}")
            
            # Create backup
            backup_path = self._create_backup(script_path)
            if backup_path:
                self.optimization_stats["backup_files"].append(str(backup_path))
            
            # Analyze script for optimization opportunities
            optimization_plan = self._analyze_script_for_optimization(script_path)
            
            if not optimization_plan["optimizable"]:
                print(f"   ⚠️  {agent_name}: No clear optimization opportunities found")
                return False
            
            # Apply optimizations
            success = self._apply_optimizations(script_path, optimization_plan)
            
            if success:
                self.optimization_stats["agents_processed"] += 1
                self.optimization_stats["optimizations_applied"] += len(optimization_plan["patterns"])
                self.optimization_stats["estimated_improvements"][agent_name] = optimization_plan["estimated_improvement"]
            
            return success
            
        except Exception as e:
            print(f"   ❌ {agent_name}: Optimization error - {e}")
            return False
    
    def _find_agent_script(self, agent_name: str) -> str:
        """Find the script path for an agent"""
        # Common locations to search
        search_paths = [
            f"main_pc_code/agents/{agent_name}.py",
            f"pc2_code/agents/{agent_name}.py", 
            f"pc2_code/agents/core_agents/{agent_name}.py",
            f"agents/{agent_name}.py",
            f"phase1_implementation/consolidated_agents/**/{agent_name}.py"
        ]
        
        project_root = Path(PathManager.get_project_root())
        
        for search_path in search_paths:
            if '**' in search_path:
                # Glob search for consolidated agents
                base_path = project_root / search_path.split('**')[0]
                if base_path.exists():
                    for file_path in base_path.rglob(f"{agent_name}.py"):
                        return str(file_path.relative_to(project_root))
            else:
                file_path = project_root / search_path
                if file_path.exists():
                    return search_path
        
        # Alternative naming patterns
        alternative_names = [
            agent_name.lower(),
            agent_name.replace('Agent', '').lower() + '_agent',
            agent_name.lower() + '_agent'
        ]
        
        for alt_name in alternative_names:
            for search_path in search_paths:
                modified_path = search_path.replace(agent_name, alt_name)
                file_path = project_root / modified_path
                if file_path.exists():
                    return modified_path
        
        return None
    
    def _create_backup(self, script_path: str) -> Path:
        """Create backup of original script"""
        try:
            full_path = Path(PathManager.get_project_root()) / script_path
            backup_path = full_path.with_suffix(f'.py.backup_{int(time.time())}')
            shutil.copy2(full_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"   ⚠️  Backup creation failed: {e}")
            return None
    
    def _analyze_script_for_optimization(self, script_path: str) -> Dict[str, Any]:
        """Analyze script to determine optimization opportunities"""
        try:
            full_path = Path(PathManager.get_project_root()) / script_path
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse to find imports and initialization patterns
            heavy_imports = self._find_heavy_imports(content)
            initialization_code = self._find_initialization_code(content)
            
            # Determine if optimization is worthwhile
            optimizable = (
                len(heavy_imports) >= 2 or
                len(initialization_code) >= 3 or
                any(lib in content for lib in ['torch', 'transformers', 'cv2', 'tensorflow'])
            )
            
            if not optimizable:
                return {"optimizable": False}
            
            # Estimate improvement potential
            improvement_score = self._estimate_improvement(heavy_imports, initialization_code, content)
            
            return {
                "optimizable": True,
                "heavy_imports": heavy_imports,
                "initialization_code": initialization_code,
                "patterns": ["lazy_loading"],  # Start with lazy loading
                "estimated_improvement": improvement_score
            }
            
        except Exception as e:
            return {"optimizable": False, "error": str(e)}
    
    def _find_heavy_imports(self, content: str) -> List[str]:
        """Find heavy imports that can be lazy loaded"""
        heavy_libraries = [
            'torch', 'tensorflow', 'transformers', 'cv2', 'opencv',
            'numpy', 'pandas', 'sklearn', 'scipy', 'matplotlib',
            'requests', 'aiohttp', 'fastapi', 'uvicorn'
        ]
        
        heavy_imports = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                for lib in heavy_libraries:
                    if lib in line and line not in heavy_imports:
                        heavy_imports.append(line)
                        break
        
        return heavy_imports
    
    def _find_initialization_code(self, content: str) -> List[str]:
        """Find initialization code that can be deferred"""
        init_patterns = [
            r'.*\.load\(',
            r'.*\.from_pretrained\(',
            r'.*= torch\.',
            r'.*= cv2\.',
            r'.*= tf\.',
            r'model\s*=',
            r'tokenizer\s*=',
            r'pipeline\s*='
        ]
        
        initialization_code = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            for pattern in init_patterns:
                if re.match(pattern, line) and line not in initialization_code:
                    initialization_code.append(line)
                    break
        
        return initialization_code
    
    def _estimate_improvement(self, heavy_imports: List[str], init_code: List[str], content: str) -> float:
        """Estimate potential improvement percentage"""
        base_improvement = 20.0  # Base improvement from lazy loading
        
        # Add improvement based on heavy dependencies
        improvement = base_improvement + (len(heavy_imports) * 10)
        
        # Add improvement based on initialization complexity
        improvement += (len(init_code) * 5)
        
        # Bonus for ML/AI models
        if any(lib in content for lib in ['torch', 'transformers', 'tensorflow']):
            improvement += 15
        
        # Bonus for vision processing
        if any(lib in content for lib in ['cv2', 'opencv']):
            improvement += 10
        
        return min(improvement, 90.0)  # Cap at 90% improvement
    
    def _apply_optimizations(self, script_path: str, optimization_plan: Dict) -> bool:
        """Apply optimizations to the script"""
        try:
            full_path = Path(PathManager.get_project_root()) / script_path
            with open(full_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Apply lazy loading pattern
            if "lazy_loading" in optimization_plan["patterns"]:
                optimized_content = self._apply_lazy_loading_pattern(
                    original_content, 
                    optimization_plan["heavy_imports"]
                )
            else:
                optimized_content = original_content
            
            # Validate that the optimized content is syntactically correct
            try:
                ast.parse(optimized_content)
            except SyntaxError as e:
                print(f"   ❌ Syntax error in optimized code: {e}")
                return False
            
            # Write optimized content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(optimized_content)
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error applying optimizations: {e}")
            return False
    
    def _apply_lazy_loading_pattern(self, content: str, heavy_imports: List[str]) -> str:
        """Apply lazy loading pattern to the content"""
        lines = content.split('\n')
        optimized_lines = []
        imports_moved = []
        in_class = False
        class_name = None
        
        # First pass: identify and remove heavy imports, track class structure
        for line in lines:
            stripped = line.strip()
            
            # Track class definitions
            if stripped.startswith('class ') and '(' in stripped:
                in_class = True
                class_name = stripped.split('class ')[1].split('(')[0].strip()
                optimized_lines.append(line)
                continue
            
            # Check if line is a heavy import
            is_heavy_import = any(imp.strip() == stripped for imp in heavy_imports)
            
            if is_heavy_import:
                # Comment out the original import
                optimized_lines.append(f"# LAZY LOADING: {line}")
                imports_moved.append(line.strip())
            else:
                optimized_lines.append(line)
        
        # Second pass: add lazy loading method after class definition
        if imports_moved and class_name:
            final_lines = []
            class_found = False
            init_found = False
            
            for i, line in enumerate(optimized_lines):
                final_lines.append(line)
                
                # Add lazy loading method after class definition
                if not class_found and line.strip().startswith(f'class {class_name}'):
                    class_found = True
                
                # Add lazy loading method after __init__ or first method
                if (class_found and not init_found and 
                    (line.strip().startswith('def __init__') or 
                     (line.strip().startswith('def ') and '    ' in line))):
                    
                    init_found = True
                    
                    # Find end of current method
                    j = i + 1
                    while j < len(optimized_lines) and (optimized_lines[j].startswith('        ') or optimized_lines[j].strip() == ''):
                        j += 1
                    
                    # Insert lazy loading method
                    indent = "    "
                    final_lines.extend([
                        "",
                        f"{indent}def _lazy_import_dependencies(self):",
                        f"{indent}    \"\"\"Lazy import heavy dependencies only when needed\"\"\"",
                        f"{indent}    if not hasattr(self, '_dependencies_loaded'):",
                        f"{indent}        try:"
                    ])
                    
                    # Add the imports
                    for imp in imports_moved:
                        final_lines.append(f"{indent}            {imp}")
                    
                    final_lines.extend([
                        f"{indent}            self._dependencies_loaded = True",
                        f"{indent}            if hasattr(self, 'logger'):",
                        f"{indent}                self.logger.info(f'{{self.name}}: Dependencies loaded successfully')",
                        f"{indent}        except ImportError as e:",
                        f"{indent}            self._dependencies_loaded = False",
                        f"{indent}            if hasattr(self, 'logger'):",
                        f"{indent}                self.logger.error(f'{{self.name}}: Failed to load dependencies: {{e}}')",
                        f"{indent}        except Exception as e:",
                        f"{indent}            self._dependencies_loaded = False",
                        f"{indent}            if hasattr(self, 'logger'):",
                        f"{indent}                self.logger.warning(f'{{self.name}}: Dependency loading error: {{e}}')",
                        "",
                        f"{indent}    return self._dependencies_loaded",
                        "",
                        f"{indent}def _ensure_dependencies_loaded(self):",
                        f"{indent}    \"\"\"Ensure dependencies are loaded before use\"\"\"",
                        f"{indent}    if not self._lazy_import_dependencies():",
                        f"{indent}        raise ImportError(f'{{self.name}}: Required dependencies not available')",
                        ""
                    ])
            
            return '\n'.join(final_lines)
        
        return '\n'.join(optimized_lines)
    
    def _apply_cache_optimization_pattern(self, content: str, optimization_plan: Dict) -> str:
        """Apply cache optimization pattern"""
        # Placeholder for cache optimization
        return content
    
    def _apply_dependency_reduction_pattern(self, content: str, optimization_plan: Dict) -> str:
        """Apply dependency reduction pattern"""
        # Placeholder for dependency reduction
        return content
    
    def _apply_async_initialization_pattern(self, content: str, optimization_plan: Dict) -> str:
        """Apply async initialization pattern"""
        # Placeholder for async initialization
        return content
    
    def _generate_optimization_report(self, successful: int, total: int):
        """Generate comprehensive optimization report"""
        try:
            results_dir = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN"
            report_file = results_dir / f"PHASE_1_WEEK_3_DAY_3_OPTIMIZATION_DEPLOYMENT_REPORT.json"
            
            report_data = {
                "deployment_timestamp": time.time(),
                "optimization_type": "lazy_loading",
                "deployment_phase": "Week 3 Day 3 Batch 1",
                "results": {
                    "total_agents": total,
                    "successful_optimizations": successful,
                    "success_rate": (successful / total * 100) if total > 0 else 0,
                    "agents_processed": self.optimization_stats["agents_processed"],
                    "optimizations_applied": self.optimization_stats["optimizations_applied"]
                },
                "estimated_improvements": self.optimization_stats["estimated_improvements"],
                "backup_files": self.optimization_stats["backup_files"],
                "errors": self.optimization_stats["errors"],
                "rollback_info": {
                    "rollback_command": "python scripts/rollback_optimization.py --restore-backups",
                    "backup_count": len(self.optimization_stats["backup_files"])
                }
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n📊 OPTIMIZATION DEPLOYMENT SUMMARY:")
            print(f"   📈 Success Rate: {successful}/{total} ({(successful/total*100):.1f}%)")
            print(f"   🔧 Optimizations Applied: {self.optimization_stats['optimizations_applied']}")
            print(f"   💾 Backup Files Created: {len(self.optimization_stats['backup_files'])}")
            print(f"   📋 Report Saved: {report_file}")
            
            if self.optimization_stats["errors"]:
                print(f"   ⚠️  Errors Encountered: {len(self.optimization_stats['errors'])}")
                for error in self.optimization_stats["errors"][:3]:  # Show first 3 errors
                    print(f"      • {error}")
                if len(self.optimization_stats["errors"]) > 3:
                    print(f"      • ... and {len(self.optimization_stats['errors']) - 3} more")
            
        except Exception as e:
            print(f"❌ Error generating optimization report: {e}")

def main():
    """Main deployment execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy lazy loading optimizations")
    parser.add_argument("--agents-file", default="batch1_candidates.txt", help="File containing agent names to optimize")
    parser.add_argument("--pattern", default="face_recognition_proven", help="Optimization pattern to apply")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of agents to process in each batch")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, don't apply changes")
    
    args = parser.parse_args()
    
    optimizer = LazyLoadingOptimizer()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE: Analysis only, no changes will be applied")
        # Load and analyze candidates without applying changes
        candidates = optimizer._load_candidates(args.agents_file)
        print(f"✅ Would optimize {len(candidates)} agents")
        return True
    else:
        success = optimizer.deploy_optimizations(
            args.agents_file, 
            args.pattern, 
            args.batch_size
        )
        
        if success:
            print("\n🎉 LAZY LOADING OPTIMIZATION DEPLOYMENT SUCCESSFUL!")
        else:
            print("\n❌ OPTIMIZATION DEPLOYMENT COMPLETED WITH ISSUES")
        
        return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 