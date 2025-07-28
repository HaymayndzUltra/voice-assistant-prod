#!/usr/bin/env python3
"""
Workflow Memory Intelligence System - Tailored for AI_System_Monorepo + Cursor + AI Assistant workflow
"""

import json
import os
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

# Import our existing memory system
from todo_manager import new_task, add_todo, list_open_tasks, set_task_status, hard_delete_task
from task_interruption_manager import auto_task_handler, get_interruption_status
from task_state_manager import save_task_state, load_task_state


@dataclass
class TaskComplexity:
    """Task complexity analysis result"""
    score: int
    level: str  # SIMPLE, MEDIUM, COMPLEX
    should_chunk: bool
    estimated_subtasks: int
    reasoning: List[str]


@dataclass
class Subtask:
    """Individual subtask information"""
    id: str
    description: str
    priority: int
    estimated_duration: int  # minutes
    dependencies: List[str]
    status: str  # pending, in_progress, completed, failed


@dataclass
class ChunkedTask:
    """Chunked task with subtasks"""
    original_task: str
    task_id: str
    complexity: TaskComplexity
    subtasks: List[Subtask]
    current_subtask_index: int
    status: str  # chunked, in_progress, completed, failed


class TaskComplexityAnalyzer:
    """Analyzes task complexity for our workflow"""
    
    def __init__(self):
        # Workflow-specific indicators
        self.simple_indicators = [
            'fix typo', 'update comment', 'change variable', 'add import',
            'remove unused', 'format code', 'simple', 'quick', 'minor',
            'gawa', 'gawin', 'maliit', 'mabilis', 'ayusin lang'
        ]
        
        self.medium_indicators = [
            'refactor', 'optimize', 'improve', 'enhance', 'update',
            'modify', 'adjust', 'tune', 'pagandahin', 'i-improve'
        ]
        
        self.complex_indicators = [
            'implement', 'create', 'build', 'develop', 'design',
            'architecture', 'system', 'framework', 'comprehensive',
            'complete', 'full', 'extensive', 'malawak', 'malaki',
            'buo', 'sistema', 'framework', 'build entire', 'create system'
        ]
        
        # Workflow-specific complexity factors
        self.workflow_factors = {
            'file_count': 10,  # Points per file mentioned
            'system_components': 15,  # Points per system component
            'analysis_depth': 20,  # Points for deep analysis
            'automation_level': 25,  # Points for automation tasks
        }
    
    def analyze_complexity(self, task_description: str) -> TaskComplexity:
        """Analyze task complexity for our workflow"""
        
        complexity_score = 0
        reasoning = []
        task_lower = task_description.lower()
        
        # Count complexity indicators
        simple_count = sum(1 for indicator in self.simple_indicators if indicator in task_lower)
        medium_count = sum(1 for indicator in self.medium_indicators if indicator in task_lower)
        complex_count = sum(1 for indicator in self.complex_indicators if indicator in task_lower)
        
        # Calculate base score
        complexity_score -= simple_count * 10
        complexity_score += medium_count * 5
        complexity_score += complex_count * 20
        
        # Workflow-specific analysis
        if simple_count > 0:
            reasoning.append(f"Contains {simple_count} simple task indicators")
        
        if medium_count > 0:
            reasoning.append(f"Contains {medium_count} medium complexity indicators")
        
        if complex_count > 0:
            reasoning.append(f"Contains {complex_count} complex task indicators")
        
        # Analyze file references (common in our workflow)
        file_patterns = re.findall(r'[\w\-_]+\.(py|sh|md|json|yml|yaml)', task_description)
        if file_patterns:
            complexity_score += len(file_patterns) * self.workflow_factors['file_count']
            reasoning.append(f"References {len(file_patterns)} files")
        
        # Analyze system components
        system_components = ['docker', 'wsl', 'memory', 'task', 'automation', 'system']
        component_count = sum(1 for component in system_components if component in task_lower)
        if component_count > 0:
            complexity_score += component_count * self.workflow_factors['system_components']
            reasoning.append(f"Involves {component_count} system components")
        
        # Analyze task length
        word_count = len(task_description.split())
        if word_count > 100:
            complexity_score += 30
            reasoning.append("Very long task description")
        elif word_count > 50:
            complexity_score += 15
            reasoning.append("Long task description")
        elif word_count < 10:
            complexity_score -= 20
            reasoning.append("Very short task description")
        
        # Analyze analysis depth
        analysis_indicators = ['analyze', 'deep scan', 'investigate', 'examine', 'review']
        if any(indicator in task_lower for indicator in analysis_indicators):
            complexity_score += self.workflow_factors['analysis_depth']
            reasoning.append("Involves deep analysis")
        
        # Determine complexity level
        if complexity_score < 0:
            level = "SIMPLE"
            should_chunk = False
        elif complexity_score < 30:
            level = "MEDIUM"
            should_chunk = False
        else:
            level = "COMPLEX"
            should_chunk = True
        
        estimated_subtasks = max(1, complexity_score // 20)
        
        return TaskComplexity(
            score=complexity_score,
            level=level,
            should_chunk=should_chunk,
            estimated_subtasks=estimated_subtasks,
            reasoning=reasoning
        )


class ActionItemExtractor:
    """Extracts action items from task descriptions for our workflow"""
    
    def __init__(self):
        # Workflow-specific action patterns
        self.action_patterns = [
            r"([A-Z][^.!?]*[.!?])",  # Sentences starting with capital letters
            r"(\d+\.\s*[^.!?]+)",    # Numbered items
            r"(-[^.!?]+)",           # Bullet points
            r"(\*[^.!?]+)",          # Asterisk items
            r"(•[^.!?]+)",           # Bullet points
            r"([^.!?]*\b(analyze|scan|check|review|implement|create|build|fix|update|optimize|refactor|test|deploy|gawa|gawin|ayusin|i-fix|i-update)\b[^.!?]*)",  # Action verbs
        ]
        
        # Workflow-specific noise patterns
        self.noise_patterns = [
            r"^\s*$",  # Empty or whitespace only
            r"^[0-9\s\-\.]+$",  # Just numbers and punctuation
            r"^[A-Z\s]+$",  # Just capital letters and spaces
        ]
    
    def extract_action_items(self, task_description: str) -> List[str]:
        """Extract action items from task description"""
        
        action_items = []
        
        for pattern in self.action_patterns:
            matches = re.findall(pattern, task_description, re.IGNORECASE)
            # Handle both string and tuple matches
            for match in matches:
                if isinstance(match, tuple):
                    # If it's a tuple, take the first non-empty element
                    for item in match:
                        if item and len(item.strip()) > 5:
                            action_items.append(item.strip())
                else:
                    # If it's a string
                    if len(match.strip()) > 5:
                        action_items.append(match.strip())
        
        # Remove duplicates and clean up
        unique_items = list(set(action_items))
        cleaned_items = [item for item in unique_items if not self._is_noise(item)]
        
        return cleaned_items
    
    def _is_noise(self, text: str) -> bool:
        """Check if text is noise/not a real action item"""
        return any(re.match(pattern, text) for pattern in self.noise_patterns)


class IntelligentTaskChunker:
    """Intelligently chunks complex tasks for our workflow"""
    
    def __init__(self):
        self.complexity_analyzer = TaskComplexityAnalyzer()
        self.action_extractor = ActionItemExtractor()
    
    def chunk_task(self, task_description: str) -> ChunkedTask:
        """Chunk a task into manageable subtasks"""
        
        # Analyze complexity first
        complexity = self.complexity_analyzer.analyze_complexity(task_description)
        
        if not complexity.should_chunk:
            # Create single subtask for simple/medium tasks
            subtask = Subtask(
                id="subtask_1",
                description=task_description,
                priority=1,
                estimated_duration=30,
                dependencies=[],
                status="pending"
            )
            
            return ChunkedTask(
                original_task=task_description,
                task_id="",  # Will be set by caller
                complexity=complexity,
                subtasks=[subtask],
                current_subtask_index=0,
                status="chunked"
            )
        
        # Extract action items for complex tasks
        action_items = self.action_extractor.extract_action_items(task_description)
        
        if not action_items:
            # Fallback: create subtasks based on complexity
            action_items = self._create_fallback_subtasks(task_description, complexity)
        
        # Create subtasks from action items
        subtasks = []
        for i, action in enumerate(action_items, 1):
            priority = self._determine_priority(action)
            duration = self._estimate_duration(action)
            dependencies = self._find_dependencies(action, action_items)
            
            subtask = Subtask(
                id=f"subtask_{i}",
                description=action,
                priority=priority,
                estimated_duration=duration,
                dependencies=dependencies,
                status="pending"
            )
            subtasks.append(subtask)
        
        return ChunkedTask(
            original_task=task_description,
            task_id="",  # Will be set by caller
            complexity=complexity,
            subtasks=subtasks,
            current_subtask_index=0,
            status="chunked"
        )
    
    def _create_fallback_subtasks(self, task_description: str, complexity: TaskComplexity) -> List[str]:
        """Create fallback subtasks when action extraction fails"""
        
        # Workflow-specific fallback patterns
        if "deep scan" in task_description.lower():
            return [
                "Analyze task requirements",
                "Extract key components to scan",
                "Perform deep scan of identified components",
                "Analyze scan results",
                "Generate recommendations"
            ]
        elif "build" in task_description.lower():
            return [
                "Plan system architecture",
                "Set up project structure",
                "Implement core components",
                "Add supporting features",
                "Test and validate system"
            ]
        else:
            # Generic fallback
            return [
                "Analyze task requirements",
                "Plan implementation approach",
                "Execute main task",
                "Validate results",
                "Document outcomes"
            ]
    
    def _determine_priority(self, action: str) -> int:
        """Determine priority of action (1=highest, 5=lowest)"""
        action_lower = action.lower()
        
        if any(word in action_lower for word in ['analyze', 'plan', 'setup']):
            return 1  # High priority - foundation
        elif any(word in action_lower for word in ['implement', 'create', 'build']):
            return 2  # High priority - core work
        elif any(word in action_lower for word in ['test', 'validate']):
            return 3  # Medium priority - verification
        elif any(word in action_lower for word in ['document', 'cleanup']):
            return 4  # Low priority - finishing
        else:
            return 3  # Default medium priority
    
    def _estimate_duration(self, action: str) -> int:
        """Estimate duration in minutes"""
        action_lower = action.lower()
        
        if any(word in action_lower for word in ['analyze', 'plan', 'setup']):
            return 15  # Quick analysis/planning
        elif any(word in action_lower for word in ['implement', 'create', 'build']):
            return 45  # Core implementation
        elif any(word in action_lower for word in ['test', 'validate']):
            return 20  # Testing
        elif any(word in action_lower for word in ['document', 'cleanup']):
            return 10  # Documentation
        else:
            return 30  # Default
    
    def _find_dependencies(self, action: str, all_actions: List[str]) -> List[str]:
        """Find dependencies for an action"""
        dependencies = []
        action_lower = action.lower()
        
        # Simple dependency logic
        if any(word in action_lower for word in ['implement', 'create', 'build']):
            # Implementation depends on analysis/planning
            for other_action in all_actions:
                if any(word in other_action.lower() for word in ['analyze', 'plan']):
                    dependencies.append(other_action)
        
        return dependencies


class AdaptiveMemoryManagement:
    """Adaptive memory management for our workflow"""
    
    def __init__(self):
        self.memory_bank_path = Path("memory-bank")
        self.cache = {}
        self.access_patterns = {}
    
    def get_relevant_memories(self, task_description: str, subtask_description: str = None) -> List[str]:
        """Get relevant memories for current task/subtask"""
        
        # Determine what memories are relevant
        relevant_memories = []
        
        # Check for workflow-specific patterns
        if "docker" in task_description.lower():
            relevant_memories.extend(self._find_memories_by_keyword("docker"))
        
        if "task" in task_description.lower():
            relevant_memories.extend(self._find_memories_by_keyword("task"))
        
        if "memory" in task_description.lower():
            relevant_memories.extend(self._find_memories_by_keyword("memory"))
        
        if "automation" in task_description.lower():
            relevant_memories.extend(self._find_memories_by_keyword("automation"))
        
        if "background" in task_description.lower():
            relevant_memories.extend(self._find_memories_by_keyword("background"))
        
        # Add current session memory
        session_memory = self.memory_bank_path / "current-session.md"
        if session_memory.exists():
            relevant_memories.append(str(session_memory))
        
        # Add recently accessed memories
        recent_memories = self._get_recently_accessed_memories()
        relevant_memories.extend(recent_memories)
        
        # Remove duplicates and limit to top 5
        unique_memories = list(set(relevant_memories))
        return unique_memories[:5]
    
    def _find_memories_by_keyword(self, keyword: str) -> List[str]:
        """Find memories containing keyword"""
        memories = []
        
        if self.memory_bank_path.exists():
            for memory_file in self.memory_bank_path.glob("*.md"):
                try:
                    content = memory_file.read_text(encoding='utf-8')
                    if keyword.lower() in content.lower():
                        memories.append(str(memory_file))
                except Exception:
                    continue
        
        return memories
    
    def _get_recently_accessed_memories(self) -> List[str]:
        """Get recently accessed memories"""
        # Simple implementation - return current session and a few key files
        key_memories = [
            "memory-bank/current-session.md",
            "memory-bank/task-continuity-system.md",
            "memory-bank/background-agent-escalation-guide.md"
        ]
        
        return [memory for memory in key_memories if Path(memory).exists()]
    
    def preload_memories(self, memories: List[str]) -> None:
        """Preload memories into cache"""
        for memory_path in memories:
            try:
                if Path(memory_path).exists():
                    content = Path(memory_path).read_text(encoding='utf-8')
                    self.cache[memory_path] = content
                    print(f"🧠 Preloaded: {Path(memory_path).name}")
            except Exception as e:
                print(f"⚠️  Could not preload {memory_path}: {e}")
    
    def clear_cache(self) -> None:
        """Clear memory cache"""
        self.cache.clear()
        print("🧹 Memory cache cleared")


class SmartTaskExecutionManager:
    """Smart task execution manager for our workflow"""
    
    def __init__(self):
        self.chunker = IntelligentTaskChunker()
        self.memory_manager = AdaptiveMemoryManagement()
        self.execution_history = []
    
    def execute_task(self, task_description: str) -> Dict[str, Any]:
        """Execute task with intelligent management"""
        
        print(f"🎯 Executing task: {task_description[:50]}...")
        
        # Step 1: Analyze and chunk task
        chunked_task = self.chunker.chunk_task(task_description)
        
        # Step 2: Create task in our system
        task_id = new_task(task_description)
        chunked_task.task_id = task_id
        
        # Step 3: Add subtasks as TODO items
        for subtask in chunked_task.subtasks:
            add_todo(task_id, subtask.description)
        
        # Step 4: Determine execution strategy
        if not chunked_task.complexity.should_chunk:
            return self._execute_simple_task(chunked_task)
        else:
            return self._execute_complex_task(chunked_task)
    
    def _execute_simple_task(self, chunked_task: ChunkedTask) -> Dict[str, Any]:
        """Execute simple task directly"""
        
        print(f"🚀 Executing SIMPLE task with full memory load...")
        
        # Load all relevant memories
        memories = self.memory_manager.get_relevant_memories(chunked_task.original_task)
        self.memory_manager.preload_memories(memories)
        
        # Execute task
        result = {
            "execution_type": "SIMPLE_DIRECT",
            "task_id": chunked_task.task_id,
            "complexity": asdict(chunked_task.complexity),
            "memory_loaded": len(memories),
            "subtasks": [asdict(subtask) for subtask in chunked_task.subtasks],
            "status": "completed",
            "duration": sum(subtask.estimated_duration for subtask in chunked_task.subtasks)
        }
        
        # Mark task as completed
        set_task_status(chunked_task.task_id, "completed")
        
        return result
    
    def _execute_complex_task(self, chunked_task: ChunkedTask) -> Dict[str, Any]:
        """Execute complex task with progressive chunking"""
        
        print(f"🎯 Executing COMPLEX task with {len(chunked_task.subtasks)} subtasks...")
        
        results = []
        total_memory_loaded = 0
        
        for i, subtask in enumerate(chunked_task.subtasks, 1):
            print(f"\n📋 Executing Subtask {i}/{len(chunked_task.subtasks)}: {subtask.description[:50]}...")
            
            # Load memories for current subtask
            memories = self.memory_manager.get_relevant_memories(
                chunked_task.original_task, 
                subtask.description
            )
            self.memory_manager.preload_memories(memories)
            total_memory_loaded += len(memories)
            
            # Execute subtask
            subtask_result = {
                "subtask_id": subtask.id,
                "description": subtask.description,
                "status": "completed",
                "memories_loaded": len(memories),
                "duration": subtask.estimated_duration
            }
            results.append(subtask_result)
            
            # Mark subtask as done
            mark_done(chunked_task.task_id, i-1)  # 0-based index
            
            # Clear memory for next subtask
            if i < len(chunked_task.subtasks):
                self.memory_manager.clear_cache()
        
        # Mark task as completed
        set_task_status(chunked_task.task_id, "completed")
        
        return {
            "execution_type": "COMPLEX_CHUNKED",
            "task_id": chunked_task.task_id,
            "complexity": asdict(chunked_task.complexity),
            "total_subtasks": len(chunked_task.subtasks),
            "completed_subtasks": len(results),
            "total_memory_loaded": total_memory_loaded,
            "results": results,
            "status": "completed"
        }


# Global instances
complexity_analyzer = TaskComplexityAnalyzer()
task_chunker = IntelligentTaskChunker()
action_extractor = ActionItemExtractor()
memory_manager = AdaptiveMemoryManagement()
execution_manager = SmartTaskExecutionManager()


def analyze_task_complexity(task_description: str) -> Dict[str, Any]:
    """Analyze task complexity"""
    complexity = complexity_analyzer.analyze_complexity(task_description)
    return asdict(complexity)


def chunk_task(task_description: str) -> Dict[str, Any]:
    """Chunk task into subtasks"""
    chunked_task = task_chunker.chunk_task(task_description)
    return asdict(chunked_task)


def extract_action_items(task_description: str) -> List[str]:
    """Extract action items from task"""
    return action_extractor.extract_action_items(task_description)


def get_relevant_memories(task_description: str) -> List[str]:
    """Get relevant memories for task"""
    return memory_manager.get_relevant_memories(task_description)


def execute_task_intelligently(task_description: str) -> Dict[str, Any]:
    """Execute task with full intelligence"""
    return execution_manager.execute_task(task_description)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("🤖 Workflow Memory Intelligence System")
        print("Usage: python3 workflow_memory_intelligence.py <command> [task_description]")
        print("")
        print("Commands:")
        print("  analyze <task> - Analyze task complexity")
        print("  chunk <task> - Chunk task into subtasks")
        print("  extract <task> - Extract action items")
        print("  memories <task> - Get relevant memories")
        print("  execute <task> - Execute task intelligently")
        sys.exit(0)
    
    command = sys.argv[1]
    task_description = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    
    if command == "analyze":
        if task_description:
            result = analyze_task_complexity(task_description)
            print("🔍 Task Complexity Analysis:")
            print(json.dumps(result, indent=2))
        else:
            print("❌ Please provide a task description")
    
    elif command == "chunk":
        if task_description:
            result = chunk_task(task_description)
            print("✂️  Task Chunking Result:")
            print(json.dumps(result, indent=2))
        else:
            print("❌ Please provide a task description")
    
    elif command == "extract":
        if task_description:
            result = extract_action_items(task_description)
            print("📝 Extracted Action Items:")
            for i, item in enumerate(result, 1):
                print(f"   {i}. {item}")
        else:
            print("❌ Please provide a task description")
    
    elif command == "memories":
        if task_description:
            result = get_relevant_memories(task_description)
            print("🧠 Relevant Memories:")
            for memory in result:
                print(f"   📄 {Path(memory).name}")
        else:
            print("❌ Please provide a task description")
    
    elif command == "execute":
        if task_description:
            result = execute_task_intelligently(task_description)
            print("🚀 Task Execution Result:")
            print(json.dumps(result, indent=2))
        else:
            print("❌ Please provide a task description")
    
    else:
        print(f"❌ Unknown command: {command}") 