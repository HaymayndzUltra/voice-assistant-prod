"""
Hybrid ActionItemExtractor - High-Performance Task Decomposition Engine
Combines rule-based parsing for simple tasks with LLM parsing for complex tasks
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
logger = logging.getLogger(__name__)

class ActionItemExtractor:
    """Hybrid task decomposer with rule-based and LLM-based parsing engines"""

    def __init__(self):
        """Initialize hybrid parsing system with both rule-based and LLM engines.

        The extractor now implements a "triage" approach:
        1. Calculate complexity score for incoming task
        2. Route to appropriate parsing engine:
           - Fast Lane: Rule-based parser for simple sequential tasks
           - Power Lane: LLM-based parser for complex tasks with conditionals/parallelism
        """
        try:
            from ollama_client import call_ollama, SYSTEM_PROMPTS
            self.ollama_available = True
            self.call_ollama = call_ollama
            self.system_prompts = SYSTEM_PROMPTS
            logger.info('✅ Ollama client available for LLM parsing')
        except ImportError as e:
            self.ollama_available = False
            logger.warning(f'⚠️ Ollama client not available: {e}')
        self.SIMPLE_THRESHOLD = 3
        self.COMPLEX_THRESHOLD = 6
        self.simple_indicators = ['fix typo', 'update comment', 'change variable', 'add import', 'remove unused', 'format code', 'simple', 'quick', 'minor', 'gawa', 'gawin', 'maliit', 'mabilis', 'ayusin lang']
        self.complex_indicators = ['implement', 'create', 'build', 'develop', 'design', 'architecture', 'system', 'framework', 'comprehensive', 'if', 'when', 'kung', 'kapag', 'parallel', 'simultaneously', 'database', 'authentication', 'integration', 'deployment']
        self.conditional_indicators = ['if', 'when', 'unless', 'kung', 'kapag', 'otherwise', 'else', 'then', 'in case', 'should', 'might', 'could']
        self.parallel_indicators = ['simultaneously', 'at the same time', 'in parallel', 'concurrently', 'while', 'sabay', 'kasabay']
        self.sequential_markers = {'first': '[SEQ_1]', 'initially': '[SEQ_1]', 'start': '[SEQ_1]', 'begin': '[SEQ_1]', 'setup': '[SEQ_1]', 'prepare': '[SEQ_1]', 'then': '[SEQ_2]', 'next': '[SEQ_2]', 'after': '[SEQ_2]', 'finally': '[SEQ_3]', 'lastly': '[SEQ_3]', 'complete': '[SEQ_3]', 'una': '[SEQ_1]', 'simula': '[SEQ_1]', 'sunod': '[SEQ_2]', 'pangatlo': '[SEQ_3]', 'wakas': '[SEQ_3]', 'tapusin': '[SEQ_3]'}
        self.action_verbs = ['create', 'make', 'build', 'update', 'modify', 'fix', 'repair', 'delete', 'remove', 'test', 'check', 'verify', 'configure', 'setup', 'install', 'deploy', 'gumawa', 'ayusin', 'gawin']
        logger.info('✅ Hybrid ActionItemExtractor initialized')

    def extract_action_items(self, task_description: str) -> List[str]:
        """
        Main extraction engine with intelligent routing between rule-based and LLM parsing.
        
        Args:
            task_description: Natural language task description
            
        Returns:
            List of actionable steps
        """
        logger.info(f'🎯 Processing task: {task_description[:50]}...')
        complexity_score = self._calculate_complexity_score(task_description)
        if complexity_score <= self.SIMPLE_THRESHOLD:
            logger.info(f'🚀 Fast Lane: Rule-based parsing (complexity: {complexity_score})')
            return self._parse_with_rules(task_description)
        else:
            logger.info(f'🧠 Power Lane: LLM-based parsing (complexity: {complexity_score})')
            return self._parse_with_llm(task_description)

    def _calculate_complexity_score(self, task: str) -> int:
        """
        Calculate complexity score to determine parsing strategy.
        
        Returns:
            Integer score (0-10, higher = more complex)
        """
        task_lower = task.lower()
        score = 0
        if len(task) > 100:
            score += 1
        if len(task) > 200:
            score += 1
        simple_count = sum((1 for indicator in self.simple_indicators if indicator in task_lower))
        score -= simple_count
        complex_count = sum((1 for indicator in self.complex_indicators if indicator in task_lower))
        score += complex_count * 2
        conditional_count = sum((1 for indicator in self.conditional_indicators if indicator in task_lower))
        score += conditional_count * 3
        parallel_count = sum((1 for indicator in self.parallel_indicators if indicator in task_lower))
        score += parallel_count * 3
        word_count = len(task.split())
        if word_count > 20:
            score += 1
        if word_count > 40:
            score += 2
        score = max(0, min(10, score))
        logger.info(f'📊 Complexity analysis: {score}/10 (simple: {simple_count}, complex: {complex_count}, conditional: {conditional_count}, parallel: {parallel_count})')
        return score

    def _parse_with_rules(self, task: str) -> List[str]:
        """
        Fast rule-based parser for simple sequential tasks.
        
        Args:
            task: Task description
            
        Returns:
            List of extracted steps
        """
        logger.info('⚡ Using rule-based parsing...')
        steps = []
        normalized = task
        for marker, token in self.sequential_markers.items():
            normalized = re.sub(f'\\b{re.escape(marker)}\\b', token, normalized, flags=re.IGNORECASE)
        sentences = re.split('[.!?;]', normalized)
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            has_action = any((verb in sentence.lower() for verb in self.action_verbs))
            if has_action:
                cleaned = sentence
                for token in ['[SEQ_1]', '[SEQ_2]', '[SEQ_3]']:
                    cleaned = cleaned.replace(token, '').strip()
                if len(cleaned) > 5:
                    steps.append(cleaned)
        if not steps:
            if any((verb in task.lower() for verb in ['create', 'gumawa', 'make'])):
                steps.append(f'Create the required component')
            if any((verb in task.lower() for verb in ['test', 'subukan', 'check'])):
                steps.append(f'Test the implementation')
            if any((verb in task.lower() for verb in ['deploy', 'release'])):
                steps.append(f'Deploy the changes')
        logger.info(f'✅ Rule-based parsing extracted {len(steps)} steps')
        return steps

    def _parse_with_llm(self, task: str) -> List[str]:
        """
        Powerful LLM-based parser for complex tasks with conditionals and parallelism.
        
        Args:
            task: Task description
            
        Returns:
            List of extracted steps
        """
        logger.info('🧠 Using LLM-based parsing...')
        if not self.ollama_available:
            logger.warning('⚠️ Ollama not available, falling back to rule-based parsing')
            return self._parse_with_rules(task)
        prompt = f'Break down this task into clear, actionable steps:\n\nTASK: {task}\n\nRequirements:\n- Each step should be specific and actionable\n- Include conditional logic with "IF condition: then action" format\n- Mark parallel tasks with "PARALLEL:" prefix\n- Support both English and Filipino/Taglish\n- Estimate 5-30 minutes per step'
        try:
            response = self.call_ollama(prompt, self.system_prompts['task_decomposition'])
            if not response:
                logger.error('❌ No response from LLM, falling back to rules')
                return self._parse_with_rules(task)
            if 'steps' in response:
                steps = response['steps']
                logger.info(f'✅ LLM parsing extracted {len(steps)} steps')
                return steps
            elif 'raw_response' in response:
                raw_text = response['raw_response']
                steps = self._extract_steps_from_text(raw_text)
                logger.info(f'✅ Extracted {len(steps)} steps from raw LLM response')
                return steps
            else:
                logger.warning('⚠️ Invalid LLM response format')
                return self._parse_with_rules(task)
        except Exception as e:
            logger.error(f'❌ Error in LLM parsing: {e}')
            return self._parse_with_rules(task)

    def _extract_steps_from_text(self, text: str) -> List[str]:
        """
        Extract steps from unstructured LLM text response.
        
        Args:
            text: Raw text from LLM
            
        Returns:
            List of extracted steps
        """
        steps = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.lower().startswith(('task:', 'steps:', 'requirements:')):
                continue
            cleaned = re.sub('^[\\d\\.\\-\\*\\+]\\s*', '', line).strip()
            if any((verb in cleaned.lower() for verb in self.action_verbs)):
                steps.append(cleaned)
            elif len(cleaned) > 10 and any((word in cleaned.lower() for word in ['if', 'parallel', 'then', 'configure', 'setup'])):
                steps.append(cleaned)
        return steps

def get_parsing_engine_name(complexity_score: int) -> str:
    """Get the name of the parsing engine used for reporting"""
    if complexity_score <= 3:
        return 'Rule-Based'
    else:
        return 'LLM'
if __name__ == '__main__':
    extractor = ActionItemExtractor()
    simple_task = 'Fix typo in the documentation'
    logger.info(f'\n🧪 Testing simple task: {simple_task}')
    simple_steps = extractor.extract_action_items(simple_task)
    logger.info('Steps:', simple_steps)
    complex_task = 'Create a login system with authentication and error handling. If credentials are correct, redirect to dashboard. If incorrect, show error message.'
    logger.info(f'\n🧪 Testing complex task: {complex_task}')
    complex_steps = extractor.extract_action_items(complex_task)
    logger.info('Steps:', complex_steps)