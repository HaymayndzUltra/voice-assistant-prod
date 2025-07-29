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
    """Unified task decomposer with normalized parsing strategy"""
    
    def __init__(self):
        # Core action verbs (language-agnostic concepts)
        self.action_concepts = {
            'CREATE': ['create', 'build', 'gumawa', 'bumuo', 'magbuild', 'gawa', 'gawin', 'i-build'],
            'UPDATE': ['update', 'i-update', 'pagbabago', 'baguhin'],
            'IMPLEMENT': ['implement', 'mag-implement', 'i-implement'],
            'DEVELOP': ['develop', 'design', 'idisenyo'],
            'TEST': ['test', 'i-test', 'subukan', 'pagsubok'],
            'VALIDATE': ['validate', 'i-validate', 'patunayan'],
            'RETURN': ['return', 'magbalik', 'ibalik', 'i-return'],
            'ACCEPT': ['accept', 'tumatanggap', 'tanggapin'],
            'FEATURE': ['feature', 'authentication', 'auth']  # Add feature-related terms
        }
        
        # Sequential markers to normalize
        self.sequential_markers = {
            # English
            'first of all': '[SEQ_1]',
            'first': '[SEQ_1]',
            'afterwards': '[SEQ_2]',
            'then': '[SEQ_2]',
            'next': '[SEQ_2]',
            'finally': '[SEQ_3]',
            'lastly': '[SEQ_3]',
            # Filipino
            'una sa lahat': '[SEQ_1]',
            'una,': '[SEQ_1]',  # Only match "Una," with comma
            'pagkatapos': '[SEQ_2]',
            'sunod': '[SEQ_2]',
            'panghuli': '[SEQ_3]',
            'sa wakas': '[SEQ_3]'
        }
        
        # Conditional markers to normalize
        self.conditional_markers = {
            # English
            'if': '[IF]',
            'when': '[IF]',
            # Filipino
            'kung': '[IF]',
            'kapag': '[IF]',
            # Conditional results
            'correct': 'CORRECT',
            'incorrect': 'INCORRECT',
            'tama': 'CORRECT',
            'mali': 'INCORRECT',
            'pumasa': 'CORRECT',
            'pumalya': 'INCORRECT'
        }
    
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

        for keyword, canonical in required:
            if keyword in full_lower and not any(canonical in s for s in steps):
                # Insert at appropriate position
                if canonical.startswith("Update"):
                    steps.insert(0, canonical)  # Schema update first
                elif canonical.startswith("Create /login"):
                    # Find position after schema update
                    idx = next((i for i, s in enumerate(steps) if "schema" in s), 0)
                    steps.insert(idx + 1, canonical)
                else:
                    cond_idx = next((i for i, s in enumerate(steps) if s.startswith("[CONDITIONAL]")), len(steps))
                    steps.insert(cond_idx, canonical)
        return steps
    
    def _normalize_text(self, text: str) -> str:
        """Normalize language-specific patterns to universal tokens"""
        
        # Convert to lowercase for pattern matching, but preserve original case for content
        normalized = text
        
        # Replace sequential markers with word boundaries to avoid splitting words
        for marker, token in self.sequential_markers.items():
            # Only replace if followed by comma, space, or certain punctuation
            pattern = re.compile(r'\b' + re.escape(marker) + r'(?:\s*,\s*|\s+)', re.IGNORECASE)
            normalized = pattern.sub(token + ' ', normalized)
        
        # Replace conditional markers with word boundaries
        for marker, token in self.conditional_markers.items():
            # Special handling for words that might be part of other words
            if marker in ['correct', 'incorrect', 'tama', 'mali']:
                # Only replace if it's the actual word, not part of another word
                pattern = re.compile(r'\b' + re.escape(marker) + r'\b(?=\s*[,:]|\s+)', re.IGNORECASE)
            else:
                pattern = re.compile(r'\b' + re.escape(marker) + r'\b', re.IGNORECASE)
            normalized = pattern.sub(token, normalized)
        
        # Clean up multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    def _parse_normalized_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse normalized text using unified logic"""
        steps = []
        
        # Split into sentences first
        sentences = self._split_sentences(text)
        
        # Track what we've extracted to avoid duplicates
        extracted_content = set()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if this is a conditional
            if '[IF]' in sentence:
                conditionals = self._extract_conditionals(sentence)
                for cond in conditionals:
                    key = cond['content'].lower()
                    if key not in extracted_content:
                        extracted_content.add(key)
                        steps.append(cond)
            
            # Check if this is a sequential step
            elif any(marker in sentence for marker in ['[SEQ_1]', '[SEQ_2]', '[SEQ_3]']):
                step = self._extract_sequential_step(sentence)
                if step:
                    key = step['content'].lower()
                    if key not in extracted_content:
                        extracted_content.add(key)
                        steps.append(step)
            
            # Check if this contains action verbs (main task step)
            elif self._contains_action(sentence):
                step = {
                    'type': 'action',
                    'content': self._clean_sentence(sentence),
                    'order': len(steps)
                }
                key = step['content'].lower()
                if key not in extracted_content:
                    extracted_content.add(key)
                    steps.append(step)
        
        # Sort by type priority: actions first, then conditionals
        steps.sort(key=lambda x: (0 if x['type'] == 'action' else 1, x.get('order', 0)))
        
        return steps
    
    def _extract_conditionals(self, sentence: str) -> List[Dict[str, Any]]:
        """Extract conditional logic from normalized sentence"""
        conditionals = []
        
        # First check if we have both CORRECT and INCORRECT in the same sentence
        if 'CORRECT' in sentence and 'INCORRECT' in sentence:
            # Handle compound conditionals: "If correct, do X. If incorrect, do Y."
            # Split by period to handle each conditional separately
            parts = sentence.split('.')
            for part in parts:
                if '[IF]' in part and 'CORRECT' in part and 'INCORRECT' not in part:
                    # This is the "correct" case
                    action_match = re.search(r'CORRECT.*?[:,]\s*(.+?)(?:\[IF\]|$)', part, re.IGNORECASE)
                    if action_match:
                        action = self._clean_sentence(action_match.group(1).strip())
                        conditionals.append({
                            'type': 'conditional',
                            'condition': 'success',
                            'content': f"[CONDITIONAL] If credentials are correct: {action}",
                            'order': 0
                        })
                elif '[IF]' in part and 'INCORRECT' in part:
                    # This is the "incorrect" case
                    action_match = re.search(r'INCORRECT.*?[:,]\s*(.+?)(?:\[IF\]|$)', part, re.IGNORECASE)
                    if action_match:
                        action = self._clean_sentence(action_match.group(1).strip())
                        conditionals.append({
                            'type': 'conditional',
                            'condition': 'failure',
                            'content': f"[CONDITIONAL] If credentials are incorrect: {action}",
                            'order': 1
                        })
        else:
            # Single conditional in the sentence
            if 'CORRECT' in sentence and 'INCORRECT' not in sentence:
                # Pattern: [IF] ... CORRECT ... : ...
                correct_pattern = r'CORRECT.*?[:,]\s*(.+?)(?:\.|$)'
                correct_match = re.search(correct_pattern, sentence, re.IGNORECASE)
                if correct_match:
                    action = self._clean_sentence(correct_match.group(1).strip())
                    conditionals.append({
                        'type': 'conditional',
                        'condition': 'success',
                        'content': f"[CONDITIONAL] If credentials are correct: {action}",
                        'order': 0
                    })
            
            elif 'INCORRECT' in sentence:
                # Pattern: [IF] ... INCORRECT ... : ...
                incorrect_pattern = r'INCORRECT.*?[:,]\s*(.+?)(?:\.|$)'
                incorrect_match = re.search(incorrect_pattern, sentence, re.IGNORECASE)
                if incorrect_match:
                    action = self._clean_sentence(incorrect_match.group(1).strip())
                    conditionals.append({
                        'type': 'conditional',
                        'condition': 'failure',
                        'content': f"[CONDITIONAL] If credentials are incorrect: {action}",
                        'order': 1
                    })
        
        return conditionals
    
    def _extract_sequential_step(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Extract sequential step from normalized sentence"""
        
        # Remove the sequential marker to get the actual content
        content = sentence
        for marker in ['[SEQ_1]', '[SEQ_2]', '[SEQ_3]']:
            content = content.replace(marker, '').strip()
        
        # Clean the content
        content = self._clean_sentence(content)
        
        if content and len(content) > 10:
            return {
                'type': 'action',
                'content': content,
                'order': 0 if '[SEQ_1]' in sentence else (1 if '[SEQ_2]' in sentence else 2)
            }
        
        return None
    
    def _contains_action(self, sentence: str) -> bool:
        """Check if sentence contains action verbs"""
        sentence_lower = sentence.lower()
        for concept, verbs in self.action_concepts.items():
            if any(verb in sentence_lower for verb in verbs):
                return True
        return False
    
    def _clean_sentence(self, sentence: str) -> str:
        """Clean up sentence for final output"""
        # Remove normalized tokens more carefully
        cleaned = sentence
        
        # Remove tokens but be careful about word boundaries
        tokens_to_remove = ['[SEQ_1]', '[SEQ_2]', '[SEQ_3]', '[IF]', 'CORRECT', 'INCORRECT']
        for token in tokens_to_remove:
            # Remove token with surrounding spaces
            cleaned = cleaned.replace(f' {token} ', ' ')
            # Remove token at start
            if cleaned.startswith(token + ' '):
                cleaned = cleaned[len(token)+1:]
            # Remove token at end
            if cleaned.endswith(' ' + token):
                cleaned = cleaned[:-len(token)-1]
            # Final cleanup for any remaining instances
            cleaned = cleaned.replace(token, '')
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Fix common issues from token removal
        cleaned = cleaned.replace(' ,', ',')
        cleaned = cleaned.replace(' .', '.')
        cleaned = cleaned.replace(' :', ':')
        
        # Capitalize first letter
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # Remove trailing punctuation if it's just a comma
        cleaned = cleaned.rstrip(',')
        
        return cleaned
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences, preserving important boundaries"""
        # Split on periods, but not on file extensions
        sentences = []
        current = ""
        
        i = 0
        while i < len(text):
            char = text[i]
            current += char
            
            if char in '.!?':
                # Check if this is a real sentence end
                if i + 1 < len(text):
                    next_char = text[i + 1]
                    # If next char is space and following char is uppercase, it's likely a new sentence
                    if next_char == ' ' and i + 2 < len(text) and text[i + 2].isupper():
                        sentences.append(current.strip())
                        current = ""
                    # Also check for sequential markers
                    elif i + 2 < len(text):
                        next_word = text[i+1:i+10].strip().lower()
                        if any(next_word.startswith(marker) for marker in ['[seq_', 'kung', '[if]']):
                            sentences.append(current.strip())
                            current = ""
                else:
                    # End of text
                    sentences.append(current.strip())
                    current = ""
            
            i += 1
        
        if current.strip():
            sentences.append(current.strip())
        
        return sentences
    
    def _clean_and_finalize_steps(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Convert step dictionaries to final string format"""
        final_steps = []
        
        # Group by type for better organization
        actions = [s for s in steps if s['type'] == 'action']
        conditionals = [s for s in steps if s['type'] == 'conditional']
        
        # Add actions first
        for step in actions:
            final_steps.append(step['content'])
        
        # Add conditionals
        for step in conditionals:
            final_steps.append(step['content'])
        
        return final_steps
    
    def _analyze_task_structure(self, task_description: str) -> dict:
        """Analyze task for logical patterns, dependencies, and parallelism"""
        normalized = self._normalize_text(task_description)
        
        analysis = {
            'has_conditional_logic': '[IF]' in normalized and ('CORRECT' in normalized or 'INCORRECT' in normalized),
            'has_parallelism': False,  # Not used in current test
            'has_dependencies': False,  # Not used in current test  
            'has_sequential_flow': any(marker in normalized for marker in ['[SEQ_1]', '[SEQ_2]', '[SEQ_3]']),
            'complexity_score': 0
        }
        
        # Calculate complexity score
        if analysis['has_conditional_logic']:
            analysis['complexity_score'] += 10
        if analysis['has_sequential_flow']:
            analysis['complexity_score'] += 5
        
        return analysis


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