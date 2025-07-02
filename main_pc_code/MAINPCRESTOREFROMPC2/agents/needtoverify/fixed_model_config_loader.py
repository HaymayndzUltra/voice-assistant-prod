from src.core.base_agent import BaseAgent
def _load_models_from_config(self):
    """
    Load model configurations from the central config
    Respects the active PC settings key (main_pc_settings or pc2_settings) based on environment variable
    """
    try:
        # Determine active PC settings key based on environment variable
        from utils.config_loader import Config
        cfg = Config()
        active_pc_settings_key = cfg.active_pc_settings_key
        logger.info(f"Active PC settings key: {active_pc_settings_key}")
        
        # Get model configurations directly from config object
        model_configs = {}
        try:
            # Try to access model_configs from the active PC settings
            model_configs = config.get(f'{active_pc_settings_key}.model_configs', {})
            logger.info(f"Found model configurations in {active_pc_settings_key}.model_configs")
        except Exception as e:
            logger.warning(f"Could not load model configs from {active_pc_settings_key}: {e}")
            # Fallback to direct model_configs
            try:
                model_configs = config.get('model_configs', {})
                logger.info(f"Found model configurations in model_configs")
            except Exception as e:
                logger.warning(f"Could not load model configs directly: {e}")
        gguf_models_count = 0
        
        # Process models from system_config.py
        for model_id, model_cfg in model_configs.items():
            # Log every model config processed, with ZMQ address if present
            zmq_addr = model_cfg.get('zmq_address', None)
            is_enabled = model_cfg.get('enabled', True)
            logger.debug(f"Config entry processed: ID='{model_id}', ZMQ_Address='{zmq_addr}', Enabled='{is_enabled}', ServingMethod='{model_cfg.get('serving_method')}'")            
            if model_cfg.get('serving_method') == 'gguf_direct' and is_enabled:
                self.models[model_id] = {
                    'serving_method': 'gguf_direct',
                    'display_name': model_cfg.get('display_name', model_id),
                    'model_path': model_cfg.get('model_path'),
                    'capabilities': model_cfg.get('capabilities', []),
                    'status': 'available_not_loaded',
                    'last_check': 0,
                    'estimated_vram_mb': model_cfg.get('estimated_vram_mb', 0),
                    'context_length': model_cfg.get('context_length', 2048),
                    'idle_timeout_seconds': model_cfg.get('idle_timeout_seconds', 300),
                    'n_gpu_layers': model_cfg.get('n_gpu_layers', -1),
                    'n_threads': model_cfg.get('n_threads', 4),
                    'verbose': model_cfg.get('verbose', False)
                }
                gguf_models_count += 1
        
        logger.info(f"Loaded {gguf_models_count} GGUF model configurations from system_config.py")
        
        # Then try to load additional GGUF models configuration if it exists
        try:
            gguf_models_path = Path("config/gguf_models.json")
            if gguf_models_path.exists():
                with open(gguf_models_path, 'r') as f:
                    gguf_models = json.load(f)
                logger.info(f"Loaded {len(gguf_models)} additional GGUF model configurations from {gguf_models_path}")
                
                # Add GGUF models to main PC settings if they don't exist
                if "main_pc_settings" in machine_config and "model_configs" in machine_config["main_pc_settings"]:
                    for model_id, model_config in gguf_models.items():
                        if model_id not in machine_config["main_pc_settings"]["model_configs"]:
                            machine_config["main_pc_settings"]["model_configs"][model_id] = model_config
                            logger.info(f"Added GGUF model {model_id} to model configurations")
        except Exception as e:
            logger.warning(f"Error loading GGUF models configuration: {e}")
        
        # Log success
        logger.info("Loaded configurations from system_config.py")
        
        # Get the active machine settings based on environment variable
        machine_settings = machine_config.get(active_pc_settings_key, {})
        model_configs = machine_settings.get('model_configs', {})
        
        if not model_configs:
            logger.warning(f"No model_configs found in {active_pc_settings_key}. Attempting to load from legacy config.")
            self._load_models_from_legacy_config()
            return
        
        self.models = {} # Clear existing models before loading from new config
        for model_id, model_cfg_item in model_configs.items():
            if not model_cfg_item.get('enabled', True):
                logger.info(f"Model {model_id} is disabled in config. Skipping.")
                continue
            
            model_data = {
                'display_name': model_cfg_item.get('display_name', model_id),
                'serving_method': model_cfg_item.get('serving_method'),
                'capabilities': model_cfg_item.get('capabilities', []),
                'status': 'unknown',  # Initial status
                'last_check': 0,
                'estimated_vram_mb': model_cfg_item.get('estimated_vram_mb', 0),
                'context_length': model_cfg_item.get('context_length', 2048),
                'idle_timeout_seconds': model_cfg_item.get('idle_timeout_seconds', 300),
            }
            
            # Add additional fields based on serving method
            serving_method = model_cfg_item.get('serving_method')
            if serving_method == 'ollama':
                model_data.update({
                    'ollama_tag': model_cfg_item.get('ollama_tag'),
                })
            elif serving_method == 'zmq_service':
                model_data.update({
                    'zmq_address': model_cfg_item.get('zmq_address'),
                    'zmq_actions': model_cfg_item.get('zmq_actions', {}),
                    'expected_health_response': model_cfg_item.get('expected_health_response', {}),
                    'expected_health_response_contains': model_cfg_item.get('expected_health_response_contains', {}),
                })
            elif serving_method == 'zmq_service_remote':
                model_data.update({
                    'zmq_address': model_cfg_item.get('zmq_address'),
                    'zmq_actions': model_cfg_item.get('zmq_actions', {}),
                    'expected_health_response': model_cfg_item.get('expected_health_response', {}),
                    'expected_health_response_contains': model_cfg_item.get('expected_health_response_contains', {}),
                })
            elif serving_method == 'custom_api':
                model_data.update({
                    'api_url': model_cfg_item.get('api_url'),
                    'api_headers': model_cfg_item.get('api_headers', {}),
                    'api_auth': model_cfg_item.get('api_auth', {}),
                })
            elif serving_method == 'gguf_direct':
                model_data.update({
                    'model_path': model_cfg_item.get('model_path'),
                    'n_gpu_layers': model_cfg_item.get('n_gpu_layers', -1),
                    'n_threads': model_cfg_item.get('n_threads', 4),
                    'verbose': model_cfg_item.get('verbose', False),
                })
            
            # Add the model to the models dictionary
            self.models[model_id] = model_data
            logger.info(f"Added model {model_id} with serving method {serving_method}")
        
        logger.info(f"Loaded {len(self.models)} total model configurations from {active_pc_settings_key}")
        
        # Special handling for ZMQ remote services (log them separately for diagnostics)
        zmq_remote_models = {k: v.get('zmq_address') for k, v in self.models.items() 
                          if v.get('serving_method') == 'zmq_service_remote'}
        if zmq_remote_models:
            logger.info(f"Found {len(zmq_remote_models)} ZMQ remote services: {zmq_remote_models}")
        else:
            logger.warning(f"No ZMQ remote services found in {active_pc_settings_key}")
        
    except Exception as e:
        logger.error(f"Error loading configurations: {e}")
        logger.exception("Detailed error loading model configurations:")
        self._load_models_from_legacy_config()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
