# Agents Linter Report

This report summarizes the flake8 linter errors and warnings for all agents in the `main_pc_code/config/startup_config.yaml` file. Only active, non-archived agents are included. Use this report for targeted compliance and code quality improvements.

---

## Summary

- Only agents defined in `startup_config.yaml` are included.
- Errors and warnings are grouped by agent script.
- Address all `E` (error) codes first for compliance. `W` (warning) codes are recommended but not strictly required.
- After fixing, re-run the linter and update this report.

---

## Linter Results by Agent

---

### main_pc_code/agents/ProactiveAgent.py
- blank line contains whitespace
- line too long

### main_pc_code/agents/streaming_speech_recognition.py
- line too long
- blank line contains whitespace

### main_pc_code/agents/wake_word_detector.py
No linter issues found.

### main_pc_code/agents/model_orchestrator.py
No linter issues found.

### main_pc_code/agents/voice_profiling_agent.py
- line too long
- blank line contains whitespace

### main_pc_code/agents/translation_service.py
- blank line contains whitespace
- line too long

### main_pc_code/agents/model_manager_agent.py
- blank line contains whitespace
- line too long
- redefinition of unused name

### main_pc_code/agents/nlu_agent.py
- line too long
- blank line contains whitespace

### main_pc_code/agents/predictive_health_monitor.py
- blank line contains whitespace
- line too long

### main_pc_code/agents/vram_optimizer_agent.py
- blank line contains whitespace
- line too long

---

## Next Steps for Compliance

1. Fix all `E` (error) codes for each agent first. These are required for compliance.
2. Address `W` (warning) codes as time allows.
3. After making fixes, re-run the linter and regenerate this report.
4. For any agent not listed, no issues were found.
5. If an agent is deprecated or archived, remove it from the config to avoid unnecessary checks.

---

_Last updated: 2025-07-10 15:16:12 +08:00_
*If you need a summary of the most common issues or want a grouped report (per agent), let me know!*
