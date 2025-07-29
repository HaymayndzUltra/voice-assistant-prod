#!/usr/bin/env python3
"""
Workflow Memory Intelligence System - FIXED VERSION for Option #10
Enhanced with better error handling and logging for automatic TODO generation
"""

import json
import os
import re
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import asyncio
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our existing memory system
try:
    from todo_manager import (
        new_task,
        add_todo,
        list_open_tasks,
        set_task_status,
        hard_delete_task,
        mark_done,
    )
    logger.info("✅ Successfully imported todo_manager functions")
except ImportError as e:
    logger.error(f"❌ Failed to import todo_manager: {e}")
    raise

try:
    from task_interruption_manager import auto_task_handler, get_interruption_status
    logger.info("✅ Successfully imported task_interruption_manager functions")
except ImportError as e:
    logger.error(f"❌ Failed to import task_interruption_manager: {e}")
    raise

try:
    from task_state_manager import save_task_state, load_task_state
    logger.info("✅ Successfully imported task_state_manager functions")
except ImportError as e:
    logger.error(f"❌ Failed to import task_state_manager: {e}")
    raise

# Try to import telemetry (optional)
try:
    from memory_system.services.telemetry import span
    from memory_system.services.memory_provider import get_provider, MemoryProvider
    TELEMETRY_AVAILABLE = True
    logger.info("✅ Telemetry system available")
except ImportError:
    TELEMETRY_AVAILABLE = False
    logger.warning("⚠️ Telemetry system not available, using fallback")
    
    # Fallback span decorator
    def span(name, description=""):
        def decorator(func):
            def wrapper(*args, **kwargs):
                logger.info(f"🔍 {name}: {description}")
                return func(*args, **kwargs)
            return wrapper
        return decorator


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
    
    @lru_cache(maxsize=256)
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
        
        # Determine level
        if complexity_score <= 0:
            level = "SIMPLE"
            should_chunk = False
            estimated_subtasks = 1
        elif complexity_score <= 30:
            level = "MEDIUM"
            should_chunk = True
            estimated_subtasks = 3
        else:
            level = "COMPLEX"
            should_chunk = True
            estimated_subtasks = 5
        
        # Add reasoning
        if simple_count > 0:
            reasoning.append(f"Contains {simple_count} simple task indicators")
        if medium_count > 0:
            reasoning.append(f"Contains {medium_count} medium complexity indicators")
        if complex_count > 0:
            reasoning.append(f"Contains {complex_count} complex task indicators")
        
        return TaskComplexity(
            score=complexity_score,
            level=level,
            should_chunk=should_chunk,
            estimated_subtasks=estimated_subtasks,
            reasoning=reasoning
        )


class ActionItemExtractor:
    """Extracts action items from task descriptions"""
    
    def __init__(self):
        self.action_patterns = [
            r'(\w+)\s+(?:the\s+)?(\w+)',  # "fix the bug", "update code"
            r'(\w+)\s+(?:a\s+)?(\w+)',    # "create a file", "add feature"
            r'(\w+)\s+(\w+)',             # "analyze code", "test system"
        ]
    
    def extract_action_items(self, task_description: str) -> List[str]:
        """Extract action items from task description"""
        actions = []
        
        # Split by common separators
        parts = re.split(r'[,;]|\band\b|\bor\b', task_description)
        
        for part in parts:
            part = part.strip()
            if len(part) > 5 and not self._is_noise(part):
                actions.append(part)
        
        # If no actions found, create fallback
        if not actions:
            actions = [f"Complete: {task_description}"]
        
        return actions[:5]  # Limit to 5 actions
    
    def _is_noise(self, text: str) -> bool:
        """Check if text is noise"""
        noise_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for']
        return text.lower() in noise_words


class IntelligentTaskChunker:
    """Intelligently chunks tasks into subtasks with command_chunker integration"""
    
    def __init__(self):
        self.complexity_analyzer = TaskComplexityAnalyzer()
        self.action_extractor = ActionItemExtractor()
        self.max_chunk_size = 200
        
        # Try to import auto-detect chunker (priority), fallback to command chunker
        try:
            from auto_detect_chunker import AutoDetectChunker
            self.auto_chunker = AutoDetectChunker(min_chunk_size=200, max_chunk_size=1000)
            self.auto_chunker_available = True
            logger.info("✅ Auto-detect chunker integrated")
        except ImportError:
            self.auto_chunker_available = False
            logger.warning("⚠️ Auto-detect chunker not available")
        
        # Fallback to command chunker
        if not self.auto_chunker_available:
            try:
                from command_chunker import CommandChunker
                self.command_chunker = CommandChunker(max_chunk_size=self.max_chunk_size)
                self.command_chunker_available = True
                logger.info("✅ Command chunker integrated (fallback)")
            except ImportError:
                self.command_chunker_available = False
                logger.warning("⚠️ Command chunker not available, using fallback")
    
    def chunk_task(self, task_description: str) -> ChunkedTask:
        """Chunk task into subtasks with integrated command chunking"""
        logger.info(f"🔍 Chunking task: {task_description[:50]}...")
        
        # Analyze complexity
        complexity = self.complexity_analyzer.analyze_complexity(task_description)
        logger.info(f"📊 Complexity: {complexity.level} (score: {complexity.score})")
        
        # Use integrated chunking strategy
        action_items = self._integrated_chunking(task_description)

        # ------------------------------------------------------------------
        # 🧹 New: Deduplicate & normalise to avoid redundant TODOs
        # ------------------------------------------------------------------
        action_items = self._deduplicate_actions(action_items)
        logger.info(f"📝 Extracted {len(action_items)} unique action items after deduplication")
        
        # Create subtasks
        subtasks = []
        for i, action in enumerate(action_items):
            subtask = Subtask(
                id=f"subtask_{i+1}",
                description=action,
                priority=i+1,
                estimated_duration=self._estimate_duration(action),
                dependencies=[],
                status="pending"
            )
            subtasks.append(subtask)
        
        # Create chunked task
        chunked_task = ChunkedTask(
            original_task=task_description,
            task_id="",  # Will be set by execution manager
            complexity=complexity,
            subtasks=subtasks,
            current_subtask_index=0,
            status="chunked"
        )
        
        logger.info(f"✅ Task chunked into {len(subtasks)} subtasks")
        return chunked_task
    
    def _integrated_chunking(self, task_description: str) -> List[str]:
        """Integrated chunking using auto-detect chunker with fallback strategies"""
        
        # If auto-detect chunker is available, try it first (PRIORITY)
        if self.auto_chunker_available:
            try:
                logger.info("🤖 Using auto-detect chunker for intelligent memory-optimized chunking...")
                
                # Auto-detect optimal chunking
                chunks, analysis = self.auto_chunker.auto_chunk(task_description)
                
                logger.info(f"   Auto-analysis: {analysis['structure_complexity']:.2f} complexity, {analysis['optimal_chunk_size']} chars optimal")
                logger.info(f"   Strategy used: {analysis['strategy_used']}")
                
                # Validate chunks for AI memory management
                if chunks and len(chunks) <= 10:  # Reasonable number of chunks for AI memory
                    logger.info(f"✅ Auto-detect chunker created {len(chunks)} memory-optimized chunks")
                    return chunks
                else:
                    logger.warning("⚠️ Auto-detect chunker produced too many chunks, falling back...")
                    
            except Exception as e:
                logger.warning(f"⚠️ Auto-detect chunker failed: {e}, falling back...")
        
        # If command_chunker is available, try it next
        elif hasattr(self, 'command_chunker_available') and self.command_chunker_available:
            try:
                logger.info("🔧 Using command_chunker for intelligent chunking...")
                
                # Analyze task size
                analysis = self.command_chunker.analyze_command_size(task_description)
                logger.info(f"   Size analysis: {analysis}")
                
                # Use auto strategy for best results
                chunks = self.command_chunker.chunk_command(task_description, strategy="auto")
                
                # Validate chunks
                if chunks and len(chunks) <= 10:  # Reasonable number of chunks
                    logger.info(f"✅ Command chunker created {len(chunks)} chunks")
                    return chunks
                else:
                    logger.warning("⚠️ Command chunker produced too many chunks, falling back...")
                    
            except Exception as e:
                logger.warning(f"⚠️ Command chunker failed: {e}, falling back...")
        
        # Final fallback to original action item extraction
        logger.info("🔄 Using fallback action item extraction...")
        return self.action_extractor.extract_action_items(task_description)
    
    def _estimate_duration(self, action: str) -> int:
        """Estimate duration in minutes"""
        action_lower = action.lower()
        
        if any(word in action_lower for word in ['quick', 'simple', 'minor', 'fix']):
            return 5
        elif any(word in action_lower for word in ['analyze', 'review', 'check']):
            return 15
        elif any(word in action_lower for word in ['create', 'build', 'implement']):
            return 30
        else:
            return 10

    # ------------------------------------------------------------------
    # 🔬 Advanced post-processing helpers (new)
    # ------------------------------------------------------------------

    def _deduplicate_actions(self, actions: List[str]) -> List[str]:
        """Remove near-duplicate or semantically identical action strings.

        Uses simple textual normalisation + fuzzy ratio (difflib) to identify
        overlaps. This lightweight approach avoids heavy NLP dependencies but
        is sufficient for obvious redundancy such as "-audit code" vs
        "audit the code"."""
        from difflib import SequenceMatcher

        def norm(txt: str) -> str:
            txt = txt.lower().strip(" -•*:\t\n")  # strip bullet markers & punc
            txt = re.sub(r"[^a-z0-9\s]", "", txt)  # keep alphanum + space
            txt = re.sub(r"\s+", " ", txt)
            return txt.strip()

        unique: List[str] = []
        seen_norms: List[str] = []

        for action in actions:
            n = norm(action)
            if not n:
                continue
            # Check similarity against already kept items
            is_dup = False
            for prev in seen_norms:
                if SequenceMatcher(None, n, prev).ratio() >= 0.8:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(action.strip())
                seen_norms.append(n)

        return unique


class SmartTaskExecutionManager:
    """Smart task execution manager with enhanced error handling"""
    
    def __init__(self):
        self.chunker = IntelligentTaskChunker()
        self.execution_history = []
        logger.info("🚀 SmartTaskExecutionManager initialized")
    
    def execute_task(self, task_description: str) -> Dict[str, Any]:
        """Execute task with intelligent management and enhanced error handling"""
        
        logger.info(f"🎯 Starting intelligent execution: {task_description[:50]}...")
        
        try:
            # Step 1: Analyze and chunk task
            logger.info("📋 Step 1: Analyzing and chunking task...")
            chunked_task = self.chunker.chunk_task(task_description)
            
            # Step 2: Create task in our system (with timeout protection)
            logger.info("📝 Step 2: Creating task in todo system...")
            try:
                # Check if task already exists
                from todo_manager import list_open_tasks
                existing_tasks = list_open_tasks()
                
                # Look for existing task with same description
                existing_task = None
                for task in existing_tasks:
                    if task['description'] == task_description:
                        existing_task = task
                        break
                
                if existing_task:
                    logger.info(f"✅ Found existing task: {existing_task['id']}")
                    task_id = existing_task['id']
                    chunked_task.task_id = task_id
                else:
                    task_id = new_task(task_description)
                    logger.info(f"✅ Task created with ID: {task_id}")
                    chunked_task.task_id = task_id
                    
            except Exception as e:
                logger.error(f"❌ Failed to create/find task: {e}")
                return {
                    "execution_type": "ERROR",
                    "error": f"Task creation failed: {e}",
                    "status": "failed",
                    "task_description": task_description
                }
            
            # Step 3: Add subtasks as TODO items (with timeout protection)
            logger.info(f"📋 Step 3: Adding {len(chunked_task.subtasks)} TODO items...")
            todos_added = 0
            
            # Check existing TODOs to avoid duplicates
            existing_todos = []
            if existing_task:
                existing_todos = [todo['text'] for todo in existing_task.get('todos', [])]
                logger.info(f"📋 Found {len(existing_todos)} existing TODOs")
            
            for i, subtask in enumerate(chunked_task.subtasks):
                try:
                    # Skip if TODO already exists
                    if subtask.description in existing_todos:
                        logger.info(f"⏭️  TODO {i+1} already exists: {subtask.description[:30]}...")
                        todos_added += 1
                        continue
                    
                    add_todo(task_id, subtask.description)
                    todos_added += 1
                    logger.info(f"✅ Added TODO {i+1}: {subtask.description[:30]}...")
                except Exception as e:
                    logger.error(f"❌ Failed to add TODO {i+1}: {e}")
            
            logger.info(f"📊 Successfully processed {todos_added}/{len(chunked_task.subtasks)} TODOs")
            
            # Step 4: Determine execution strategy
            if not chunked_task.complexity.should_chunk:
                logger.info("🚀 Executing as SIMPLE task...")
                return self._execute_simple_task(chunked_task)
            else:
                logger.info("🎯 Executing as COMPLEX task...")
                return self._execute_complex_task(chunked_task)
                
        except Exception as e:
            logger.error(f"💥 Error during task execution: {e}")
            return {
                "execution_type": "ERROR",
                "error": str(e),
                "status": "failed",
                "task_description": task_description
            }
    
    def _execute_simple_task(self, chunked_task: ChunkedTask) -> Dict[str, Any]:
        """Execute simple task directly"""
        
        logger.info("🚀 Executing SIMPLE task...")
        
        try:
            # Keep task as in_progress for user to complete
            set_task_status(chunked_task.task_id, "in_progress")
            logger.info("✅ Task marked as in_progress (ready for user to complete)")
            
            result = {
                "execution_type": "SIMPLE_DIRECT",
                "task_id": chunked_task.task_id,
                "complexity": asdict(chunked_task.complexity),
                "subtasks": [asdict(subtask) for subtask in chunked_task.subtasks],
                "status": "in_progress",
                "todos_added": len(chunked_task.subtasks),
                "duration": sum(subtask.estimated_duration for subtask in chunked_task.subtasks),
                "message": "Task created with TODOs. Please complete the actual work manually."
            }
            
            logger.info("✅ Simple task setup completed - ready for user execution")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in simple task execution: {e}")
            return {
                "execution_type": "SIMPLE_DIRECT",
                "task_id": chunked_task.task_id,
                "status": "failed",
                "error": str(e)
            }
    
    def _execute_complex_task(self, chunked_task: ChunkedTask) -> Dict[str, Any]:
        """Execute complex task with progressive chunking"""
        
        logger.info(f"🎯 Executing COMPLEX task with {len(chunked_task.subtasks)} subtasks...")
        
        try:
            results = []
            
            for i, subtask in enumerate(chunked_task.subtasks, 1):
                logger.info(f"📋 Executing Subtask {i}/{len(chunked_task.subtasks)}: {subtask.description[:30]}...")
                
                # Execute subtask
                subtask_result = {
                    "subtask_id": subtask.id,
                    "description": subtask.description,
                    "status": "completed",
                    "duration": subtask.estimated_duration
                }
                results.append(subtask_result)
                
                # Don't mark subtask as done automatically - let user do the work
                logger.info(f"📋 Subtask {i} ready for user to complete: {subtask.description[:30]}...")
            
            # Keep task as in_progress for user to complete
            set_task_status(chunked_task.task_id, "in_progress")
            logger.info("✅ Complex task setup completed - ready for user execution")
            
            return {
                "execution_type": "COMPLEX_CHUNKED",
                "task_id": chunked_task.task_id,
                "complexity": asdict(chunked_task.complexity),
                "subtasks": results,
                "status": "in_progress",
                "todos_added": len(chunked_task.subtasks),
                "total_duration": sum(subtask.estimated_duration for subtask in chunked_task.subtasks),
                "message": "Task created with TODOs. Please complete the actual work manually."
            }
            
        except Exception as e:
            logger.error(f"❌ Error in complex task execution: {e}")
            return {
                "execution_type": "COMPLEX_CHUNKED",
                "task_id": chunked_task.task_id,
                "status": "failed",
                "error": str(e)
            }


# Global execution manager instance
execution_manager = SmartTaskExecutionManager()


def execute_task_intelligently(task_description: str) -> Dict[str, Any]:
    """Execute task with full intelligence and enhanced error handling"""
    logger.info(f"🧠 Starting intelligent task execution: {task_description[:50]}...")
    
    try:
        result = execution_manager.execute_task(task_description)
        logger.info("✅ Intelligent task execution completed successfully")
        return result
    except Exception as e:
        logger.error(f"💥 Error in intelligent task execution: {e}")
        return {
            "execution_type": "ERROR",
            "error": str(e),
            "status": "failed",
            "task_description": task_description
        }


if __name__ == "__main__":
    # Test the fixed version
    test_task = "Create a test task with automatic TODO generation"
    print(f"🧪 Testing fixed intelligent execution: {test_task}")
    
    result = execute_task_intelligently(test_task)
    print("📊 Result:")
    print(json.dumps(result, indent=2)) 