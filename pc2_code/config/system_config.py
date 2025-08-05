# system_config.py - Centralized configuration for Voice Assistant (PC2)

import os
from typing import Any


def get_env_override(key: str, default: Any) -> Any:
    """
    Get configuration value from environment variable with fallback to default.
    Environment variables should be in format: TARGET_AGENT_NAME_HOST
    """
    return os.environ.get(key, default)

# Define PC2 settings
pc2_settings = {
    "machine_id": "pc2",
    "machine_role": "pc2_worker",
    "log_level": "INFO",
    "logs_dir": "logs",
    "main_pc_ip": get_mainpc_ip(),
    "pc2_ip": get_pc2_ip(),
    "connection": {
        "timeout": 10.0,
        "retry_attempts": 3,
        "heartbeat_interval": 5
    },
    "model_configs": {
        # Example model config, add more as needed
        "tinyllama": {
            "serving_method": "zmq_service_self_managed",
            "zmq_port": 5615,
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "ensure_loaded", "request_unload", "generate"],
            "estimated_vram_mb": 2800,
            "idle_timeout_seconds_self": 600,
            "model_path_or_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "device": "auto"
        },
        "phi3": {
            "serving_method": "http_service",
            "http_port": 11434,
            "http_bind_address": "0.0.0.0",
            "http_actions_provided": ["generate"],
            "estimated_vram_mb": 2000,
            "idle_timeout_seconds_self": 600,
            "model_path_or_name": "phi3",
            "device": "auto"
        },
        "nllb": {
            "serving_method": "zmq_service_self_managed",
            "zmq_port": 5581,
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["translate"],
            "estimated_vram_mb": 2400,
            "idle_timeout_seconds_self": 600,
            "model_path_or_name": "facebook/nllb-200-distilled-600M",
            "device": "auto"
        },
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 5563,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check", "translate"],
        "dependencies": {
            "google_translate_api": True,
            "translation_confidence": {
                "high_threshold_pattern": 0.98,
                "high_threshold_nllb": 0.85,
                "medium_threshold_nllb": 0.60,
                "low_threshold": 0.30,
                "default_google_confidence": 0.90
            }
        },
        "unified_memory_reasoning": {
            "service_name": "Unified Memory & Reasoning Service",
            "serving_method": "zmq_service_self_managed",
            "zmq_port": 5596,
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "store", "retrieve", "reason"],
            "dependencies": {
                "episodic_memory": "episodic_memory",
                "dreamworld": "dreamworld",
                "contextual_memory": "contextual_memory"
            }
        },
        "enhanced_contextual_memory": {
            "service_name": "Enhanced Contextual Memory Service",
            "serving_method": "zmq_service_self_managed",
            "zmq_port": 5596,
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "store", "retrieve", "context"],
            "memory_types": ["Code", "Query", "Error", "Response", "Decision"],
            "priority_levels": ["low", "normal", "high"]
        },
        "episodic_memory": {
            "service_name": "Episodic Memory Service",
            "serving_method": "zmq_service_self_managed",
            "zmq_port": 5629,
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "store", "retrieve", "episode"],
            "importance_thresholds": {
                "low": 0.3,
                "medium": 0.6,
                "high": 0.9
            }
        },
        "memory_decay": {
            "service_name": "Memory Decay Manager",
            "serving_method": "zmq_service_self_managed",
            "zmq_port": 5630,
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "decay", "manage"],
            "decay_rates": {
                "short_term": 0.1,
                "medium_term": 0.05,
                "long_term": 0.01
            }
        },
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 5641,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check", "analyze", "predict"],
        "model_capabilities": {
            "reasoning": True,
            "context_inference": True,
            "pattern_recognition": True
        }
    },
    "serving_method": "http_service",
    "http_port": 11434,
    "http_bind_address": "0.0.0.0",
    "http_actions_provided": ["generate"],
    "estimated_vram_mb": 2000,
    "idle_timeout_seconds_self": 600,
    "model_path_or_name": "phi3",
    "device": "auto",
    "serving_method": "zmq_service_self_managed",
    "zmq_port": 5581,
    "zmq_bind_address": "0.0.0.0",
    "zmq_actions_provided": ["translate"],
    "estimated_vram_mb": 2400,
    "idle_timeout_seconds_self": 600,
    "model_path_or_name": "facebook/nllb-200-distilled-600M",
    "device": "auto",
    "serving_method": "zmq_service_self_managed",
    "zmq_port": 5563,
    "zmq_bind_address": "0.0.0.0",
    "zmq_actions_provided": ["health_check", "translate"],
    "translation_engines": ["nllb", "google"],
    "serving_method": "zmq_service_self_managed",
    "zmq_port": 5596,
    "zmq_bind_address": "0.0.0.0",
    "zmq_actions_provided": ["health_check", "store", "retrieve"],
    "memory_types": ["short_term", "medium_term", "long_term"],
    "digital_twin": {
        "service_name": "Digital Twin Service",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 5597,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check", "twin", "sync"],
        "sync_interval": 60
    },
    "error_pattern": {
        "service_name": "Error Pattern Memory",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 5611,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check", "store", "retrieve"],
        "pattern_types": ["syntax", "runtime", "logic", "resource"]
    },
    "consolidated_translator": {
        "service_name": "Consolidated Translator Service",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 5563,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check", "translate"],
        "translation_engines": ["nllb", "google"]
    },
    # --- PHASE 1 & 2 AGENTS (INTEGRATION LAYER + PC2-SPECIFIC) ---
    "TieredResponder": {
        "service_name": "TieredResponder",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7100,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "AsyncProcessor": {
        "service_name": "AsyncProcessor",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7101,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "CacheManager": {
        "service_name": "CacheManager",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7102,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "PerformanceMonitor": {
        "service_name": "PerformanceMonitor",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7103,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "DreamWorldAgent": {
        "service_name": "DreamWorldAgent",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7104,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "UnifiedMemoryReasoningAgent": {
        "service_name": "UnifiedMemoryReasoningAgent",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7105,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "EpisodicMemoryAgent": {
        "service_name": "EpisodicMemoryAgent",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7106,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "LearningAgent": {
        "service_name": "LearningAgent",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7107,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "TutoringAgent": {
        "service_name": "TutoringAgent",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7108,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "KnowledgeBaseAgent": {
        "service_name": "KnowledgeBaseAgent",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7109,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "MemoryManager": {
        "service_name": "MemoryManager",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7110,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "ContextManager": {
        "service_name": "ContextManager",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7111,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "ExperienceTracker": {
        "service_name": "ExperienceTracker",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7112,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "ResourceManager": {
        "service_name": "ResourceManager",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7113,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "HealthMonitor": {
        "service_name": "HealthMonitor",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7114,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    },
    "TaskScheduler": {
        "service_name": "TaskScheduler",
        "serving_method": "zmq_service_self_managed",
        "zmq_port": 7115,
        "zmq_bind_address": "0.0.0.0",
        "zmq_actions_provided": ["health_check"]
    }
}

# Define Main PC settings
main_pc_settings = {
    "machine_id": "main_pc",
    "machine_role": "main_controller",
    "log_level": "INFO",
    "logs_dir": "logs",
    "model_configs": {
        "streaming-asr-main-pc": {
            "service_name": "Streaming Speech Recognition (Main PC)",
            "serving_method": "zmq_pub_health_local",
            "zmq_port": 5570,  # Input port
            "zmq_pub_port": 5571,  # Output port
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "transcribe"],
            "health_check_port": 5597,  # Shared health monitoring port
            "expected_health_response_contains": {"component_name": "ASR_Agent", "status": "healthy"},
            "health_message_timeout_seconds": 15,
            "script_path": "streaming_speech_recognition.py"
        },
        "streaming-language-analyzer-main-pc": {
            "service_name": "Streaming Language Analyzer (Main PC)",
            "serving_method": "zmq_pub_health_local",
            "zmq_port": 5571,  # Input port
            "zmq_pub_port": 5572,  # Output port
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "analyze"],
            "health_check_port": 5597,  # Shared health monitoring port
            "expected_health_response_contains": {"component_name": "Language_Analyzer", "status": "healthy"},
            "health_message_timeout_seconds": 15,
            "script_path": "streaming_language_analyzer.py"
        },
        "streaming-text-processor-main-pc": {
            "service_name": "Streaming Text Processor (Main PC)",
            "serving_method": "zmq_pub_health_local",
            "zmq_port": 5573,  # Input port
            "zmq_pub_port": 5574,  # Output port
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "process"],
            "health_check_port": 5597,  # Shared health monitoring port
            "expected_health_response_contains": {"component_name": "Text_Processor", "status": "healthy"},
            "health_message_timeout_seconds": 15,
            "script_path": "streaming_text_processor.py"
        },
        "fixed-streaming-translation-main-pc": {
            "service_name": "Fixed Streaming Translation (Main PC)",
            "serving_method": "zmq_pub_health_local",
            "zmq_port": 5572,  # Input port
            "zmq_pub_port": 5573,  # Output port
            "zmq_bind_address": "0.0.0.0",
            "zmq_actions_provided": ["health_check", "translate"],
            "health_check_port": 5597,  # Shared health monitoring port
            "expected_health_response_contains": {"component_name": "Translation_Component", "status": "healthy"},
            "health_message_timeout_seconds": 15,
            "script_path": "fixed_streaming_translation.py"
        }
    }
}

# Global config dictionary that can be imported
config_data = {
    "pc2": pc2_settings,
    "main_pc": main_pc_settings
}

def get_config_for_machine(machine_id="pc2"):
    """
    Returns the full configuration dictionary for a given machine.
    Defaults to 'pc2' if running on PC2.
    """
    return config_data.get(machine_id, {})

def get_config_for_service(service_id, machine_id="pc2"):
    """
    Retrieves the specific configuration for a service on a given machine.
    """
    machine_conf = get_config_for_machine(machine_id)
    return machine_conf.get("model_configs", {}).get(service_id, {})

def get_service_host(service_name: str, default_host: str) -> str:
    """
    Get the host for a service with environment variable override.
    
    Args:
        service_name: Name of the service (e.g., 'enhanced_model_router')
        default_host: Default host to use if no environment variable is set
        
    Returns:
        Host address for the service
    """
    env_key = f"{service_name.upper()}_HOST"
    return get_env_override(env_key, default_host)

def get_service_port(service_name: str, default_port: int) -> int:
    """
    Get the port for a service with environment variable override.
    
    Args:
        service_name: Name of the service (e.g., 'enhanced_model_router')
        default_port: Default port to use if no environment variable is set
        
    Returns:
        Port number for the service
    """
    env_key = f"{service_name.upper()}_PORT"
    port_str = get_env_override(env_key, str(default_port)
    try:
        return int(port_str)
    except ValueError:
        return default_port

# Direct config variable for compatibility with existing agent imports
config = {
    # ZMQ Configuration
    'zmq.remote_connector_port': 5557,
    'zmq.translator_port': 5563,
    'zmq.llm_translation_adapter_port': 5581,
    'zmq.unified_memory_reasoning_port': 5596,
    'zmq.digital_twin_port': 7596,
    'zmq.digital_twin_pub_port': 7597,
    'zmq.got_tot_port': 5646,
    'zmq.tutor_port': 5647,
    'zmq.tutoring_service_port': 5568,
    'zmq.local_fine_tuner_port': 5645,
    'zmq.agent_trust_scorer_port': 5648,
    'zmq.self_training_orchestrator_port': 5644,
    'zmq.dreaming_mode_port': 5640,
    'zmq.tinyllama_service_port': 5615,
    'zmq.model_manager_port': 5610,
    'zmq.dream_world_port': 5642,
    # System Configuration
    'system.log_level': 'INFO',
    'system.logs_dir': 'logs',
    'system.cache_dir': 'cache',
    
    # Memory Agent Configuration
    'memory.proactive_reminder_broadcast': True,  # Enable/disable proactive reminder broadcasting
    
    # Model Configuration
    'models.cache_enabled': True,
    'models.cache_ttl': 3600,
    
    # Network Configuration
    'network.bind_address': '0.0.0.0'
}
# LOGS_DIR = general_pc2_config.get("logs_dir", "logs")

# For simple import by services if they know they are on PC2 and want their specific section
# from config.system_config import pc2_settings
# service_config = pc2_settings.get("model_configs", {}).get("my-service-id", {})
