"""DAG executor for orchestrating parallel emotion processing modules."""

import asyncio
import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import deque, defaultdict
import time
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .schemas import Payload, EmotionalContext, ModuleOutput
from .cache import EmbeddingCache
from .fusion import BaseFusion
from modules.base import BaseModule

logger = logging.getLogger(__name__)


class DAGNode:
    """Represents a node in the dependency graph."""
    
    def __init__(self, module: BaseModule):
        self.module = module
        self.name = module.name
        self.dependencies = set(module.requires)
        self.dependents = set()
        self.is_ready = False
        self.is_running = False
        self.is_completed = False
        self.result: Optional[ModuleOutput] = None
        self.error: Optional[Exception] = None
    
    def can_execute(self, completed_modules: Set[str]) -> bool:
        """Check if this node can be executed given completed modules."""
        return (not self.is_completed and 
                not self.is_running and 
                self.dependencies.issubset(completed_modules))
    
    def __repr__(self) -> str:
        return f"DAGNode({self.name}, deps={self.dependencies})"


class DAGExecutor:
    """
    Directed Acyclic Graph executor for emotion processing modules.
    
    This class builds a dependency graph from the enabled modules and
    executes them in parallel where possible, respecting dependencies.
    """
    
    def __init__(
        self, 
        modules: Dict[str, BaseModule], 
        fusion: BaseFusion, 
        cache: EmbeddingCache,
        max_concurrent: int = 4
    ):
        """
        Initialize DAG executor.
        
        Args:
            modules: Dictionary of available modules
            fusion: Fusion algorithm instance
            cache: Feature cache instance
            max_concurrent: Maximum concurrent module executions
        """
        self.modules = modules
        self.fusion = fusion
        self.cache = cache
        self.max_concurrent = max_concurrent
        
        # Build dependency graph
        self.graph = self._build_dependency_graph()
        
        # Execution statistics
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'avg_execution_time_ms': 0.0,
            'module_stats': defaultdict(list)
        }
        
        logger.info(f"DAGExecutor initialized with {len(self.modules)} modules")
        logger.info(f"Dependency graph: {self._get_graph_summary()}")
    
    def _build_dependency_graph(self) -> Dict[str, DAGNode]:
        """Build the dependency graph from modules."""
        graph = {}
        
        # Create nodes for each module
        for name, module in self.modules.items():
            graph[name] = DAGNode(module)
        
        # Build dependency relationships
        for name, node in graph.items():
            for dep_name in node.dependencies:
                if dep_name in graph:
                    graph[dep_name].dependents.add(name)
                else:
                    logger.warning(f"Module {name} depends on unknown module {dep_name}")
        
        # Validate graph for cycles
        self._validate_graph(graph)
        
        return graph
    
    def _validate_graph(self, graph: Dict[str, DAGNode]) -> None:
        """Validate that the dependency graph is acyclic."""
        # Use topological sort to detect cycles
        in_degree = {name: len(node.dependencies) for name, node in graph.items()}
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        processed = 0
        
        while queue:
            current = queue.popleft()
            processed += 1
            
            # Reduce in-degree for dependents
            for dependent in graph[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if processed != len(graph):
            raise ValueError("Circular dependency detected in module graph")
        
        logger.info(f"Dependency graph validated: {processed} modules, no cycles")
    
    def _get_graph_summary(self) -> Dict[str, Any]:
        """Get a summary of the dependency graph."""
        return {
            'total_modules': len(self.graph),
            'root_modules': [name for name, node in self.graph.items() if not node.dependencies],
            'leaf_modules': [name for name, node in self.graph.items() if not node.dependents],
            'dependency_edges': sum(len(node.dependencies) for node in self.graph.values())
        }
    
    async def run(self, payload: Payload) -> EmotionalContext:
        """
        Execute the DAG for the given payload.
        
        Args:
            payload: Input payload to process
            
        Returns:
            Unified emotional context from fusion
        """
        start_time = time.time()
        
        try:
            # Reset graph state
            self._reset_graph_state()
            
            # Execute modules in dependency order
            module_outputs = await self._execute_dag(payload)
            
            # Fuse results
            emotional_context = self.fusion.combine(module_outputs)
            
            # Update statistics
            execution_time = (time.time() - start_time) * 1000
            self._update_stats(module_outputs, execution_time, success=True)
            
            logger.debug(f"DAG execution completed in {execution_time:.2f}ms")
            
            return emotional_context
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self._update_stats({}, execution_time, success=False)
            
            logger.error(f"DAG execution failed: {e}")
            
            # Return empty context on failure
            return self.fusion.combine({})
    
    def _reset_graph_state(self) -> None:
        """Reset the graph state for a new execution."""
        for node in self.graph.values():
            node.is_ready = False
            node.is_running = False
            node.is_completed = False
            node.result = None
            node.error = None
    
    async def _execute_dag(self, payload: Payload) -> Dict[str, ModuleOutput]:
        """
        Execute the DAG using parallel processing where possible.
        
        Args:
            payload: Input payload
            
        Returns:
            Dictionary of module outputs
        """
        completed_modules = set()
        running_modules = set()
        module_outputs = {}
        
        # Semaphore to limit concurrent executions
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        while len(completed_modules) < len(self.graph):
            # Find modules ready to execute
            ready_modules = [
                name for name, node in self.graph.items()
                if node.can_execute(completed_modules) and name not in running_modules
            ]
            
            if not ready_modules and not running_modules:
                # No modules can run and none are running - deadlock or completion
                break
            
            # Start ready modules
            tasks = []
            for module_name in ready_modules:
                if len(running_modules) < self.max_concurrent:
                    task = asyncio.create_task(
                        self._execute_module_with_semaphore(
                            semaphore, module_name, payload
                        )
                    )
                    tasks.append((module_name, task))
                    running_modules.add(module_name)
            
            # Wait for at least one module to complete
            if tasks:
                done, pending = await asyncio.wait(
                    [task for _, task in tasks],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Process completed tasks
                for module_name, task in tasks:
                    if task in done:
                        try:
                            result = await task
                            node = self.graph[module_name]
                            node.result = result
                            node.is_completed = True
                            
                            if result and not result.metadata.get('failed', False):
                                module_outputs[module_name] = result
                            
                            completed_modules.add(module_name)
                            
                        except Exception as e:
                            logger.error(f"Module {module_name} failed: {e}")
                            self.graph[module_name].error = e
                            self.graph[module_name].is_completed = True
                            completed_modules.add(module_name)  # Mark as completed even if failed
                        
                        finally:
                            running_modules.discard(module_name)
            
            # Small delay to prevent busy waiting
            if not ready_modules:
                await asyncio.sleep(0.001)
        
        logger.debug(f"DAG execution completed: {len(module_outputs)} successful modules")
        return module_outputs
    
    async def _execute_module_with_semaphore(
        self, 
        semaphore: asyncio.Semaphore, 
        module_name: str, 
        payload: Payload
    ) -> Optional[ModuleOutput]:
        """Execute a single module with semaphore control."""
        async with semaphore:
            node = self.graph[module_name]
            node.is_running = True
            
            try:
                logger.debug(f"Executing module: {module_name}")
                result = await node.module.process(payload, self.cache)
                
                logger.debug(f"Module {module_name} completed in {result.processing_time_ms:.2f}ms")
                return result
                
            except Exception as e:
                logger.error(f"Module {module_name} execution failed: {e}")
                # Return error result
                return ModuleOutput(
                    module_name=module_name,
                    features=[],
                    confidence=0.0,
                    processing_time_ms=0.0,
                    metadata={'failed': True, 'error': str(e)}
                )
            finally:
                node.is_running = False
    
    def _update_stats(
        self, 
        module_outputs: Dict[str, ModuleOutput], 
        execution_time: float, 
        success: bool
    ) -> None:
        """Update execution statistics."""
        self.execution_stats['total_executions'] += 1
        
        if success:
            self.execution_stats['successful_executions'] += 1
        else:
            self.execution_stats['failed_executions'] += 1
        
        # Update average execution time
        total_time = (self.execution_stats['avg_execution_time_ms'] * 
                     (self.execution_stats['total_executions'] - 1) + execution_time)
        self.execution_stats['avg_execution_time_ms'] = total_time / self.execution_stats['total_executions']
        
        # Update module-specific stats
        for module_name, output in module_outputs.items():
            self.execution_stats['module_stats'][module_name].append(output.processing_time_ms)
    
    def get_execution_order(self) -> List[List[str]]:
        """
        Get the execution order of modules as a list of levels.
        
        Returns:
            List where each element is a list of modules that can run in parallel
        """
        in_degree = {name: len(node.dependencies) for name, node in self.graph.items()}
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        levels = []
        
        while queue:
            current_level = []
            next_queue = deque()
            
            # Process all modules at current level
            while queue:
                current = queue.popleft()
                current_level.append(current)
                
                # Update dependents
                for dependent in self.graph[current].dependents:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)
            
            if current_level:
                levels.append(sorted(current_level))
            
            queue = next_queue
        
        return levels
    
    def get_critical_path(self) -> Tuple[List[str], float]:
        """
        Calculate the critical path through the DAG.
        
        Returns:
            Tuple of (path, estimated_time_ms)
        """
        # Use average processing times for estimation
        processing_times = {}
        for name, node in self.graph.items():
            stats = self.execution_stats['module_stats'].get(name, [])
            if stats:
                processing_times[name] = sum(stats) / len(stats)
            else:
                # Default estimate based on module type
                default_times = {
                    'tone': 10.0,
                    'mood': 20.0,
                    'empathy': 15.0,
                    'voice_profile': 10.0,
                    'human_awareness': 8.0,
                    'synthesis': 25.0
                }
                processing_times[name] = default_times.get(name, 15.0)
        
        # Find longest path using topological sort
        distances = {name: 0.0 for name in self.graph}
        predecessors = {name: None for name in self.graph}
        
        # Process in topological order
        levels = self.get_execution_order()
        for level in levels:
            for node_name in level:
                node = self.graph[node_name]
                
                # Update distances to dependents
                for dependent in node.dependents:
                    new_distance = distances[node_name] + processing_times[node_name]
                    if new_distance > distances[dependent]:
                        distances[dependent] = new_distance
                        predecessors[dependent] = node_name
        
        # Find the node with maximum distance
        end_node = max(distances.keys(), key=lambda x: distances[x])
        max_time = distances[end_node] + processing_times[end_node]
        
        # Reconstruct path
        path = []
        current = end_node
        while current is not None:
            path.append(current)
            current = predecessors[current]
        
        path.reverse()
        return path, max_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics."""
        critical_path, critical_time = self.get_critical_path()
        
        return {
            'graph_summary': self._get_graph_summary(),
            'execution_stats': self.execution_stats.copy(),
            'execution_order': self.get_execution_order(),
            'critical_path': {
                'modules': critical_path,
                'estimated_time_ms': critical_time
            },
            'parallelization_factor': len(self.graph) / len(self.get_execution_order()) if self.get_execution_order() else 1.0
        }
    
    def visualize_graph(self) -> str:
        """Generate a text representation of the dependency graph."""
        lines = ["Dependency Graph:"]
        levels = self.get_execution_order()
        
        for i, level in enumerate(levels):
            lines.append(f"  Level {i}: {', '.join(level)}")
            
            # Show dependencies
            for module in level:
                deps = self.graph[module].dependencies
                if deps:
                    lines.append(f"    {module} depends on: {', '.join(deps)}")
        
        return "\n".join(lines)
    
    async def warmup_modules(self) -> None:
        """Warm up all modules concurrently."""
        logger.info("Warming up modules...")
        
        warmup_tasks = [
            module.warmup() for module in self.modules.values()
        ]
        
        await asyncio.gather(*warmup_tasks, return_exceptions=True)
        
        logger.info("Module warmup completed")
    
    async def shutdown_modules(self) -> None:
        """Shutdown all modules gracefully."""
        logger.info("Shutting down modules...")
        
        shutdown_tasks = [
            module.shutdown() for module in self.modules.values()
        ]
        
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        logger.info("Module shutdown completed")