# Deep Agent Inventory - main_pc_code

### ActiveLearningMonitor

- group: learning_knowledge
- script_path: main_pc_code/agents/active_learning_monitor.py
- port: 5638
- health_check_port: 6638
- dependencies: ['LearningManager', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ActiveLearningMonitor
- functions: __init__, _is_high_value_interaction, _save_training_data, _monitor_umra, _monitor_coordinator, _analyze_interactions, get_training_data_stats, shutdown, _get_health_status, health_check, report_error, cleanup
- exceptions: Exception as e, KeyboardInterrupt

### AdvancedCommandHandler

- group: language_processing
- script_path: main_pc_code/agents/advanced_command_handler.py
- port: 5710
- health_check_port: 6710
- dependencies: ['NLUAgent', 'CodeGenerator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: AdvancedCommandHandler
- functions: __init__, load_domain_modules, get_domain_commands, get_available_domains, toggle_domain, detect_command_registration, register_command, _parse_sequence, execute_command, _execute_sequence, _execute_script, get_running_processes, _update_process_status, stop_process, process_command_registration ...
- exceptions: Exception as e, KeyboardInterrupt
- caching occurrences: 1

### AudioCapture

- group: audio_interface
- script_path: main_pc_code/agents/streaming_audio_capture.py
- port: 6550
- health_check_port: 7550
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: StreamingAudioCapture
- functions: setup_health_check_server, register_service, find_available_port, __init__, setup_zmq, _bind_socket_with_retry, _health_check_loop, _get_health_status, __enter__, _cleanup_resources, __exit__, initialize_wake_word_detection, wake_word_detection_loop, _similar_string, process_audio_buffer_for_wake_word ...
- exceptions: ImportError, ModuleNotFoundError, (TypeError, ValueError), OSError, Exception as e_pyaudio_init, Exception as e, zmq.error.ZMQError as e, zmq.error.Again, ImportError as e, Exception as e_zmq, Exception as e_device, Exception as e_stream_open, Exception as e_http, Exception as e_outer, KeyboardInterrupt
- session/auth related occurrences: 1

### ChainOfThoughtAgent

- group: reasoning_services
- script_path: main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
- port: 5612
- health_check_port: 6612
- dependencies: ['ModelManagerAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ChainOfThoughtAgent
- functions: __init__, connect_llm_router, report_error, send_to_llm, generate_problem_breakdown, generate_solution_for_step, verify_solution, refine_solution, generate_combined_solution, generate_with_cot, cleanup, _get_health_status, health_check
- exceptions: Exception as e, KeyboardInterrupt
- session/auth related occurrences: 1

### ChitchatAgent

- group: language_processing
- script_path: main_pc_code/agents/chitchat_agent.py
- port: 5711
- health_check_port: 6711
- dependencies: ['NLUAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ChitchatAgent
- functions: _get_default_port, __init__, _init_sockets, _get_conversation_history, _add_to_history, _format_messages_for_llm, _generate_response_with_local_llm, _generate_response_with_remote_llm, process_chitchat, handle_request, health_broadcast_loop, run, stop, _get_health_status, cleanup ...
- actions: health_check, chitchat, clear_history
- exceptions: zmq.error.ZMQError as e, Exception as e, KeyboardInterrupt
- session/auth related occurrences: 1

### CodeGenerator

- group: utility_services
- script_path: main_pc_code/agents/code_generator.py
- port: 5650
- health_check_port: 6650
- dependencies: ['SystemDigitalTwin', 'ModelManagerAgent']
- required: True
**Code Details:**
- classes: CodeGeneratorAgent
- functions: __init__, process_request, generate_code, perform_health_check, _get_health_status, cleanup
- actions: generate_code, health_check
- exceptions: KeyboardInterrupt, Exception as exc

### CognitiveModelAgent

- group: reasoning_services
- script_path: main_pc_code/FORMAINPC/CognitiveModelAgent.py
- port: 5641
- health_check_port: 6641
- dependencies: ['ChainOfThoughtAgent', 'SystemDigitalTwin']
- required: False
**Code Details:**
- classes: CognitiveModelAgent
- functions: __init__, _initialize_belief_system, add_belief, _check_belief_consistency, query_belief_consistency, get_belief_system, handle_request, start, process_message, _get_health_status, _update_health_status, cleanup, health_check
- actions: health_check, add_belief, query_belief, get_belief_system
- exceptions: Exception as e, KeyboardInterrupt

### DynamicIdentityAgent

- group: language_processing
- script_path: main_pc_code/agents/DynamicIdentityAgent.py
- port: 5802
- health_check_port: 6802
- dependencies: ['RequestCoordinator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: DynamicIdentityAgent
- functions: __init__, _get_health_status, _connect_to_request_coordinator, _perform_initialization, _update_model_orchestrator, _update_empathy_agent, switch_persona, get_current_persona, list_personas, handle_request, run, stop, health_check, cleanup
- actions: health_check, switch_persona, get_current_persona, list_personas
- exceptions: Exception as e, UnicodeDecodeError, KeyboardInterrupt

### EmotionEngine

- group: emotion_system
- script_path: main_pc_code/agents/emotion_engine.py
- port: 5590
- health_check_port: 6590
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: EmotionEngine
- functions: __init__, _signal_handler, setup_zmq, _bind_socket_with_retry, _health_check_loop, _get_health_status, _broadcast_emotional_state, get_emotional_state, run, handle_request, update_emotional_state, health_check, cleanup
- actions: update_emotional_state, get_emotional_state, health_check
- exceptions: Exception as e, zmq.error.ZMQError as e, zmq.error.Again, Exception, KeyboardInterrupt, ValueError

### EmotionSynthesisAgent

- group: language_processing
- script_path: main_pc_code/agents/emotion_synthesis_agent.py
- port: 5706
- health_check_port: 6706
- dependencies: ['RequestCoordinator', 'ModelManagerAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: EmotionSynthesisAgent
- functions: __init__, _add_emotional_markers, synthesize_emotion, handle_request, report_error, cleanup, _get_health_status, health_check
- actions: synthesize_emotion
- exceptions: Exception as e, KeyboardInterrupt

### EmpathyAgent

- group: emotion_system
- script_path: main_pc_code/agents/EmpathyAgent.py
- port: 5703
- health_check_port: 6703
- dependencies: ['EmotionEngine', 'StreamingTTSAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: EmpathyAgent
- functions: __init__, _initialize_connections, update_emotional_profile, send_voice_settings_to_tts, _monitor_emotions, _update_emotional_state, determine_voice_settings, _send_voice_settings_to_tts, _get_health_status, handle_request, run, stop, health_check, _perform_initialization, get_health_status ...
- actions: ping, get_health, get_voice_settings, update_emotional_state
- exceptions: Exception as e, zmq.Again, zmq.error.ZMQError as zmq_err, KeyboardInterrupt

### Executor

- group: utility_services
- script_path: main_pc_code/agents/executor.py
- port: 5606
- health_check_port: 6606
- dependencies: ['CodeGenerator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ExecutorAgent
- functions: log_usage_analytics, send_log, __init__, authenticate_user, execute_command, send_feedback, run, cleanup, hot_reload_watcher, health_check, _get_health_status
- exceptions: Exception as _e, Exception as e, zmq.ZMQError as e, json.JSONDecodeError as e, KeyboardInterrupt, ImportError as e
- session/auth related occurrences: 1

### FaceRecognitionAgent

- group: vision_processing
- script_path: main_pc_code/agents/face_recognition_agent.py
- port: 5610
- health_check_port: 6610
- dependencies: ['RequestCoordinator', 'ModelManagerAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: EmotionState:, PrivacyZone:, KalmanTracker, EmotionAnalyzer, LivenessDetector, PrivacyManager, FaceRecognitionAgent
- functions: __init__, update, get_bbox, _load_emotion_model, _load_voice_model, _start_voice_processing, process_voice, analyze_emotion, get_emotion_trend, detect_blink, detect_motion, detect_anti_spoofing, is_live, load_privacy_zones, apply_privacy ...
- actions: health_check, process_frame
- exceptions: Exception as e, Exception, Exception as zmq_err, KeyboardInterrupt
- session/auth related occurrences: 1

### FeedbackHandler

- group: language_processing
- script_path: main_pc_code/agents/feedback_handler.py
- port: 5636
- health_check_port: 6636
- dependencies: ['NLUAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: FeedbackHandler
- functions: __init__, send_visual_feedback, send_voice_feedback, send_combined_feedback, send_command_feedback, show_processing, clear_processing, _try_reconnect_gui, _try_reconnect_voice, _check_connections, shutdown, _perform_initialization, _get_health_status, health_check, cleanup
- exceptions: zmq.ZMQError as e, Exception as e, KeyboardInterrupt

### FixedStreamingTranslation

- group: utility_services
- script_path: main_pc_code/agents/fixed_streaming_translation.py
- port: 5584
- health_check_port: 6584
- dependencies: ['ModelManagerAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: PerformanceMonitor, TranslationCache, AdvancedTimeoutManager, PerformanceMetrics, FixedStreamingTranslation
- functions: __init__, start, stop, _monitor_loop, report_error, _update_metrics, get_best_service, get_service_stats, get, set, clear, cleanup, calculate_timeout, record_response_time, get_timeout_stats ...
- exceptions: Exception as e, Exception as _, Exception, KeyboardInterrupt
- caching occurrences: 1

### FusedAudioPreprocessor

- group: audio_interface
- script_path: main_pc_code/agents/fused_audio_preprocessor.py
- port: 6551
- health_check_port: 7551
- dependencies: ['AudioCapture', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: FusedAudioPreprocessor
- functions: __init__, _load_config, _init_aec, _init_agc, _init_sockets, _init_vad_model, apply_noise_reduction, _resample_audio, _update_adaptive_threshold, detect_speech, _publish_vad_event, apply_aec, apply_agc, process_audio_loop, health_check ...
- exceptions: Exception as e, ImportError as e, zmq.Again, KeyboardInterrupt
- caching occurrences: 1
- session/auth related occurrences: 1

### GGUFModelManager

- group: gpu_infrastructure
- script_path: main_pc_code/agents/gguf_model_manager.py
- port: 5575
- health_check_port: 6575
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: GGUFModelManager, GGUFStateTracker
- functions: get_main_pc_code, join_path, __init__, _load_model_metadata, list_models, load_model, unload_model, generate_text, get_model_status, get_all_model_status, check_idle_models, cleanup, _kv_cache_cleanup_loop, _manage_kv_cache_size, clear_kv_cache ...
- actions: list_models, load_model, unload_model, generate_text, health_check
- exceptions: ImportError as e, Exception as e, (AttributeError, NotImplementedError) as e
- caching occurrences: 1
- session/auth related occurrences: 1

### GoTToTAgent

- group: reasoning_services
- script_path: main_pc_code/FORMAINPC/GOT_TOTAgent.py
- port: 5646
- health_check_port: 6646
- dependencies: ['ModelManagerAgent', 'SystemDigitalTwin', 'ChainOfThoughtAgent']
- required: False
**Code Details:**
- classes: Node:, GoTToTAgent
- functions: __init__, add_child, _get_health_status, _load_reasoning_model, _process_loop, _handle_request, reason, _expand_tree, _generate_reasoning_step, _fallback_reasoning_step, _create_reasoning_prompt, _score_path, _trace_path, cleanup
- actions: reason
- exceptions: ImportError, zmq.Again, Exception as e, zmq.ZMQError, KeyboardInterrupt
- session/auth related occurrences: 1

### GoalManager

- group: language_processing
- script_path: main_pc_code/agents/goal_manager.py
- port: 7005
- health_check_port: 8005
- dependencies: ['RequestCoordinator', 'ModelOrchestrator', 'SystemDigitalTwin', 'MemoryClient']
- required: True
**Code Details:**
- classes: CircuitBreaker:, GoalManager
- functions: __init__, record_success, record_failure, allow_request, _init_circuit_breakers, _start_background_threads, _load_active_goals, _load_tasks_for_goal, handle_request, set_goal, get_goal_status, list_goals, search_goals, _break_down_goal, _update_goal_status ...
- exceptions: Exception as e, KeyboardInterrupt
- caching occurrences: 1

### HumanAwarenessAgent

- group: emotion_system
- script_path: main_pc_code/agents/human_awareness_agent.py
- port: 5705
- health_check_port: 6705
- dependencies: ['EmotionEngine', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: HumanAwarenessAgent
- functions: __init__, _load_config, _perform_initialization, _init_components, _get_health_status, handle_request, run, _update_presence, _update_emotion, health_check, cleanup
- actions: get_presence, get_emotion
- exceptions: Exception as e, Exception as zmq_err, KeyboardInterrupt

### IntentionValidatorAgent

- group: language_processing
- script_path: main_pc_code/agents/IntentionValidatorAgent.py
- port: 5701
- health_check_port: 6701
- dependencies: ['RequestCoordinator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: IntentionValidatorAgent
- functions: __init__, _perform_initialization, _init_database, _get_health_status, handle_request, _validate_command_structure, _check_command_history, _log_validation, health_check, cleanup
- actions: validate_command, get_validation_history
- exceptions: Exception as e, KeyboardInterrupt

### KnowledgeBase

- group: memory_system
- script_path: main_pc_code/agents/knowledge_base.py
- port: 5715
- health_check_port: 6715
- dependencies: ['MemoryClient', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: KnowledgeBase
- functions: __init__, _report_error, process_request, add_fact, get_fact, update_fact, _update_memory_item, search_facts, perform_health_check, _get_health_status, cleanup
- exceptions: Exception as exc, KeyboardInterrupt

### LearningAdjusterAgent

- group: learning_knowledge
- script_path: main_pc_code/FORMAINPC/LearningAdjusterAgent.py
- port: 5643
- health_check_port: 6643
- dependencies: ['SelfTrainingOrchestrator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ParameterType, ParameterConfig:, LearningAdjusterAgent
- functions: __init__, _init_db, _update_health_status, register_parameter, adjust_parameter, record_performance, optimize_parameters, _get_active_parameters, _analyze_parameter_trend, _get_health_status, handle_request, run, cleanup, health_check
- actions: health_check, register_parameter, adjust_parameter, record_performance, optimize_parameters
- exceptions: ImportError as e, Exception as e, zmq.error.Again, json.JSONDecodeError, Exception, KeyboardInterrupt

### LearningManager

- group: learning_knowledge
- script_path: main_pc_code/agents/learning_manager.py
- port: 5580
- health_check_port: 6580
- dependencies: ['MemoryClient', 'RequestCoordinator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: LearningManager
- functions: __init__, _perform_initialization, _init_components, _setup_sockets, _init_learning_resources, _create_learning_session, _update_learning_session, _get_learning_session, _delete_learning_session, _adjust_learning_rate, handle_request, health_broadcast_loop, run, stop, _get_health_status ...
- actions: create_session, update_session, get_session, delete_session, get_learning_rate
- exceptions: Exception as e, Exception as zmq_err, KeyboardInterrupt
- session/auth related occurrences: 1

### LearningOpportunityDetector

- group: learning_knowledge
- script_path: main_pc_code/agents/learning_opportunity_detector.py
- port: 7200
- health_check_port: 7201
- dependencies: ['LearningOrchestrationService', 'MemoryClient', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: LearningOpportunityDetector
- functions: __init__, _register_with_service_discovery, _init_circuit_breakers, _setup_zmq_connections, _init_database, _start_background_threads, _monitor_umra, _monitor_coordinator, _analyze_interactions, _score_interaction, _detect_explicit_correction, _detect_implicit_correction, _detect_positive_reinforcement, _detect_question_answer_pattern, _detect_complex_reasoning ...
- actions: get_top_opportunities, mark_processed, get_stats
- exceptions: ImportError as e, Exception as e, KeyboardInterrupt

### LearningOrchestrationService

- group: learning_knowledge
- script_path: main_pc_code/agents/learning_orchestration_service.py
- port: 7210
- health_check_port: 7211
- dependencies: ['ModelEvaluationFramework', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: LearningOrchestrationService
- functions: __init__, _register_with_service_discovery, _init_circuit_breakers, _init_database, _setup_zmq, _start_background_threads, _main_loop, handle_request, _handle_new_opportunity, _handle_get_training_cycles, safe_uuid, _get_health_status, report_error, cleanup
- actions: new_learning_opportunity, get_training_cycles, get_stats
- exceptions: Exception as e, Exception, KeyboardInterrupt

### LocalFineTunerAgent

- group: utility_services
- script_path: main_pc_code/FORMAINPC/LocalFineTunerAgent.py
- port: 5642
- health_check_port: 6642
- dependencies: ['SelfTrainingOrchestrator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: TuningStatus, ArtifactType, TuningJob:, LocalFineTunerAgent, ModelClientModel:, ModelClientTokenizer:
- functions: __init__, _init_db, _init_artifact_dir, create_tuning_job, start_tuning_job, _create_job_from_db, _run_job_manager, _execute_tuning_step, _record_metrics, _save_artifacts, _fail_job, _cleanup_job, get_job_status, handle_request, run ...
- actions: health_check, create_job, start_job, get_status
- exceptions: ImportError as e, Exception as e, zmq.Again, zmq.ZMQError, KeyboardInterrupt
- session/auth related occurrences: 1

### MemoryClient

- group: memory_system
- script_path: main_pc_code/agents/memory_client.py
- port: 5713
- health_check_port: 6713
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: CircuitBreaker:, MemoryClient
- functions: get_service_address, __init__, record_success, record_failure, is_closed, get_state, _initialize_client_socket, _report_error, _send_request, set_agent_id, set_session_id, create_session, add_memory, get_memory, search_memory ...
- actions: health_check, reset_circuit_breaker
- exceptions: Exception as e, zmq.error.Again, KeyboardInterrupt
- session/auth related occurrences: 1

### ModelEvaluationFramework

- group: learning_knowledge
- script_path: main_pc_code/agents/model_evaluation_framework.py
- port: 7220
- health_check_port: 7221
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ModelEvaluationFramework
- functions: __init__, _register_with_service_discovery, _init_circuit_breakers, _init_database, _setup_zmq, _start_background_threads, _main_loop, handle_request, _handle_log_performance_metric, _handle_get_performance_metrics, _handle_log_model_evaluation, _handle_get_model_evaluation_scores, _get_health_status, report_error, cleanup
- actions: log_performance_metric, get_performance_metrics, log_model_evaluation, get_model_evaluation_scores, get_stats
- exceptions: Exception as e, KeyboardInterrupt

### ModelManagerAgent

- group: gpu_infrastructure
- script_path: main_pc_code/agents/model_manager_agent.py
- port: 5570
- health_check_port: 6570
- dependencies: ['GGUFModelManager', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ModelManagerAgent
- functions: get_main_pc_code, __init__, handle_request
- actions: status, generate

### ModelOrchestrator

- group: language_processing
- script_path: main_pc_code/agents/model_orchestrator.py
- port: 7010
- health_check_port: 8010
- dependencies: ['RequestCoordinator', 'ModelManagerAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ModelOrchestrator
- functions: __init__, _get_language_configs, _init_circuit_breakers, _init_embedding_model, setup_error_reporting, report_error, _load_task_embeddings, _load_metrics, _save_metrics, _metrics_reporting_loop, _log_metrics, _build_context_prompt, _send_to_llm, _execute_code_safely, _resilient_send_request ...
- exceptions: ImportError, Exception as e, subprocess.TimeoutExpired, KeyboardInterrupt
- caching occurrences: 1
- session/auth related occurrences: 1

### MoodTrackerAgent

- group: emotion_system
- script_path: main_pc_code/agents/mood_tracker_agent.py
- port: 5704
- health_check_port: 6704
- dependencies: ['EmotionEngine', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: MoodTrackerAgent
- functions: __init__, _monitor_emotions, _update_mood, _handle_queries, _process_request, get_current_mood, get_mood_history, get_long_term_mood, _get_health_status, health_check, run, cleanup
- actions: ping, get_health, get_current_mood, get_mood_history, get_long_term_mood
- exceptions: Exception as e, zmq.error.ZMQError as zmq_err, KeyboardInterrupt

### NLLBAdapter

- group: utility_services
- script_path: main_pc_code/FORMAINPC/NLLBAdapter.py
- port: 5581
- health_check_port: 6581
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ModelClientModel:, ModelClientTokenizer:, NLLBTranslationAdapter
- functions: __init__, generate, to, setup_language_mappings, __call__, batch_decode, report_error, _load_model, _unload_model, translate_text, _monitor_resources, handle_requests, run, _get_health_status, cleanup
- exceptions: zmq.error.ZMQError as e, zmq.error.ZMQError as e2, Exception as e, KeyError as e, zmq.error.Again, zmq.error.ZMQError, KeyboardInterrupt
- caching occurrences: 1
- session/auth related occurrences: 1

### NLUAgent

- group: language_processing
- script_path: main_pc_code/agents/nlu_agent.py
- port: 5709
- health_check_port: 6709
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: NLUAgent
- functions: __init__, _perform_initialization, start, stop, _handle_requests, _process_request, _analyze_text, _extract_intent, _extract_entities, _get_health_status, health_check, cleanup
- actions: analyze, health_check
- exceptions: Exception as e, KeyboardInterrupt, zmq.ZMQError as e

### PredictiveHealthMonitor

- group: utility_services
- script_path: main_pc_code/agents/predictive_health_monitor.py
- port: 5613
- health_check_port: 6613
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: PredictiveHealthMonitor
- functions: __init__, _create_tables, _load_model, _monitor_output, _identify_machine, _load_agent_configs, start_agent, stop_agent, restart_agent, handle_discovery_requests, optimize_memory, find_large_files, optimize_system, _run_windows_disk_cleanup, _get_memory_usage ...
- actions: restart_agent, clear_agent_state, restart_dependencies, restart_all_agents
- exceptions: zmq.error.ZMQError as e, zmq.error.ZMQError as e2, ImportError, Exception as e, zmq.Again, json.JSONDecodeError, (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess), subprocess.CalledProcessError as e, ImportError as e, PermissionError, zmq.error.Again, ConnectionRefusedError, KeyboardInterrupt

### PredictiveLoader

- group: gpu_infrastructure
- script_path: main_pc_code/agents/predictive_loader.py
- port: 5617
- health_check_port: 6617
- dependencies: ['RequestCoordinator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: PredictiveLoader
- functions: __init__, _get_health_status, _start_health_check, _health_check_loop, run, _prediction_loop, _predict_models, _preload_models, _handle_predict_models, _handle_record_usage, _handle_health_check, cleanup
- actions: predict_models, record_usage, health_check
- exceptions: Exception as e, KeyboardInterrupt

### ProactiveAgent

- group: audio_interface
- script_path: main_pc_code/agents/ProactiveAgent.py
- port: 5624
- health_check_port: 6624
- dependencies: ['RequestCoordinator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ProactiveAgent
- functions: __init__, _init_coordinator, _get_health_status, _perform_initialization, _load_tasks, _save_tasks, _monitor_tasks, _execute_task, _execute_reminder, add_task, add_reminder, get_tasks, handle_request, run, stop ...
- actions: add_task, add_reminder, get_tasks
- exceptions: Exception as e, zmq.error.Again, KeyboardInterrupt

### RequestCoordinator

- group: core_services
- script_path: main_pc_code/agents/request_coordinator.py
- port: 26002
- health_check_port: 27002
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: TextRequest, AudioRequest, VisionRequest, AgentResponse, CircuitBreaker:, RequestCoordinator
- functions: __init__, record_success, record_failure, allow_request, get_status, _init_zmq_sockets, _connect_to_service, _init_circuit_breakers, _listen_for_language_analysis, _start_threads, _register_service, _load_metrics, _save_metrics, _metrics_reporting_loop, _log_metrics ...
- exceptions: Exception as e, zmq.Again, Exception as cleanup_error, Exception, KeyboardInterrupt
- session/auth related occurrences: 1

### Responder

- group: language_processing
- script_path: main_pc_code/agents/responder.py
- port: 5637
- health_check_port: 6637
- dependencies: ['EmotionEngine', 'FaceRecognitionAgent', 'NLUAgent', 'StreamingTTSAgent', 'SystemDigitalTwin', 'TTSService']
- required: True
**Code Details:**
- classes: Responder
- functions: add_all_safe_globals, __init__, _connect_to_services, _connect_to_tts_services, _refresh_service_connections, _load_tts_model, face_recognition_listener, _interrupt_listener, _send_stop_to_tts_services, _start_interrupt_thread, process_message, speak, _show_visual_feedback, show_overlay, _is_light_color ...
- exceptions: ImportError as e, Exception as e, zmq.Again, json.JSONDecodeError, KeyboardInterrupt
- caching occurrences: 1

### STTService

- group: speech_services
- script_path: main_pc_code/services/stt_service.py
- port: 5800
- health_check_port: 6800
- dependencies: ['ModelManagerAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: STTService
- functions: __init__, _register_service, transcribe, batch_transcribe, queue_for_batch, _batch_processing_loop, report_error, handle_request, _get_health_status, _get_performance_metrics, run, cleanup
- actions: transcribe, batch_transcribe, queue_for_batch, health_check, performance_metrics
- exceptions: Exception as e, zmq.error.Again, KeyboardInterrupt

### SelfTrainingOrchestrator

- group: utility_services
- script_path: main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py
- port: 5660
- health_check_port: 6660
- dependencies: ['SystemDigitalTwin', 'ModelManagerAgent']
- required: True
**Code Details:**
- classes: TrainingStatus, ResourceType, TrainingCycle:, SelfTrainingOrchestrator
- functions: __init__, setup_zmq, _bind_socket_with_retry, _health_check_loop, _get_health_status, _init_db, create_training_cycle, _validate_resources, start_training_cycle, _check_resource_availability, _allocate_resources, _release_resources, _create_cycle_from_db, _run_cycle_manager, _update_cycle_progress ...
- actions: health_check, create_cycle, start_cycle, get_status
- exceptions: Exception as e, zmq.error.ZMQError as e, zmq.error.Again, ValueError, Exception, KeyboardInterrupt

### ServiceRegistry

- group: core_services
- script_path: main_pc_code/agents/service_registry_agent.py
- port: 7100
- health_check_port: 8100
- dependencies: []
- required: True
**Code Details:**
- classes: RegistryBackend, MemoryBackend:, RedisBackend:, ServiceRegistryAgent
- functions: get, set, list_agents, close, __init__, _key, handle_request, _register_agent, _get_agent_endpoint, cleanup
- actions: register_agent, get_agent_endpoint, list_agents
- exceptions: ImportError, json.JSONDecodeError, Exception as exc, KeyboardInterrupt

### SessionMemoryAgent

- group: memory_system
- script_path: main_pc_code/agents/session_memory_agent.py
- port: 5574
- health_check_port: 6574
- dependencies: ['RequestCoordinator', 'SystemDigitalTwin', 'MemoryClient']
- required: True
**Code Details:**
- classes: SessionMemoryAgent
- functions: __init__, _report_error, process_request, _create_session, _add_interaction, _get_context, _delete_session, _search_interactions, _cleanup_expired_sessions, run, _run_cleanup_thread, cleanup, _get_health_status
- actions: create_session, add_interaction, get_context, delete_session, search_interactions, health_check
- exceptions: Exception as e, KeyboardInterrupt
- session/auth related occurrences: 1

### StreamingInterruptHandler

- group: audio_interface
- script_path: main_pc_code/agents/streaming_interrupt_handler.py
- port: 5576
- health_check_port: 6576
- dependencies: ['StreamingSpeechRecognition', 'StreamingTTSAgent', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: StreamingInterruptHandler
- functions: __init__, _register_service, detect_interruption, send_tts_stop_command, publish_interrupt, run, cleanup, health_check, _get_health_status, _perform_initialization, report_error
- exceptions: Exception as e, zmq.Again, KeyboardInterrupt

### StreamingLanguageAnalyzer

- group: audio_interface
- script_path: main_pc_code/agents/streaming_language_analyzer.py
- port: 5579
- health_check_port: 6579
- dependencies: ['StreamingSpeechRecognition', 'SystemDigitalTwin', 'TranslationService']
- required: True
**Code Details:**
- classes: StreamingLanguageAnalyzer
- functions: find_available_port, __init__, _register_service, _connect_to_tagabert, _connect_to_translation_service, _contains_potential_taglish_short_words, report_health, analyze_tagalog_sentiment, analyze_language, analyze_with_llm, start, shutdown, cleanup, _process_loop, _get_health_status
- exceptions: ImportError as e, Exception as e, OSError, Exception as fallback_error, zmq.error.Again, json.JSONDecodeError, pickle.UnpicklingError, zmq.Again, KeyboardInterrupt

### StreamingSpeechRecognition

- group: audio_interface
- script_path: main_pc_code/agents/streaming_speech_recognition.py
- port: 6553
- health_check_port: 7553
- dependencies: ['FusedAudioPreprocessor', 'RequestCoordinator', 'STTService', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ResourceManager:, StreamingSpeechRecognition
- functions: __init__, get_system_load, get_batch_size, get_quantization, use_tensorrt, _connect_to_request_coordinator, _init_sockets, _connect_to_stt_service, _check_wake_word_events, _check_vad_events, apply_noise_reduction, detect_language, process_audio_loop, _cleanup_idle_models, health_broadcast_loop ...
- exceptions: ImportError as e, Exception, Exception as e, zmq.Again, (json.JSONDecodeError, UnicodeDecodeError, AttributeError), pickle.UnpicklingError as pe, Exception as pub_error, zmq.error.Again, KeyboardInterrupt, Exception as resample_error, Exception as lang_error, Exception as transcribe_error
- session/auth related occurrences: 1

### StreamingTTSAgent

- group: audio_interface
- script_path: main_pc_code/agents/streaming_tts_agent.py
- port: 5562
- health_check_port: 6562
- dependencies: ['RequestCoordinator', 'TTSService', 'SystemDigitalTwin', 'UnifiedSystemAgent']
- required: True
**Code Details:**
- classes: UltimateTTSAgent
- functions: __init__, _register_service, _connect_to_tts_service, _async_initialize_tts_engines, _add_to_cache, split_into_sentences, speak, _speak_with_tts_service, _speak_with_sapi, _speak_with_pyttsx3, _speak_with_console, audio_playback_loop, _send_health_updates, _interrupt_listener, _start_interrupt_thread ...
- exceptions: Exception as e, queue.Empty, zmq.Again, json.JSONDecodeError as e, zmq.ZMQError, KeyboardInterrupt
- caching occurrences: 1

### SystemDigitalTwin

- group: core_services
- script_path: main_pc_code/agents/system_digital_twin.py
- port: 7120
- health_check_port: 8120
- dependencies: ['ServiceRegistry']
- required: True
**Code Details:**
- classes: SystemDigitalTwinAgent
- functions: __init__, setup, _setup_zmq, _register_service, _setup_prometheus, _register_self_agent, _start_metrics_collection, _register_agent, update_agent_status, get_all_agent_statuses, _collect_metrics_loop, _fetch_current_metrics, _get_prometheus_value, _get_current_state, get_metrics_history ...
- actions: ping, get_metrics, get_history, get_all_agents, get_registered_agents, get_agent_info, simulate_load, register_agent, get_agent_endpoint, publish_event, report_error, get_ok_agents, update_vram_metrics
- exceptions: Exception as r_err, Exception as e, Exception as db_err, Exception as redis_err, Exception, zmq.error.Again, Exception as exc, (ValueError, TypeError), UnicodeDecodeError, json.JSONDecodeError, KeyboardInterrupt
- caching occurrences: 1
- session/auth related occurrences: 1

### TTSService

- group: speech_services
- script_path: main_pc_code/services/tts_service.py
- port: 5801
- health_check_port: 6801
- dependencies: ['ModelManagerAgent', 'SystemDigitalTwin', 'StreamingInterruptHandler']
- required: True
**Code Details:**
- classes: TTSService
- functions: __init__, _register_service, _add_to_cache, speak, _stream_audio, audio_playback_loop, _interrupt_listener, _start_interrupt_thread, report_error, handle_request, _get_health_status, run, cleanup
- actions: speak, stop, set_voice, health_check
- exceptions: Exception as e, queue.Empty, zmq.Again, zmq.error.Again, KeyboardInterrupt
- caching occurrences: 1

### TinyLlamaServiceEnhanced

- group: utility_services
- script_path: main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
- port: 5615
- health_check_port: 6615
- dependencies: ['ModelManagerAgent', 'SystemDigitalTwin']
- required: False
**Code Details:**
- classes: ModelState, GenerationConfig:, ResourceManager:, TinyLlamaService
- functions: __init__, get_stats, check_resources, cleanup, get_system_load, get_batch_size, get_quantization, use_tensorrt, _start_health_check, _health_check_loop, report_error, _get_health_status, _setup_zmq_socket, _load_model, _unload_model ...
- actions: generate, ensure_loaded, request_unload, resource_stats
- exceptions: ImportError as e, Exception, Exception as e, zmq.error.Again, KeyboardInterrupt
- caching occurrences: 1
- session/auth related occurrences: 1

### ToneDetector

- group: emotion_system
- script_path: main_pc_code/agents/tone_detector.py
- port: 5625
- health_check_port: 6625
- dependencies: ['EmotionEngine', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: ToneDetector
- functions: get_main_pc_code, join_path, __init__, _start_tone_monitor, _connect_to_whisper, _initialize_whisper_model, _connect_to_tagalog_analyzer, _detect_language, _analyze_tone, _record_and_transcribe, _simulate_tone_detection, handle_request, shutdown, cleanup, _get_health_status ...
- actions: get_tone
- exceptions: ImportError as e, Exception, Exception as e, KeyboardInterrupt
- caching occurrences: 1

### TranslationService

- group: language_processing
- script_path: main_pc_code/agents/translation_service.py
- port: 5595
- health_check_port: 6595
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: AdvancedTimeoutManager:, ConnectionManager:, BaseEngineClient:, NLLBEngineClient, StreamingEngineClient, RemoteGoogleEngineClient, DictionaryEngineClient, LanguageDetector:, TranslationCache:, SessionManager:, LocalPatternEngineClient, EmergencyWordEngineClient, EngineManager:, TranslationService
- functions: is_secure_zmq_enabled, __init__, calculate_timeout, record_response_time, _get_length_bucket, _create_socket, get_socket, reset_socket, cleanup, _send_request, translate, _test_tagabert_connection, _is_taglish_candidate, detect_language, get ...
- exceptions: ImportError, Exception as e, Exception as se_conn, ValueError as e, KeyboardInterrupt
- caching occurrences: 1
- session/auth related occurrences: 1

### UnifiedSystemAgent

- group: core_services
- script_path: main_pc_code/agents/unified_system_agent.py
- port: 7125
- health_check_port: 8125
- dependencies: ['SystemDigitalTwin']
- required: True
**Code Details:**
- classes: UnifiedSystemAgent
- functions: start_unified_system_agent, __init__, _create_readiness_file, _send_ready_signal, _initialize_background, _load_config, _monitor_services, _discover_services, _restart_service, handle_request, _get_service_status, _start_service, _stop_service, _cleanup_system, _get_system_info ...
- actions: start_service, stop_service, restart_service, get_service_status, list_services, cleanup_system, get_system_info
- exceptions: Exception as e, psutil.NoSuchProcess, zmq.ZMQError as e, KeyboardInterrupt

### VRAMOptimizerAgent

- group: gpu_infrastructure
- script_path: main_pc_code/agents/vram_optimizer_agent.py
- port: 5572
- health_check_port: 6572
- dependencies: ['ModelManagerAgent', 'RequestCoordinator', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: VramOptimizerAgent
- functions: __init__, _get_health_status, _load_configuration, _init_service_connections, _init_fallback_connections, start_monitoring, stop_monitoring, get_vram_usage, _consult_digital_twin, can_load_model, register_model, unregister_model, get_least_used_model, update_model_usage, _monitor_vram ...
- exceptions: Exception as e, ImportError as e, zmq.ZMQError as e, Exception, KeyboardInterrupt
- caching occurrences: 1
- session/auth related occurrences: 1

### VoiceProfilingAgent

- group: emotion_system
- script_path: main_pc_code/agents/voice_profiling_agent.py
- port: 5708
- health_check_port: 6708
- dependencies: ['EmotionEngine', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: VoiceProfilingAgent
- functions: __init__, load_config, load_voice_profiles, save_voice_profile, enroll_new_speaker, identify_speaker, update_voice_profile, handle_request, run, cleanup, _get_health_status, health_check
- exceptions: Exception as e, KeyboardInterrupt

### WakeWordDetector

- group: audio_interface
- script_path: main_pc_code/agents/wake_word_detector.py
- port: 6552
- health_check_port: 7552
- dependencies: ['AudioCapture', 'FusedAudioPreprocessor', 'SystemDigitalTwin']
- required: True
**Code Details:**
- classes: WakeWordDetector
- functions: __init__, _load_api_key, _init_zmq, _init_porcupine, _calculate_energy, _convert_audio_format, _publish_wake_word_event, _publish_health_status, _check_vad_events, _audio_capture_thread, _health_broadcast_thread, _calculate_confidence, start, stop, __enter__ ...
- exceptions: Exception as e, zmq.Again, KeyboardInterrupt
