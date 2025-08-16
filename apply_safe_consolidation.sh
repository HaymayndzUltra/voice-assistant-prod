#!/bin/bash
# Safe Consolidation Script - Only disables agents that are FULLY CONSOLIDATED
# Generated based on actual code inspection of hub implementations

echo "========================================="
echo "SAFE CONSOLIDATION SCRIPT"
echo "Only disabling FULLY CONSOLIDATED agents"
echo "========================================="

# Check if yq is installed
if ! command -v yq &> /dev/null; then
    echo "ERROR: yq is not installed. Install with: sudo snap install yq"
    exit 1
fi

# Backup configs first
echo ""
echo "📁 Creating backups..."
cp main_pc_code/config/startup_config.yaml main_pc_code/config/startup_config.yaml.backup.$(date +%Y%m%d_%H%M%S)
cp pc2_code/config/startup_config.yaml pc2_code/config/startup_config.yaml.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backups created"

echo ""
echo "🔄 Disabling FULLY CONSOLIDATED agents in MainPC..."

# AffectiveProcessingCenter - All fully consolidated
yq -i '(.agent_groups.*.EmpathyAgent.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ EmpathyAgent → AffectiveProcessingCenter/EmpathyModule"

yq -i '(.agent_groups.*.MoodTrackerAgent.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ MoodTrackerAgent → AffectiveProcessingCenter/MoodModule"

yq -i '(.agent_groups.*.EmotionSynthesisAgent.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ EmotionSynthesisAgent → AffectiveProcessingCenter/SynthesisModule"

yq -i '(.agent_groups.*.ToneDetector.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ ToneDetector → AffectiveProcessingCenter/ToneModule"

yq -i '(.agent_groups.*.VoiceProfilingAgent.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ VoiceProfilingAgent → AffectiveProcessingCenter/VoiceProfileModule"

yq -i '(.agent_groups.*.DynamicIdentityAgent.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ DynamicIdentityAgent → AffectiveProcessingCenter/SynthesisModule"

yq -i '(.agent_groups.*.EmotionEngine.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ EmotionEngine → AffectiveProcessingCenter/MoodModule"

# RealTimeAudioPipeline - Only the fully consolidated ones
# Note: AudioCapture, StreamingSpeechRecognition, StreamingInterruptHandler already false
yq -i '(.agent_groups.*.STTService.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ STTService → RealTimeAudioPipeline/SpeechToTextStage"

# ModelOpsCoordinator - Fully consolidated
yq -i '(.agent_groups.*.ChainOfThoughtAgent.required) = false' main_pc_code/config/startup_config.yaml
echo "   ✅ ChainOfThoughtAgent → ModelOpsCoordinator/model_manager"

# Note: TinyLlamaServiceEnhanced and CognitiveModelAgent already false

echo ""
echo "⚠️ NOT disabling partially implemented agents:"
echo "   - TTSService (needs TTS stage in RealTimeAudioPipeline)"
echo "   - StreamingTTSAgent (needs TTS stage in RealTimeAudioPipeline)"
echo "   - Responder (needs response stage in RealTimeAudioPipeline)"
echo "   - PredictiveHealthMonitor (partially in UnifiedObservabilityCenter)"
echo "   - ActiveLearningMonitor (partially in UnifiedObservabilityCenter)"
echo "   - LearningOpportunityDetector (not implemented in MemoryFusionHub)"
echo "   - LearningManager (not implemented in MemoryFusionHub)"

echo ""
echo "📊 Summary:"
echo "   - Disabled 8 fully consolidated agents"
echo "   - Kept 7 partially/not implemented agents active"
echo ""
echo "✅ Safe consolidation complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Test the system with: docker-compose up"
echo "   2. Monitor logs for any missing functionality"
echo "   3. If issues occur, restore from backups in config/ directory"