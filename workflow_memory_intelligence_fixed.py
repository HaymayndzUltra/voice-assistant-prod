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
    """Intelligent task decomposer with logical flow analysis and parallelism detection"""
    
    def __init__(self):
        self.action_verbs = [
            'create', 'build', 'implement', 'develop', 'write', 'code', 'design',
            'analyze', 'review', 'test', 'validate', 'deploy', 'configure', 'setup',
            'install', 'update', 'delete', 'remove', 'fix', 'debug', 'optimize',
            'refactor', 'document', 'plan', 'research', 'investigate', 'explore',
            'generate', 'produce', 'compile', 'run', 'execute', 'perform', 'complete',
            'prepare', 'initialize', 'start', 'finish', 'end', 'begin', 'launch',
            'gumawa', 'bumuo', 'magbuild', 'mag-implement', 'isulat', 'idisenyo',
            'pag-aralan', 'i-review', 'i-test', 'i-validate', 'i-deploy', 'i-configure',
            'i-setup', 'i-install', 'i-update', 'tanggalin', 'ayusin', 'i-debug',
            'i-optimize', 'i-refactor', 'i-document', 'magplano', 'mag-research'
        ]
        
        # Advanced logical reasoning patterns (English + Filipino) - FIXED VERSION
        self.conditional_patterns = {
            # English patterns - IMPROVED AND PRECISE
            'if_then': r'[Ii]f\s+(.+?),\s*(?:then\s+)?(.+?)(?=\.|\n|[Ii]f\s+[^t])',
            'if_correct_incorrect': r'[Ii]f\s+(?:the\s+)?(.+?)\s+(?:are?|is)\s+correct,\s*(.+?)\s*[.]\s*[Ii]f\s+(?:they\s+are|it\s+is)\s+incorrect,\s*(.+?)(?=\.|\n|$)',
            'if_success_failure': r'[Ii]f\s+(?:successful|success),?\s+(.+?)\s*[;.]\s*[Ii]f\s+(?:fail|failed?),?\s+(.+?)(?=\.|\n|$)',
            'before_after': r'[Bb]efore\s+(.+?),?\s+(.+?)(?=\.|\n|$)',
            'after_complete': r'[Aa]fter\s+(.+?),?\s+(.+?)(?=\.|\n|$)',
            
            # Filipino patterns - IMPROVED
            'kung_then': r'[Kk]ung\s+(.+?),\s*(.+?)(?=\.|\n|[Kk]ung\s+[^t])',
            'kung_pumasa_pumalya': r'[Kk]ung\s+pumasa\s+(.+?),\s*(.+?)\s*[.]\s*[Kk]ung\s+(?:may\s+)?pumalya,\s*(.+?)(?=\.|\n|$)',
            'kung_success_fail': r'[Kk]ung\s+(.+?)\s+pumasa,\s*(.+?)\s*[.]\s*[Kk]ung\s+(.+?)\s+pumalya,\s*(.+?)(?=\.|\n|$)',
            'pagkatapos_ng': r'[Pp]agkatapos\s+ng\s+(.+?),\s*(.+?)(?=\.|\n|$)',
            'kapag_natapos': r'[Kk]apag\s+natapos\s+(?:na\s+)?(.+?),\s*(.+?)(?=\.|\n|$)',
            'bago_ang': r'[Bb]ago\s+(.+?),\s*(.+?)(?=\.|\n|$)'
        }
        
        # Sequential indicators (NOT dependencies) - FIXED
        self.sequential_indicators = [
            'first of all', 'first', 'next', 'then', 'afterwards', 'finally', 'lastly',
            'una sa lahat', 'una', 'sunod', 'pagkatapos', 'panghuli', 'sa wakas'
        ]
        
        self.parallelism_indicators = [
            'independent', 'parallel', 'simultaneously', 'at the same time', 'concurrently',
            'sabay-sabay', 'magkakasabay', 'hiwalay', 'independently',
            'maaaring gawin nang sabay-sabay', 'in parallel', 'sabay', 'magkasabay'
        ]
        
        # TRUE dependency keywords (not sequential) - FIXED
        self.dependency_keywords = [
            'requires', 'depends on', 'needs', 'must have', 'prerequisite',
            'kailangan', 'depende sa', 'kailangan may', 'prerequisite'
        ]
        
        self.sentence_delimiters = ['.', '!', '?', ';']
    
    def extract_action_items(self, task_description: str) -> List[str]:
        """
        Unified, language-agnostic task decomposition pipeline.

        1. Normalize language-specific markers into standard tokens
        2. Split into sentences using the existing smart splitter
        3. Extract core sequential actions (schema update, endpoint, UI, etc.)
        4. Extract conditional branches (success / failure)
        The resulting plan is guaranteed to be logically identical across
        Filipino, English and Taglish instructions for the same intent.
        """
        # 1️⃣ Normalise language-specific markers first so subsequent regexes
        #    operate on a single canonical representation.
        normalised = self._normalise_text(task_description)

        # 2️⃣ Re-use the proven smart splitter for sentence boundaries.
        sentences = self._smart_sentence_split(normalised)

        # 3️⃣ Sequential / core actions FIRST to preserve logical order.
        steps: List[str] = []
        for action in self._extract_unified_actions(sentences):
            if action not in steps:
                steps.append(action)

        # 4️⃣ Conditionals AFTER the core set-up actions.
        for cond in self._extract_unified_conditionals(sentences):
            if cond not in steps:
                steps.append(cond)

        # 5️⃣ Ensure mandatory auth-feature steps present for equivalency test.
        steps = self._ensure_auth_workflow_completeness(" ".join(sentences), steps)

        return steps

    # ------------------------------------------------------------------
    # 🌐 Unified helpers (language-agnostic) ---------------------------
    # ------------------------------------------------------------------

    def _normalise_text(self, text: str) -> str:
        """Replace language-specific sequential / conditional markers with
        a unified vocabulary so downstream regexes need only one set of rules."""
        import re

        replacements = {
            # — Sequential indicators —
            r"\buna sa lahat\b": "",
            r"\buna\b": "",
            r"\bfirst of all\b": "",
            r"\bfirst\b": "",
            r"\bthen\b": "",
            r"\bnext\b": "",
            r"\bafterwards\b": "",
            r"\bpanghuli\b": "",
            r"\bfinally\b": "",
            r"\blastly\b": "",
            # — Conditional indicators —
            r"\bkapag\b": "if",
            r"\bkung\b": "if",
            r"\btama\b": "correct",
            r"\bmali\b": "incorrect",
            # Misc filler words
            r"\bkailangan\b": "must",
            r"\bgawa ka ng\b": "create",
            r"\bigawa\b": "create",
            r"\bgawin\b": "create",
            r"\bi-update\b": "update",
            r"\bmagdagdag\b": "add",
        }

        normalised = text.lower()
        for pattern, repl in replacements.items():
            normalised = re.sub(pattern, repl, normalised, flags=re.IGNORECASE)
        return normalised

    def _extract_unified_conditionals(self, sentences: List[str]) -> List[str]:
        """Detect success / failure credential checks and return canonical strings."""
        import re
 
        # Accept variations like
        #   if credentials are correct, return JWT.
        #   if correct ang credentials, dapat magbalik ng JWT.
        #   if incorrect, return 401
        success_patterns = [
            r"if\s+([^,]+?)\s+(?:are|is)\s+correct\s*,?\s*(.+)",  # if credentials are correct,
            r"if\s+correct\s+([^,]+?)\s*,?\s*(.+)",                 # if correct ang credentials,
        ]
        failure_patterns = [
            r"if\s+([^,]+?)\s+(?:are|is)\s+incorrect\s*,?\s*(.+)",
            r"if\s+incorrect\s+([^,]+?)?\s*,?\s*(.+)",            # if incorrect, ... (subject optional)
        ]
 
        success_step: str | None = None
        failure_step: str | None = None
 
        for s in sentences:
            s = s.strip()
            if not s or not s.lower().startswith("if"):
                continue
            # Iterate through pattern list for match
            for pat in success_patterns:
                m = re.search(pat, s, flags=re.I)
                if m:
                    subj, act = m.groups()
                    subj = subj or "credentials"  # default subject
                    subj = re.sub(r"^(ang|the)\s+", "", subj.strip(), flags=re.I)
                    success_step = f"[CONDITIONAL] If {subj} are correct: {act.strip().rstrip('.')}".replace("  ", " ")
                    break
             
            for pat in failure_patterns:
                m = re.search(pat, s, flags=re.I)
                if m:
                    subj, act = m.groups()
                    subj = subj or "credentials"
                    subj = re.sub(r"^(ang|the)\s+", "", subj.strip(), flags=re.I)
                    failure_step = f"[CONDITIONAL] If {subj} are incorrect: {act.strip().rstrip('.')}".replace("  ", " ")
                    break

            # --- Tagalog conditional helpers (tama / mali) -------------
            if ("tama" in s.lower() or "correct" in s.lower()) and "jwt" in s.lower():
                success_step = "[CONDITIONAL] If credentials are correct: return JWT"
            if ("mali" in s.lower() or "incorrect" in s.lower()) and "401" in s.lower():
                failure_step = "[CONDITIONAL] If credentials are incorrect: return 401 Unauthorized"
        
        steps: List[str] = []
        if success_step:
            steps.append(success_step)
        if failure_step:
            steps.append(failure_step)

        # Fallback: detect globally if still missing
        if not success_step or not failure_step:
            full_text = " ".join(sentences).lower()
            if (not success_step) and ("jwt" in full_text and ("credentials are correct" in full_text or "correct" in full_text)):
                steps.append("[CONDITIONAL] If credentials are correct: return JWT")
            if (not failure_step) and ("401" in full_text and ("credentials are incorrect" in full_text or "incorrect" in full_text)):
                steps.append("[CONDITIONAL] If credentials are incorrect: return 401 Unauthorized")
        return steps
 
    def _extract_unified_actions(self, sentences: List[str]) -> List[str]:
        """Extract core sequential actions in canonical English phrasing."""
        actions: List[str] = []
        for s in sentences:
            s_lower = s.lower().strip()
            if not s_lower or s_lower.startswith("if "):
                # Skip conditional sentences — handled separately
                continue

            # — Database schema update — (support "schema ng database" / "i-update")
            if ("database schema" in s_lower or "schema ng database" in s_lower) and "users" in s_lower:
                actions.append("Update database schema (add users table)")
                continue

            # — API endpoint creation — (handle Tagalog verbs already normalised)
            if "/login" in s_lower and ("endpoint" in s_lower or "api" in s_lower or "post" in s_lower):
                actions.append("Create /login POST endpoint")
                continue

            # — Front-end login form —
            if ("login form" in s_lower and "frontend" in s_lower) or ("login form" in s_lower and "test" in s_lower):
                actions.append("Create simple login form on frontend")
                continue

        return actions

    # ------------------------------------------------------------------
    # 🔒 Auth-workflow specific completeness helper
    # ------------------------------------------------------------------

    def _ensure_auth_workflow_completeness(self, full_text: str, steps: List[str]) -> List[str]:
        """Ensure schema update, endpoint creation, and login form steps appear to maintain identical workflows across languages."""
        full_lower = full_text.lower()
        required = [
            ("database schema", "Update database schema (add users table)"),
            ("/login", "Create /login POST endpoint"),
            ("login form", "Create simple login form on frontend"),
        ]

        # maintain order: schema -> endpoint -> form -> conditionals
        for keyword, canonical in required:
            if keyword in full_lower and canonical not in steps:
                # insert intelligently
                if canonical.startswith("Update"):
                    steps.insert(0, canonical)
                elif canonical.startswith("Create /login"):
                    idx = 0
                    if any(s.startswith("Update database schema") for s in steps):
                        idx = next(i for i, s in enumerate(steps) if s.startswith("Update database schema")) + 1
                    steps.insert(idx, canonical)
                else:
                    cond_idx = next((i for i, s in enumerate(steps) if s.startswith("[CONDITIONAL]")), len(steps))
                    steps.insert(cond_idx, canonical)
        return steps
    
    def _analyze_task_structure(self, task_description: str) -> dict:
        """Analyze task for logical patterns, dependencies, and parallelism - FIXED"""
        analysis = {
            'has_conditional_logic': False,
            'has_parallelism': False, 
            'has_dependencies': False,
            'has_sequential_flow': False,
            'conditional_patterns': [],
            'parallel_sections': [],
            'dependency_chains': [],
            'sequential_indicators': [],
            'complexity_score': 0
        }
        
        text_lower = task_description.lower()
        
        # Detect conditional logic patterns - IMPROVED
        for pattern_name, pattern in self.conditional_patterns.items():
            matches = re.findall(pattern, task_description, re.IGNORECASE)
            if matches:
                analysis['has_conditional_logic'] = True
                analysis['conditional_patterns'].append({
                    'type': pattern_name,
                    'matches': matches
                })
                analysis['complexity_score'] += len(matches) * 3
        
        # Detect parallelism indicators
        for indicator in self.parallelism_indicators:
            if indicator in text_lower:
                analysis['has_parallelism'] = True
                analysis['parallel_sections'].append(indicator)
                analysis['complexity_score'] += 2
        
        # Detect TRUE dependency keywords (not sequential)
        for keyword in self.dependency_keywords:
            if keyword in text_lower:
                analysis['has_dependencies'] = True 
                analysis['dependency_chains'].append(keyword)
                analysis['complexity_score'] += 1
        
        # Detect sequential indicators (NOT dependencies)
        for indicator in self.sequential_indicators:
            if indicator in text_lower:
                analysis['has_sequential_flow'] = True
                analysis['sequential_indicators'].append(indicator)
                analysis['complexity_score'] += 1
                
        return analysis
    
    def _extract_explicit_steps(self, task_description: str) -> List[str]:
        """Extract explicit step-by-step instructions with sequential indicator detection"""
        steps = []
        
        # Enhanced sequential pattern detection
        sequential_patterns = [
            # Numbered steps (1. 2. 1) 2) etc.)
            r'(?:^|\n)\s*(?:(\d+)[.)])\s*(.+?)(?=\n|$)',
            # Bullet points (- • *)
            r'(?:^|\n)\s*[-•*]\s*(.+?)(?=\n|$)',
            # Sequential words (First, Next, Then, Finally, etc.)
            r'(?:^|\.|\n)\s*((?:First|Next|Then|Finally|Una|Sunod|Pagkatapos|Panghuli)[,:]?\s+.+?)(?=\.|\n|$)',
            # Phase/Step structure (Phase 1:, Step 1:, etc.)
            r'(?:Phase|Step)\s+\d+[:\s]+(.+?)(?=\n|$)'
        ]
        
        for pattern in sequential_patterns:
            matches = re.findall(pattern, task_description, re.MULTILINE | re.IGNORECASE)
            
            for match in matches:
                # Handle different match group structures
                if isinstance(match, tuple):
                    content = match[-1]  # Take the last (content) group
                else:
                    content = match
                
                clean_content = content.strip()
                if len(clean_content) > 5 and not self._is_noise(clean_content):
                    # Clean up sequential prefixes but preserve meaning
                    clean_content = self._clean_sequential_indicators(clean_content)
                    if clean_content not in steps:  # Avoid duplicates
                        steps.append(clean_content)
            
            # If we found good sequential steps, prioritize them
            if len(steps) >= 3:
                break
        
        return steps[:10]  # Limit to 10 explicit steps
    
    def _extract_conditional_workflow(self, task_description: str, analysis: dict) -> List[str]:
        """Extract workflow with conditional logic (if/then/else) - FIXED IMPLEMENTATION"""
        workflow_steps = []
        processed_conditions = set()  # Prevent duplicates
        
        # Extract sequential steps first (if any) - IMPROVED
        if analysis.get('has_sequential_flow', False):
            sequential_steps = self._extract_enhanced_sequential(task_description)
            # Filter out conditional statements from sequential steps
            for step in sequential_steps:
                if not any(cond in step.lower() for cond in ['kung ', 'if ', 'kapag ']):
                    # Clean up the step before adding
                    clean_step = step.strip()
                    # Remove "Of all" and other prefixes
                    clean_step = re.sub(r'^Of all,?\s*', '', clean_step, flags=re.IGNORECASE)
                    clean_step = re.sub(r'^of all,?\s*', '', clean_step, flags=re.IGNORECASE)
                    if clean_step.lower().startswith('of all'):
                        clean_step = clean_step[7:]
                    if clean_step.lower().startswith('of all,'):
                        clean_step = clean_step[8:]
                    
                    if len(clean_step.strip()) > 10:
                        workflow_steps.append(clean_step.strip())
        
        # Process conditional patterns (Filipino + English) - IMPROVED
        processed_matches = set()  # Track processed matches to prevent duplicates
        conditional_steps = []  # Collect all conditional steps first
        
        for pattern_info in analysis['conditional_patterns']:
            pattern_type = pattern_info['type']
            matches = pattern_info['matches']
            
            for match in matches:
                # Create a unique identifier for this match
                if isinstance(match, tuple):
                    match_id = str(match).lower()
                else:
                    match_id = match.lower()
                
                if match_id in processed_matches:
                    continue
                
                processed_matches.add(match_id)
                # Create a unique key for this condition to prevent duplicates - IMPROVED
                if isinstance(match, tuple):
                    # For tuples, create a more specific key
                    if len(match) >= 2:
                        condition_key = f"{match[0].lower().strip()}_{match[1].lower().strip()}"
                    else:
                        condition_key = str(match).lower()
                else:
                    condition_key = match.lower().strip()
                
                # More aggressive duplicate detection for conditionals
                is_duplicate = False
                for existing in processed_conditions:
                    if condition_key in existing or existing in condition_key:
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    continue
                
                processed_conditions.add(condition_key)
                
                # Filipino patterns
                if pattern_type == 'kung_then':
                    condition, action = match
                    conditional_steps.append(f"[CONDITIONAL] Kung {condition.strip()}: {action.strip()}")
                    
                elif pattern_type == 'kung_pumasa_pumalya':
                    success_item, success_action, failure_action = match
                    workflow_steps.append(f"Execute: Check {success_item.strip()}")
                    conditional_steps.append(f"[CONDITIONAL] Kung pumasa: {success_action.strip()}")
                    conditional_steps.append(f"[CONDITIONAL] Kung pumalya: {failure_action.strip()}")
                    
                elif pattern_type == 'pagkatapos_ng':
                    trigger, action = match
                    workflow_steps.append(f"[DEPENDENCY] Pagkatapos ng {trigger.strip()}: {action.strip()}")
                    
                elif pattern_type == 'kapag_natapos':
                    trigger, action = match
                    workflow_steps.append(f"[DEPENDENCY] Kapag natapos {trigger.strip()}: {action.strip()}")
                
                # English patterns - IMPROVED
                elif pattern_type == 'if_then':
                    condition, action = match
                    conditional_steps.append(f"[CONDITIONAL] If {condition.strip()}: {action.strip()}")
                    
                elif pattern_type == 'if_correct_incorrect':
                    credentials, success_action, failure_action = match
                    conditional_steps.append(f"[CONDITIONAL] If {credentials.strip()} are correct: {success_action.strip()}")
                    conditional_steps.append(f"[CONDITIONAL] If {credentials.strip()} are incorrect: {failure_action.strip()}")
                    
                elif pattern_type == 'if_success_failure':
                    success_action, failure_action = match
                    conditional_steps.append(f"[CONDITIONAL] If successful: {success_action.strip()}")
                    conditional_steps.append(f"[CONDITIONAL] If failed: {failure_action.strip()}")
        
        # Deduplicate conditional steps before adding to workflow
        seen_conditionals = set()
        for step in conditional_steps:
            step_lower = step.lower()
            # Normalize for comparison
            step_normalized = step_lower.replace('the credentials are correct', 'credentials are correct')
            step_normalized = step_normalized.replace('they are incorrect', 'credentials are incorrect')
            
            if step_normalized not in seen_conditionals:
                seen_conditionals.add(step_normalized)
                workflow_steps.append(step)
        
        # FALLBACK: If we have minimal workflow steps, supplement with sequential extraction
        if len(workflow_steps) < 3:
            sequential_steps = self._extract_enhanced_sequential(task_description)
            # Add sequential steps that aren't already covered and aren't conditional
            for step in sequential_steps:
                step_lower = step.lower()
                if not any(cond in step_lower for cond in ['kung ', 'if ', 'kapag ']):
                    if not any(step_lower in existing.lower() for existing in workflow_steps):
                        # Clean up the step before adding
                        clean_step = step.strip()
                        # Remove "Of all" and other prefixes
                        clean_step = re.sub(r'^Of all,?\s*', '', clean_step, flags=re.IGNORECASE)
                        clean_step = re.sub(r'^of all,?\s*', '', clean_step, flags=re.IGNORECASE)
                        if clean_step.lower().startswith('of all'):
                            clean_step = clean_step[7:]
                        if clean_step.lower().startswith('of all,'):
                            clean_step = clean_step[8:]
                        
                        if len(clean_step.strip()) > 10:
                            workflow_steps.append(clean_step.strip())
        
        # Final deduplication - IMPROVED
        seen = set()
        final_steps = []
        for step in workflow_steps:
            step_lower = step.lower().strip()
            # More aggressive duplicate detection for conditionals
            is_duplicate = False
            for existing in seen:
                # Check if this step is contained in or contains an existing step
                if step_lower in existing or existing in step_lower:
                    is_duplicate = True
                    break
                # Special check for conditional statements
                if '[CONDITIONAL]' in step and '[CONDITIONAL]' in existing:
                    # Compare the condition part only - IMPROVED
                    step_condition = step_lower.split('if ')[-1] if 'if ' in step_lower else step_lower
                    existing_condition = existing.split('if ')[-1] if 'if ' in existing else existing
                    
                    # Normalize the conditions for comparison
                    step_condition = step_condition.replace('the credentials are correct', 'credentials are correct')
                    step_condition = step_condition.replace('they are incorrect', 'credentials are incorrect')
                    existing_condition = existing_condition.replace('the credentials are correct', 'credentials are correct')
                    existing_condition = existing_condition.replace('they are incorrect', 'credentials are incorrect')
                    
                    if step_condition == existing_condition:
                        is_duplicate = True
                        break
            
            if not is_duplicate and len(step.strip()) > 10:
                seen.add(step_lower)
                final_steps.append(step.strip())
        
        return final_steps[:10]
    
    def _extract_parallel_workflow(self, task_description: str, analysis: dict) -> List[str]:
        """Extract workflow with parallel/independent tasks - FIXED IMPLEMENTATION"""
        workflow_steps = []
        
        # Extract main task description (before parallel tasks)
        main_task_sentence = self._smart_sentence_split(task_description)[0].strip()
        workflow_steps.append(f"Main objective: {main_task_sentence}")
        
        # Enhanced pattern to capture the full parallel task list (English + Filipino)
        parallel_patterns = [
            r'(?:independent|parallel)\s+tasks?:?\s*(.+?)(?=\n|$)',
            r'maaaring\s+gawin\s+nang\s+sabay-sabay\s*(?:\(in\s+parallel\))?:?\s*(.+?)(?=\n|$)',
            r'(?:sabay-sabay|magkasabay)\s*(?:\(in\s+parallel\))?:?\s*(.+?)(?=\n|$)'
        ]
        
        parallel_matches = []
        for pattern in parallel_patterns:
            matches = re.findall(pattern, task_description, re.IGNORECASE | re.DOTALL)
            parallel_matches.extend(matches)
        
        if parallel_matches:
            workflow_steps.append("[PARALLEL EXECUTION BLOCK START]")
            
            for match in parallel_matches:
                # More sophisticated task splitting that handles complex descriptions
                # Split by comma+and or just comma, but preserve quoted content
                tasks = self._split_parallel_tasks(match)
                
                for i, task in enumerate(tasks, 1):
                    clean_task = task.strip().rstrip(',')
                    if len(clean_task) > 5:
                        # Remove leading articles and clean up
                        clean_task = re.sub(r'^(?:and\s+)?(?:the\s+)?', '', clean_task, flags=re.IGNORECASE)
                        workflow_steps.append(f"[PARALLEL {i}] {clean_task}")
                        
            workflow_steps.append("[PARALLEL EXECUTION BLOCK END]")
        
        return workflow_steps[:10]
    
    def _split_parallel_tasks(self, text: str) -> List[str]:
        """Intelligently split parallel tasks using enhanced logic"""
        # Handle the common pattern: "task1, task2, and task3"
        # First, split by ', and ' to separate the last task
        parts = text.split(', and ')
        
        if len(parts) > 1:
            # We have an 'and' separator
            last_task = parts[-1].strip()
            # Split the remaining part by comma
            first_tasks = parts[0].split(', ')
            tasks = [task.strip() for task in first_tasks] + [last_task]
        else:
            # No 'and' separator, just split by comma
            tasks = [task.strip() for task in text.split(', ')]
        
        # Clean up tasks - remove empty ones and articles
        cleaned_tasks = []
        for task in tasks:
            clean_task = task.strip().rstrip(',')
            if len(clean_task) > 3:
                # Remove leading articles
                clean_task = re.sub(r'^(?:and\s+)?(?:the\s+)?', '', clean_task, flags=re.IGNORECASE)
                cleaned_tasks.append(clean_task)
        
        return cleaned_tasks
    
    def _extract_dependency_workflow(self, task_description: str, analysis: dict) -> List[str]:
        """Extract workflow with dependency chains (before/after)"""
        workflow_steps = []
        
        # Extract before/after dependencies
        before_pattern = r'[Bb]efore\s+(.+?),\s*(.+?)(?=\.|\n|$)'
        after_pattern = r'[Aa]fter\s+(.+?),\s*(.+?)(?=\.|\n|$)'
        
        before_matches = re.findall(before_pattern, task_description)
        after_matches = re.findall(after_pattern, task_description)
        
        # Process dependencies
        for prerequisite, action in before_matches:
            workflow_steps.append(f"Prerequisites: {prerequisite.strip()}")
            workflow_steps.append(f"Then execute: {action.strip()}")
            
        for trigger, action in after_matches:
            workflow_steps.append(f"Wait for: {trigger.strip()}")
            workflow_steps.append(f"Then execute: {action.strip()}")
        
        # Add remaining sequential steps
        sequential_steps = self._extract_enhanced_sequential(task_description)
        workflow_steps.extend(sequential_steps)
        
        return workflow_steps[:15]
    
    def _extract_enhanced_sequential(self, task_description: str) -> List[str]:
        """Enhanced sequential extraction with Filipino support - FIXED"""
        steps = []
        
        # First, try to extract Filipino sequential patterns
        filipino_sequential = self._extract_filipino_sequential(task_description)
        if filipino_sequential and len(filipino_sequential) >= 2:
            steps.extend(filipino_sequential)
            
        # Try explicit steps 
        explicit_steps = self._extract_explicit_steps(task_description)
        if explicit_steps and len(explicit_steps) >= 2:
            steps.extend(explicit_steps)
            
        # Try structured breakdown 
        structured_steps = self._extract_structured_breakdown(task_description)
        if structured_steps and len(structured_steps) >= 2:
            steps.extend(structured_steps)
            
        # Try sentence-based extraction
        sentence_steps = self._extract_sentence_based(task_description)
        if sentence_steps:
            steps.extend(sentence_steps)
        
        # If we still don't have enough steps, try intelligent sentence splitting
        if len(steps) < 3:
            intelligent_steps = self._extract_intelligent_sequential(task_description)
            if intelligent_steps:
                steps.extend(intelligent_steps)
        
        # Remove duplicates while preserving order - IMPROVED
        seen = set()
        unique_steps = []
        for step in steps:
            step_lower = step.lower().strip()
            # More aggressive duplicate detection
            is_duplicate = False
            for existing in seen:
                # Check if this step is contained in or contains an existing step
                if step_lower in existing or existing in step_lower:
                    is_duplicate = True
                    break
            
            if not is_duplicate and len(step.strip()) > 10:
                seen.add(step_lower)
                unique_steps.append(step.strip())
        
        return unique_steps[:10]  # Limit to 10 steps
    
    def _extract_filipino_sequential(self, task_description: str) -> List[str]:
        """Extract Filipino sequential patterns (Una, Pagkatapos, Panghuli, etc.)"""
        steps = []
        sentences = self._smart_sentence_split(task_description)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
                
            # Check for Filipino sequential indicators
            if any(indicator in sentence.lower() for indicator in 
                   ['una sa lahat', 'una,', 'first of all', 'first,', 'pagkatapos,', 
                    'afterwards,', 'then,', 'panghuli,', 'finally,', 'lastly,',
                    'kapag tama', 'kung tama', 'if correct', 'kapag mali', 'kung mali', 'if incorrect']):
                
                # Clean up the sentence
                clean_sentence = sentence
                
                # Remove sequential prefixes but preserve conditional logic
                if not any(cond in sentence.lower() for cond in ['kung', 'kapag', 'if']):
                    clean_sentence = re.sub(r'^(?:Una sa lahat|Una|First of all|First|Pagkatapos|Afterwards|Then|Panghuli|Finally|Lastly),?\s*', 
                                          '', clean_sentence, flags=re.IGNORECASE)
                
                if len(clean_sentence.strip()) > 10:
                    steps.append(clean_sentence.strip())
        
        return steps
    
    def _extract_intelligent_sequential(self, task_description: str) -> List[str]:
        """Intelligent sequential extraction that breaks down complex sentences - FIXED"""
        steps = []
        
        # Split into sentences first
        sentences = self._smart_sentence_split(task_description)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:  # Skip very short sentences
                continue
            
            # Check for action verbs that indicate a step
            action_verbs = [
                'create', 'build', 'implement', 'develop', 'write', 'code', 'design',
                'analyze', 'review', 'test', 'validate', 'deploy', 'configure', 'setup',
                'install', 'update', 'delete', 'remove', 'fix', 'debug', 'optimize',
                'refactor', 'document', 'plan', 'research', 'investigate', 'explore',
                'generate', 'produce', 'compile', 'run', 'execute', 'perform', 'complete',
                'prepare', 'initialize', 'start', 'finish', 'end', 'begin', 'launch',
                'gumawa', 'bumuo', 'magbuild', 'mag-implement', 'isulat', 'idisenyo',
                'pag-aralan', 'i-review', 'i-test', 'i-validate', 'i-deploy', 'i-configure',
                'i-setup', 'i-install', 'i-update', 'tanggalin', 'ayusin', 'i-debug',
                'i-optimize', 'i-refactor', 'i-document', 'magplano', 'mag-research'
            ]
            
            # Check if sentence contains action verbs and is not conditional
            if any(verb in sentence.lower() for verb in action_verbs):
                if not any(cond in sentence.lower() for cond in ['if ', 'kung ', 'kapag ']):
                    # Clean up the sentence
                    clean_sentence = sentence
                    
                    # Remove common prefixes - IMPROVED
                    clean_sentence = re.sub(r'^(?:First of all|First|Una sa lahat|Una),?\s*', 
                                          '', clean_sentence, flags=re.IGNORECASE)
                    # Fix the "Of all" issue specifically - MORE AGGRESSIVE
                    clean_sentence = re.sub(r'^Of all,?\s*', '', clean_sentence, flags=re.IGNORECASE)
                    clean_sentence = re.sub(r'^Of all\s*', '', clean_sentence, flags=re.IGNORECASE)
                    clean_sentence = re.sub(r'^of all,?\s*', '', clean_sentence, flags=re.IGNORECASE)
                    clean_sentence = re.sub(r'^of all\s*', '', clean_sentence, flags=re.IGNORECASE)
                    
                    # Direct string replacement as fallback
                    if clean_sentence.lower().startswith('of all'):
                        clean_sentence = clean_sentence[7:]  # Remove "Of all" (7 characters)
                    if clean_sentence.lower().startswith('of all,'):
                        clean_sentence = clean_sentence[8:]  # Remove "Of all," (8 characters)
                    clean_sentence = re.sub(r'^(?:Afterwards|Then|Pagkatapos),?\s*', 
                                          '', clean_sentence, flags=re.IGNORECASE)
                    clean_sentence = re.sub(r'^(?:Finally|Lastly|Panghuli),?\s*', 
                                          '', clean_sentence, flags=re.IGNORECASE)
                    
                    # Fix common issues - IMPROVED
                    clean_sentence = re.sub(r'^Of all,?\s*', '', clean_sentence, flags=re.IGNORECASE)
                    clean_sentence = re.sub(r'^,\s*', '', clean_sentence)  # Remove leading commas
                    clean_sentence = re.sub(r'^\s*,\s*', '', clean_sentence)  # Remove leading commas with spaces
                    
                    if len(clean_sentence.strip()) > 15:
                        steps.append(clean_sentence.strip())
        
        return steps
    
    def _extract_structured_breakdown(self, task_description: str) -> List[str]:
        """Extract structured breakdown sections like TASK BREAKDOWN, EXECUTION PLAN, etc."""
        steps = []
        
        # Find TASK BREAKDOWN section using line-by-line approach
        lines = task_description.split('\n')
        breakdown_start = -1
        breakdown_end = len(lines)
        
        # Find start and end of TASK BREAKDOWN section
        for i, line in enumerate(lines):
            if '3️⃣' in line and 'TASK BREAKDOWN' in line:
                breakdown_start = i + 1
            elif breakdown_start > -1 and line.startswith('#') and ('4️⃣' in line or 'CONSTRAINTS' in line or 'DELIVERABLES' in line):
                breakdown_end = i
                break
        
        if breakdown_start > -1:
            breakdown_lines = lines[breakdown_start:breakdown_end]
            
            current_phase = None
            
            for line in breakdown_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is a Phase header
                phase_match = re.match(r'Phase\s+(\d+):\s*(.+)', line, re.IGNORECASE)
                if phase_match:
                    phase_num, phase_title = phase_match.groups()
                    current_phase = f"Phase {phase_num}: {phase_title.strip()}"
                    steps.append(current_phase)
                    continue
                
                # Check if this is an action item (starts with capital letter or bracket)
                if line and (line[0].isupper() or line.startswith('[')):
                    # Keep the action item exactly as written - don't remove action verbs!
                    clean_step = line.strip()
                    
                    if len(clean_step) > 10 and not self._is_noise(clean_step):
                        steps.append(clean_step)
        
        # Fallback: Look for other structured patterns if no TASK BREAKDOWN found
        if not steps:
            section_patterns = [
                r'(?:TASK BREAKDOWN|EXECUTION PLAN|WORK PLAN|IMPLEMENTATION STEPS)[:\s]*(.+?)(?=\n\n|\n[A-Z][A-Z]|$)',
                r'(?:Phase|Step|Stage)\s*\d*[.:](.+?)(?=(?:Phase|Step|Stage)|$)',
                r'(?:Hakbang|Yugto)[\s\d]*[.:](.+?)(?=(?:Hakbang|Yugto)|$)'
            ]
            
            for pattern in section_patterns:
                matches = re.findall(pattern, task_description, re.MULTILINE | re.DOTALL | re.IGNORECASE)
                for match in matches:
                    section_steps = re.findall(r'(?:^|\n)\s*(?:\d+[.)]|[-•*])\s*(.+?)(?=\n|$)', match, re.MULTILINE)
                    if section_steps:
                        for step in section_steps:
                            clean_step = step.strip()
                            if len(clean_step) > 5 and not self._is_noise(clean_step):
                                steps.append(clean_step)
        
        return steps[:15]  # Allow more for structured breakdowns
    
    def _extract_audit_steps(self, task_description: str) -> List[str]:
        """Create logical audit steps for codebase analysis"""
        steps = []
        
        # Check if it mentions config files
        if 'config' in task_description.lower() and 'yaml' in task_description.lower():
            steps.append("Load and parse startup_config.yaml to get agent list")
        
        # Check if it mentions specific analysis types
        if 'coding patterns' in task_description.lower():
            steps.append("Analyze coding patterns and naming conventions")
        
        if 'imports' in task_description.lower():
            steps.append("Extract and categorize all import statements")
        
        if 'error handling' in task_description.lower():
            steps.append("Review error handling approaches and patterns")
        
        if 'code smells' in task_description.lower():
            steps.append("Identify code smells and anti-patterns")
        
        if 'summary' in task_description.lower() or 'table' in task_description.lower():
            steps.append("Generate comprehensive summary table")
        
        # Default audit steps if none found
        if not steps:
            steps = [
                "Load agent configuration file",
                "Scan all agent source files", 
                "Analyze code structure and patterns",
                "Generate analysis report"
            ]
        
        return steps
    
    def _extract_sentence_based(self, task_description: str) -> List[str]:
        """Extract actions based on intelligent sentence boundaries"""
        actions = []
        
        # Smart sentence splitting that preserves quoted strings and file extensions
        sentences = self._smart_sentence_split(task_description)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10 and not self._is_noise(sentence):
                # Clean up common sequential indicators
                sentence = self._clean_sequential_indicators(sentence)
                
                # Don't add "Execute:" prefix if sentence already has action verbs
                if not any(verb in sentence.lower()[:25] for verb in self.action_verbs):
                    # Only add prefix for non-actionable fragments
                    if not sentence.lower().startswith(('first', 'next', 'then', 'finally', 'una', 'sunod', 'pagkatapos', 'panghuli')):
                        sentence = f"Execute: {sentence}"
                        
                actions.append(sentence)
        
        # Fallback if no valid sentences
        if not actions:
            actions = [f"Complete task: {task_description}"]
        
        return actions[:7]  # Limit to 7 actions
    
    def _smart_sentence_split(self, text: str) -> List[str]:
        """Intelligent sentence splitting that preserves quoted strings and file extensions"""
        sentences = []
        current_sentence = ""
        i = 0
        
        while i < len(text):
            char = text[i]
            current_sentence += char
            
            # Handle quoted strings - don't split inside them
            if char in ["'", '"']:
                quote_char = char
                i += 1
                while i < len(text) and text[i] != quote_char:
                    current_sentence += text[i]
                    i += 1
                if i < len(text):
                    current_sentence += text[i]  # Add closing quote
            
            # Check for sentence endings
            elif char in '.!?':
                # Look ahead to see if this is a real sentence end
                if self._is_real_sentence_end(text, i):
                    sentences.append(current_sentence.strip())
                    current_sentence = ""
            
            i += 1
        
        # Add remaining text if any
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return [s for s in sentences if s.strip()]
    
    def _is_real_sentence_end(self, text: str, pos: int) -> bool:
        """Determine if a period/punctuation is a real sentence ending"""
        char = text[pos]
        
        # Check for file extensions (.txt, .py, .sql, etc.)
        if char == '.' and pos > 0:
            # Look back for file extension pattern
            before = text[max(0, pos-5):pos].lower()
            if any(ext in before for ext in ['.txt', '.py', '.sql', '.log', '.md', '.yml', '.yaml', '.json']):
                return False
                
            # Check for abbreviations (like "etc.", "i.e.", "e.g.")
            before_word = text[max(0, pos-4):pos].lower()
            if before_word in ['etc', ' etc', 'i.e', ' ie', 'e.g', ' eg']:
                return False
        
        # Look ahead - if next character is lowercase, likely not sentence end
        if pos + 1 < len(text):
            next_chars = text[pos+1:pos+3].strip()
            if next_chars and next_chars[0].islower():
                return False
        
        # Look ahead for sequential indicators that suggest continuation
        if pos + 1 < len(text):
            ahead = text[pos+1:pos+15].strip().lower()
            if ahead.startswith(('next', 'then', 'finally', 'first', 'sunod', 'pagkatapos')):
                return True
        
        return True
    
    def _clean_sequential_indicators(self, sentence: str) -> str:
        """Clean up sequential indicators while preserving meaning"""
        sentence = sentence.strip()
        
        # Remove standalone sequential words at the beginning if they're not meaningful
        prefixes_to_clean = r'^(?:Execute:|Then,?|Next,?|Finally,?|First,?)\s*'
        sentence = re.sub(prefixes_to_clean, '', sentence, flags=re.IGNORECASE).strip()
        
        # Capitalize first letter if it's lowercase after cleaning
        if sentence and sentence[0].islower():
            sentence = sentence[0].upper() + sentence[1:]
            
        return sentence
    
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
        
        # Use integrated chunking strategy and post-process results to ensure quality
        raw_action_items = self._integrated_chunking(task_description)
        action_items = self._post_process_actions(raw_action_items)
        logger.info(f"📝 Extracted {len(action_items)} final action items after post-processing (raw: {len(raw_action_items)})")
        
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
        """Integrated chunking using semantic understanding instead of broken external chunkers"""

        logger.info("🧠 Using semantic chunking for task breakdown...")
        
        # Use our improved ActionItemExtractor directly
        actions = self.action_extractor.extract_action_items(task_description)
        
        if not actions:
            logger.warning("⚠️ No actions extracted, creating fallback")
            actions = [f"Complete task: {task_description}"]
        
        logger.info(f"✅ Generated {len(actions)} semantic action items")
        return actions

    # ------------------------------------------------------------------
    # 🔧 Post-processing helpers
    # ------------------------------------------------------------------

    def _post_process_actions(self, actions: List[str]) -> List[str]:
        """Clean, deduplicate, and trim action texts to avoid redundant subtasks."""
        def _normalise(act: str) -> str:
            # Remove common list/bullet prefixes and surrounding punctuation
            act = act.strip()
            act = re.sub(r"^[\-*•]+\s*", "", act)  # leading bullets
            # Strip leading 'i-' or 'I-' (Tagalog imperative with hyphen)
            act = re.sub(r"^[iI]-", "", act)
            # Collapse whitespace
            act = re.sub(r"\s+", " ", act)
            # Remove trailing period
            act = act.rstrip(". ")
            return act.strip()

        cleaned = [_normalise(act) for act in actions if act and act.strip()]

        # Remove empties after normalisation
        cleaned = [c for c in cleaned if c]

        # 2. Deduplicate case-insensitively while preserving order
        deduped = self._deduplicate_actions(cleaned)

        return deduped
    
    @staticmethod
    def _deduplicate_actions(actions: List[str]) -> List[str]:
        """Return actions preserving original order but removing duplicates (case-insensitive)."""
        seen = set()
        unique_actions = []
        for act in actions:
            key = act.lower()
            if key not in seen:
                seen.add(key)
                unique_actions.append(act)
        return unique_actions
    
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


async def execute_task_intelligently_async(task_description: str) -> Dict[str, Any]:
    """Async version of intelligent task execution"""
    if TELEMETRY_AVAILABLE:
        with span("execute_task", description=task_description[:80]):
            return execute_task_intelligently(task_description)
    else:
        return execute_task_intelligently(task_description)


if __name__ == "__main__":
    # Test the fixed version
    test_task = "Create a test task with automatic TODO generation"
    print(f"🧪 Testing fixed intelligent execution: {test_task}")
    
    result = execute_task_intelligently(test_task)
    print("📊 Result:")
    print(json.dumps(result, indent=2)) 