#!/usr/bin/env python3
"""
WP-08 Performance Optimization Migration Script
Migrates agents to use caching, profiling, and performance optimization patterns
Target: Agents with performance bottlenecks or resource-intensive operations
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class PerformanceAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect performance optimization opportunities"""
    
    def __init__(self):
        self.expensive_operations = []
        self.loop_patterns = []
        self.computation_patterns = []
        self.io_operations = []
        self.cache_candidates = []
        self.performance_score = 0
        
    def visit_FunctionDef(self, node):
        # Look for expensive computations
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['compute', 'calculate', 'process', 'analyze']):
                    self.expensive_operations.append(f"Expensive operation: {node.name} (line {child.lineno})")
                    self.performance_score += 3
        
        # Look for nested loops
        loop_depth = self._count_loop_depth(node)
        if loop_depth >= 2:
            self.loop_patterns.append(f"Nested loops in {node.name} (depth: {loop_depth}, line {node.lineno})")
            self.performance_score += loop_depth * 2
        
        # Look for repeated computations
        if self._has_repeated_computations(node):
            self.cache_candidates.append(f"Repeated computations in {node.name} (line {node.lineno})")
            self.performance_score += 4
                
        self.generic_visit(node)
    
    def visit_For(self, node):
        # Check for expensive operations inside loops
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['requests', 'get', 'post', 'query', 'fetch']):
                    self.io_operations.append(f"I/O in loop (line {node.lineno})")
                    self.performance_score += 5
        
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Look for mathematical operations that could benefit from optimization
        if (isinstance(node.func, ast.Name) and 
            node.func.id in ['sum', 'max', 'min', 'sorted']):
            self.computation_patterns.append(f"Mathematical operation: {node.func.id} (line {node.lineno})")
            self.performance_score += 1
        
        # Look for file I/O operations
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['open', 'read', 'write', 'load', 'save']):
            self.io_operations.append(f"File I/O operation (line {node.lineno})")
            self.performance_score += 2
        
        # Look for network operations
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['get', 'post', 'put', 'delete', 'request']):
            self.io_operations.append(f"Network operation (line {node.lineno})")
            self.performance_score += 3
            
        self.generic_visit(node)
    
    def _count_loop_depth(self, node) -> int:
        """Count maximum loop nesting depth"""
        max_depth = 0
        
        def count_depth(n, current_depth=0):
            nonlocal max_depth
            if isinstance(n, (ast.For, ast.While)):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            
            for child in ast.iter_child_nodes(n):
                count_depth(child, current_depth)
        
        count_depth(node)
        return max_depth
    
    def _has_repeated_computations(self, node) -> bool:
        """Check for repeated function calls or computations"""
        calls = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        
        # Check for repeated calls
        unique_calls = set(calls)
        return len(calls) - len(unique_calls) >= 3  # 3+ repeated calls

def find_performance_candidates() -> List[Path]:
    """Find agents that would benefit from performance optimization"""
    root = Path.cwd()
    agent_files = []
    
    search_dirs = [
        "main_pc_code/agents",
        "pc2_code/agents", 
        "common",
        "phase1_implementation",
        "phase2_implementation"
    ]
    
    for search_dir in search_dirs:
        search_path = root / search_dir
        if search_path.exists():
            for python_file in search_path.rglob("*.py"):
                if (python_file.name != "__init__.py" and 
                    not python_file.name.startswith("test_") and
                    "_test" not in python_file.name):
                    agent_files.append(python_file)
    
    return agent_files

def analyze_performance_needs(file_path: Path) -> Dict:
    """Analyze a file for performance optimization needs"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = PerformanceAnalyzer()
        analyzer.visit(tree)
        
        # Additional pattern-based analysis
        content_lower = content.lower()
        
        # Heavy computation patterns
        computation_patterns = len(re.findall(r'(for.*for|while.*while|numpy|scipy|pandas|sklearn)', content_lower))
        
        # I/O intensive patterns
        io_patterns = len(re.findall(r'(requests\.|http|open\(|file|json\.load|pickle)', content_lower))
        
        # Memory intensive patterns
        memory_patterns = len(re.findall(r'(list\(|dict\(|\[.*for.*\]|\.append|\.extend)', content_lower))
        
        # Caching opportunity patterns
        cache_patterns = len(re.findall(r'(def.*\(.*\).*return|@.*cache|memoize)', content_lower))
        
        # Calculate needs
        needs_caching = (analyzer.performance_score > 8 or 
                        len(analyzer.cache_candidates) > 0 or 
                        cache_patterns > 3)
        
        needs_profiling = (analyzer.performance_score > 12 or 
                          len(analyzer.expensive_operations) > 2)
        
        needs_optimization = (analyzer.performance_score > 15 or 
                             computation_patterns > 5 or 
                             io_patterns > 5)
        
        needs_async = (io_patterns > 3 and 
                      'async' not in content_lower)
        
        return {
            'file_path': file_path,
            'expensive_operations': analyzer.expensive_operations,
            'loop_patterns': analyzer.loop_patterns,
            'computation_patterns': analyzer.computation_patterns,
            'io_operations': analyzer.io_operations,
            'cache_candidates': analyzer.cache_candidates,
            'computation_count': computation_patterns,
            'io_count': io_patterns,
            'memory_count': memory_patterns,
            'cache_count': cache_patterns,
            'performance_score': analyzer.performance_score + computation_patterns + io_patterns,
            'needs_caching': needs_caching,
            'needs_profiling': needs_profiling,
            'needs_optimization': needs_optimization,
            'needs_async': needs_async,
            'priority': 'high' if analyzer.performance_score > 20 else 'medium' if analyzer.performance_score > 10 else 'low'
        }
    
    except Exception as e:
        return {
            'file_path': file_path,
            'error': str(e),
            'performance_score': 0,
            'needs_caching': False,
            'needs_profiling': False,
            'needs_optimization': False,
            'needs_async': False,
            'priority': 'low'
        }

def generate_caching_integration(file_path: Path) -> str:
    """Generate caching integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-08 Caching Integration for {agent_name}
# Add intelligent caching for performance optimization

from common.performance.caching import (
    get_cache, cached, CacheConfig, CacheBackend, cache_invalidate
)

class {agent_name.title().replace("_", "")}CacheIntegration:
    """Caching integration for {agent_name}"""
    
    def __init__(self):
        # Configure different cache types
        self.response_cache = get_cache(
            "{agent_name}_responses",
            CacheConfig(
                backend=CacheBackend.REDIS,
                max_size=1000,
                default_ttl=300.0  # 5 minutes
            )
        )
        
        self.computation_cache = get_cache(
            "{agent_name}_computations",
            CacheConfig(
                backend=CacheBackend.MEMORY,
                max_size=500,
                default_ttl=3600.0  # 1 hour
            )
        )
    
    @cached(cache_name="{agent_name}_responses", ttl=300.0)
    async def cached_api_call(self, endpoint: str, params: dict):
        """API call with automatic caching"""
        # Your original API call code here
        response = await api_client.get(endpoint, params=params)
        return response.json()
    
    @cached(cache_name="{agent_name}_computations", ttl=3600.0)
    async def cached_computation(self, data: str) -> dict:
        """Expensive computation with caching"""
        # Your expensive computation here
        result = expensive_computation(data)
        return result
    
    async def get_processed_data(self, key: str):
        """Get data with multi-level caching"""
        # Try response cache first
        cached_result = await self.response_cache.get(key)
        if cached_result:
            return cached_result
        
        # Try computation cache
        computation_key = f"comp_{{key}}"
        cached_computation = await self.computation_cache.get(computation_key)
        if cached_computation:
            return cached_computation
        
        # Compute and cache
        result = await self.expensive_operation(key)
        await self.response_cache.set(key, result, ttl=300.0)
        await self.computation_cache.set(computation_key, result, ttl=3600.0)
        
        return result
    
    @cache_invalidate(cache_name="{agent_name}_responses", pattern="user_")
    async def update_user_data(self, user_id: str, data: dict):
        """Update operation that invalidates related cache"""
        # Your update logic here
        result = await update_database(user_id, data)
        return result

# Example usage:
# cache_integration = {agent_name.title().replace("_", "")}CacheIntegration()
# result = await cache_integration.cached_api_call("/users", {{"limit": 10}})
# data = await cache_integration.get_processed_data("user_123")
'''
    
    return integration_example

def generate_profiling_integration(file_path: Path) -> str:
    """Generate profiling integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-08 Profiling Integration for {agent_name}
# Add performance profiling and monitoring

from common.performance.profiler import (
    get_profiler, profile_time, profile_memory, profile_cpu, profile_all
)

class {agent_name.title().replace("_", "")}ProfilingIntegration:
    """Profiling integration for {agent_name}"""
    
    def __init__(self):
        self.profiler = get_profiler()
    
    @profile_time(name="{agent_name}_main_operation")
    async def main_operation(self, data):
        """Main operation with time profiling"""
        return await self.process_data(data)
    
    @profile_memory(name="{agent_name}_memory_intensive")
    async def memory_intensive_operation(self, large_data):
        """Memory-intensive operation with memory profiling"""
        # Your memory-intensive code here
        processed = []
        for item in large_data:
            processed.append(complex_processing(item))
        return processed
    
    @profile_cpu(name="{agent_name}_cpu_intensive")
    def cpu_intensive_operation(self, data):
        """CPU-intensive operation with CPU profiling"""
        # Your CPU-intensive code here
        result = 0
        for i in range(len(data)):
            for j in range(len(data)):
                result += compute_complex(data[i], data[j])
        return result
    
    @profile_all(name="{agent_name}_comprehensive")
    async def comprehensive_operation(self, data):
        """Operation with comprehensive profiling"""
        # This will profile CPU, memory, and time
        return await self.complex_operation(data)
    
    async def start_monitoring(self):
        """Start system performance monitoring"""
        await self.profiler.start_system_monitoring(interval=10.0)
    
    async def stop_monitoring(self):
        """Stop system performance monitoring"""
        await self.profiler.stop_system_monitoring()
    
    def get_performance_report(self):
        """Get performance analysis report"""
        # Get profiling results
        results = self.profiler.get_profile_results()
        
        # Get system metrics
        system_metrics = self.profiler.get_system_summary()
        
        # Analyze specific functions
        main_op_summary = self.profiler.get_profile_summary("{agent_name}_main_operation")
        
        return {{
            "agent": "{agent_name}",
            "main_operation_performance": main_op_summary,
            "system_metrics": system_metrics,
            "all_functions": list(results.keys())
        }}

# Example usage:
# profiling = {agent_name.title().replace("_", "")}ProfilingIntegration()
# await profiling.start_monitoring()
# result = await profiling.main_operation(data)
# report = profiling.get_performance_report()
'''
    
    return integration_example

def generate_optimization_integration(file_path: Path) -> str:
    """Generate optimization integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-08 Optimization Integration for {agent_name}
# Add automatic performance optimization and analysis

from common.performance.optimizer import (
    get_optimizer, optimize_function, run_system_optimization
)
from common.performance.profiler import get_profiler

class {agent_name.title().replace("_", "")}OptimizationIntegration:
    """Optimization integration for {agent_name}"""
    
    def __init__(self):
        self.optimizer = get_optimizer()
        self.profiler = get_profiler()
    
    async def optimize_operations(self):
        """Run optimization analysis on all operations"""
        # Get profiling data
        profiler_data = self.profiler.get_profile_results()
        
        # Get optimization recommendations
        recommendations = self.optimizer.optimize_system(profiler_data)
        
        return recommendations
    
    async def get_optimization_report(self):
        """Get comprehensive optimization report"""
        return run_system_optimization()
    
    async def benchmark_optimization(self, original_func, optimized_func, test_data):
        """Benchmark optimization effectiveness"""
        return self.optimizer.benchmark_optimization(
            original_func, optimized_func, test_data, iterations=50
        )
    
    def apply_caching_optimization(self, func_name: str):
        """Apply caching optimization to function"""
        # Example of applying caching based on analysis
        from common.performance.caching import cached
        
        # This would be applied to your actual functions
        @cached(cache_name=f"{agent_name}_{{func_name}}", ttl=600.0)
        def optimized_function(*args, **kwargs):
            # Your original function logic
            pass
        
        return optimized_function
    
    async def apply_async_optimization(self):
        """Convert I/O operations to async"""
        # Example optimization: convert sync I/O to async
        import aiohttp
        import aiofiles
        
        # Before: synchronous I/O
        # response = requests.get(url)
        # with open(file) as f: data = f.read()
        
        # After: asynchronous I/O
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                json_data = await response.json()
        
        async with aiofiles.open(file_path) as f:
            data = await f.read()
        
        return json_data, data
    
    def optimize_memory_usage(self, large_list):
        """Optimize memory usage with generators"""
        # Before: memory-intensive list comprehension
        # result = [expensive_operation(item) for item in large_list]
        
        # After: memory-efficient generator
        def optimized_generator():
            for item in large_list:
                yield expensive_operation(item)
        
        return optimized_generator()
    
    def optimize_cpu_intensive(self, data):
        """Optimize CPU-intensive operations"""
        import asyncio
        from concurrent.futures import ProcessPoolExecutor
        
        # Use process pool for CPU-bound tasks
        with ProcessPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, cpu_intensive_task, chunk)
                for chunk in data_chunks
            ]
            return await asyncio.gather(*tasks)

# Example usage:
# optimization = {agent_name.title().replace("_", "")}OptimizationIntegration()
# recommendations = await optimization.optimize_operations()
# report = await optimization.get_optimization_report()
# 
# # Apply specific optimizations
# optimized_data = optimization.optimize_memory_usage(large_dataset)
# async_result = await optimization.apply_async_optimization()
'''
    
    return integration_example

def update_requirements_for_performance():
    """Update requirements.txt with performance optimization dependencies"""
    requirements_path = Path("requirements.txt")
    
    try:
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                content = f.read()
        else:
            content = ""
        
        # Performance optimization dependencies
        new_deps = [
            "# WP-08 Performance Optimization Dependencies",
            "psutil==5.9.6",
            "memory-profiler==0.61.0",
            "py-spy==0.3.14",
            "line-profiler==4.1.1",
            "aiofiles==23.2.1"
        ]
        
        # Add dependencies if not already present
        for dep in new_deps:
            dep_name = dep.split('==')[0].replace("# ", "")
            if dep_name not in content:
                content += f"\n{dep}"
        
        with open(requirements_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated requirements.txt with performance optimization dependencies")
        return True
    
    except Exception as e:
        print(f"❌ Error updating requirements.txt: {e}")
        return False

def main():
    print("🚀 WP-08: PERFORMANCE OPTIMIZATION MIGRATION")
    print("=" * 50)
    
    # Update requirements first
    update_requirements_for_performance()
    
    # Find performance optimization candidates
    agent_files = find_performance_candidates()
    print(f"📁 Found {len(agent_files)} agent files to analyze")
    
    # Analyze performance needs
    analysis_results = []
    for agent_file in agent_files:
        result = analyze_performance_needs(agent_file)
        analysis_results.append(result)
    
    # Sort by performance score
    analysis_results.sort(key=lambda x: x.get('performance_score', 0), reverse=True)
    
    # Filter candidates
    high_priority = [r for r in analysis_results if r.get('performance_score', 0) >= 20]
    caching_candidates = [r for r in analysis_results if r.get('needs_caching', False)]
    profiling_candidates = [r for r in analysis_results if r.get('needs_profiling', False)]
    optimization_candidates = [r for r in analysis_results if r.get('needs_optimization', False)]
    async_candidates = [r for r in analysis_results if r.get('needs_async', False)]
    
    print(f"\n📊 PERFORMANCE OPTIMIZATION ANALYSIS:")
    print(f"✅ High priority targets: {len(high_priority)}")
    print(f"💾 Caching candidates: {len(caching_candidates)}")
    print(f"📊 Profiling candidates: {len(profiling_candidates)}")
    print(f"⚡ Optimization candidates: {len(optimization_candidates)}")
    print(f"🔄 Async candidates: {len(async_candidates)}")
    
    # Show top agents needing performance optimization
    if high_priority:
        print(f"\n🎯 TOP PERFORMANCE OPTIMIZATION TARGETS:")
        for result in high_priority[:10]:  # Show top 10
            file_path = result['file_path']
            score = result.get('performance_score', 0)
            print(f"\n📄 {file_path} (Score: {score})")
            print(f"   💾 Caching: {'✅' if result.get('needs_caching') else '❌'}")
            print(f"   📊 Profiling: {'✅' if result.get('needs_profiling') else '❌'}")
            print(f"   ⚡ Optimization: {'✅' if result.get('needs_optimization') else '❌'}")
            print(f"   🔄 Async: {'✅' if result.get('needs_async') else '❌'}")
            print(f"   🎯 Priority: {result.get('priority', 'low')}")
    
    # Generate integration examples
    examples_dir = Path("docs/performance_examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    generated_count = 0
    for result in high_priority[:15]:  # Top 15 candidates
        file_path = result['file_path']
        agent_name = file_path.stem
        
        # Generate caching example
        if result.get('needs_caching'):
            cache_example = generate_caching_integration(file_path)
            cache_file = examples_dir / f"{agent_name}_caching.py"
            with open(cache_file, 'w') as f:
                f.write(cache_example)
        
        # Generate profiling example
        if result.get('needs_profiling'):
            profiling_example = generate_profiling_integration(file_path)
            profiling_file = examples_dir / f"{agent_name}_profiling.py"
            with open(profiling_file, 'w') as f:
                f.write(profiling_example)
        
        # Generate optimization example
        if result.get('needs_optimization'):
            optimization_example = generate_optimization_integration(file_path)
            optimization_file = examples_dir / f"{agent_name}_optimization.py"
            with open(optimization_file, 'w') as f:
                f.write(optimization_example)
        
        generated_count += 1
    
    print(f"\n✅ WP-08 PERFORMANCE OPTIMIZATION ANALYSIS COMPLETE!")
    print(f"💾 Caching candidates: {len(caching_candidates)} agents")
    print(f"📊 Profiling candidates: {len(profiling_candidates)} agents")
    print(f"⚡ Optimization candidates: {len(optimization_candidates)} agents")
    print(f"🔄 Async candidates: {len(async_candidates)} agents")
    print(f"📝 Generated examples: {generated_count} agents")
    
    print(f"\n🚀 Performance Optimization Benefits:")
    print(f"💾 Intelligent caching reduces computation load")
    print(f"📊 Detailed profiling identifies bottlenecks")
    print(f"⚡ Automatic optimization recommendations")
    print(f"🔄 Async patterns improve I/O performance")
    print(f"📈 Comprehensive performance monitoring")
    
    print(f"\n🚀 Next Steps:")
    print(f"1. Performance optimization implemented in common/performance/")
    print(f"2. Integration examples: docs/performance_examples/")
    print(f"3. Use: from common.performance.caching import cached")
    print(f"4. Use: from common.performance.profiler import profile_time")
    print(f"5. Use: from common.performance.optimizer import run_system_optimization")

if __name__ == "__main__":
    main() 