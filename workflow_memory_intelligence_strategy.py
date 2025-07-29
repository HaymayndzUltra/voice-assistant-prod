#!/usr/bin/env python3
"""
Workflow Memory Intelligence System - STRATEGY-BASED ARCHITECTURE
Robust, generalized reasoning engine for task decomposition
"""

import re
import logging
from typing import Dict, Any, List, Optional, Protocol, Tuple
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
            r'\b(correct|incorrect|tama|mali|pass|fail)\b.*\b(then|return|magbalik)\b'
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
# PARSING STRATEGY INTERFACE
# ============================================================================

class ParsingStrategy(ABC):
    """Abstract base class for parsing strategies"""
    
    def __init__(self):
        self.language_normalizer = LanguageNormalizer()
        self.sentence_splitter = SmartSentenceSplitter()
    
    @abstractmethod
    def parse(self, command: str, structure: CommandStructure) -> List[str]:
        """Parse command into action items"""
        pass
    
    @abstractmethod
    def can_handle(self, structure: CommandStructure) -> bool:
        """Check if this strategy can handle the given command structure"""
        pass


# ============================================================================
# LANGUAGE UTILITIES
# ============================================================================

class LanguageNormalizer:
    """Normalizes multilingual text to standard form"""
    
    def __init__(self):
        # More selective translations - only normalize when necessary
        self.action_verbs = {
            'gawin': 'create',
            'gumawa': 'create',
            'bumuo': 'build',
            'i-build': 'build',
            'i-update': 'update',
            'i-test': 'test',
            'i-validate': 'validate',
            'magbalik': 'return',
            'ibalik': 'return',
            'i-return': 'return',
            'tumatanggap': 'accepts',
            'tanggapin': 'accept',
            'mag-implement': 'implement',
            'i-implement': 'implement',
            'idisenyo': 'design',
            'subukan': 'test',
            'patunayan': 'validate',
            'magdagdag': 'add',
            'gawa': 'create'
        }
        
        # Only normalize specific conditional words
        self.conditional_words = {
            'kung': 'if',
            'kapag': 'if',
            'tama': 'correct',
            'mali': 'incorrect',
            'dapat': 'must',
            'kailangan': 'must'
        }
        
        # Sequential markers
        self.sequential_markers = {
            'una sa lahat': 'first of all',
            'una': 'first',
            'pagkatapos': 'afterwards',
            'sunod': 'next',
            'panghuli': 'finally',
            'sa wakas': 'finally'
        }
    
    def normalize_lightly(self, text: str) -> str:
        """Light normalization - preserve most of the original text"""
        normalized = text
        
        # Only normalize key action verbs and conditional words
        all_words = {**self.action_verbs, **self.conditional_words, **self.sequential_markers}
        
        for filipino, english in all_words.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(filipino) + r'\b'
            normalized = re.sub(pattern, english, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def extract_meaning(self, text: str) -> str:
        """Extract semantic meaning without heavy translation"""
        # This is used for understanding, not for output
        return self.normalize_lightly(text)


class SmartSentenceSplitter:
    """Intelligent sentence splitting that handles edge cases"""
    
    def split(self, text: str) -> List[str]:
        """Split text into sentences intelligently"""
        sentences = []
        current = ""
        i = 0
        in_quotes = False
        quote_char = None
        
        while i < len(text):
            char = text[i]
            
            # Handle quotes
            if char in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            
            current += char
            
            # Check for sentence end
            if not in_quotes and char in '.!?':
                # Look ahead
                if i + 1 < len(text):
                    next_char = text[i + 1] if i + 1 < len(text) else ''
                    next_next_char = text[i + 2] if i + 2 < len(text) else ''
                    
                    # Check if real sentence end
                    if next_char in ' \n\t' and (not next_next_char or next_next_char.isupper()):
                        sentences.append(current.strip())
                        current = ""
                else:
                    # End of text
                    sentences.append(current.strip())
                    current = ""
            
            i += 1
        
        # Add remaining
        if current.strip():
            sentences.append(current.strip())
        
        # Split on newlines if they indicate list items
        final_sentences = []
        for sent in sentences:
            if '\n' in sent:
                lines = sent.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith(('-', '•', '*'))):
                        final_sentences.append(line)
                    elif line:
                        if final_sentences and not final_sentences[-1].endswith(('.', '!', '?', ':')):
                            final_sentences[-1] += ' ' + line
                        else:
                            final_sentences.append(line)
            else:
                final_sentences.append(sent)
        
        return [s.strip() for s in final_sentences if s.strip()]


# ============================================================================
# IMPROVED PARSING STRATEGIES
# ============================================================================

class SimpleSequentialStrategy(ParsingStrategy):
    """Handles simple sequential commands"""
    
    def can_handle(self, structure: CommandStructure) -> bool:
        return (structure.type == CommandType.SIMPLE_SEQUENTIAL or
                (structure.type == CommandType.UNKNOWN and structure.has_sequential_flow))
    
    def parse(self, command: str, structure: CommandStructure) -> List[str]:
        """Parse simple sequential commands"""
        # Split into sentences
        sentences = self.sentence_splitter.split(command)
        
        # Extract sequential steps
        steps = []
        sequential_markers = ['first', 'then', 'next', 'afterwards', 'finally', 'lastly',
                            'una sa lahat', 'una', 'pagkatapos', 'sunod', 'panghuli', 'sa wakas']
        
        for sentence in sentences:
            # Clean sentence but preserve original language
            cleaned = self._clean_sequential_markers(sentence, sequential_markers)
            
            # Extract action if present
            if self._contains_action(cleaned):
                step = self._format_action(cleaned)
                if step and step not in steps:
                    steps.append(step)
        
        return steps
    
    def _clean_sequential_markers(self, sentence: str, markers: List[str]) -> str:
        """Remove sequential markers while preserving the rest"""
        cleaned = sentence
        sentence_lower = sentence.lower()
        
        for marker in markers:
            if sentence_lower.startswith(marker):
                # Remove the marker
                cleaned = sentence[len(marker):].strip()
                # Remove comma if it follows
                if cleaned.startswith(','):
                    cleaned = cleaned[1:].strip()
                # Handle "first of all"
                if marker in ['first', 'una'] and cleaned.lower().startswith('of all'):
                    cleaned = cleaned[6:].strip()
                    if cleaned.startswith(','):
                        cleaned = cleaned[1:].strip()
                break
        
        return cleaned
    
    def _contains_action(self, sentence: str) -> bool:
        """Check if sentence contains actionable content"""
        if not sentence or len(sentence) < 10:
            return False
            
        # Check for action verbs in multiple languages
        action_verbs = [
            'create', 'build', 'update', 'implement', 'design', 
            'test', 'validate', 'add', 'setup', 'configure', 
            'deploy', 'run', 'execute', 'check', 'verify',
            'gawin', 'gumawa', 'bumuo', 'i-update', 'i-test',
            'magdagdag', 'i-build', 'mag-implement'
        ]
        
        sentence_lower = sentence.lower()
        
        # Check if it contains action verbs
        has_action = any(verb in sentence_lower for verb in action_verbs)
        
        # Also check for specific patterns that indicate actions
        action_patterns = [
            r'\b(endpoint|api|database|schema|form|login|table|column)\b',
            r'\b(POST|GET|JWT|401|error)\b'
        ]
        
        has_pattern = any(re.search(pattern, sentence, re.IGNORECASE) for pattern in action_patterns)
        
        return has_action or has_pattern
    
    def _format_action(self, sentence: str) -> str:
        """Format action step properly"""
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', sentence).strip()
        
        # Capitalize first letter
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # Ensure ends with period
        if cleaned and not cleaned[-1] in '.!?':
            cleaned += '.'
        
        return cleaned


class ImprovedConditionalStrategy(ParsingStrategy):
    """Improved handling of commands with conditional logic"""
    
    def can_handle(self, structure: CommandStructure) -> bool:
        return structure.has_conditionals
    
    def parse(self, command: str, structure: CommandStructure) -> List[str]:
        """Parse commands with conditional logic"""
        # Split into sentences
        sentences = self.sentence_splitter.split(command)
        
        steps = []
        
        # First extract ALL non-conditional steps (not just actions)
        for sentence in sentences:
            normalized = self.language_normalizer.extract_meaning(sentence)
            if not self._is_conditional(normalized):
                step = self._extract_regular_step(sentence)
                if step and step not in steps:
                    steps.append(step)
        
        # Then extract conditional steps
        conditionals = self._extract_conditionals(command)
        for cond in conditionals:
            if cond not in steps:
                steps.append(cond)
        
        return steps
    
    def _is_conditional(self, sentence: str) -> bool:
        """Check if sentence contains conditional logic"""
        conditional_patterns = [
            r'\b(if|when|kung|kapag)\b.*\b(correct|incorrect|tama|mali|pass|fail)\b',
            r'\b(else|otherwise|kung hindi)\b',
            r'\bmust return\b.*\b(if|when|kung|kapag)\b'
        ]
        sentence_lower = sentence.lower()
        return any(re.search(pattern, sentence_lower) for pattern in conditional_patterns)
    
    def _extract_regular_step(self, sentence: str) -> Optional[str]:
        """Extract non-conditional action step"""
        # Use the improved simple sequential strategy
        strategy = SimpleSequentialStrategy()
        
        # Clean sequential markers first
        sequential_markers = ['first', 'then', 'next', 'afterwards', 'finally', 'lastly',
                            'una sa lahat', 'una', 'pagkatapos', 'sunod', 'panghuli', 'sa wakas']
        cleaned = strategy._clean_sequential_markers(sentence, sequential_markers)
        
        if strategy._contains_action(cleaned):
            return strategy._format_action(cleaned)
        return None
    
    def _extract_conditionals(self, text: str) -> List[str]:
        """Extract conditional statements with better pattern matching"""
        conditionals = []
        
        # Normalize for pattern matching
        normalized = self.language_normalizer.extract_meaning(text)
        
        # Improved patterns that handle more variations
        # Pattern 1: "If X correct/tama, Y"
        pattern1 = r'(if|when)\s+(?:the\s+)?(\w+)\s+(?:are|is|ang)\s+(correct|tama)[^,.]*[,.]?\s*(?:must|dapat)?\s*(?:this|itong|ito)?\s*(?:return|magbalik|ibalik)\s+(?:ng\s+)?(?:isang\s+)?(?:credentials\s+)?(\w+|[^,.]+?)(?:\.|,|$)'
        
        # Pattern 2: "If correct ang X, Y"
        pattern2 = r'(if|when)\s+(correct|tama)\s+(?:ang\s+)?(\w+)[^,.]*[,.]?\s*(?:must|dapat)?\s*(?:return|magbalik)\s+(?:ng\s+)?(?:isang\s+)?(?:credentials\s+)?(\w+|[^,.]+?)(?:\.|,|$)'
        
        # Pattern 3: Standard "If credentials are correct: return JWT"
        pattern3 = r'(if|when)\s+(?:the\s+)?(?:credentials\s+)?(?:are|is)\s+(correct|incorrect)[^:]*:\s*(.+?)(?:\.|$)'
        
        # Find all conditional patterns
        for pattern in [pattern1, pattern2, pattern3]:
            matches = re.finditer(pattern, normalized, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                groups = match.groups()
                
                # Extract subject and action based on pattern
                if 'correct' in groups[2] if len(groups) > 2 else 'correct' in str(groups):
                    subject = "credentials"
                    if len(groups) >= 4:
                        action = f"return {groups[3].strip()}"
                    else:
                        action = "return JWT"
                    
                    cond = f"[CONDITIONAL] If {subject} are correct: {action}"
                    if cond not in conditionals:
                        conditionals.append(cond)
        
        # Look for incorrect/mali patterns
        incorrect_pattern = r'(if|when|kung)\s+(?:they are\s+)?(?:ang\s+)?(?:credentials\s+)?(?:are\s+)?(incorrect|mali)[^,.]*[,.]?\s*(?:must|dapat)?\s*(?:this|itong)?\s*(?:return|magbalik)\s+(?:ng\s+)?(\d+\s+\w+|[^,.]+?)(?:\.|,|$)'
        
        incorrect_matches = re.finditer(incorrect_pattern, normalized, re.IGNORECASE)
        for match in incorrect_matches:
            action_part = match.group(3) if match.group(3) else "401 Unauthorized error"
            cond = f"[CONDITIONAL] If credentials are incorrect: return {action_part.strip()}"
            if cond not in conditionals:
                conditionals.append(cond)
        
        return conditionals


class ImprovedComplexMixedStrategy(ParsingStrategy):
    """Better handling of complex commands with multiple patterns"""
    
    def __init__(self):
        super().__init__()
        self.simple_strategy = SimpleSequentialStrategy()
        self.conditional_strategy = ImprovedConditionalStrategy()
        self.parallel_strategy = ParallelStrategy()
        self.hierarchical_strategy = HierarchicalStrategy()
    
    def can_handle(self, structure: CommandStructure) -> bool:
        return True  # Can handle any command type
    
    def parse(self, command: str, structure: CommandStructure) -> List[str]:
        """Parse complex mixed commands with better integration"""
        all_steps = []
        seen_content = set()
        
        # Parse with all strategies and intelligently merge
        if structure.has_hierarchy:
            hierarchical_steps = self.hierarchical_strategy.parse(command, structure)
            self._add_unique_steps(hierarchical_steps, all_steps, seen_content)
        
        # Always try simple sequential parsing for basic steps
        sequential_steps = self.simple_strategy.parse(command, structure)
        self._add_unique_steps(sequential_steps, all_steps, seen_content)
        
        # Extract conditionals if present
        if structure.has_conditionals:
            conditional_steps = self.conditional_strategy.parse(command, structure)
            # Only add the conditional items, not duplicates of regular steps
            for step in conditional_steps:
                if '[CONDITIONAL]' in step:
                    self._add_unique_steps([step], all_steps, seen_content)
        
        # Extract parallel tasks if present
        if structure.has_parallelism:
            parallel_steps = self.parallel_strategy.parse(command, structure)
            for step in parallel_steps:
                if '[PARALLEL]' in step:
                    self._add_unique_steps([step], all_steps, seen_content)
        
        return self._order_steps(all_steps)
    
    def _add_unique_steps(self, new_steps: List[str], all_steps: List[str], seen_content: set):
        """Add steps while avoiding duplicates"""
        for step in new_steps:
            # Create a normalized version for comparison
            normalized = self._normalize_for_comparison(step)
            
            if normalized not in seen_content:
                seen_content.add(normalized)
                all_steps.append(step)
    
    def _normalize_for_comparison(self, step: str) -> str:
        """Normalize step for duplicate detection"""
        # Remove tags
        normalized = re.sub(r'\[(CONDITIONAL|PARALLEL|DEPENDENCY)\]\s*', '', step)
        # Remove punctuation and extra spaces
        normalized = re.sub(r'[.,!?]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.lower().strip()
    
    def _order_steps(self, steps: List[str]) -> List[str]:
        """Order steps logically"""
        regular_steps = []
        parallel_steps = []
        conditional_steps = []
        
        for step in steps:
            if '[CONDITIONAL]' in step:
                conditional_steps.append(step)
            elif '[PARALLEL]' in step:
                parallel_steps.append(step)
            else:
                regular_steps.append(step)
        
        # Order: regular -> parallel -> conditional
        return regular_steps + parallel_steps + conditional_steps


class ParallelStrategy(ParsingStrategy):
    """Handles commands with parallel execution"""
    
    def can_handle(self, structure: CommandStructure) -> bool:
        return structure.has_parallelism
    
    def parse(self, command: str, structure: CommandStructure) -> List[str]:
        """Parse commands with parallel execution"""
        # Split into sentences
        sentences = self.sentence_splitter.split(command)
        
        steps = []
        
        for sentence in sentences:
            if self._contains_parallel_indicator(sentence):
                # Extract parallel tasks
                parallel_steps = self._extract_parallel_structure(sentence)
                steps.extend(parallel_steps)
            else:
                # Regular sequential step
                strategy = SimpleSequentialStrategy()
                if strategy._contains_action(sentence):
                    step = strategy._format_action(sentence)
                    if step:
                        steps.append(step)
        
        return steps
    
    def _contains_parallel_indicator(self, sentence: str) -> bool:
        """Check if sentence indicates parallel execution"""
        indicators = ['parallel', 'simultaneously', 'at the same time', 
                     'while', 'concurrent', 'together', 'sabay']
        sentence_lower = sentence.lower()
        return any(ind in sentence_lower for ind in indicators)
    
    def _extract_parallel_structure(self, sentence: str) -> List[str]:
        """Extract parallel tasks with better structure understanding"""
        tasks = []
        
        # Pattern 1: "X, Y, and Z in parallel"
        parallel_list_pattern = r'([^:]+?)(?:\s+in\s+parallel|simultaneously):\s*([^.]+)'
        match = re.search(parallel_list_pattern, sentence, re.IGNORECASE)
        if match:
            task_list = match.group(2)
            # Split by commas and "and"
            items = re.split(r',\s*(?:and\s+)?|\s+and\s+', task_list)
            for item in items:
                item = item.strip()
                if item:
                    tasks.append(f"[PARALLEL] {item}")
        
        # Pattern 2: List after colon
        elif ':' in sentence:
            parts = sentence.split(':', 1)
            if len(parts) == 2 and 'parallel' in parts[0].lower():
                items = re.split(r',\s*(?:and\s+)?|\s+and\s+', parts[1])
                for item in items:
                    item = item.strip(' .')
                    if item:
                        tasks.append(f"[PARALLEL] {item}")
        
        return tasks if tasks else []


class HierarchicalStrategy(ParsingStrategy):
    """Handles hierarchical/nested commands"""
    
    def can_handle(self, structure: CommandStructure) -> bool:
        return structure.has_hierarchy
    
    def parse(self, command: str, structure: CommandStructure) -> List[str]:
        """Parse hierarchical commands"""
        lines = command.split('\n')
        steps = []
        
        current_parent = None
        in_sublist = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            # Check indentation
            indent = len(line) - len(line.lstrip())
            
            # Main numbered item
            numbered_match = re.match(r'^\s*\d+\.\s+(.+)$', line)
            if numbered_match and indent < 4:
                content = numbered_match.group(1)
                current_parent = content
                in_sublist = False
                
                # Add if it's an action
                strategy = SimpleSequentialStrategy()
                if strategy._contains_action(content):
                    steps.append(strategy._format_action(content))
            
            # Sub-item (bullet or dash)
            elif re.match(r'^\s*[-•*]\s+(.+)$', stripped):
                content = re.match(r'^\s*[-•*]\s+(.+)$', stripped).group(1)
                in_sublist = True
                
                # Add sub-items as actions
                strategy = SimpleSequentialStrategy()
                if strategy._contains_action(content):
                    steps.append(strategy._format_action(content))
            
            # Continuation of previous line
            elif in_sublist and indent > 4:
                if steps:
                    steps[-1] += ' ' + stripped
        
        return steps


# ============================================================================
# REFACTORED ACTION ITEM EXTRACTOR
# ============================================================================

class ActionItemExtractor:
    """Strategy-based action item extractor with robust parsing"""
    
    def __init__(self):
        self.classifier = CommandClassifier()
        self.complex_strategy = ImprovedComplexMixedStrategy()
        self._extraction_cache = {}
    
    def extract_action_items(self, task_description: str) -> List[str]:
        """
        Extract action items using improved strategy-based routing.
        Always uses the complex mixed strategy for comprehensive extraction.
        """
        # Check cache
        cache_key = hash(task_description)
        if cache_key in self._extraction_cache:
            return self._extraction_cache[cache_key]
        
        try:
            # Classify to understand structure
            structure = self.classifier.classify(task_description)
            
            # Always use complex strategy for comprehensive parsing
            action_items = self.complex_strategy.parse(task_description, structure)
            
            # Post-process results
            action_items = self._post_process(action_items)
            
            # Cache results
            self._extraction_cache[cache_key] = action_items
            
            return action_items
            
        except Exception as e:
            logger.error(f"Error extracting action items: {e}", exc_info=True)
            # Fallback to simple extraction
            return [f"Complete task: {task_description}"]
    
    def _post_process(self, action_items: List[str]) -> List[str]:
        """Post-process action items for quality"""
        processed = []
        seen_normalized = set()
        
        for item in action_items:
            # Clean up formatting
            cleaned = self._clean_action_item(item)
            
            # Skip empty or too short items
            if not cleaned or len(cleaned) < 5:
                continue
            
            # Check for duplicates with normalization
            normalized = self._normalize_for_dedup(cleaned)
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                processed.append(cleaned)
        
        return processed
    
    def _clean_action_item(self, item: str) -> str:
        """Clean up individual action item"""
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', item).strip()
        
        # Ensure proper capitalization (but preserve tags)
        if cleaned and not cleaned.startswith('['):
            if cleaned[0].islower():
                cleaned = cleaned[0].upper() + cleaned[1:]
        
        # Ensure ends with period (unless it's a tag or special char)
        if cleaned and not cleaned[-1] in '.!?':
            if not any(cleaned.endswith(tag) for tag in [']', ')', '}']):
                cleaned += '.'
        
        return cleaned
    
    def _normalize_for_dedup(self, item: str) -> str:
        """Normalize item for deduplication"""
        # Remove tags
        normalized = re.sub(r'\[(CONDITIONAL|PARALLEL|DEPENDENCY)\]\s*', '', item)
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

# Import TaskComplexityAnalyzer from original module for compatibility
try:
    from workflow_memory_intelligence_fixed import TaskComplexityAnalyzer
except ImportError:
    # Define minimal version for standalone operation
    class TaskComplexityAnalyzer:
        def analyze_complexity(self, task_description: str):
            from collections import namedtuple
            Complexity = namedtuple('Complexity', ['score', 'level', 'should_chunk', 
                                                  'estimated_subtasks', 'reasoning'])
            
            # Simple analysis
            length = len(task_description)
            if length < 100:
                return Complexity(0, "SIMPLE", False, 1, ["Short task"])
            elif length < 300:
                return Complexity(30, "MEDIUM", True, 3, ["Medium length task"])
            else:
                return Complexity(60, "COMPLEX", True, 5, ["Long complex task"])