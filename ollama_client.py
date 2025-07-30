"""
Ollama Client for LLM-based Task Parsing
Provides robust communication with Ollama API for complex task decomposition
"""
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
logger = logging.getLogger(__name__)

@dataclass
class OllamaConfig:
    """Configuration for Ollama client"""
    base_url: str = 'http://localhost:11434'
    model: str = 'phi3:instruct'
    timeout: int = 60
    max_retries: int = 2
    stream: bool = False

class OllamaClient:
    """Robust Ollama client for LLM-based task parsing"""

    def __init__(self, config: Optional[OllamaConfig]=None):
        """TODO: Add description for __init__."""
        self.config = config or OllamaConfig()
        self.session = requests.Session()

    def call_ollama(self, prompt: str, system_prompt: str='') -> Optional[Dict[str, Any]]:
        """
        Send a prompt to Ollama and parse JSON response

        Args:
            prompt: User prompt for task decomposition
            system_prompt: System instructions for the LLM

        Returns:
            Parsed JSON response or None if failed
        """
        payload = {'model': self.config.model, 'prompt': prompt, 'stream': self.config.stream, 'format': 'json', 'options': {'temperature': 0.2, 'top_p': 0.8, 'num_predict': 1024, 'num_ctx': 2048, 'repeat_penalty': 1.1, 'stop': ['\n\n\n', '---', '###']}}
        if system_prompt:
            payload['system'] = system_prompt
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f'🤖 Calling Ollama (attempt {attempt + 1}/{self.config.max_retries})...')
                response = self.session.post(f'{self.config.base_url}/api/generate', json=payload, timeout=self.config.timeout)
                response.raise_for_status()
                result = response.json()
                if 'response' not in result:
                    logger.error("❌ Ollama response missing 'response' field")
                    continue
                ollama_response = result['response']
                if not isinstance(ollama_response, str):
                    logger.warning(f'⚠️ Unexpected response type: {type(ollama_response)}')
                    return {'raw_response': str(ollama_response), 'error': 'non_string_response'}
                try:
                    parsed_response = json.loads(ollama_response)
                    logger.info('✅ Successfully parsed Ollama JSON response')
                    return parsed_response
                except json.JSONDecodeError as e:
                    logger.warning(f'⚠️ Failed to parse JSON response: {e}')
                    return {'raw_response': ollama_response, 'error': 'json_parse_failed'}
            except requests.exceptions.ConnectionError:
                logger.error(f'❌ Connection error to Ollama (attempt {attempt + 1})')
                if attempt == self.config.max_retries - 1:
                    logger.error('❌ Max retries exceeded - Ollama unavailable')
                    return None
            except requests.exceptions.Timeout:
                logger.error(f'❌ Timeout calling Ollama (attempt {attempt + 1})')
                if attempt == self.config.max_retries - 1:
                    logger.error('❌ Max retries exceeded - Ollama timeout')
                    return None
            except Exception as e:
                logger.error(f'❌ Unexpected error calling Ollama: {e}')
                return None
        return None

    def test_connection(self) -> bool:
        """Test if Ollama is available and responding"""
        try:
            response = self.session.get(f'{self.config.base_url}/api/tags', timeout=5)
            response.raise_for_status()
            logger.info('✅ Ollama connection test successful')
            return True
        except Exception as e:
            logger.error(f'❌ Ollama connection test failed: {e}')
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            response = self.session.get(f'{self.config.base_url}/api/tags', timeout=10)
            response.raise_for_status()
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            logger.info(f'📋 Available Ollama models: {models}')
            return models
        except Exception as e:
            logger.error(f'❌ Failed to get available models: {e}')
            return []
_ollama_client = None

def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client

def call_ollama(prompt: str, system_prompt: str='') -> Optional[Dict[str, Any]]:
    """Convenience function to call Ollama with global client"""
    client = get_ollama_client()
    return client.call_ollama(prompt, system_prompt)
SYSTEM_PROMPTS = {'task_decomposition': 'You are an expert task decomposition assistant. Your job is to break down complex tasks into clear, actionable steps.\n\nRULES:\n1. Always respond with valid JSON in this exact format:\n{\n  "steps": ["step 1 description", "step 2 description", ...],\n  "complexity": "COMPLEX|MEDIUM|SIMPLE",\n  "estimated_duration": 60,\n  "reasoning": ["why this task is complex", "what makes it challenging"]\n}\n\n2. Each step should be:\n   - Specific and actionable\n   - Roughly 5-30 minutes of work\n   - Independent when possible\n   - Clear about what success looks like\n\n3. For conditionals (if/when/kung), include them as: "IF condition: then action"\n4. For parallel tasks, prefix with "PARALLEL:" when tasks can be done simultaneously\n5. Be practical and realistic about time estimates\n6. Support both English and Filipino/Taglish input\n\nFocus on creating a clear, executable plan.', 'simple_validation': 'You are a task complexity validator. Determine if a task is simple enough for rule-based parsing.\n\nRULES:\n1. Always respond with valid JSON:\n{\n  "is_simple": true|false,\n  "confidence": 0.8,\n  "reasoning": "explanation of decision"\n}\n\n2. Consider SIMPLE if task:\n   - Has clear sequential steps (first, then, next)\n   - No complex conditionals or branching\n   - Single domain/technology\n   - Can be done in under 30 minutes\n\n3. Consider COMPLEX if task:\n   - Has conditional logic (if/when/kung)\n   - Multiple parallel workflows\n   - Cross-system integration\n   - Requires decision-making\n\nBe conservative - when in doubt, mark as complex.'}
if __name__ == '__main__':
    client = OllamaClient()
    logger.info('🧪 Testing Ollama connection...')
    if client.test_connection():
        logger.info('✅ Connection successful')
        logger.info('\n📋 Available models:')
        models = client.get_available_models()
        for model in models:
            logger.info(f'  - {model}')
        logger.info('\n🤖 Testing task decomposition...')
        test_prompt = 'Create a login system with authentication and error handling'
        result = client.call_ollama(test_prompt, SYSTEM_PROMPTS['task_decomposition'])
        if result:
            logger.info('✅ LLM response received:')
            logger.info(json.dumps(result, indent=2))
        else:
            logger.info('❌ Failed to get LLM response')
    else:
        logger.info('❌ Connection failed - is Ollama running?')