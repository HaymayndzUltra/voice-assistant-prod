#!/bin/bash
# Script to set consolidated services to required=false
# This implements the 5-hub consolidation strategy

echo 'Setting MainPC consolidated services to required=false...'
yq -i '(.agent_groups.*.PredictiveHealthMonitor.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.ChainOfThoughtAgent.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.LearningOpportunityDetector.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.LearningManager.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.ActiveLearningMonitor.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.Responder.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.DynamicIdentityAgent.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.EmotionSynthesisAgent.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.STTService.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.TTSService.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.StreamingTTSAgent.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.EmotionEngine.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.MoodTrackerAgent.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.ToneDetector.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.VoiceProfilingAgent.required) = false' main_pc_code/config/startup_config.yaml
yq -i '(.agent_groups.*.EmpathyAgent.required) = false' main_pc_code/config/startup_config.yaml

echo 'Setting PC2 consolidated services to required=false...'
yq -i '(.pc2_services[] | select(.name == "SpeechRelayService")).required = false' pc2_code/config/startup_config.yaml

echo 'Consolidation complete!'
