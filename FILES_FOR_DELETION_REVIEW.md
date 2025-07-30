# FILES FOR DELETION REVIEW

## 🔴 DEFINITE DUPLICATES & BACKUPS (SAFE TO DELETE)

### Backup Files
- `cursor_state.json.backup` (287 bytes)
- `task-state.json.backup` (8.3K)
- `workflow_memory_intelligence_fixed.py.backup` (57K)
- `workflow_memory_intelligence_fixed.py.backup2` (57K)
- `deleted_md_files_backup_20250730_024103.json` (23K)

### Test Output Files
- `test_output.txt` (447 bytes)
- `temp.hex` (137K) - hex dump file
- `testt.pyu` (1.4K) - typo/test file

### Temporary/Generated Reports
- `codebase_analysis_report.json` (45K) - from refactoring
- `refactoring_changes.json` (37K) - from refactoring
- `linting_results.json` (6.4K) - from refactoring
- `logging_implementation_report.json` (8.1K) - from refactoring
- `type_hints_report.json` (638 bytes) - from refactoring
- `md_cleanup_results.json` (6.9K) - from cleanup
- `md_cleanup_remaining_results.json` (4.9K) - from cleanup

### Log Files
- `port_changes.log` (3.3K)

## 🟡 LEGACY & OLD FILES (PROBABLY SAFE TO DELETE)

### Legacy Agent Files
- `legacy_agents.txt` (3.4K)
- `actual_legacy_agents.txt` (772 bytes)

### Old Test Files (Many duplicates/variations)
- `test.py` (1.3K) - generic test
- `testt.py` (8.4K) - duplicate/typo
- `simple_test.py` (1.1K)
- `test_simple.py` (973 bytes)
- `test_fix.py` (1.7K)
- `test_hang_fix.py` (1.4K)
- `test_prompt.py` (3.5K)
- `test_your_prompt.py` (2.0K)

### Old Scripts/Utilities
- `auto.py` - generic name, unclear purpose
- `simple_debug.py`
- `simple_check.py`
- `simple_integration.py`
- `debug_strip_error.py`
- `debug_complex_task.py`
- `debug_option_10.py`
- `debug_pattern_detection.py`
- `debug_workflow_extraction.py`

### Duplicate/Old Cleanup Scripts
- `cleanup_duplicate_classes.py` (6.5K)
- `cleanup_duplicate_tasks.py` (2.1K)
- `duplicate_classes_scanner.py` (1.8K)

### Migration Scripts (If migrations are complete)
- `migrate_hardcoded_ips.py`
- `migrate_hardcoded_ips_v2.py`
- `migrate_health_checks.py`
- `migrate_zmq_connections.py`

## 🟠 TEST FILES (REVIEW BEFORE DELETING)

### Unit Test Files (Keep if tests are active)
- `test_agent_connection.py` (1.1K)
- `test_auto_sync.py` (4.9K)
- `test_chunking.py` (2.3K)
- `test_command_chunker_integration.py` (6.3K)
- `test_command_integration.py` (7.8K)
- `test_complete_system.py` (48K)
- `test_coordinator_health.py` (1.7K)
- `test_docker_plan.py` (3.6K)
- `test_event_loop_fix.py` (6.3K)
- `test_framework.py` (11K)
- `test_full_execution_auth.py` (4.3K)
- `test_health_check.py` (1.1K)
- `test_health_simple.py` (3.0K)
- `test_imports.py` (2.6K)
- `test_improved_layer0.py` (6.4K)
- `test_mcp_memory.py` (6.0K)
- `test_memory_health.py` (7.8K)
- `test_memory_integration.py` (18K)
- `test_memory_orchestrator.py` (5.8K)
- `test_memory_orchestrator_service.py` (20K)
- `test_memory_performance.py` (22K)
- `test_memory_system.py` (15K)
- `test_memory_system_local.py` (3.8K)
- `test_multilingual_auth.py` (6.3K)
- `test_option_10.py` (2.5K)
- `test_option_10_fix.py` (2.4K)
- `test_phi3_instruct_integration.py` (9.9K)
- `test_phi3_mini.py` (7.8K)
- `test_philippines_time.py` (3.0K)
- `test_service_connection.py` (3.8K)
- `test_service_discovery.py` (870 bytes)
- `test_stability_improvements.py` (9.0K)
- `test_system_integration.py` (18K)
- `test_umra.py` (16K)
- `test_unified_error_reporting.py` (9.6K)
- `test_vram_optimizer.py` (11K)
- `test_with_rule_parser.py` (2.1K)
- `test_with_your_client.py` (1.8K)
- `test_zmq_client.py` (2.2K)
- `test_auto_chunker_simple.py` (2.2K)
- `test_advanced_extraction.py` (8.0K)

### Test Support Files
- `test-requirements.txt` (156 bytes)
- `test.yaml` (15K)
- `run_tests_in_container.sh` (634 bytes)

### Integration Test Files
- `complete_model_test.py` (16K)
- `comprehensive_system_test.py` (6.6K)
- `real_agent_communication_test.py` (14K)
- `voice_command_end_to_end_test.py` (17K)
- `smart_nlp_pipeline_test.py` (9.2K)
- `pc2_agent_status_test.py` (5.4K)
- `run_language_test_fixed.py` (4.0K)

## 🔵 UNCERTAIN FILES (NEED REVIEW)

### Template/Example Files
- `template_agent.py` (9.0K) - might be needed for reference
- `type_hints_example.py` - created during refactoring, might be useful
- `logging_config.py` - created during refactoring, might be in use

### Validation/Check Scripts (Might be useful)
- `check_active_agents.py`
- `check_agent_health.py`
- `check_agents.py`
- `check_all_agents_health.py`
- `check_ast.py`
- `check_mvs_health.py`
- `check_my_memory.py`
- `check_ports.py`
- `check_running_agents.py`
- `check_running_coordinator.py`
- `check_syntax.py`
- `check_task_command_dependencies.py`
- `validate_all_agents.py`
- `validate_final_extractor.py`
- `validate_scanner_paths.py`
- `validate_stability.py`
- `validate_stability_fixed.py`

### Fix Scripts (Check if fixes were applied)
- `fix_all_core_agents.py`
- `fix_all_health_checks.py`
- `fix_health_check_indentation.py`
- `fix_incomplete_blocks.py`
- `fix_indentation.py`
- `fix_long_task.py`
- `fix_mainpc_imports.py`
- `fix_mood_tracker.py`
- `fix_null_bytes.py`
- `fix_syntax_errors.py`
- `fix_task_router_port.py`
- `o3_batch_fix_script.py`
- `o3_port_fix_script.py`

### Batch Scripts
- `add_health_check_batch2.py`
- `add_health_check_batch3.py`
- `add_missing_health_check.py`
- `standardize_config_batch1.py`
- `verify_config_standardization_batch1.py`
- `verify_health_check_batch2.py`
- `verify_health_check_batch3.py`
- `phase3_batch2_refactoring.py`

### Startup/Launch Scripts (Check if in use)
- `fixed_layer0_startup.py`
- `improved_layer0_startup.py`
- `launch_layer0_fixed.py`
- `launch_mvs.py`
- `unified_layer0_startup.py`
- `start_mainpc_agents.py`
- `start_mainpc_core_agents.py`
- `start_mainpc_improved.py`
- `start_pc2_agents.py`

### Utility Scripts (Check usage)
- `agent_scanner.py`
- `agent_validation_checklist.py`
- `audit_all_agents.py`
- `code_analyzer.py`
- `source_code_scanner.py`
- `extract_pc2_agents.py`
- `cleanup_agents.py`
- `cleanup_imports_script.py`
- `cleanup_pc2_imports.py`
- `diagnostic_and_fix.py`
- `register_agents.py`
- `verify_registration.py`

### Integration/Demo Scripts
- `hybrid_demo.py`
- `integrate_translator_and_interrupt.py`
- `integration_complete_status.py`
- `run_consistency_fix.py`

### Memory System Files
- `memory_orchestrator_new.py` - check if this is the active version
- `create_clean_memory_orchestrator.py`
- `unified_memory_access.py`
- `test_memory_system_report.md` (6.5K)

### Workflow Files
- `workflow_memory_intelligence.py`
- `workflow_memory_intelligence_fixed.py` (+ backups above)

### Documentation (Review content first)
- `HYBRID_SYSTEM_REPORT.md`
- `IMPLEMENTATION_ACTION_PLAN.md`
- `memory-system-workflow-documentation.md`
- `todo_manager_integration_explanation.md`
- `voice_pipeline_recommendation.py`
- `WP-01_COMPLETION_REPORT.md` through `WP-10_COMPLETION_REPORT.md`

### Miscellaneous
- `ting-branch` (5.4K) - appears to be a git command typo file
- `sitecustomize.py` - Python customization, check if needed
- `payload_serialized_object.py` - check if in use
- `minimal_agent.py` - might be useful reference

## 🟣 ADDITIONAL TEST FILES IN SUBDIRECTORIES

### main_pc_code/ Test Files
- `manual_health_check_test.py` (1.2K)
- `simple_agent_health_test.py` (7.5K)
- `test_base_agent_health.py` (1.7K)
- `test_emotion_engine_minimal.py` (1.7K)
- `test_health_check.py` (3.1K)
- `test_health_monitor.py` (1.2K)
- `test_health.py` (2.1K)
- `test_health_simple.py` (556 bytes)
- `test_imports.py` (2.1K)
- `test_mood_tracker_health.py` (3.3K)
- `test_port_connection.py` (992 bytes)
- `test_single_agent.py` (2.8K)
- `test_system_digital_twin.py` (1.9K)
- `working_agent_health_test.py` (6.0K)

### pc2_code/ Test Files
- `custom_translator_test.py` (8.1K)
- `distributed_bridge_test.py` (1.2K)
- `main_pc_integration_test.py` (13.8K)
- `simple_ollama_test.py` (900 bytes)
- `simple_test_nllb.py` (3.4K)
- `simple_test.py` (3.1K)
- `test_adapter.py` (2.1K)
- `test_agent_health.py` (2.6K)
- `test_agent_integration.py` (6.0K)
- `test_all_health_checks.py` (4.7K)
- `test_async_processor.py` (1.7K)
- `test_auth_agent.py` (1.2K)
- `test_cache_manager.py` (1.6K)
- `test_cache_standalone.py` (8.4K)
- `test_contextual_memory.py` (16.3K)
- `test_contextual_translation.py` (4.8K)
- `test_dreaming_mode_agent.py` (3.6K)
- `test_dreamworld_agent.py` (1.3K)
- `test_episodic_memory_agent.py` (1.6K)
- `test_health_rep_alert.py` (356 bytes)
- (and more test files in pc2_code/)

## 📊 SUMMARY

### Definitely Delete (Safe):
- All backup files (.backup, .backup2)
- Temporary hex/output files
- Generated JSON reports from refactoring
- Log files

### Probably Delete (After Review):
- Legacy agent lists
- Old/duplicate test files
- Debug scripts
- Migration scripts (if complete)
- Fix scripts (if applied)

### Keep Until Verified:
- Active test files
- Validation/check utilities
- Template files
- Current configuration files
- Documentation until reviewed

### Phase/Validation Scripts
- `phase1_week2_day2_optimization_implementation.py`
- `phase1_week2_day2_validation_runner.py` (16K)
- `phase3_batch2_refactoring.py`
- `verify_output_pc2.txt` - output file

### Total Potential Cleanup:
- **Root directory**: ~200+ Python files, ~50+ test files
- **Subdirectories**: ~50+ test files in main_pc_code and pc2_code
- **Total size**: ~3-5 MB of space
- **Backup files alone**: ~145K

## 🎯 IMMEDIATE ACTION ITEMS

### 1. DELETE NOW (100% Safe) - 24 files, ~360KB
```bash
# Backup files
rm cursor_state.json.backup
rm task-state.json.backup
rm workflow_memory_intelligence_fixed.py.backup
rm workflow_memory_intelligence_fixed.py.backup2
rm deleted_md_files_backup_20250730_024103.json

# Test outputs
rm test_output.txt
rm temp.hex
rm testt.pyu

# Refactoring reports
rm codebase_analysis_report.json
rm refactoring_changes.json
rm linting_results.json
rm logging_implementation_report.json
rm type_hints_report.json
rm md_cleanup_results.json
rm md_cleanup_remaining_results.json

# Logs
rm port_changes.log

# Git typo
rm ting-branch

# Legacy lists
rm legacy_agents.txt
rm actual_legacy_agents.txt

# Duplicate test files
rm testt.py
rm test.py
rm simple_test.py
```

### 2. REVIEW THEN DELETE (Likely Safe) - ~50 files
- Old debug scripts (debug_*.py)
- Simple test variations (simple_*.py, test_simple.py)
- Migration scripts if complete (migrate_*.py)
- Fix scripts if applied (fix_*.py)
- Old cleanup scripts (cleanup_duplicate_*.py)

### 3. KEEP FOR NOW
- Active test suites in /tests directory
- Validation utilities (validate_*, check_*)
- Template files (template_agent.py)
- Example files (type_hints_example.py)
- Current runners and managers
- Documentation until reviewed

## RECOMMENDATION
1. Run the DELETE NOW commands first (100% safe)
2. Review LEGACY & OLD FILES section
3. Check which test files are part of active test suite
4. Verify which utilities are still being used
5. Keep templates and examples for reference