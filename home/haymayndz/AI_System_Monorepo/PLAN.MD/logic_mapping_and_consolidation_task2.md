# Logic Mapping & Consolidation Proposal

## Proposed Consolidated Agent: UnifiedMemoryManagementAgent

| Original Agent | Logic/Feature | Status in UnifiedMemoryManagementAgent | Notes |
|---|---|---|---|
| MemoryClient | get_service_address | Retained |  |
| MemoryClient | __init__ | Merged | Shared across agents |
| MemoryClient | record_success | Retained |  |
| MemoryClient | record_failure | Retained |  |
| MemoryClient | is_closed | Retained |  |
| MemoryClient | get_state | Retained |  |
| MemoryClient | _initialize_client_socket | Retained |  |
| MemoryClient | _report_error | Merged | Shared across agents |
| MemoryClient | _send_request | Retained |  |
| MemoryClient | set_agent_id | Retained |  |
| MemoryClient | set_session_id | Retained |  |
| MemoryClient | create_session | Merged | Shared across agents |
| MemoryClient | add_memory | Retained |  |
| MemoryClient | get_memory | Merged | Shared across agents |
| MemoryClient | search_memory ... | Retained |  |
| MemoryClient | health_check | Merged | Shared across agents |
| MemoryClient | reset_circuit_breaker | Retained |  |
| SessionMemoryAgent | __init__ | Merged | Shared across agents |
| SessionMemoryAgent | _report_error | Merged | Shared across agents |
| SessionMemoryAgent | process_request | Merged | Shared across agents |
| SessionMemoryAgent | _create_session | Retained |  |
| SessionMemoryAgent | _add_interaction | Retained |  |
| SessionMemoryAgent | _get_context | Retained |  |
| SessionMemoryAgent | _delete_session | Retained |  |
| SessionMemoryAgent | _search_interactions | Retained |  |
| SessionMemoryAgent | _cleanup_expired_sessions | Retained |  |
| SessionMemoryAgent | run | Merged | Shared across agents |
| SessionMemoryAgent | _run_cleanup_thread | Retained |  |
| SessionMemoryAgent | cleanup | Merged | Shared across agents |
| SessionMemoryAgent | _get_health_status | Merged | Shared across agents |
| SessionMemoryAgent | create_session | Merged | Shared across agents |
| SessionMemoryAgent | add_interaction | Merged | Shared across agents |
| SessionMemoryAgent | get_context | Merged | Shared across agents |
| SessionMemoryAgent | delete_session | Retained |  |
| SessionMemoryAgent | search_interactions | Retained |  |
| SessionMemoryAgent | health_check | Merged | Shared across agents |
| KnowledgeBase | __init__ | Merged | Shared across agents |
| KnowledgeBase | _report_error | Merged | Shared across agents |
| KnowledgeBase | process_request | Merged | Shared across agents |
| KnowledgeBase | add_fact | Retained |  |
| KnowledgeBase | get_fact | Retained |  |
| KnowledgeBase | update_fact | Retained |  |
| KnowledgeBase | _update_memory_item | Retained |  |
| KnowledgeBase | search_facts | Retained |  |
| KnowledgeBase | perform_health_check | Retained |  |
| KnowledgeBase | _get_health_status | Merged | Shared across agents |
| KnowledgeBase | cleanup | Merged | Shared across agents |
| MemoryOrchestratorService | __init__ | Merged | Shared across agents |
| MemoryOrchestratorService | _get_conn | Retained |  |
| MemoryOrchestratorService | _init_database | Retained |  |
| MemoryOrchestratorService | add_or_update_memory | Retained |  |
| MemoryOrchestratorService | get_memory | Merged | Shared across agents |
| MemoryOrchestratorService | get_memory_children | Retained |  |
| MemoryOrchestratorService | add_memory_relationship | Retained |  |
| MemoryOrchestratorService | get_related_memories | Retained |  |
| MemoryOrchestratorService | get_all_memories_for_lifecycle | Retained |  |
| MemoryOrchestratorService | create_context_group | Retained |  |
| MemoryOrchestratorService | add_memory_to_group | Retained |  |
| MemoryOrchestratorService | _cache_get | Retained |  |
| MemoryOrchestratorService | _cache_put | Retained |  |
| MemoryOrchestratorService | _cache_invalidate | Retained |  |
| MemoryOrchestratorService | _get_health_status ... | Retained |  |
| CacheManager | __init__ | Merged | Shared across agents |
| CacheManager | get_stats | Retained |  |
| CacheManager | check_resources | Retained |  |
| CacheManager | run | Merged | Shared across agents |
| CacheManager | handle_request | Merged | Shared across agents |
| CacheManager | process_request | Merged | Shared across agents |
| CacheManager | get_cached_memory | Merged | Shared across agents |
| CacheManager | cache_memory | Merged | Shared across agents |
| CacheManager | invalidate_memory_cache | Merged | Shared across agents |
| CacheManager | get_cache_entry | Retained |  |
| CacheManager | put_cache_entry | Retained |  |
| CacheManager | invalidate_cache_entry | Retained |  |
| CacheManager | flush_cache | Retained |  |
| CacheManager | _run_maintenance | Retained |  |
| CacheManager | stop ... | Retained |  |
| CacheManager | get_cached_memory | Merged | Shared across agents |
| CacheManager | cache_memory | Merged | Shared across agents |
| CacheManager | invalidate_memory_cache | Merged | Shared across agents |
| CacheManager | get | Retained |  |
| CacheManager | put | Retained |  |
| CacheManager | invalidate | Retained |  |
| CacheManager | flush | Retained |  |
| UnifiedMemoryReasoningAgent | __init__ | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | add_to_context | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | get_context | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | get_context_text | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | clear_context | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | _calculate_importance | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | _adjust_context_size | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | prune_context | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | _perform_initialization | Retained |  |
| UnifiedMemoryReasoningAgent | load_context_store | Retained |  |
| UnifiedMemoryReasoningAgent | save_context_store | Retained |  |
| UnifiedMemoryReasoningAgent | load_error_patterns | Retained |  |
| UnifiedMemoryReasoningAgent | save_error_patterns | Retained |  |
| UnifiedMemoryReasoningAgent | load_twins | Retained |  |
| UnifiedMemoryReasoningAgent | save_twins ... | Retained |  |
| UnifiedMemoryReasoningAgent | update_twin | Retained |  |
| UnifiedMemoryReasoningAgent | get_twin | Retained |  |
| UnifiedMemoryReasoningAgent | delete_twin | Retained |  |
| UnifiedMemoryReasoningAgent | add_interaction | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | get_context | Merged | Shared across agents |
| UnifiedMemoryReasoningAgent | add_error_pattern | Retained |  |
| UnifiedMemoryReasoningAgent | get_error_solution | Retained |  |
| ContextManager | __init__ | Merged | Shared across agents |
| ContextManager | add_to_context | Merged | Shared across agents |
| ContextManager | get_context | Merged | Shared across agents |
| ContextManager | get_context_text | Merged | Shared across agents |
| ContextManager | clear_context | Merged | Shared across agents |
| ContextManager | _calculate_importance | Merged | Shared across agents |
| ContextManager | _adjust_context_size | Merged | Shared across agents |
| ContextManager | prune_context | Merged | Shared across agents |
| ContextManager | connect_to_main_pc_service | Merged | Shared across agents |
| ContextManager | _setup_sockets | Merged | Shared across agents |
| ContextManager | _start_health_check | Merged | Shared across agents |
| ContextManager | health_check_loop | Merged | Shared across agents |
| ContextManager | _initialize_background | Merged | Shared across agents |
| ContextManager | handle_request | Merged | Shared across agents |
| ContextManager | run ... | Retained |  |
| ContextManager | add_to_context | Merged | Shared across agents |
| ContextManager | get_context | Merged | Shared across agents |
| ContextManager | get_context_text | Merged | Shared across agents |
| ContextManager | clear_context | Merged | Shared across agents |
| ContextManager | prune_context | Merged | Shared across agents |
| ExperienceTracker | load_network_config | Retained |  |
| ExperienceTracker | __init__ | Merged | Shared across agents |
| ExperienceTracker | _setup_sockets | Merged | Shared across agents |
| ExperienceTracker | _start_health_check | Merged | Shared across agents |
| ExperienceTracker | health_check_loop | Merged | Shared across agents |
| ExperienceTracker | _initialize_background | Merged | Shared across agents |
| ExperienceTracker | handle_request | Merged | Shared across agents |
| ExperienceTracker | run | Merged | Shared across agents |
| ExperienceTracker | _get_health_status | Merged | Shared across agents |
| ExperienceTracker | cleanup | Merged | Shared across agents |
| ExperienceTracker | shutdown | Retained |  |
| ExperienceTracker | connect_to_main_pc_service | Merged | Shared across agents |
| ExperienceTracker | track_experience | Retained |  |
| ExperienceTracker | get_experiences | Retained |  |

Rationale: Consolidating MemoryClient, SessionMemoryAgent, KnowledgeBase, MemoryOrchestratorService, CacheManager, UnifiedMemoryReasoningAgent, ContextManager, ExperienceTracker reduces overlap and improves maintainability by centralizing related logic.

---

## Proposed Consolidated Agent: UnifiedTaskCoordinatorAgent

| Original Agent | Logic/Feature | Status in UnifiedTaskCoordinatorAgent | Notes |
|---|---|---|---|
| RequestCoordinator | __init__ | Merged | Shared across agents |
| RequestCoordinator | record_success | Retained |  |
| RequestCoordinator | record_failure | Retained |  |
| RequestCoordinator | allow_request | Retained |  |
| RequestCoordinator | get_status | Merged | Shared across agents |
| RequestCoordinator | _init_zmq_sockets | Retained |  |
| RequestCoordinator | _connect_to_service | Retained |  |
| RequestCoordinator | _init_circuit_breakers | Retained |  |
| RequestCoordinator | _listen_for_language_analysis | Retained |  |
| RequestCoordinator | _start_threads | Retained |  |
| RequestCoordinator | _register_service | Retained |  |
| RequestCoordinator | _load_metrics | Retained |  |
| RequestCoordinator | _save_metrics | Retained |  |
| RequestCoordinator | _metrics_reporting_loop | Retained |  |
| RequestCoordinator | _log_metrics ... | Retained |  |
| AsyncProcessor | __init__ | Merged | Shared across agents |
| AsyncProcessor | get_stats | Merged | Shared across agents |
| AsyncProcessor | check_resources | Merged | Shared across agents |
| AsyncProcessor | add_task | Retained |  |
| AsyncProcessor | get_next_task | Retained |  |
| AsyncProcessor | update_stats | Retained |  |
| AsyncProcessor | _setup_sockets | Merged | Shared across agents |
| AsyncProcessor | _setup_logging | Merged | Shared across agents |
| AsyncProcessor | _setup_health_monitoring | Merged | Shared across agents |
| AsyncProcessor | monitor_health | Merged | Shared across agents |
| AsyncProcessor | _start_task_processor | Retained |  |
| AsyncProcessor | process_requests | Merged | Shared across agents |
| AsyncProcessor | _process_task | Retained |  |
| AsyncProcessor | _handle_task | Retained |  |
| AsyncProcessor | _handle_logging ... | Retained |  |
| TaskScheduler | load_network_config | Merged | Shared across agents |
| TaskScheduler | __init__ | Merged | Shared across agents |
| TaskScheduler | _setup_sockets | Merged | Shared across agents |
| TaskScheduler | _start_health_check | Merged | Shared across agents |
| TaskScheduler | health_check_loop | Merged | Shared across agents |
| TaskScheduler | _initialize_background | Merged | Shared across agents |
| TaskScheduler | handle_request | Merged | Shared across agents |
| TaskScheduler | run | Merged | Shared across agents |
| TaskScheduler | _get_health_status | Merged | Shared across agents |
| TaskScheduler | cleanup | Merged | Shared across agents |
| TaskScheduler | shutdown | Retained |  |
| TaskScheduler | connect_to_main_pc_service | Retained |  |
| TaskScheduler | schedule_task | Retained |  |
| TaskScheduler | ping | Retained |  |
| AdvancedRouter | load_network_config | Merged | Shared across agents |
| AdvancedRouter | detect_task_type | Merged | Shared across agents |
| AdvancedRouter | map_task_to_model_capabilities | Retained |  |
| AdvancedRouter | __init__ | Merged | Shared across agents |
| AdvancedRouter | setup_error_reporting | Retained |  |
| AdvancedRouter | report_error | Retained |  |
| AdvancedRouter | _start_health_check_thread | Retained |  |
| AdvancedRouter | _health_check | Retained |  |
| AdvancedRouter | _get_health_status | Merged | Shared across agents |
| AdvancedRouter | handle_request | Merged | Shared across agents |
| AdvancedRouter | run | Merged | Shared across agents |
| AdvancedRouter | _health_check_loop | Retained |  |
| AdvancedRouter | cleanup | Merged | Shared across agents |
| AdvancedRouter | health_check | Retained |  |
| AdvancedRouter | detect_task_type | Merged | Shared across agents |
| AdvancedRouter | get_model_capabilities | Retained |  |
| AdvancedRouter | get_task_type_stats | Retained |  |
| TieredResponder | __init__ | Merged | Shared across agents |
| TieredResponder | get_stats | Merged | Shared across agents |
| TieredResponder | check_resources | Merged | Shared across agents |
| TieredResponder | get_average_stats | Retained |  |
| TieredResponder | _setup_sockets | Merged | Shared across agents |
| TieredResponder | _setup_tiers | Retained |  |
| TieredResponder | _setup_logging | Merged | Shared across agents |
| TieredResponder | _setup_health_monitoring | Merged | Shared across agents |
| TieredResponder | monitor_health | Merged | Shared across agents |
| TieredResponder | start | Retained |  |
| TieredResponder | _start_response_processor | Retained |  |
| TieredResponder | process_requests | Merged | Shared across agents |
| TieredResponder | _handle_query | Retained |  |
| TieredResponder | _get_canned_response | Retained |  |
| TieredResponder | _handle_health_check ... | Retained |  |
| ResourceManager | __init__ | Merged | Shared across agents |
| ResourceManager | _setup_sockets | Merged | Shared across agents |
| ResourceManager | _start_health_check | Merged | Shared across agents |
| ResourceManager | health_check_loop | Merged | Shared across agents |
| ResourceManager | _initialize_background | Merged | Shared across agents |
| ResourceManager | _init_resource_monitoring | Retained |  |
| ResourceManager | get_current_stats | Retained |  |
| ResourceManager | check_resources_available | Retained |  |
| ResourceManager | allocate_resources | Merged | Shared across agents |
| ResourceManager | release_resources | Merged | Shared across agents |
| ResourceManager | get_resource_status | Retained |  |
| ResourceManager | set_thresholds | Merged | Shared across agents |
| ResourceManager | handle_request | Merged | Shared across agents |
| ResourceManager | run | Merged | Shared across agents |
| ResourceManager | _get_health_status ... | Retained |  |
| ResourceManager | get_stats | Merged | Shared across agents |
| ResourceManager | check_resources | Merged | Shared across agents |
| ResourceManager | allocate_resources | Merged | Shared across agents |
| ResourceManager | release_resources | Merged | Shared across agents |
| ResourceManager | get_status | Merged | Shared across agents |
| ResourceManager | set_thresholds | Merged | Shared across agents |

Rationale: Consolidating RequestCoordinator, AsyncProcessor, TaskScheduler, AdvancedRouter, TieredResponder, ResourceManager reduces overlap and improves maintainability by centralizing related logic.

---

## Proposed Consolidated Agent: UnifiedHealthPerformanceMonitor

| Original Agent | Logic/Feature | Status in UnifiedHealthPerformanceMonitor | Notes |
|---|---|---|---|
| PredictiveHealthMonitor | __init__ | Merged | Shared across agents |
| PredictiveHealthMonitor | _create_tables | Retained |  |
| PredictiveHealthMonitor | _load_model | Retained |  |
| PredictiveHealthMonitor | _monitor_output | Retained |  |
| PredictiveHealthMonitor | _identify_machine | Retained |  |
| PredictiveHealthMonitor | _load_agent_configs | Retained |  |
| PredictiveHealthMonitor | start_agent | Retained |  |
| PredictiveHealthMonitor | stop_agent | Retained |  |
| PredictiveHealthMonitor | restart_agent | Merged | Shared across agents |
| PredictiveHealthMonitor | handle_discovery_requests | Retained |  |
| PredictiveHealthMonitor | optimize_memory | Retained |  |
| PredictiveHealthMonitor | find_large_files | Retained |  |
| PredictiveHealthMonitor | optimize_system | Retained |  |
| PredictiveHealthMonitor | _run_windows_disk_cleanup | Retained |  |
| PredictiveHealthMonitor | _get_memory_usage ... | Retained |  |
| PredictiveHealthMonitor | restart_agent | Merged | Shared across agents |
| PredictiveHealthMonitor | clear_agent_state | Retained |  |
| PredictiveHealthMonitor | restart_dependencies | Retained |  |
| PredictiveHealthMonitor | restart_all_agents | Retained |  |
| PerformanceMonitor | __init__ | Merged | Shared across agents |
| PerformanceMonitor | get_stats | Retained |  |
| PerformanceMonitor | get_averages | Retained |  |
| PerformanceMonitor | check_resources | Retained |  |
| PerformanceMonitor | _setup_logging | Retained |  |
| PerformanceMonitor | _setup_zmq | Merged | Shared across agents |
| PerformanceMonitor | _setup_metrics | Retained |  |
| PerformanceMonitor | _start_monitoring | Retained |  |
| PerformanceMonitor | _broadcast_metrics | Retained |  |
| PerformanceMonitor | _monitor_health | Retained |  |
| PerformanceMonitor | _calculate_metrics | Retained |  |
| PerformanceMonitor | _get_health_status | Merged | Shared across agents |
| PerformanceMonitor | log_metric | Merged | Shared across agents |
| PerformanceMonitor | get_service_metrics | Retained |  |
| PerformanceMonitor | get_alerts ... | Retained |  |
| PerformanceMonitor | get_metrics | Retained |  |
| PerformanceMonitor | get_alerts | Retained |  |
| PerformanceMonitor | log_metric | Merged | Shared across agents |
| PerformanceLoggerAgent | __init__ | Merged | Shared across agents |
| PerformanceLoggerAgent | _start_health_check | Merged | Shared across agents |
| PerformanceLoggerAgent | _health_check_loop | Retained |  |
| PerformanceLoggerAgent | _get_health_status | Merged | Shared across agents |
| PerformanceLoggerAgent | _init_database | Merged | Shared across agents |
| PerformanceLoggerAgent | _cleanup_old_metrics | Retained |  |
| PerformanceLoggerAgent | _log_metric | Retained |  |
| PerformanceLoggerAgent | _log_resource_usage | Retained |  |
| PerformanceLoggerAgent | _get_agent_metrics | Retained |  |
| PerformanceLoggerAgent | _get_agent_resource_usage | Retained |  |
| PerformanceLoggerAgent | handle_request | Merged | Shared across agents |
| PerformanceLoggerAgent | run | Merged | Shared across agents |
| PerformanceLoggerAgent | cleanup | Merged | Shared across agents |
| PerformanceLoggerAgent | stop | Retained |  |
| PerformanceLoggerAgent | report_error ... | Retained |  |
| PerformanceLoggerAgent | log_metric | Merged | Shared across agents |
| PerformanceLoggerAgent | log_resource_usage | Retained |  |
| PerformanceLoggerAgent | get_agent_metrics | Retained |  |
| PerformanceLoggerAgent | get_agent_resource_usage | Retained |  |
| HealthMonitor | load_network_config | Merged | Shared across agents |
| HealthMonitor | __init__ | Merged | Shared across agents |
| HealthMonitor | _setup_sockets | Retained |  |
| HealthMonitor | _start_health_check | Merged | Shared across agents |
| HealthMonitor | health_check_loop | Retained |  |
| HealthMonitor | _initialize_background | Retained |  |
| HealthMonitor | handle_request | Merged | Shared across agents |
| HealthMonitor | run | Merged | Shared across agents |
| HealthMonitor | _get_health_status | Merged | Shared across agents |
| HealthMonitor | cleanup | Merged | Shared across agents |
| HealthMonitor | shutdown | Retained |  |
| HealthMonitor | connect_to_main_pc_service | Retained |  |
| HealthMonitor | get_status | Retained |  |
| HealthMonitor | ping | Retained |  |
| SystemHealthManager | __init__ | Merged | Shared across agents |
| SystemHealthManager | _setup_zmq | Merged | Shared across agents |
| SystemHealthManager | _run_health_checks | Retained |  |
| SystemHealthManager | _check_memory_orchestrator_health | Retained |  |
| SystemHealthManager | _check_memory_scheduler_health | Retained |  |
| SystemHealthManager | _report_error | Retained |  |
| SystemHealthManager | process_request | Retained |  |
| SystemHealthManager | handle_health_check | Retained |  |
| SystemHealthManager | get_system_status | Merged | Shared across agents |
| SystemHealthManager | _get_orchestrator_status | Retained |  |
| SystemHealthManager | _get_scheduler_status | Retained |  |
| SystemHealthManager | cleanup | Merged | Shared across agents |
| SystemHealthManager | _get_health_status | Merged | Shared across agents |
| SystemHealthManager | health_check | Merged | Shared across agents |
| SystemHealthManager | get_system_status | Merged | Shared across agents |
| AgentTrustScorer | load_network_config | Merged | Shared across agents |
| AgentTrustScorer | __init__ | Merged | Shared across agents |
| AgentTrustScorer | setup_error_reporting | Retained |  |
| AgentTrustScorer | report_error | Retained |  |
| AgentTrustScorer | _init_database | Merged | Shared across agents |
| AgentTrustScorer | _update_trust_score | Retained |  |
| AgentTrustScorer | _get_trust_score | Retained |  |
| AgentTrustScorer | _get_performance_history | Retained |  |
| AgentTrustScorer | handle_request | Merged | Shared across agents |
| AgentTrustScorer | _get_health_status | Merged | Shared across agents |
| AgentTrustScorer | cleanup | Merged | Shared across agents |
| AgentTrustScorer | run | Merged | Shared across agents |
| AgentTrustScorer | log_performance | Retained |  |
| AgentTrustScorer | get_trust_score | Retained |  |
| AgentTrustScorer | get_performance_history | Retained |  |
| AgentTrustScorer | health_check | Merged | Shared across agents |

Rationale: Consolidating PredictiveHealthMonitor, PerformanceMonitor, PerformanceLoggerAgent, HealthMonitor, SystemHealthManager, AgentTrustScorer reduces overlap and improves maintainability by centralizing related logic.

---

## Proposed Consolidated Agent: UnifiedLearningAgent

| Original Agent | Logic/Feature | Status in UnifiedLearningAgent | Notes |
|---|---|---|---|
| LearningManager | __init__ | Merged | Shared across agents |
| LearningManager | _perform_initialization | Retained |  |
| LearningManager | _init_components | Retained |  |
| LearningManager | _setup_sockets | Retained |  |
| LearningManager | _init_learning_resources | Retained |  |
| LearningManager | _create_learning_session | Retained |  |
| LearningManager | _update_learning_session | Retained |  |
| LearningManager | _get_learning_session | Retained |  |
| LearningManager | _delete_learning_session | Retained |  |
| LearningManager | _adjust_learning_rate | Retained |  |
| LearningManager | handle_request | Merged | Shared across agents |
| LearningManager | health_broadcast_loop | Retained |  |
| LearningManager | run | Merged | Shared across agents |
| LearningManager | stop | Retained |  |
| LearningManager | _get_health_status ... | Retained |  |
| LearningManager | create_session | Retained |  |
| LearningManager | update_session | Retained |  |
| LearningManager | get_session | Retained |  |
| LearningManager | delete_session | Retained |  |
| LearningManager | get_learning_rate | Retained |  |
| LearningOpportunityDetector | __init__ | Merged | Shared across agents |
| LearningOpportunityDetector | _register_with_service_discovery | Merged | Shared across agents |
| LearningOpportunityDetector | _init_circuit_breakers | Merged | Shared across agents |
| LearningOpportunityDetector | _setup_zmq_connections | Retained |  |
| LearningOpportunityDetector | _init_database | Merged | Shared across agents |
| LearningOpportunityDetector | _start_background_threads | Merged | Shared across agents |
| LearningOpportunityDetector | _monitor_umra | Merged | Shared across agents |
| LearningOpportunityDetector | _monitor_coordinator | Merged | Shared across agents |
| LearningOpportunityDetector | _analyze_interactions | Merged | Shared across agents |
| LearningOpportunityDetector | _score_interaction | Retained |  |
| LearningOpportunityDetector | _detect_explicit_correction | Retained |  |
| LearningOpportunityDetector | _detect_implicit_correction | Retained |  |
| LearningOpportunityDetector | _detect_positive_reinforcement | Retained |  |
| LearningOpportunityDetector | _detect_question_answer_pattern | Retained |  |
| LearningOpportunityDetector | _detect_complex_reasoning ... | Retained |  |
| LearningOpportunityDetector | get_top_opportunities | Retained |  |
| LearningOpportunityDetector | mark_processed | Retained |  |
| LearningOpportunityDetector | get_stats | Merged | Shared across agents |
| LearningOrchestrationService | __init__ | Merged | Shared across agents |
| LearningOrchestrationService | _register_with_service_discovery | Merged | Shared across agents |
| LearningOrchestrationService | _init_circuit_breakers | Merged | Shared across agents |
| LearningOrchestrationService | _init_database | Merged | Shared across agents |
| LearningOrchestrationService | _setup_zmq | Merged | Shared across agents |
| LearningOrchestrationService | _start_background_threads | Merged | Shared across agents |
| LearningOrchestrationService | _main_loop | Merged | Shared across agents |
| LearningOrchestrationService | handle_request | Merged | Shared across agents |
| LearningOrchestrationService | _handle_new_opportunity | Retained |  |
| LearningOrchestrationService | _handle_get_training_cycles | Retained |  |
| LearningOrchestrationService | safe_uuid | Retained |  |
| LearningOrchestrationService | _get_health_status | Merged | Shared across agents |
| LearningOrchestrationService | report_error | Merged | Shared across agents |
| LearningOrchestrationService | cleanup | Merged | Shared across agents |
| LearningOrchestrationService | new_learning_opportunity | Retained |  |
| LearningOrchestrationService | get_training_cycles | Retained |  |
| LearningOrchestrationService | get_stats | Merged | Shared across agents |
| ModelEvaluationFramework | __init__ | Merged | Shared across agents |
| ModelEvaluationFramework | _register_with_service_discovery | Merged | Shared across agents |
| ModelEvaluationFramework | _init_circuit_breakers | Merged | Shared across agents |
| ModelEvaluationFramework | _init_database | Merged | Shared across agents |
| ModelEvaluationFramework | _setup_zmq | Merged | Shared across agents |
| ModelEvaluationFramework | _start_background_threads | Merged | Shared across agents |
| ModelEvaluationFramework | _main_loop | Merged | Shared across agents |
| ModelEvaluationFramework | handle_request | Merged | Shared across agents |
| ModelEvaluationFramework | _handle_log_performance_metric | Retained |  |
| ModelEvaluationFramework | _handle_get_performance_metrics | Retained |  |
| ModelEvaluationFramework | _handle_log_model_evaluation | Retained |  |
| ModelEvaluationFramework | _handle_get_model_evaluation_scores | Retained |  |
| ModelEvaluationFramework | _get_health_status | Merged | Shared across agents |
| ModelEvaluationFramework | report_error | Merged | Shared across agents |
| ModelEvaluationFramework | cleanup | Merged | Shared across agents |
| ModelEvaluationFramework | log_performance_metric | Retained |  |
| ModelEvaluationFramework | get_performance_metrics | Retained |  |
| ModelEvaluationFramework | log_model_evaluation | Retained |  |
| ModelEvaluationFramework | get_model_evaluation_scores | Retained |  |
| ModelEvaluationFramework | get_stats | Merged | Shared across agents |
| ActiveLearningMonitor | __init__ | Merged | Shared across agents |
| ActiveLearningMonitor | _is_high_value_interaction | Retained |  |
| ActiveLearningMonitor | _save_training_data | Retained |  |
| ActiveLearningMonitor | _monitor_umra | Merged | Shared across agents |
| ActiveLearningMonitor | _monitor_coordinator | Merged | Shared across agents |
| ActiveLearningMonitor | _analyze_interactions | Merged | Shared across agents |
| ActiveLearningMonitor | get_training_data_stats | Retained |  |
| ActiveLearningMonitor | shutdown | Retained |  |
| ActiveLearningMonitor | _get_health_status | Merged | Shared across agents |
| ActiveLearningMonitor | health_check | Merged | Shared across agents |
| ActiveLearningMonitor | report_error | Merged | Shared across agents |
| ActiveLearningMonitor | cleanup | Merged | Shared across agents |
| LearningAdjusterAgent | __init__ | Merged | Shared across agents |
| LearningAdjusterAgent | _init_db | Retained |  |
| LearningAdjusterAgent | _update_health_status | Retained |  |
| LearningAdjusterAgent | register_parameter | Merged | Shared across agents |
| LearningAdjusterAgent | adjust_parameter | Merged | Shared across agents |
| LearningAdjusterAgent | record_performance | Merged | Shared across agents |
| LearningAdjusterAgent | optimize_parameters | Merged | Shared across agents |
| LearningAdjusterAgent | _get_active_parameters | Retained |  |
| LearningAdjusterAgent | _analyze_parameter_trend | Retained |  |
| LearningAdjusterAgent | _get_health_status | Merged | Shared across agents |
| LearningAdjusterAgent | handle_request | Merged | Shared across agents |
| LearningAdjusterAgent | run | Merged | Shared across agents |
| LearningAdjusterAgent | cleanup | Merged | Shared across agents |
| LearningAdjusterAgent | health_check | Merged | Shared across agents |
| LearningAdjusterAgent | health_check | Merged | Shared across agents |
| LearningAdjusterAgent | register_parameter | Merged | Shared across agents |
| LearningAdjusterAgent | adjust_parameter | Merged | Shared across agents |
| LearningAdjusterAgent | record_performance | Merged | Shared across agents |
| LearningAdjusterAgent | optimize_parameters | Merged | Shared across agents |

Rationale: Consolidating LearningManager, LearningOpportunityDetector, LearningOrchestrationService, ModelEvaluationFramework, ActiveLearningMonitor, LearningAdjusterAgent reduces overlap and improves maintainability by centralizing related logic.

---

## Proposed Consolidated Agent: UnifiedTranslationService

| Original Agent | Logic/Feature | Status in UnifiedTranslationService | Notes |
|---|---|---|---|
| FixedStreamingTranslation | __init__ | Merged | Shared across agents |
| FixedStreamingTranslation | start | Merged | Shared across agents |
| FixedStreamingTranslation | stop | Retained |  |
| FixedStreamingTranslation | _monitor_loop | Retained |  |
| FixedStreamingTranslation | report_error | Merged | Shared across agents |
| FixedStreamingTranslation | _update_metrics | Retained |  |
| FixedStreamingTranslation | get_best_service | Retained |  |
| FixedStreamingTranslation | get_service_stats | Retained |  |
| FixedStreamingTranslation | get | Retained |  |
| FixedStreamingTranslation | set | Retained |  |
| FixedStreamingTranslation | clear | Retained |  |
| FixedStreamingTranslation | cleanup | Merged | Shared across agents |
| FixedStreamingTranslation | calculate_timeout | Merged | Shared across agents |
| FixedStreamingTranslation | record_response_time | Merged | Shared across agents |
| FixedStreamingTranslation | get_timeout_stats ... | Retained |  |
| NLLBAdapter | __init__ | Merged | Shared across agents |
| NLLBAdapter | generate | Retained |  |
| NLLBAdapter | to | Retained |  |
| NLLBAdapter | setup_language_mappings | Retained |  |
| NLLBAdapter | __call__ | Retained |  |
| NLLBAdapter | batch_decode | Retained |  |
| NLLBAdapter | report_error | Merged | Shared across agents |
| NLLBAdapter | _load_model | Retained |  |
| NLLBAdapter | _unload_model | Retained |  |
| NLLBAdapter | translate_text | Retained |  |
| NLLBAdapter | _monitor_resources | Retained |  |
| NLLBAdapter | handle_requests | Retained |  |
| NLLBAdapter | run | Retained |  |
| NLLBAdapter | _get_health_status | Merged | Shared across agents |
| NLLBAdapter | cleanup | Merged | Shared across agents |
| TranslationService | is_secure_zmq_enabled | Retained |  |
| TranslationService | __init__ | Merged | Shared across agents |
| TranslationService | calculate_timeout | Merged | Shared across agents |
| TranslationService | record_response_time | Merged | Shared across agents |
| TranslationService | _get_length_bucket | Retained |  |
| TranslationService | _create_socket | Retained |  |
| TranslationService | get_socket | Retained |  |
| TranslationService | reset_socket | Retained |  |
| TranslationService | cleanup | Merged | Shared across agents |
| TranslationService | _send_request | Retained |  |
| TranslationService | translate | Retained |  |
| TranslationService | _test_tagabert_connection | Retained |  |
| TranslationService | _is_taglish_candidate | Retained |  |
| TranslationService | detect_language | Retained |  |
| TranslationService | get ... | Retained |  |
| StreamingLanguageAnalyzer | find_available_port | Retained |  |
| StreamingLanguageAnalyzer | __init__ | Merged | Shared across agents |
| StreamingLanguageAnalyzer | _register_service | Retained |  |
| StreamingLanguageAnalyzer | _connect_to_tagabert | Retained |  |
| StreamingLanguageAnalyzer | _connect_to_translation_service | Retained |  |
| StreamingLanguageAnalyzer | _contains_potential_taglish_short_words | Retained |  |
| StreamingLanguageAnalyzer | report_health | Retained |  |
| StreamingLanguageAnalyzer | analyze_tagalog_sentiment | Retained |  |
| StreamingLanguageAnalyzer | analyze_language | Retained |  |
| StreamingLanguageAnalyzer | analyze_with_llm | Retained |  |
| StreamingLanguageAnalyzer | start | Merged | Shared across agents |
| StreamingLanguageAnalyzer | shutdown | Retained |  |
| StreamingLanguageAnalyzer | cleanup | Merged | Shared across agents |
| StreamingLanguageAnalyzer | _process_loop | Retained |  |
| StreamingLanguageAnalyzer | _get_health_status | Merged | Shared across agents |

Rationale: Consolidating FixedStreamingTranslation, NLLBAdapter, TranslationService, StreamingLanguageAnalyzer reduces overlap and improves maintainability by centralizing related logic.

---

## Proposed Consolidated Agent: UnifiedVisionProcessingAgent

| Original Agent | Logic/Feature | Status in UnifiedVisionProcessingAgent | Notes |
|---|---|---|---|
| FaceRecognitionAgent | __init__ | Merged | Shared across agents |
| FaceRecognitionAgent | update | Retained |  |
| FaceRecognitionAgent | get_bbox | Retained |  |
| FaceRecognitionAgent | _load_emotion_model | Retained |  |
| FaceRecognitionAgent | _load_voice_model | Retained |  |
| FaceRecognitionAgent | _start_voice_processing | Retained |  |
| FaceRecognitionAgent | process_voice | Retained |  |
| FaceRecognitionAgent | analyze_emotion | Retained |  |
| FaceRecognitionAgent | get_emotion_trend | Retained |  |
| FaceRecognitionAgent | detect_blink | Retained |  |
| FaceRecognitionAgent | detect_motion | Retained |  |
| FaceRecognitionAgent | detect_anti_spoofing | Retained |  |
| FaceRecognitionAgent | is_live | Retained |  |
| FaceRecognitionAgent | load_privacy_zones | Retained |  |
| FaceRecognitionAgent | apply_privacy ... | Retained |  |
| FaceRecognitionAgent | health_check | Merged | Shared across agents |
| FaceRecognitionAgent | process_frame | Retained |  |
| VisionProcessingAgent | __init__ | Merged | Shared across agents |
| VisionProcessingAgent | handle_request | Retained |  |
| VisionProcessingAgent | _describe_image | Retained |  |
| VisionProcessingAgent | health_check | Merged | Shared across agents |
| VisionProcessingAgent | _get_health_status | Retained |  |
| VisionProcessingAgent | cleanup | Retained |  |

Rationale: Consolidating FaceRecognitionAgent, VisionProcessingAgent reduces overlap and improves maintainability by centralizing related logic.

---

## Rationale, Benefits & Risks for Each Consolidation

### UnifiedMemoryManagementAgent
- Benefits:
  - Eliminates round-trip latency between separate memory/caching/context agents.
  - Single authoritative schema for memory entries, reducing inconsistency bugs.
  - Simplified client SDK; all memory operations handled via one endpoint.
  - Shared cache avoids duplicate reads/writes and enables smarter eviction.
- Risks / Considerations:
  - Larger code-base may increase blast-radius of failures → mitigate with modular package folders and rigorous unit tests.
  - Need to maintain backward-compatibility ZMQ API for external callers (provide adapter shim for deprecation period).
  - Migration script required to move existing SQLite + Redis data into unified store.

### UnifiedTaskCoordinatorAgent
- Benefits:
  - Consolidates queueing, scheduling and routing, preventing circular/cascading task dispatch.
  - Single circuit-breaker set with global visibility of downstream agents.
  - Easier to implement QoS and global prioritisation (e.g., voice interrupts vs background training).
- Risks / Considerations:
  - Throughput bottleneck if implemented single-threaded → design with worker-pool or async IO.
  - ResourceManager merge means careful dead-lock avoidance on allocate/release paths.
  - Must maintain per-machine health-check endpoints for blue/green deployment.

### UnifiedHealthPerformanceMonitor
- Benefits:
  - Removes duplicate metrics collectors and loggers.
  - Provides one consolidated dashboard (Prometheus/Grafana) and single error-bus publisher.
  - Fosters holistic view for self-healing logic (predictive + reactive combined).
- Risks / Considerations:
  - Different sampling frequencies today (PredictiveHealthMonitor 1s vs PerformanceMonitor 5s) – harmonise with adaptive polling.
  - TrustScore logic depends on historical metrics; ensure DB schema upgraded not lost.

### UnifiedLearningAgent
- Benefits:
  - Collapses six closely related learning agents into cohesive pipeline (opportunity detect → cycle orchestrate → evaluation → parameter tuning).
  - Reduces inter-process serialization cost for large training artifacts.
  - Easier A/B experimentation with feature flags inside one code-base.
- Risks / Considerations:
  - LearningAdjuster uses blocking long-running jobs; integrate via async task queue inside unified agent.
  - Ensure GPU resource contention resolved with UnifiedTaskCoordinator hand-shake.

### UnifiedTranslationService
- Benefits:
  - One streaming translation pipeline with pluggable adapters (NLLB, Whisper, etc.).
  - Deduplicates per-language caches and timeout logic.
  - Lowers memory usage by sharing tokenizer + vocab tables.
- Risks / Considerations:
  - Existing downstream agents rely on different gRPC/ZMQ message shape; provide compatibility layer.
  - Performance regression risk while refactoring decoding loops – benchmark before rollout.

### UnifiedVisionProcessingAgent
- Benefits:
  - Combines face recognition and generic image description enabling code re-use of OpenCV/FFmpeg stack.
  - Shared model cache for detection & classification avoids double GPU loads.
- Risks / Considerations:
  - FaceRecognition pipeline real-time; VisionProcessing batch – need internal priority queue.
  - Privacy constraints (privacy zones) must be preserved; compliance review required.

---
