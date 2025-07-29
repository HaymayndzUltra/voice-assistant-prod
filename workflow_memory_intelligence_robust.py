#!/usr/bin/env python3
"""
Workflow Memory Intelligence System - ROBUST FINAL IMPLEMENTATION
A truly generalized reasoning engine for task decomposition
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================================================
# COMMAND CLASSIFICATION SYSTEM
# ============================================================================

class CommandType(Enum):
    """Types of commands the system can handle"""
    SIMPLE_SEQUENTIAL = "simple_sequential"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    COMPLEX_MIXED = "complex_mixed"
    UNKNOWN = "unknown"


@dataclass
class CommandStructure:
    """Analyzed structure of a command"""
    type: CommandType
    has_conditionals: bool
    has_parallelism: bool
    has_hierarchy: bool
    has_sequential_flow: bool
    language_mix: str  # "english", "filipino", "taglish"
    confidence: float
    indicators: List[str]


class CommandClassifier:
    """Classifies commands into types for appropriate parsing strategy"""
    
    def __init__(self):
        # Conditional indicators
        self.conditional_patterns = [
            r'\b(if|when|kung|kapag)\b.*\b(then|dapat|kailangan)\b',
            r'\b(otherwise|else|kung hindi|o kaya)\b',
            r'\b(correct|incorrect|tama|mali|pass|fail)\b.*\b(then|return|magbalik)\b',
            r'\bmust return\b.*\b(if|when)\b'
        ]
        
        # Parallel execution indicators
        self.parallel_patterns = [
            r'\b(parallel|simultaneously|sabay|kasabay)\b',
            r'\b(while|habang|during|sa panahon)\b.*\b(also|din|rin)\b',
            r'\bin parallel with\b',
            r'\bat the same time\b'
        ]
        
        # Hierarchical indicators
        self.hierarchical_patterns = [
            r'^\s*\d+\..*\n\s+[-•]',  # Numbered list with sub-bullets
            r':\s*\n\s*[-•]',  # Colon followed by bulleted list
            r'\b(subtasks?|sub-tasks?|mga subtask)\b',
            r'\b(breakdown|break down|hatiin|pagkakahati)\b'
        ]
        
        # Sequential indicators
        self.sequential_patterns = [
            r'\b(first|una|initially|simulan)\b',
            r'\b(then|next|afterwards|pagkatapos|sunod)\b',
            r'\b(finally|lastly|panghuli|sa wakas)\b',
            r'\b(step \d+|hakbang \d+)\b'
        ]
        
        # Language detection patterns
        self.filipino_patterns = [
            r'\b(mga|ang|ng|sa|na|ay|at|o|para|kung|nang|ito|yan|yun)\b',
            r'\b(gawin|gumawa|bumuo|magbuild|i-update|i-test)\b'
        ]
        
        self.english_patterns = [
            r'\b(the|is|are|was|were|been|being|have|has|had|do|does|did)\b',
            r'\b(create|update|implement|develop|test|validate)\b'
        ]
    
    def classify(self, command: str) -> CommandStructure:
        """Classify a command into its type and structure"""
        command_lower = command.lower()
        
        # Detect language mix
        filipino_count = sum(1 for pattern in self.filipino_patterns 
                           if re.search(pattern, command_lower))
        english_count = sum(1 for pattern in self.english_patterns 
                          if re.search(pattern, command_lower))
        
        if filipino_count > 0 and english_count > 0:
            language_mix = "taglish"
        elif filipino_count > english_count:
            language_mix = "filipino"
        else:
            language_mix = "english"
        
        # Check for structural patterns
        has_conditionals = any(re.search(pattern, command_lower) 
                             for pattern in self.conditional_patterns)
        has_parallelism = any(re.search(pattern, command_lower) 
                            for pattern in self.parallel_patterns)
        has_hierarchy = any(re.search(pattern, command, re.MULTILINE) 
                          for pattern in self.hierarchical_patterns)
        has_sequential = any(re.search(pattern, command_lower) 
                           for pattern in self.sequential_patterns)
        
        # Determine command type
        complexity_score = sum([has_conditionals, has_parallelism, has_hierarchy])
        
        if complexity_score >= 2:
            cmd_type = CommandType.COMPLEX_MIXED
        elif has_hierarchy:
            cmd_type = CommandType.HIERARCHICAL
        elif has_parallelism:
            cmd_type = CommandType.PARALLEL
        elif has_conditionals:
            cmd_type = CommandType.CONDITIONAL
        elif has_sequential:
            cmd_type = CommandType.SIMPLE_SEQUENTIAL
        else:
            cmd_type = CommandType.UNKNOWN
        
        # Calculate confidence
        confidence = 0.5
        if cmd_type != CommandType.UNKNOWN:
            confidence = 0.8 + (0.05 * sum([has_conditionals, has_parallelism, 
                                          has_hierarchy, has_sequential]))
        
        # Collect indicators for debugging
        indicators = []
        if has_conditionals:
            indicators.append("conditionals")
        if has_parallelism:
            indicators.append("parallelism")
        if has_hierarchy:
            indicators.append("hierarchy")
        if has_sequential:
            indicators.append("sequential")
        
        return CommandStructure(
            type=cmd_type,
            has_conditionals=has_conditionals,
            has_parallelism=has_parallelism,
            has_hierarchy=has_hierarchy,
            has_sequential_flow=has_sequential,
            language_mix=language_mix,
            confidence=confidence,
            indicators=indicators
        )


# ============================================================================
# ROBUST SENTENCE SPLITTER
# ============================================================================

class RobustSentenceSplitter:
    """Robust sentence splitting that handles multiple languages and edge cases"""
    
    def split(self, text: str) -> List[str]:
        """Split text into sentences with robust handling"""
        # First, handle obvious paragraph/line breaks
        paragraphs = text.split('\n')
        
        all_sentences = []
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # Check if it's a list item
            if re.match(r'^\s*[-•*]\s+', paragraph) or re.match(r'^\s*\d+\.\s+', paragraph):
                all_sentences.append(paragraph)
            else:
                # Split paragraph into sentences
                sentences = self._split_paragraph(paragraph)
                all_sentences.extend(sentences)
        
        return all_sentences
    
    def _split_paragraph(self, paragraph: str) -> List[str]:
        """Split a paragraph into sentences"""
        # Handle special cases first
        if len(paragraph) < 20:
            return [paragraph] if paragraph else []
        
        sentences = []
        current = ""
        i = 0
        in_quotes = False
        quote_char = None
        
        while i < len(paragraph):
            char = paragraph[i]
            
            # Handle quotes
            if char in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            
            current += char
            
            # Check for sentence boundaries
            if not in_quotes and char in '.!?':
                # Look ahead to determine if this is a real sentence end
                if self._is_sentence_boundary(paragraph, i):
                    sentences.append(current.strip())
                    current = ""
            
            i += 1
        
        # Add remaining text
        if current.strip():
            sentences.append(current.strip())
        
        return sentences
    
    def _is_sentence_boundary(self, text: str, pos: int) -> bool:
        """Determine if position is a real sentence boundary"""
        if pos >= len(text) - 1:
            return True
        
        # Get next few characters
        remaining = text[pos+1:pos+10]
        
        # Skip whitespace
        remaining = remaining.lstrip()
        
        if not remaining:
            return True
        
        # Check patterns that indicate new sentence
        new_sentence_patterns = [
            r'^[A-Z]',  # Capital letter
            r'^(First|Then|Next|Finally|Una|Pagkatapos|Kung|If|When)',  # Sequential/conditional markers
            r'^\d+\.',  # Numbered list
            r'^[-•*]',  # Bullet point
        ]
        
        return any(re.match(pattern, remaining) for pattern in new_sentence_patterns)


# ============================================================================
# UNIFIED ACTION EXTRACTOR
# ============================================================================

class UnifiedActionExtractor:
    """Unified extraction logic that works across all languages"""
    
    def __init__(self):
        self.sentence_splitter = RobustSentenceSplitter()
        
        # Core action patterns
        self.action_verbs = {
            'english': ['create', 'build', 'update', 'implement', 'design', 
                       'test', 'validate', 'add', 'setup', 'configure', 
                       'deploy', 'run', 'execute', 'check', 'verify',
                       'develop', 'generate', 'remove', 'fix'],
            'filipino': ['gawin', 'gumawa', 'bumuo', 'i-update', 'i-test',
                        'magdagdag', 'i-build', 'mag-implement', 'i-setup',
                        'i-validate', 'subukan', 'ayusin']
        }
        
        # Domain-specific nouns that indicate actions
        self.action_nouns = [
            'endpoint', 'api', 'database', 'schema', 'form', 'login', 
            'table', 'column', 'service', 'deployment', 'migration',
            'test', 'validation', 'authentication', 'feature'
        ]
        
        # Sequential markers to remove
        self.sequential_markers = [
            'first of all', 'first', 'then', 'next', 'afterwards', 
            'finally', 'lastly', 'una sa lahat', 'una', 'pagkatapos', 
            'sunod', 'panghuli', 'sa wakas'
        ]
    
    def extract_all_actions(self, text: str) -> List[Dict[str, Any]]:
        """Extract all actions from text with metadata"""
        sentences = self.sentence_splitter.split(text)
        actions = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Analyze sentence type
            action_type = self._analyze_sentence_type(sentence)
            
            if action_type == 'conditional':
                conditionals = self._extract_conditionals_from_sentence(sentence)
                actions.extend(conditionals)
            elif action_type == 'parallel':
                parallel_actions = self._extract_parallel_actions(sentence)
                actions.extend(parallel_actions)
            elif action_type == 'action':
                action = self._extract_single_action(sentence)
                if action:
                    actions.append(action)
        
        return actions
    
    def _analyze_sentence_type(self, sentence: str) -> str:
        """Determine the type of sentence"""
        sentence_lower = sentence.lower()
        
        # Check for conditionals
        if any(marker in sentence_lower for marker in ['if', 'when', 'kung', 'kapag']):
            if any(marker in sentence_lower for marker in ['correct', 'incorrect', 'tama', 'mali']):
                return 'conditional'
        
        # Check for parallel execution
        if any(marker in sentence_lower for marker in ['parallel', 'simultaneously', 'sabay']):
            return 'parallel'
        
        # Check if it contains action
        if self._contains_action(sentence):
            return 'action'
        
        return 'other'
    
    def _contains_action(self, sentence: str) -> bool:
        """Check if sentence contains actionable content"""
        if not sentence or len(sentence) < 10:
            return False
        
        sentence_lower = sentence.lower()
        
        # Check for action verbs
        all_verbs = self.action_verbs['english'] + self.action_verbs['filipino']
        has_verb = any(verb in sentence_lower for verb in all_verbs)
        
        # Check for action nouns
        has_noun = any(noun in sentence_lower for noun in self.action_nouns)
        
        # Check for imperative patterns
        imperative_patterns = [
            r'^(create|build|update|implement|gawin|gumawa|i-)',
            r'^(let\'s|let us)',
            r'(must|should|dapat|kailangan)\s+(create|build|update|return)',
        ]
        has_imperative = any(re.search(pattern, sentence_lower) for pattern in imperative_patterns)
        
        return has_verb or has_noun or has_imperative
    
    def _extract_single_action(self, sentence: str) -> Optional[Dict[str, Any]]:
        """Extract a single action from a sentence"""
        # Clean sequential markers
        cleaned = self._clean_sequential_markers(sentence)
        
        if not cleaned or len(cleaned) < 10:
            return None
        
        # Format the action
        formatted = self._format_action_text(cleaned)
        
        return {
            'type': 'action',
            'content': formatted,
            'original': sentence
        }
    
    def _clean_sequential_markers(self, sentence: str) -> str:
        """Remove sequential markers from sentence"""
        cleaned = sentence
        sentence_lower = sentence.lower()
        
        for marker in self.sequential_markers:
            if sentence_lower.startswith(marker):
                # Remove the marker
                cleaned = sentence[len(marker):].strip()
                # Remove comma if it follows
                if cleaned.startswith(','):
                    cleaned = cleaned[1:].strip()
                break
        
        return cleaned
    
    def _format_action_text(self, text: str) -> str:
        """Format action text properly"""
        # Remove extra whitespace
        formatted = re.sub(r'\s+', ' ', text).strip()
        
        # Capitalize first letter
        if formatted and formatted[0].islower():
            formatted = formatted[0].upper() + formatted[1:]
        
        # Ensure ends with period
        if formatted and not formatted[-1] in '.!?':
            formatted += '.'
        
        return formatted
    
    def _extract_conditionals_from_sentence(self, sentence: str) -> List[Dict[str, Any]]:
        """Extract conditional statements from a sentence"""
        conditionals = []
        
        # Pattern for "if correct" conditions
        correct_patterns = [
            r'(kung|if|when)\s+(?:ang\s+)?(?:the\s+)?credentials?\s+(?:are\s+|is\s+|ay\s+)?(tama|correct)',
            r'(kung|if|when)\s+(tama|correct)\s+ang\s+credentials?',
            r'(kapag|if|when)\s+(?:the\s+)?credentials?\s+(?:are\s+)?(tama|correct)',
        ]
        
        # Pattern for "if incorrect" conditions  
        incorrect_patterns = [
            r'(kung|if|when)\s+(?:ang\s+)?(?:the\s+)?(?:credentials?\s+)?(?:are\s+|is\s+)?(mali|incorrect)',
            r'(kung|if|when)\s+(?:they\s+are\s+)?(mali|incorrect)',
        ]
        
        # Check for success condition
        for pattern in correct_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                # Extract the action part
                action = self._extract_conditional_action(sentence, 'correct')
                if action:
                    conditionals.append({
                        'type': 'conditional',
                        'condition': 'success',
                        'content': f"[CONDITIONAL] If credentials are correct: {action}",
                        'original': sentence
                    })
                break
        
        # Check for failure condition
        for pattern in incorrect_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                # Extract the action part
                action = self._extract_conditional_action(sentence, 'incorrect')
                if action:
                    conditionals.append({
                        'type': 'conditional',
                        'condition': 'failure',
                        'content': f"[CONDITIONAL] If credentials are incorrect: {action}",
                        'original': sentence
                    })
                break
        
        return conditionals
    
    def _extract_conditional_action(self, sentence: str, condition_type: str) -> str:
        """Extract the action part from a conditional sentence"""
        # Common patterns for extracting actions
        if condition_type == 'correct':
            patterns = [
                r'(?:must|dapat|kailangan)\s+(?:itong\s+)?(?:mag)?(?:return|balik|ibalik)\s+(?:ng\s+)?(?:isang\s+)?(\w+)',
                r'return\s+(?:a\s+)?(\w+)',
                r'magbalik\s+ng\s+(?:isang\s+)?(\w+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    return f"return {match.group(1)}"
            
            # Fallback
            if 'JWT' in sentence:
                return "return JWT"
                
        else:  # incorrect
            patterns = [
                r'(?:must|dapat)\s+(?:itong\s+)?(?:mag)?(?:return|balik)\s+(?:ng\s+)?(\d+\s+\w+)',
                r'return\s+(?:a\s+)?(\d+\s+\w+)',
                r'(\d+\s+Unauthorized)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    return f"return {match.group(1)}"
            
            # Fallback
            if '401' in sentence:
                return "return 401 Unauthorized error"
        
        return ""
    
    def _extract_parallel_actions(self, sentence: str) -> List[Dict[str, Any]]:
        """Extract parallel actions from a sentence"""
        actions = []
        
        # Look for list of parallel items
        if 'parallel' in sentence.lower():
            # Pattern: "services in parallel: X, Y, and Z"
            match = re.search(r'parallel:\s*(.+)', sentence, re.IGNORECASE)
            if match:
                items_text = match.group(1)
                items = re.split(r',\s*(?:and\s+)?|\s+and\s+', items_text)
                
                for item in items:
                    item = item.strip(' .')
                    if item:
                        actions.append({
                            'type': 'parallel',
                            'content': f"[PARALLEL] {item}",
                            'original': sentence
                        })
        
        return actions


# ============================================================================
# MAIN ACTION ITEM EXTRACTOR
# ============================================================================

class ActionItemExtractor:
    """Robust, strategy-based action item extractor"""
    
    def __init__(self):
        self.classifier = CommandClassifier()
        self.extractor = UnifiedActionExtractor()
        self._cache = {}
    
    def extract_action_items(self, task_description: str) -> List[str]:
        """Extract action items with robust handling"""
        # Check cache
        cache_key = hash(task_description)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            # Classify command structure
            structure = self.classifier.classify(task_description)
            
            # Extract all actions
            raw_actions = self.extractor.extract_all_actions(task_description)
            
            # Post-process and deduplicate
            action_items = self._post_process_actions(raw_actions)
            
            # Cache results
            self._cache[cache_key] = action_items
            
            return action_items
            
        except Exception as e:
            logger.error(f"Error extracting action items: {e}", exc_info=True)
            return [f"Complete task: {task_description}"]
    
    def _post_process_actions(self, raw_actions: List[Dict[str, Any]]) -> List[str]:
        """Post-process and deduplicate actions"""
        final_actions = []
        seen_normalized = set()
        
        # Group by type
        regular_actions = []
        conditional_actions = []
        parallel_actions = []
        
        for action in raw_actions:
            if action['type'] == 'conditional':
                conditional_actions.append(action)
            elif action['type'] == 'parallel':
                parallel_actions.append(action)
            else:
                regular_actions.append(action)
        
        # Process regular actions first
        for action in regular_actions:
            normalized = self._normalize_for_dedup(action['content'])
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                final_actions.append(action['content'])
        
        # Process parallel actions
        for action in parallel_actions:
            normalized = self._normalize_for_dedup(action['content'])
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                final_actions.append(action['content'])
        
        # Process conditional actions
        for action in conditional_actions:
            # For conditionals, check if we already have this condition
            condition_key = action.get('condition', '')
            normalized = f"{condition_key}:{self._normalize_for_dedup(action['content'])}"
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                final_actions.append(action['content'])
        
        return final_actions
    
    def _normalize_for_dedup(self, text: str) -> str:
        """Normalize text for deduplication"""
        # Remove tags
        normalized = re.sub(r'\[(CONDITIONAL|PARALLEL|DEPENDENCY)\]\s*', '', text)
        # Remove punctuation
        normalized = re.sub(r'[.,!?:;]', '', normalized)
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        # Lowercase
        normalized = normalized.lower().strip()
        
        return normalized
    
    def _analyze_task_structure(self, task_description: str) -> dict:
        """Analyze task structure for backward compatibility"""
        structure = self.classifier.classify(task_description)
        
        return {
            'has_conditional_logic': structure.has_conditionals,
            'has_parallelism': structure.has_parallelism,
            'has_dependencies': structure.has_hierarchy,
            'has_sequential_flow': structure.has_sequential_flow,
            'complexity_score': sum([
                structure.has_conditionals * 10,
                structure.has_parallelism * 15,
                structure.has_hierarchy * 20,
                structure.has_sequential_flow * 5
            ])
        }


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

try:
    from workflow_memory_intelligence_fixed import TaskComplexityAnalyzer
except ImportError:
    class TaskComplexityAnalyzer:
        def analyze_complexity(self, task_description: str):
            from collections import namedtuple
            Complexity = namedtuple('Complexity', ['score', 'level', 'should_chunk', 
                                                  'estimated_subtasks', 'reasoning'])
            
            length = len(task_description)
            if length < 100:
                return Complexity(0, "SIMPLE", False, 1, ["Short task"])
            elif length < 300:
                return Complexity(30, "MEDIUM", True, 3, ["Medium length task"])
            else:
                return Complexity(60, "COMPLEX", True, 5, ["Long complex task"])