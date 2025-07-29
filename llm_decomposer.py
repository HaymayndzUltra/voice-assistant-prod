import requests
import json
import logging

class LLMDecomposer:
    """
    Decomposes high-level user commands into subtasks using a local LLM (Ollama API).
    """
    def __init__(self, model_url="http://localhost:11434/api/generate", model_name="phi"):
        self.model_url = model_url
        self.model_name = model_name
        self.logger = logging.getLogger("LLMDecomposer")

    def decompose(self, user_command: str) -> list:
        prompt = f"""
        Decompose the following high-level user command into a JSON array of subtasks. Each subtask should have:
        - id: unique string
        - description: what to do
        - priority: 1-5
        - dependencies: list of subtask ids (if any)
        - estimated_duration: minutes
        
        User Command: {user_command}
        
        Output only the JSON array, no explanation.
        """
        try:
            response = requests.post(
                self.model_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=20
            )
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                # Try to extract JSON array
                start = text.find("[")
                end = text.rfind("]")
                if start != -1 and end != -1:
                    json_str = text[start:end+1]
                    return json.loads(json_str)
                else:
                    self.logger.warning("No JSON array found in LLM output.")
                    return []
            else:
                self.logger.error(f"Ollama API error: {response.status_code}")
                return []
        except Exception as e:
            self.logger.error(f"LLM decomposition error: {e}")
            return [] 