# DEEP SCAN DELETE LIST

## 🔴 MAINPC - NON-SOT AGENT FILES (Not in startup_config.yaml)

### Duplicate/Old Versions
```bash
# Model manager duplicates
rm main_pc_code/agents/model_manager_agent_day4_optimized.py
rm main_pc_code/agents/model_manager_agent_migrated.py
rm main_pc_code/agents/model_manager_agent.py
rm main_pc_code/agents/model_manager_agent_test.py

# Emotion engine duplicates
rm main_pc_code/agents/emotion_engine_enhanced.py

# Face recognition duplicates
rm main_pc_code/agents/face_recognition_agent_optimized.py

# VRAM optimizer duplicates
rm main_pc_code/agents/vram_optimizer_agent_day4_optimized.py

# Noise reduction duplicates
rm main_pc_code/agents/noise_reduction_agent_day4_optimized.py
rm main_pc_code/agents/noise_reduction_agent.py

# NLU duplicates
rm main_pc_code/agents/nlu_agent_enhanced.py

# Memory client duplicates
rm main_pc_code/agents/memory_client_enhanced.py

# Streaming TTS duplicates
rm main_pc_code/agents/core_speech_output/streaming_tts_agent_day4_optimized.py
rm main_pc_code/agents/core_speech_output/streaming_tts_agent.py

# Other duplicates
rm main_pc_code/agents/tiered_responder.py
rm main_pc_code/agents/tiered_responder_unified.py
rm main_pc_code/agents/streaming_translation.py
rm main_pc_code/agents/streaming_interrupt.py
rm main_pc_code/agents/HumanAwarenessAgent.py  # duplicate of human_awareness_agent.py
```

### Utilities/Scripts (Not actual agents)
```bash
rm main_pc_code/agents/check_pc2_zmq_services.py
rm main_pc_code/agents/check_ports.py
rm main_pc_code/agents/error_publisher.py
rm main_pc_code/agents/generate_code_with_cga_method.py
rm main_pc_code/agents/pc2_zmq_health_report.py
rm main_pc_code/agents/pc2_zmq_health_report_win.py
rm main_pc_code/agents/pc2_zmq_protocol_finder_extended.py
rm main_pc_code/agents/pc2_zmq_protocol_finder.py
rm main_pc_code/agents/pc2_zmq_protocol_finder_win.py
rm main_pc_code/agents/record_and_transcribe.py
rm main_pc_code/agents/sd_config.py
rm main_pc_code/agents/system_digital_twin_launcher.py
rm main_pc_code/agents/test_meta_cognition.py
rm main_pc_code/agents/validate_pc2_zmq_services.py
rm main_pc_code/agents/llm_runtime_tools.py
```

### Not in SOT - Standalone Agents
```bash
rm main_pc_code/agents/context_summarizer_agent.py
rm main_pc_code/agents/dynamic_identity_agent.py  # Should be DynamicIdentityAgent.py
rm main_pc_code/agents/empathy_agent.py  # Should be EmpathyAgent.py
rm main_pc_code/agents/enhanced_vram_optimizer.py
rm main_pc_code/agents/gpu_failover_manager.py
rm main_pc_code/agents/gpu_load_balancer.py
rm main_pc_code/agents/gpu_monitoring_dashboard.py
rm main_pc_code/agents/intention_validator_agent.py  # Should be IntentionValidatorAgent.py
rm main_pc_code/agents/meta_cognition_agent.py
rm main_pc_code/agents/proactive_agent_interface.py
rm main_pc_code/agents/streaming_language_to_llm.py
rm main_pc_code/agents/trigger_word_detector.py
rm main_pc_code/agents/vision_capture_agent.py
rm main_pc_code/agents/voice_controller.py
```

### Entire needtoverify directory (56 files)
```bash
rm -rf main_pc_code/agents/needtoverify/
```

### Entire _trash_2025-06-13 directory (60+ files)
```bash
rm -rf main_pc_code/agents/_trash_2025-06-13/
```

### FORMAINPC duplicates (not in SOT)
```bash
rm main_pc_code/FORMAINPC/chain_of_thought_agent.py  # Should be ChainOfThoughtAgent.py
rm main_pc_code/FORMAINPC/cognitive_model_agent.py   # Should be CognitiveModelAgent.py
rm main_pc_code/FORMAINPC/got_tot_agent.py          # Should be GOT_TOTAgent.py
rm main_pc_code/FORMAINPC/learning_adjuster_agent.py # Should be LearningAdjusterAgent.py
rm main_pc_code/FORMAINPC/local_fine_tuner_agent.py  # Should be LocalFineTunerAgent.py
```

### Test files in agents directory
```bash
rm main_pc_code/simple_agent_health_test.py
rm main_pc_code/test_base_agent_health.py
rm main_pc_code/test_single_agent.py
rm main_pc_code/working_agent_health_test.py
```

### Other non-SOT files
```bash
rm main_pc_code/agent_health_check_validator.py
rm main_pc_code/refactor_agents.py
rm main_pc_code/validate_agent_paths.py
rm -rf main_pc_code/NEWMUSTFOLLOW/agents/  # duplicate system_digital_twin.py
rm main_pc_code/NEWMUSTFOLLOW/copy_agent_files.py
rm main_pc_code/NEWMUSTFOLLOW/find_agent_files.py
```

## 🔴 PC2 - NON-SOT AGENT FILES (Not in startup_config.yaml)

### Test files (should be in tests/)
```bash
rm pc2_code/test_agent_health.py
rm pc2_code/test_agent_integration.py
rm pc2_code/test_auth_agent.py
rm pc2_code/test_dreaming_mode_agent.py
rm pc2_code/test_dreamworld_agent.py
rm pc2_code/test_episodic_memory_agent.py
rm pc2_code/test_rca_agent.py
rm pc2_code/test_self_healing_agent.py
rm pc2_code/test_simple_agent.py
rm pc2_code/test_unified_error_agent.py
rm pc2_code/test_unified_memory_agent.py
rm pc2_code/test_unified_utils_agent.py
rm pc2_code/test_unified_web_agent.py
```

### Archive directory (old code)
```bash
rm -rf pc2_code/agents/archive/
```

### Backups directory (old versions)
```bash
rm -rf pc2_code/agents/backups/
```

### Duplicate/Wrong case files
```bash
rm pc2_code/agents/agent_trust_scorer.py      # Should be AgentTrustScorer.py
rm pc2_code/agents/dreaming_mode_agent.py     # Should be DreamingModeAgent.py
rm pc2_code/agents/dream_world_agent.py       # Should be DreamWorldAgent.py
rm pc2_code/agents/performance_logger_agent.py # Should be PerformanceLoggerAgent.py
rm pc2_code/agents/vision_processing_agent.py  # Should be VisionProcessingAgent.py
rm pc2_code/agents/authentication_agent.py     # Should be ForPC2/AuthenticationAgent.py
```

### Not in SOT files
```bash
rm pc2_code/agents/agent_utils.py
rm pc2_code/agents/auto_fixer_agent.py
rm pc2_code/agents/check_gpu.py
rm pc2_code/agents/check_pytorch_cuda.py
rm pc2_code/agents/custom_tutoring_test.py
rm pc2_code/agents/direct_emr_test.py
rm pc2_code/agents/error_bus_service.py
rm pc2_code/agents/learning_adjuster_agent.py
rm pc2_code/agents/memory_scheduler.py
rm pc2_code/agents/monitor_web_ports.py
rm pc2_code/agents/port_config.py
rm pc2_code/agents/port_health_check.py
rm pc2_code/agents/rollback_web_ports.py
rm pc2_code/agents/simple_gpu_check.py
rm pc2_code/agents/test_compliant_agent.py
rm pc2_code/agents/test_dreamworld_updates.py
rm pc2_code/agents/test_model_management.py
rm pc2_code/agents/test_translator.py
rm pc2_code/agents/test_tutoring_feature.py
rm pc2_code/agents/test_web_connections.py
rm pc2_code/agents/tutoring_service_agent.py
rm pc2_code/agents/unified_memory_reasoning_agent_simplified.py
```

### ForPC2 duplicates (not in SOT)
```bash
rm pc2_code/agents/ForPC2/error_management_system.py
rm pc2_code/agents/ForPC2/health_monitor.py
rm pc2_code/agents/ForPC2/test_task_router_health.py
rm pc2_code/agents/ForPC2/unified_monitoring.py
```

### Other non-SOT files
```bash
rm pc2_code/agent_health_check_validation.py
rm pc2_code/agent_stabilization_sweep.py
rm pc2_code/check_memory_agents.py
rm pc2_code/fix_translator_agent.py
rm pc2_code/force_second_pc_agents.py
rm pc2_code/remove_services_from_active_agents.py
rm -rf pc2_code/agents/core_agents/  # not in SOT
rm -rf pc2_code/src/core/  # not in SOT
```

## 🔵 OTHER CLEANUP FILES

### Root test/temp files (from previous scan)
```bash
rm temp.hex
rm testt.pyu
rm port_changes.log
rm test_output.txt
rm verify_output_pc2.txt
rm test.yaml
rm test.py
rm testt.py
rm simple_test.py
rm test_simple.py
```

### All txt report files
```bash
rm *.txt  # All the report txt files
```

### All JSON report files (except required ones)
```bash
rm codebase_analysis_report.json
rm refactoring_changes.json
rm linting_results.json
rm logging_implementation_report.json
rm type_hints_report.json
rm md_cleanup_results.json
rm md_cleanup_remaining_results.json
rm deleted_md_files_backup_20250730_024103.json
```

## 🟡 ADDITIONAL CLEANUP

### Backup Files
```bash
rm workflow_memory_intelligence_fixed.py.backup
rm workflow_memory_intelligence_fixed.py.backup2
rm task-state.json.backup
rm cursor_state.json.backup
```

### Legacy Files
```bash
rm actual_legacy_agents.txt
rm legacy_agents.txt
rm scripts/identify_high_risk_legacy_agents.py
rm automation/legacy_config_diff.py
rm automation/legacy_code_audit.py
```

### Entire Backup Directories
```bash
rm -rf backups/  # Contains old migration backups
rm -rf phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/
rm -rf phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/
```

### Shell Scripts (Optional - review first)
```bash
# Test scripts
rm run_tests_in_container.sh
rm main_pc_code/test_agents.sh

# Old start scripts (if using docker now)
rm main_pc_code/start.sh
rm main_pc_code/start_coordinator.sh
```

### Scripts directory cleanup
```bash
rm scripts/agent_audit.py
rm scripts/check_all_agents_health.py
rm scripts/fix_agent_health_issues.py
rm scripts/smoke_test_agents.py
rm scripts/start_agents_new.py
rm scripts/start_agents_win.py
rm scripts/start_all_agents.py
rm scripts/validate_agents.py
```

### Utils cleanup
```bash
rm main_pc_code/utils/agent_health.py
rm main_pc_code/utils/agent_supervisor.py
rm main_pc_code/utils/analyze_agent_blocking.py
```

## 📊 FINAL SUMMARY

### MainPC Cleanup:
- **needtoverify/**: 56 files
- **_trash_2025-06-13/**: 60+ files
- **Duplicates**: ~30 files
- **Non-SOT agents**: ~20 files
- **Test files**: ~10 files
- **Scripts**: ~8 files
- **Utils**: ~3 files

### PC2 Cleanup:
- **archive/**: ~30 files
- **backups/**: ~30 files
- **Test files**: 13 files
- **Non-SOT agents**: ~25 files
- **core_agents/**: ~5 files
- **Scripts**: ~4 files

### Root Cleanup:
- **Backup files**: 4 files
- **Legacy files**: 5 files
- **Test/temp files**: ~40 files
- **JSON reports**: 8 files
- **Text reports**: ~20 files
- **backups/ directory**: ~10 files

### Total: ~400+ files to delete

These are all files that are NOT defined in your SOT (startup_config.yaml files) or are clearly temporary/backup/test files.