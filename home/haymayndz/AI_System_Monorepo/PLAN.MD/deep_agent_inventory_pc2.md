# Deep Agent Inventory - pc2_code

### AdvancedRouter

- script_path: pc2_code/agents/advanced_router.py
- host: 0.0.0.0
- port: 7129
- health_check_port: 8129
- dependencies: ['TaskScheduler']
- required: True
**Code Details:**
- classes: AdvancedRouterAgent
- functions: load_network_config, detect_task_type, map_task_to_model_capabilities, __init__, setup_error_reporting, report_error, _start_health_check_thread, _health_check, _get_health_status, handle_request, run, _health_check_loop, cleanup
- actions: health_check, detect_task_type, get_model_capabilities, get_task_type_stats
- exceptions: Exception as e, zmq.error.ZMQError as e, KeyboardInterrupt

### AgentTrustScorer

- script_path: pc2_code/agents/AgentTrustScorer.py
- host: 0.0.0.0
- port: 7122
- health_check_port: 8122
- dependencies: ['HealthMonitor']
- required: True
**Code Details:**
- classes: AgentTrustScorer
- functions: load_network_config, __init__, setup_error_reporting, report_error, _init_database, _update_trust_score, _get_trust_score, _get_performance_history, handle_request, _get_health_status, cleanup, run
- actions: log_performance, get_trust_score, get_performance_history, health_check
- exceptions: Exception as e, zmq.error.ZMQError as e, KeyboardInterrupt
- caching occurrences: 1

### AsyncProcessor

- script_path: pc2_code/agents/async_processor.py
- host: 0.0.0.0
- port: 7101
- health_check_port: 8101
- dependencies: ['ResourceManager']
- required: True
**Code Details:**
- classes: ResourceManager:, TaskQueue:, AsyncProcessor
- functions: __init__, get_stats, check_resources, add_task, get_next_task, update_stats, _setup_sockets, _setup_logging, _setup_health_monitoring, monitor_health, _start_task_processor, process_requests, _process_task, _handle_task, _handle_logging ...
- exceptions: Exception as e, KeyboardInterrupt

### AuthenticationAgent

- script_path: pc2_code/agents/ForPC2/AuthenticationAgent.py
- host: 0.0.0.0
- port: 7116
- health_check_port: 8116
- dependencies: ['UnifiedUtilsAgent']
- required: True
**Code Details:**
- classes: AuthenticationAgent
- functions: load_network_config, __init__, setup_error_reporting, report_error, _cleanup_sessions_loop, _cleanup_expired_sessions, _hash_password, _generate_token, _create_session, _validate_token, handle_request, _handle_registration, _handle_login, _handle_logout, _handle_token_validation ...
- actions: register, login, logout, validate_token, health_check
- exceptions: ImportError as e, Exception as e, zmq.error.ZMQError as e, KeyboardInterrupt
- session/auth related occurrences: 1

### CacheManager

- script_path: pc2_code/agents/cache_manager.py
- host: 0.0.0.0
- port: 7102
- health_check_port: 8102
- dependencies: ['MemoryOrchestratorService']
- required: True
**Code Details:**
- classes: ResourceMonitor:, CacheManager
- functions: __init__, get_stats, check_resources, run, handle_request, process_request, get_cached_memory, cache_memory, invalidate_memory_cache, get_cache_entry, put_cache_entry, invalidate_cache_entry, flush_cache, _run_maintenance, stop ...
- actions: get_cached_memory, cache_memory, invalidate_memory_cache, get, put, invalidate, flush
- exceptions: Exception as e, KeyboardInterrupt
- caching occurrences: 1

### ContextManager

- script_path: pc2_code/agents/context_manager.py
- host: 0.0.0.0
- port: 7111
- health_check_port: 8111
- dependencies: ['MemoryOrchestratorService']
- required: True
**Code Details:**
- classes: ContextManager, ContextManagerAgent:
- functions: __init__, add_to_context, get_context, get_context_text, clear_context, _calculate_importance, _adjust_context_size, prune_context, connect_to_main_pc_service, _setup_sockets, _start_health_check, health_check_loop, _initialize_background, handle_request, run ...
- actions: add_to_context, get_context, get_context_text, clear_context, prune_context
- exceptions: zmq.error.ZMQError as e, Exception as e, KeyboardInterrupt

### DreamWorldAgent

- script_path: pc2_code/agents/DreamWorldAgent.py
- host: 0.0.0.0
- port: 7104
- health_check_port: 8104
- dependencies: ['MemoryOrchestratorService']
- required: True
**Code Details:**
- classes: ScenarioType, ScenarioTemplate:, MCTSNode:, DreamWorldAgent
- functions: __init__, add_child, update, get_ucb, _setup_sockets, _start_health_check, health_check_loop, _initialize_background, _setup_dependencies, _init_database, _load_scenario_templates, _save_simulation, _save_simulation_state, _evaluate_state, _calculate_uncertainty ...
- actions: run_simulation, get_simulation_history, create_scenario, get_scenario, update_scenario
- exceptions: zmq.error.ZMQError as e, Exception as e, KeyboardInterrupt

### DreamingModeAgent

- script_path: pc2_code/agents/DreamingModeAgent.py
- host: 0.0.0.0
- port: 7127
- health_check_port: 8127
- dependencies: ['DreamWorldAgent']
- required: True
**Code Details:**
- classes: DreamingModeAgent
- functions: load_network_config, __init__, setup_error_reporting, report_error, _start_health_check_thread, _start_scheduler_thread, _health_check, _get_health_status, start_dreaming, stop_dreaming, _dream_cycle, _record_dream_result, get_dream_status, set_dream_interval, optimize_dream_schedule ...
- actions: health_check, start_dreaming, stop_dreaming, get_dream_status, set_dream_interval, optimize_schedule
- exceptions: Exception as e, zmq.error.ZMQError as e, KeyboardInterrupt

### ExperienceTracker

- script_path: pc2_code/agents/experience_tracker.py
- host: 0.0.0.0
- port: 7112
- health_check_port: 8112
- dependencies: ['MemoryOrchestratorService']
- required: True
**Code Details:**
- classes: ExperienceTrackerAgent
- functions: load_network_config, __init__, _setup_sockets, _start_health_check, health_check_loop, _initialize_background, handle_request, run, _get_health_status, cleanup, shutdown, connect_to_main_pc_service
- actions: track_experience, get_experiences
- exceptions: Exception as e, zmq.error.ZMQError as e, KeyboardInterrupt

### FileSystemAssistantAgent

- script_path: pc2_code/agents/filesystem_assistant_agent.py
- host: 0.0.0.0
- port: 7123
- health_check_port: 8123
- dependencies: ['UnifiedUtilsAgent']
- required: True
**Code Details:**
- classes: FileSystemAssistantAgent
- functions: load_network_config, __init__, setup_error_reporting, report_error, _start_health_check_thread, _health_check_loop, _get_health_status, handle_query, get_status, run, cleanup, stop, connect_to_main_pc_service
- actions: list_dir, read_file, write_file, check_exists, delete, get_info, copy, move, create_dir, health_check
- exceptions: ImportError as e, Exception as e, zmq.error.Again, Exception, zmq.error.ZMQError as e, KeyboardInterrupt

### HealthMonitor

- script_path: pc2_code/agents/health_monitor.py
- host: 0.0.0.0
- port: 7114
- health_check_port: 8114
- dependencies: ['PerformanceMonitor']
- required: True
**Code Details:**
- classes: HealthMonitorAgent
- functions: load_network_config, __init__, _setup_sockets, _start_health_check, health_check_loop, _initialize_background, handle_request, run, _get_health_status, cleanup, shutdown, connect_to_main_pc_service
- actions: get_status, ping
- exceptions: Exception as e, zmq.error.ZMQError as e, KeyboardInterrupt

### MemoryOrchestratorService

- script_path: pc2_code/agents/memory_orchestrator_service.py
- host: 0.0.0.0
- port: 7140
- health_check_port: 8140
- dependencies: []
- required: True
**Code Details:**
- classes: MemoryEntry, MemoryStorageManager:, MemoryOrchestratorService
- functions: __init__, _get_conn, _init_database, add_or_update_memory, get_memory, get_memory_children, add_memory_relationship, get_related_memories, get_all_memories_for_lifecycle, create_context_group, add_memory_to_group, _cache_get, _cache_put, _cache_invalidate, _get_health_status ...
- exceptions: Exception as e, Exception as db_err, Exception as redis_err, (ValueError, TypeError), KeyboardInterrupt
- caching occurrences: 1

### PerformanceLoggerAgent

- script_path: pc2_code/agents/PerformanceLoggerAgent.py
- host: 0.0.0.0
- port: 7128
- health_check_port: 8128
- dependencies: []
- required: True
**Code Details:**
- classes: PerformanceLoggerAgent
- functions: __init__, _start_health_check, _health_check_loop, _get_health_status, _init_database, _cleanup_old_metrics, _log_metric, _log_resource_usage, _get_agent_metrics, _get_agent_resource_usage, handle_request, run, cleanup, stop, report_error ...
- actions: log_metric, log_resource_usage, get_agent_metrics, get_agent_resource_usage
- exceptions: ImportError as e, zmq.error.ZMQError as e, Exception as e, KeyboardInterrupt

### PerformanceMonitor

- script_path: pc2_code/agents/performance_monitor.py
- host: 0.0.0.0
- port: 7103
- health_check_port: 8103
- dependencies: ['PerformanceLoggerAgent']
- required: True
**Code Details:**
- classes: ResourceMonitor:, PerformanceMonitor
- functions: __init__, get_stats, get_averages, check_resources, _setup_logging, _setup_zmq, _setup_metrics, _start_monitoring, _broadcast_metrics, _monitor_health, _calculate_metrics, _get_health_status, log_metric, get_service_metrics, get_alerts ...
- actions: get_metrics, get_alerts, log_metric
- exceptions: Exception as e, KeyboardInterrupt

### ProactiveContextMonitor

- script_path: pc2_code/agents/ForPC2/proactive_context_monitor.py
- host: 0.0.0.0
- port: 7119
- health_check_port: 8119
- dependencies: ['ContextManager']
- required: True
**Code Details:**
- classes: ProactiveContextMonitor
- functions: load_network_config, __init__, setup_error_reporting, report_error, _start_background_threads, _context_analysis_loop, _get_health_status, handle_request, _handle_add_context, _handle_get_context_history, _handle_clear_context_history, run, cleanup, connect_to_main_pc_service
- actions: add_context, get_context_history, clear_context_history, health_check
- exceptions: ImportError as e, Exception as e, (ValueError, TypeError), zmq.error.ZMQError as e, KeyboardInterrupt

### RemoteConnectorAgent

- script_path: pc2_code/agents/remote_connector_agent.py
- host: 0.0.0.0
- port: 7124
- health_check_port: 8124
- dependencies: ['AdvancedRouter']
- required: True
**Code Details:**
- classes: RemoteConnectorAgent
- functions: load_network_config, __init__, _start_health_check_thread, _health_check_loop, _get_health_status, _calculate_cache_key, _check_cache, _save_to_cache, send_to_ollama, send_to_deepseek, check_model_status, handle_model_status_updates, handle_requests, report_error, run ...
- exceptions: ImportError as e, Exception as e, requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException as e, json.JSONDecodeError, zmq.error.Again, Exception as send_error, KeyboardInterrupt, zmq.error.ZMQError as e
- caching occurrences: 1
- session/auth related occurrences: 1

### ResourceManager

- script_path: pc2_code/agents/resource_manager.py
- host: 0.0.0.0
- port: 7113
- health_check_port: 8113
- dependencies: ['HealthMonitor']
- required: True
**Code Details:**
- classes: ResourceManager
- functions: __init__, _setup_sockets, _start_health_check, health_check_loop, _initialize_background, _init_resource_monitoring, get_current_stats, check_resources_available, allocate_resources, release_resources, get_resource_status, set_thresholds, handle_request, run, _get_health_status ...
- actions: get_stats, check_resources, allocate_resources, release_resources, get_status, set_thresholds
- exceptions: ImportError as e, zmq.error.ZMQError as e, Exception as e, KeyboardInterrupt

### SystemHealthManager

- script_path: pc2_code/agents/ForPC2/system_health_manager.py
- host: 0.0.0.0
- port: 7117
- health_check_port: 8117
- dependencies: []
- required: True
**Code Details:**
- classes: SystemHealthManager
- functions: __init__, _setup_zmq, _run_health_checks, _check_memory_orchestrator_health, _check_memory_scheduler_health, _report_error, process_request, handle_health_check, get_system_status, _get_orchestrator_status, _get_scheduler_status, cleanup, _get_health_status
- actions: health_check, get_system_status
- exceptions: Exception as e, zmq.error.Again, KeyboardInterrupt

### TaskScheduler

- script_path: pc2_code/agents/task_scheduler.py
- host: 0.0.0.0
- port: 7115
- health_check_port: 8115
- dependencies: ['AsyncProcessor']
- required: True
**Code Details:**
- classes: TaskSchedulerAgent
- functions: load_network_config, __init__, _setup_sockets, _start_health_check, health_check_loop, _initialize_background, handle_request, run, _get_health_status, cleanup, shutdown, connect_to_main_pc_service
- actions: schedule_task, ping
- exceptions: Exception as e, zmq.error.ZMQError as e, KeyboardInterrupt

### TieredResponder

- script_path: pc2_code/agents/tiered_responder.py
- host: 0.0.0.0
- port: 7100
- health_check_port: 8100
- dependencies: ['ResourceManager']
- required: True
**Code Details:**
- classes: ResourceManager:, TieredResponder
- functions: __init__, get_stats, check_resources, get_average_stats, _setup_sockets, _setup_tiers, _setup_logging, _setup_health_monitoring, monitor_health, start, _start_response_processor, process_requests, _handle_query, _get_canned_response, _handle_health_check ...
- exceptions: Exception, Exception as e, KeyboardInterrupt

### TutorAgent

- script_path: pc2_code/agents/tutor_agent.py
- host: 0.0.0.0
- port: 7108
- health_check_port: 8108
- dependencies: ['MemoryOrchestratorService']
- required: True
**Code Details:**
- classes: StudentProfile:, Lesson:, PerformanceMetrics:, AdaptiveLearningEngine:, ProgressTracker:, FeedbackGenerator:, ParentDashboard:, TutorAgent
- functions: __init__, _init_difficulty_model, _init_learning_style_model, adjust_difficulty, analyze_learning_style, update_progress, analyze_progress, _identify_weak_areas, _identify_strong_areas, _generate_recommendations, _load_feedback_templates, generate_feedback, update_dashboard, get_dashboard_data, set_goals ...
- actions: get_student, update_student, get_lesson, submit_performance, get_progress, set_goal
- exceptions: ImportError as e, Exception as e, KeyboardInterrupt

### TutoringAgent

- script_path: pc2_code/agents/tutoring_agent.py
- host: 0.0.0.0
- port: 7131
- health_check_port: 8131
- dependencies: ['MemoryOrchestratorService']
- required: True
**Code Details:**
- classes: AdvancedTutoringAgent
- functions: load_network_config, __init__, setup_error_reporting, report_error, _start_health_check, _health_check_loop, _get_health_status, _generate_lesson, _generate_fallback_lesson, handle_request, run, cleanup
- actions: generate_lesson, get_history, update_profile, health_check
- exceptions: ImportError as e, Exception as e, Exception as parse_error, zmq.error.ZMQError as e, KeyboardInterrupt
- caching occurrences: 1

### UnifiedMemoryReasoningAgent

- script_path: pc2_code/agents/unified_memory_reasoning_agent.py
- host: 0.0.0.0
- port: 7105
- health_check_port: 8105
- dependencies: ['MemoryOrchestratorService']
- required: True
**Code Details:**
- classes: ContextManager:, UnifiedMemoryReasoningAgent
- functions: __init__, add_to_context, get_context, get_context_text, clear_context, _calculate_importance, _adjust_context_size, prune_context, _perform_initialization, load_context_store, save_context_store, load_error_patterns, save_error_patterns, load_twins, save_twins ...
- actions: update_twin, get_twin, delete_twin, add_interaction, get_context, add_error_pattern, get_error_solution
- exceptions: Exception as e, KeyboardInterrupt
- session/auth related occurrences: 1

### UnifiedUtilsAgent

- script_path: pc2_code/agents/ForPC2/unified_utils_agent.py
- host: 0.0.0.0
- port: 7118
- health_check_port: 8118
- dependencies: ['SystemHealthManager']
- required: True
**Code Details:**
- classes: UnifiedUtilsAgent
- functions: load_network_config, __init__, setup_error_reporting, report_error, cleanup_temp_files, cleanup_logs, cleanup_cache, cleanup_browser_cache, _get_dir_size, run_windows_disk_cleanup, cleanup_system, _get_health_status, handle_request, run, cleanup ...
- actions: cleanup_temp_files, cleanup_logs, cleanup_cache, cleanup_browser_cache, run_windows_disk_cleanup, cleanup_system, health_check
- exceptions: ImportError as e, Exception as e, subprocess.CalledProcessError as e, zmq.error.ZMQError as e, KeyboardInterrupt
- caching occurrences: 1

### UnifiedWebAgent

- script_path: pc2_code/agents/unified_web_agent.py
- host: 0.0.0.0
- port: 7126
- health_check_port: 8126
- dependencies: ['FileSystemAssistantAgent', 'MemoryOrchestratorService']
- required: True
**Code Details:**
- classes: UnifiedWebAgent
- functions: __init__, _load_config, _create_tables, _start_interrupt_thread, _interrupt_monitor_loop, _handle_interrupt, _health_check, navigate_to_url, fill_form, _get_cached_content, _cache_content, _send_to_llm, _get_conversation_context, _enhance_search_query, _rank_search_results ...
- exceptions: ImportError as e, Exception as e, Exception as selenium_error, zmq.ZMQError as e, Exception as send_error, KeyboardInterrupt, zmq.error.Again, ImportError, zmq.error.ZMQError as e, StaleElementReferenceException, Exception as link_error, Exception as result_error, Exception as topic_error, Exception as page_error, TypeError
- caching occurrences: 1
- session/auth related occurrences: 1

### VisionProcessingAgent

- script_path: pc2_code/agents/VisionProcessingAgent.py
- host: 0.0.0.0
- port: 7150
- health_check_port: 8150
- dependencies: ['CacheManager']
- required: True
**Code Details:**
- classes: VisionProcessingAgent
- functions: __init__, handle_request, _describe_image, health_check, _get_health_status, cleanup
- exceptions: Exception as e, KeyboardInterrupt
