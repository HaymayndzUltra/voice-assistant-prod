from main_pc_code.src.core.base_agent import BaseAgent
#!/usr/bin/env python3
"""
Lazy Voting System
-----------------
An efficient voting system for LLMs that optimizes resource usage by:
1. Using only a subset of models initially (2 out of 3)
2. Only consulting the third model when necessary (tie-breaking)
3. Rotating models to balance load and prevent overuse

This system is designed to work with the Enhanced Model Router.
"""

import json
import logging
import random
import time
import threading
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Configure logging
LOG_PATH = join_path("logs", "lazy_voting.log")
Path(LOG_PATH).parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class LazyVotingSystem(BaseAgent):
    """
    Implements the lazy voting strategy for LLM model management.
    Integrates with the Enhanced Model Router for efficient model usage.
    """
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="LazyVoting")
        """
        Initialize the lazy voting system
        
        Args:
            model_config: Optional configuration dict with model details
        """
        # Default model configuration with priorities
        self.model_config = model_config or {
            "wizardcoder": {
                "path": "./wizardcoder/wizardcoder-python-13b-v1.0.Q4_K_M.gguf",
                "capabilities": ["code", "structured", "python"],
                "priority": 1,  # Higher priority = more likely to be selected first
                "weight": 2.0,  # Higher weight = more influential in voting
                "best_for": ["code_generator", "test_generator"],
                "vram_usage": 8000,  # MB
                "loaded": False
            },
            "deepseek": {
                "path": "./deepseek-coder/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
                "capabilities": ["code", "reasoning", "math"],
                "priority": 2,
                "weight": 1.5,
                "best_for": ["code_generator", "auto_fixer"],
                "vram_usage": 4500,  # MB
                "loaded": False
            },
            "llama3": {
                "path": "./llama3-instruct/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
                "capabilities": ["reasoning", "general", "creative"],
                "priority": 3,
                "weight": 1.0,
                "best_for": ["auto_fixer", "error_pattern_memory"],
                "vram_usage": 4500,  # MB
                "loaded": False
            }
        }
        
        # Statistics and metadata
        self.usage_stats = {model: 0 for model in self.model_config}
        self.last_used = {model: 0 for model in self.model_config}
        self.agreement_stats = {}  # Track model agreement patterns
        self.vote_history = []
        self.loaded_models = set()
        
        # Resource management
        self.available_vram = 24000  # Default 24GB for RTX 4090
        self.max_simultaneous_models = 3  # Maximum models to have loaded at once
        self.model_locks = {model: threading.Lock() for model in self.model_config}
        
        # Cache for similar requests
        self.response_cache = {}
        self.cache_lock = threading.Lock()
        self.cache_ttl = 3600  # 1 hour cache lifetime
        
        logging.info("[LazyVoting] System initialized with models: " + 
                    ", ".join(self.model_config.keys()))
    
    def get_request_hash(self, prompt: str) -> str:
        """Generate a hash for caching similar requests"""
        # Normalize whitespace and lowercase
        normalized = re.sub(r'\s+', ' ', prompt.lower().strip())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def check_cache(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Check if we have a cached response for a similar request"""
        request_hash = self.get_request_hash(prompt)
        with self.cache_lock:
            if request_hash in self.response_cache:
                cache_entry = self.response_cache[request_hash]
                # Check if entry is still valid
                if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                    logging.info(f"[LazyVoting] Cache hit for request hash {request_hash[:8]}")
                    return cache_entry["response"]
                else:
                    # Expired entry
                    del self.response_cache[request_hash]
        return None
    
    def update_cache(self, prompt: str, response: Dict[str, Any]) -> None:
        """Update the cache with a new response"""
        request_hash = self.get_request_hash(prompt)
        with self.cache_lock:
            self.response_cache[request_hash] = {
                "timestamp": time.time(),
                "response": response
            }
            
            # Clean expired cache entries if cache is getting large
            if len(self.response_cache) > 1000:
                current_time = time.time()
                expired_keys = [
                    k for k, v in self.response_cache.items() 
                    if current_time - v["timestamp"] > self.cache_ttl
                ]
                for k in expired_keys:
                    del self.response_cache[k]

    def select_models_for_task(self, task_type: str, agent: str = None) -> List[str]:
        """
        Select the most appropriate models for a given task based on capabilities
        and workload distribution.
        
        Args:
            task_type: Type of task (code, reasoning, general, etc.)
            agent: Optional agent name requesting the models
            
        Returns:
            List of selected model names in priority order
        """
        all_models = list(self.model_config.keys())
        
        # Filter models by capability match
        suitable_models = []
        for model, config in self.model_config.items():
            # Check if model is good for this task type
            if task_type in config["capabilities"]:
                # Bonus if model is specifically good for the requesting agent
                priority_boost = 0
                if agent and agent in config.get("best_for", []):
                    priority_boost = 2
                
                suitable_models.append((model, config["priority"] + priority_boost))
        
        # If no suitable models, use all available
        if not suitable_models:
            suitable_models = [(model, config["priority"]) for model, config in self.model_config.items()]
        
        # Sort by priority (higher priority first)
        suitable_models.sort(key=lambda x: x[1])
        
        # Get sorted model names
        sorted_models = [m[0] for m in suitable_models]
        
        # If we have more than 2 models, use workload distribution to rotate them
        if len(sorted_models) > 2:
            # Adjust based on usage stats to prevent overuse
            usage_values = [self.usage_stats[model] for model in sorted_models]
            max_usage = max(usage_values) if usage_values else 1
            
            # If some models are used significantly more than others, adjust the order
            if max_usage > 10 and max(usage_values) > 2 * min(usage_values):
                # Introduce some randomness to occasionally prioritize less-used models
                if random.random() < 0.3:  # 30% chance to prioritize less-used models
                    sorted_models.sort(key=lambda m: self.usage_stats[m])
        
        return sorted_models
    
    def ensure_models_loaded(self, models: List[str]) -> List[str]:
        """
        Ensure the specified models are loaded, managing VRAM resources.
        
        Args:
            models: List of model names to ensure are loaded
            
        Returns:
            List of successfully loaded models
        """
        # If all requested models are already loaded, no action needed
        if all(model in self.loaded_models for model in models):
            return models
        
        # Calculate VRAM needed for requested models not yet loaded
        needed_vram = sum(
            self.model_config[model]["vram_usage"] 
            for model in models 
            if model not in self.loaded_models
        )
        
        # If we need to free VRAM for new models
        current_vram_usage = sum(
            self.model_config[model]["vram_usage"]
            for model in self.loaded_models
        )
        
        available = self.available_vram - current_vram_usage
        
        loaded_models = list(self.loaded_models)
        
        # If we need more VRAM, unload least recently used models
        if needed_vram > available:
            # Sort loaded models by last usage time (oldest first)
            loaded_not_requested = [m for m in loaded_models if m not in models]
            loaded_not_requested.sort(key=lambda m: self.last_used[m])
            
            # Unload models until we have enough VRAM
            for model_to_unload in loaded_not_requested:
                if needed_vram <= available:
                    break
                    
                # Unload this model
                with self.model_locks[model_to_unload]:
                    self.loaded_models.remove(model_to_unload)
                    vram_freed = self.model_config[model_to_unload]["vram_usage"]
                    available += vram_freed
                    self.model_config[model_to_unload]["loaded"] = False
                    logging.info(f"[LazyVoting] Unloaded model {model_to_unload} to free {vram_freed} MB VRAM")
        
        # Load all requested models that aren't loaded yet
        successfully_loaded = []
        for model in models:
            if model in self.loaded_models:
                successfully_loaded.append(model)
                continue
                
            # Skip if we don't have enough VRAM for this model
            model_vram = self.model_config[model]["vram_usage"]
            if model_vram > available:
                logging.warning(f"[LazyVoting] Not enough VRAM to load {model}, needed {model_vram}MB, available {available}MB")
                continue
                
            # Load the model
            with self.model_locks[model]:
                # This is where you would actually load the model - here we just simulate
                logging.info(f"[LazyVoting] Loading model {model} using {model_vram} MB VRAM")
                self.loaded_models.add(model)
                self.model_config[model]["loaded"] = True
                available -= model_vram
                successfully_loaded.append(model)
                
        return successfully_loaded

    def execute_model(self, model: str, prompt: str, task_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute inference on a specific model (simulated function)
        
        In a real implementation, this would invoke the model inference
        """
        # Simulate model execution - in a real system this would call the actual model
        logging.info(f"[LazyVoting] Executing model {model} for {task_data.get('type', 'general')} task")
        
        # Update usage statistics
        self.usage_stats[model] += 1
        self.last_used[model] = time.time()
        
        # In a real implementation, you would call the actual model here
        # For simulation, we'll just return a mock response
        return {
            "model": model,
            "response": f"Response from {model} for task: {prompt[:20]}...",
            "confidence": random.uniform(0.7, 0.95)
        }
    
    def compare_responses(self, responses: List[Dict[str, Any]]) -> float:
        """
        Compare responses from different models to determine agreement score
        
        Args:
            responses: List of model responses
            
        Returns:
            Agreement score between 0 (total disagreement) and 1 (perfect agreement)
        """
        if len(responses) < 2:
            return 1.0  # Single response always agrees with itself
            
        # In a real implementation, you would use semantic similarity or other techniques
        # For simulation, we'll use a random score
        return random.uniform(0.5, 1.0)
    
    def get_consensus(self, responses: List[Dict[str, Any]], agreement_threshold: float = 0.8) -> Dict[str, Any]:
        """
        Determine the consensus response based on model weights and agreement
        
        Args:
            responses: List of model responses
            agreement_threshold: Threshold to determine if models agree
            
        Returns:
            Consensus response with metadata
        """
        if len(responses) == 1:
            return {
                "response": responses[0]["response"],
                "model_used": responses[0]["model"],
                "confidence": responses[0]["confidence"],
                "consensus": True,
                "agreement_score": 1.0,
                "models_consulted": [responses[0]["model"]]
            }
            
        # Get agreement score between responses
        agreement_score = self.compare_responses(responses)
        
        # Update agreement statistics
        model_pair = tuple(sorted(r["model"] for r in responses))
        if model_pair not in self.agreement_stats:
            self.agreement_stats[model_pair] = []
        self.agreement_stats[model_pair].append(agreement_score)
        
        # Get weighted scores for each response
        weighted_responses = []
        for response in responses:
            model = response["model"]
            weight = self.model_config[model]["weight"]
            confidence = response["confidence"]
            weighted_score = weight * confidence
            weighted_responses.append((response, weighted_score))
        
        # Sort by weighted score (higher is better)
        weighted_responses.sort(key=lambda x: x[1], reverse=True)
        
        # If agreement is high, use the highest weighted response
        if agreement_score >= agreement_threshold:
            winning_response = weighted_responses[0][0]
            return {
                "response": winning_response["response"],
                "model_used": winning_response["model"],
                "confidence": winning_response["confidence"],
                "consensus": True,
                "agreement_score": agreement_score,
                "models_consulted": [r["model"] for r in responses]
            }
        else:
            # Models disagree significantly, return info about the disagreement
            return {
                "response": weighted_responses[0][0]["response"],  # Use highest weighted response
                "model_used": weighted_responses[0][0]["model"],
                "confidence": weighted_responses[0][0]["confidence"] * agreement_score,  # Reduce confidence
                "consensus": False,
                "agreement_score": agreement_score,
                "models_consulted": [r["model"] for r in responses],
                "disagreement": True
            }
    
    def lazy_vote(self, prompt: str, task_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform lazy voting to get a response using minimal necessary models
        
        Args:
            prompt: The prompt to process
            task_data: Additional task data like type, agent, etc.
            
        Returns:
            Response with metadata about models used and confidence
        """
        task_data = task_data or {}
        task_type = task_data.get("type", "general")
        agent = task_data.get("agent")
        
        # Check cache first
        cached_response = self.check_cache(prompt)
        if cached_response:
            cached_response["cached"] = True
            return cached_response
            
        # Select appropriate models for this task
        all_models = self.select_models_for_task(task_type, agent)
        
        # For lazy voting, initially use only 2 models (or 1 if that's all we have)
        initial_models = all_models[:min(2, len(all_models))]
        
        # Make sure models are loaded
        loaded_models = self.ensure_models_loaded(initial_models)
        
        if not loaded_models:
            logging.error("[LazyVoting] No models could be loaded for task")
            return {"error": "No models available", "models_consulted": []}
            
        # Execute the loaded models
        responses = []
        for model in loaded_models:
            response = self.execute_model(model, prompt, task_data)
            responses.append(response)
            
        # Get initial agreement score
        agreement_score = self.compare_responses(responses)
        
        # Determine if we need the third model as a tie-breaker
        need_tiebreaker = (
            len(loaded_models) < len(all_models)  # We have more models available
            and agreement_score < 0.7  # Models disagree significantly
            and len(loaded_models) >= 2  # We have at least 2 models to disagree
        )
        
        # If needed and available, consult the tie-breaking model
        if need_tiebreaker:
            tiebreaker_model = next(m for m in all_models if m not in loaded_models)
            
            # Load the tiebreaker model
            tiebreaker_loaded = self.ensure_models_loaded([tiebreaker_model])
            
            if tiebreaker_loaded:
                tiebreaker_response = self.execute_model(tiebreaker_model, prompt, task_data)
                responses.append(tiebreaker_response)
                logging.info(f"[LazyVoting] Used {tiebreaker_model} as tiebreaker with agreement score {agreement_score:.2f}")
        
        # Get final consensus
        result = self.get_consensus(responses)
        
        # Update cache
        self.update_cache(prompt, result)
        
        # Add to vote history
        self.vote_history.append({
            "timestamp": time.time(),
            "task_type": task_type,
            "agent": agent,
            "models_used": [r["model"] for r in responses],
            "agreement_score": result["agreement_score"],
            "winning_model": result["model_used"]
        })
        
        # Keep history to reasonable size
        if len(self.vote_history) > 1000:
            self.vote_history = self.vote_history[-1000:]
            
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the lazy voting system"""
        return {
            "models": {
                model: {
                    "usage_count": self.usage_stats[model],
                    "last_used": self.last_used[model],
                    "loaded": model in self.loaded_models,
                    "vram_usage": self.model_config[model]["vram_usage"]
                }
                for model in self.model_config
            },
            "loaded_models": list(self.loaded_models),
            "cache_size": len(self.response_cache),
            "vote_history_size": len(self.vote_history),
            "agreement_stats": {
                "+".join(pair): sum(scores) / len(scores) if scores else 0
                for pair, scores in self.agreement_stats.items()
            }
        }

# Example usage
if __name__ == "__main__":
    voting_system = LazyVotingSystem()
    
    # Example task data
    task = {
        "type": "code",
        "agent": "code_generator",
        "context": "Python script development"
    }
    
    # Example prompt
    prompt = "Write a function to find the maximum element in a list"
    
    # Run lazy voting
    result = voting_system.lazy_vote(prompt, task)
    
    # Print result
    print(json.dumps(result, indent=2))
    
    # Print stats
    print("\nSystem Stats:")
    print(json.dumps(voting_system.get_stats(), indent=2))

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
