import os
import json
import logging
from pathlib import Path

# Base paths
ROOT_DIR = Path(__file__).parent.parent.absolute()
CONFIG_DIR = ROOT_DIR / "config"
MODELS_DIR = ROOT_DIR / "models"
LOGS_DIR = ROOT_DIR / "logs"

# Create directories if they don't exist
for directory in [CONFIG_DIR, MODELS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    # Common System Wide Settings
    "common_settings": {
        "system": {
            "debug_mode": False,
            "log_level": "DEBUG",
            "language": "en",
        },
        "wake_word": {
            "enabled": True,
            "primary": "tha_lim",
            "alternatives": ["hey_jarvis", "alexa", "hey_mycroft"],
            "sensitivity": 0.5,
            "vad_enabled": True,
            "vad_threshold": 0.5,
        },
        "audio": {
            "device_index": 30,
            "sample_rate": 16000,
            "channels": 1,
            "noise_reduction": True,
        },
        "face_recognition_general": { 
            "enabled": True,
            "detection_frequency": 0.5,
            "min_face_size": 30,
            "recognition_threshold": 0.6,
        },
        "tts_general": { 
            "provider": "bark",
            "voice": "v2/en_speaker_6",
            "cache_enabled": True,
        },
        "ollama_global_config": {
            "keep_alive_default": "5m", 
            "max_loaded_models": 2      
        },
        "zmq_ports_common": {
            "log_port": 5600,
            "executor_port": 5613,
            "autogen_framework_port": 5650,
        }
    },
    
    "zmq": {
        "code_generator_port": 5604,
        "executor_port": 5613,
        "model_manager_port": 5556,
        "autogen_framework_port": 5650,
        "log_port": 5600
    },
    

    
    "main_pc_settings": {
        "model_manager_port": 5556,
        "zmq_ports": {
            "orchestrator_port": 5555,
            "listener_port": 5561,
            "tts_port": 5562, 
            "face_recognition_port": 5560, 
        },
        "whisper_model_config": {
            "model_path": "models/whisper/large-ct2",
            "use_gpu": True,
            "compute_type": "float16",
        },
        "ollama_server_config": {
            "url": "http://localhost:11434", 
        },
        "deepseek_client_config": { 
            "url": "http://192.168.1.2:8003", 
            "enabled": True,
            "context_length": 16000,
        },
        "tts_config": { 
            "use_gpu": True, 
        },
        "face_recognition_config": {
            "use_gpu": True,
        },
        "model_configs": {
            "wizardcoder-python": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "WizardCoder Python 13B",
                "serving_method": "gguf_direct",
                "model_path": "wizardcoder/wizardcoder-python-13b-v1.0.Q4_K_M.gguf",
                "capabilities": ["code-generation-python", "instruction-following-code", "code-completion"],
                "estimated_vram_mb": 8000,
                "context_length": 8192,
                "idle_timeout_seconds": 300,
                "n_gpu_layers": -1,
                "n_threads": 4,
                "verbose": False
            },
            "llama3-instruct": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Llama-3 8B Instruct",
                "serving_method": "gguf_direct",
                "model_path": "llama3-instruct/Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
                "capabilities": ["instruction-following", "text-generation", "general-purpose-chat"],
                "estimated_vram_mb": 5000,
                "context_length": 8192,
                "idle_timeout_seconds": 300,
                "n_gpu_layers": -1,
                "n_threads": 4,
                "verbose": False
            },
            "deepseek-coder": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "DeepSeek Coder 6.7B",
                "serving_method": "gguf_direct",
                "model_path": "deepseek-coder/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
                "capabilities": ["code-generation-multilang", "code-completion", "instruction-following-code"],
                "estimated_vram_mb": 4000,
                "context_length": 16384,
                "idle_timeout_seconds": 240,
                "n_gpu_layers": -1,
                "n_threads": 4,
                "verbose": False
            },
            "wizardcoder-13b-ollama": {
                "enabled": False,
                "auto_load_on_start": False,
                "display_name": "WizardCoder-13B",
                "serving_method": "ollama",
                "ollama_tag": "wizardcoder-13b-gguf",
                "capabilities": ["code-generation-python", "instruction-following"],
                "estimated_vram_mb": 8000,
                "context_length": 4096,
                "idle_timeout_seconds": 60
            },
            "deepseek-6.7b-api": {
                "enabled": False,
                "auto_load_on_start": False,
                "display_name": "DeepSeek-Coder-6.7B",
                "serving_method": "custom_api",
                "api_base_url": "http://localhost:8080/v1", 
                "api_model_id": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
                "capabilities": ["instruction-following", "code-generation-multilang", "code-completion"],
                "estimated_vram_mb": 6000,
                "context_length": 32768,
                "idle_timeout_seconds": 120,
                "notes": "Ensure this API server is running and the model is loaded for MMA to detect as online."
            },
            "llama3-8b-api": {
                "enabled": False,
                "auto_load_on_start": False,
                "display_name": "LLaMA-3-8B-Instruct",
                "serving_method": "custom_api",
                "api_base_url": "http://localhost:8000/v1", 
                "api_model_id": "Meta-Llama-3-8B-Instruct.Q4_K_M.gguf",
                "capabilities": ["instruction-following", "general-purpose-chat", "basic-reasoning", "text-generation"],
                "estimated_vram_mb": 6500,
                "context_length": 8192,
                "idle_timeout_seconds": 120,
                "notes": "Ensure this API server is running and the model is loaded for MMA to detect as online."
            },
            "phi3-ollama": {
                "enabled": False,
                "auto_load_on_start": False,
                "display_name": "Phi-3",
                "serving_method": "ollama",
                "ollama_tag": "phi3:latest",
                "capabilities": ["instruction-following", "general-purpose-chat", "text-generation", "code-generation-simple"],
                "estimated_vram_mb": 3500,
                "context_length": 4096,
                "idle_timeout_seconds": 30
            },
            "mistral-7b-ollama": {
                "enabled": False,
                "auto_load_on_start": False,
                "display_name": "Mistral-7B-Instruct",
                "serving_method": "ollama",
                "ollama_tag": "mistral:7b-instruct",
                "capabilities": ["instruction-following", "general-purpose-chat", "text-generation", "summarization"],
                "estimated_vram_mb": 5500,
                "context_length": 8192,
                "idle_timeout_seconds": 90
            },
            "codellama-13b-ollama": {
                "enabled": False,
                "auto_load_on_start": False,
                "display_name": "CodeLLaMA-13B",
                "serving_method": "ollama",
                "ollama_tag": "codellama:13b",
                "capabilities": ["code-generation-multilang", "code-completion", "instruction-following-code"],
                "estimated_vram_mb": 9000,
                "context_length": 16384,
                "idle_timeout_seconds": 60
            },
            "phi-old-ollama": {
                "enabled": False,
                "auto_load_on_start": False,
                "display_name": "Phi (Older)",
                "serving_method": "ollama",
                "ollama_tag": "phi:latest",
                "capabilities": ["text-generation", "code-generation-simple", "reasoning-simple"],
                "estimated_vram_mb": 3000,
                "context_length": 2048,
                "idle_timeout_seconds": 30
            },
            "tinyllama": {
                "enabled": True,
                "display_name": "TinyLlama-1.1B-Chat-v1.0 (ZMQ Main PC)",
                "serving_method": "zmq_service",
                'zmq_address': 'tcp://localhost:5617',  
                "capabilities": ["text-generation", "fallback"],
                "estimated_vram_mb": 2800,
                "context_length": 2048,
                "idle_timeout_seconds": 300,
                "zmq_actions": {
                    "load": "ensure_loaded",
                    "unload": "request_unload",
                    "health": "health_check"
                },
                "auto_load_on_start": False
            },
            "tinylama-service-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "TinyLLaMA (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5615",
                "capabilities": ["text-generation", "fallback"],
                "estimated_vram_mb": 0, # Not managed by Main PC MMA
                "context_length": 2048,
                "idle_timeout_seconds": 0, # Not managed by Main PC MMA
                # Protocol confirmed with protocol finder
                "zmq_actions": {
                    "health": "health_check"
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            "error-pattern-memory-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Error Pattern Memory (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5611",
                "capabilities": ["error-pattern-recognition"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                # Trying alternative protocol based on RCA agent's successful protocol
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            "context-summarizer-agent-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Context Summarizer Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5610",
                "capabilities": ["context-summarization"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                # Trying alternative protocol based on RCA agent's successful protocol
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            "chain-of-thought-agent-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Chain of Thought Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5612",
                "capabilities": ["chain-of-thought-reasoning"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            # RCA Agent (PC2 Remote)
            "rca-agent-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "RCA Agent PC2",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5557",
                "capabilities": ["rca_analysis", "health_check"],
                "estimated_vram_mb": 500,
                "context_length": 4096,
                "idle_timeout_seconds": 300,
                # Protocol confirmed with protocol finder
                "zmq_actions": {
                    "health": {},
                    "process_rca_data": "process_rca_data"
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            # Translator Agent (PC2 Remote)
            "translator-agent-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Translator Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5563",
                "capabilities": ["translation"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": "health_check"
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            # Fallback Translator (PC2 Remote)
            "fallback-translator-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Fallback Translator (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5564",
                "capabilities": ["translation-fallback"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": "health_check"
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            # NLLB Translation Adapter (PC2 Remote)
            "nllb-adapter-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "NLLB Translation Adapter (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5581",
                "capabilities": ["nllb-translation"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {"action": "translate", "text": "hello", "source": "en", "target": "fr"}
                },
                "expected_health_response_contains": { "status": "" }
            },
            # Memory Agent Base (PC2 Remote)
            "memory-agent-base-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Memory Agent Base (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5590",
                "capabilities": ["memory-base"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            # Contextual Memory Agent (PC2 Remote)
            "contextual-memory-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Contextual Memory Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5596",
                "capabilities": ["contextual-memory"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            # Digital Twin Agent (PC2 Remote)
            "digital-twin-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Digital Twin Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5597",
                "capabilities": ["digital-twin"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            # Jarvis Memory Agent (PC2 Remote)
            "jarvis-memory-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Jarvis Memory Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5598",
                "capabilities": ["jarvis-memory"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            # Code Generation Models for CodeGeneratorAgent (using GGUF files available in the system)
            # Using Ollama models for code generation (all with Q4_0 quantization)
            "phi": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Phi (Q4_0)",
                "serving_method": "ollama",
                "ollama_tag": "phi",
                "capabilities": ["code-generation", "text-generation"],
                "estimated_vram_mb": 1800,  # 1.6GB + overhead
                "context_length": 2048,
                "idle_timeout_seconds": 120
            },
            "phi3": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Phi-3 (Q4_0)",
                "serving_method": "ollama",
                "ollama_tag": "phi3",
                "capabilities": ["code-generation", "text-generation"],
                "estimated_vram_mb": 2400,  # 2.2GB + overhead
                "context_length": 4096,
                "idle_timeout_seconds": 120
            },
            "mistral": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Mistral 7B Instruct (Q4_0)",
                "serving_method": "ollama",
                "ollama_tag": "mistral:7b-instruct",
                "capabilities": ["code-generation", "text-generation"],
                "estimated_vram_mb": 4300,  # 4.1GB + overhead
                "context_length": 8192,
                "idle_timeout_seconds": 120
            },
            "codellama-13b": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "CodeLlama 13B (Q4_0)",
                "serving_method": "ollama",
                "ollama_tag": "codellama:13b",
                "capabilities": ["code-generation", "multilang", "code-completion"],
                "estimated_vram_mb": 7600,  # 7.4GB + overhead
                "context_length": 16384,  # As reported by Ollama
                "idle_timeout_seconds": 120
            },
            # Code Generator Agent service (for health monitoring)
            "cga_service_main_pc": {
                "enabled": True,
                "auto_load_on_start": True,
                "display_name": "CodeGeneratorAgent",
                "serving_method": "zmq_service",
                "zmq_address": "tcp://localhost:5604",
                "capabilities": ["code-generation", "code-execution"],
                "estimated_vram_mb": 0,  # Service doesn't use VRAM directly
                "context_length": 0,      # Not applicable
                "idle_timeout_seconds": 0, # Should always be running
                "zmq_actions": { "health": "ping" },  # Using existing ping functionality
                "expected_health_response_contains": {"status": "ANY"}  # Expected response field
            }
        },
    },

    "pc2_settings": {
        "description": "Settings for PC2 when VOICE_ASSISTANT_PC_ROLE='pc2' is set",
        "model_manager_port": 5557,
        "zmq_ports": {
            "orchestrator_port": 5555,
            "enhanced_router_port": 5555,
            "task_router_port": 5556,
            "remote_connector_port": 5557,
            "context_memory_port": 5558,
            "jarvis_memory_port": 5559,
            "digital_twin_port": 5560,
            "learning_mode_port": 5561,
            "translator_port": 5563,
            "web_scraper_port": 5564,
            "tinyllama_port": 5615
        },
        "model_configs": {
            "tinylama-service-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "TinyLLaMA (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5615",
                "capabilities": ["text-generation", "fallback"],
                "estimated_vram_mb": 0, # Not managed by Main PC MMA
                "context_length": 2048,
                "idle_timeout_seconds": 0, # Not managed by Main PC MMA
                # Protocol confirmed with protocol finder
                "zmq_actions": {
                    "health": "health_check"
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            "error-pattern-memory-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Error Pattern Memory (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5611",
                "capabilities": ["error-pattern-recognition"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                # Trying alternative protocol based on RCA agent's successful protocol
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            "context-summarizer-agent-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Context Summarizer Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5610",
                "capabilities": ["context-summarization"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                # Trying alternative protocol based on RCA agent's successful protocol
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            "chain-of-thought-agent-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Chain of Thought Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5612",
                "capabilities": ["chain-of-thought-reasoning"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            "rca-agent-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "RCA Agent PC2",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5557",
                "capabilities": ["rca_analysis", "health_check"],
                "estimated_vram_mb": 500,
                "context_length": 4096,
                "idle_timeout_seconds": 300,
                # Protocol confirmed with protocol finder
                "zmq_actions": {
                    "health": {},
                    "process_rca_data": "process_rca_data"
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            "translator-agent-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Translator Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5563",
                "capabilities": ["translation"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": "health_check"
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            "fallback-translator-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Fallback Translator (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5564",
                "capabilities": ["translation-fallback"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": "health_check"
                },
                "expected_health_response_contains": {"status": "ANY"}
            },
            "nllb-adapter-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "NLLB Translation Adapter (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5581",
                "capabilities": ["nllb-translation"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {"action": "translate", "text": "hello", "source": "en", "target": "fr"}
                },
                "expected_health_response_contains": { "status": "" }
            },
            "memory-agent-base-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Memory Agent Base (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5590",
                "capabilities": ["memory-base"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            "contextual-memory-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Contextual Memory Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5596",
                "capabilities": ["contextual-memory"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            "digital-twin-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Digital Twin Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5597",
                "capabilities": ["digital-twin"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
            "jarvis-memory-pc2": {
                "enabled": True,
                "auto_load_on_start": False,
                "display_name": "Jarvis Memory Agent (PC2 Remote)",
                "serving_method": "zmq_service_remote",
                "zmq_address": "tcp://192.168.1.2:5598",
                "capabilities": ["jarvis-memory"],
                "estimated_vram_mb": 0,
                "context_length": 0,
                "idle_timeout_seconds": 0,
                "zmq_actions": {
                    "health": {}},
                "expected_health_response_contains": {"status": "ANY"}
            },
        }
    },
}

# --- End of DEFAULT_CONFIG modifications ---

class Config:
    """Singleton configuration manager for the voice assistant system"""
    _instance = None
    _config = None
    _config_file = CONFIG_DIR / "config.json"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._load_config()
        return cls._instance
    
    @classmethod
    def _load_config(cls):
        """Load configuration from file or create default if not exists"""
        try:
            if cls._config_file.exists():
                with open(cls._config_file, 'r') as f:
                    user_config = json.load(f)
                # Merge with default config (default values for missing keys)
                cls._config = cls._deep_merge(DEFAULT_CONFIG, user_config)
                logging.info(f"Loaded configuration from {cls._config_file}")
            else:
                cls._config = DEFAULT_CONFIG
                # Save default config
                cls.save_config()
                logging.info(f"Created default configuration at {cls._config_file}")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            cls._config = DEFAULT_CONFIG
    
    @classmethod
    def _deep_merge(cls, default, override):
        """Deep merge two dictionaries, with override taking precedence"""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def get(cls, key_path, default=None):
        """Get a configuration value using dot notation (e.g., 'models.whisper.use_gpu')"""
        if cls._config is None:
            cls._load_config()
            
        keys = key_path.split('.')
        value = cls._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    @classmethod
    def set(cls, key_path, value):
        """Set a configuration value using dot notation"""
        if cls._config is None:
            cls._load_config()
            
        keys = key_path.split('.')
        config = cls._config
        
        # Navigate to the nested dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the value
        config[keys[-1]] = value
    
    @classmethod
    def save_config(cls):
        """Save the current configuration to file"""
        try:
            with open(cls._config_file, 'w') as f:
                json.dump(cls._config, f, indent=4)
            logging.info(f"Saved configuration to {cls._config_file}")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    @classmethod
    def get_all(cls):
        """Get the entire configuration dictionary"""
        if cls._config is None:
            cls._load_config()
        return cls._config.copy()  

# Create a global instance for other modules to import
config = Config()

# Function to get machine-specific configuration
def get_config_for_machine():
    machine_role = os.environ.get("MACHINE_ROLE", "MAIN_PC").upper()
    config_instance = Config() 
    full_config = config_instance.get_all()

    # Start with a deep copy of common settings
    machine_config = json.loads(json.dumps(full_config.get("common_settings", {})))  # Always defined locally. No global reference.

    specific_settings_key = None
    if machine_role == "MAIN_PC":
        specific_settings_key = "main_pc_settings"
    elif machine_role == "PC2":
        specific_settings_key = "pc2_settings"
    else:
        logging.warning(f"Unknown MACHINE_ROLE: {machine_role}. Falling back to Main PC specific settings.")
        specific_settings_key = "main_pc_settings"
    
    specific_settings = json.loads(json.dumps(full_config.get(specific_settings_key, {})))

    # Deep merge specific settings into the machine_config. Specific settings take precedence.
    def _deep_update(target, source):
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                _deep_update(target[key], value)
            else:
                target[key] = value
        return target

    _deep_update(machine_config, specific_settings)
    
    # Ensure all top-level keys from the chosen specific settings are present
    # This handles cases where a key might exist in specific_settings but not in common_settings initially
    for key, value in specific_settings.items():
        if key not in machine_config:
            machine_config[key] = value
            
    return machine_config  # Ensure only returned, never referenced globally.


# Initialize logging
_initial_config_for_logging = Config().get_all() 
_log_level_to_use = _initial_config_for_logging.get("common_settings", {}).get("system", {}).get("log_level", "INFO")

logging.basicConfig(
    level=getattr(logging, _log_level_to_use.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "voice_assistant.log")
    ]
)

# Example of how to use it (can be removed or kept for testing)
if __name__ == "__main__":
    # Test with MAIN_PC role
    os.environ["MACHINE_ROLE"] = "MAIN_PC"
    main_pc_config = get_config_for_machine()
    print("--- MAIN PC Config ---")
    print(f"Main PC Model Manager Port: {main_pc_config.get('model_manager_port')}")
    print(f"Main PC Orchestrator Port: {main_pc_config.get('zmq_ports', {}).get('orchestrator_port')}")
    print(f"Log Level: {main_pc_config.get('system', {}).get('log_level')}")

    # Test with PC2 role
    os.environ["MACHINE_ROLE"] = "PC2"
    pc2_config = get_config_for_machine()
    print("\n--- PC2 Config ---")
    print(f"PC2 Translator Port: {pc2_config.get('zmq_ports', {}).get('translator_port')}")
    print(f"PC2 has model_manager_port: {'model_manager_port' in pc2_config}") 
    print(f"Log Level: {pc2_config.get('system', {}).get('log_level')}")

    # Test with unknown role
    os.environ["MACHINE_ROLE"] = "UNKNOWN_MACHINE"
    unknown_config = get_config_for_machine()
    print("\n--- Unknown Role Config (defaults to Main PC) ---")
    print(f"Model Manager Port: {unknown_config.get('model_manager_port')}")

    # Reset for other modules if they import this
    del os.environ["MACHINE_ROLE"]
