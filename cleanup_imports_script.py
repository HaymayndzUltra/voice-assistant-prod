#!/usr/bin/env python3
"""
BaseAgent Import Standardization Script
======================================
Fixes all BaseAgent imports to use the standard path: from common.core.base_agent import BaseAgent
"""

import os
import re
from pathlib import Path

# Files that need BaseAgent import fixes (from our search results)
FILES_TO_FIX = [
    # Main PC files with wrong imports
    "main_pc_code/agents/needtoverify/custom_command_handler.py",
    "main_pc_code/agents/needtoverify/filesystem_assistant_agent.py",
    "main_pc_code/agents/needtoverify/autonomous_agent_framework.py",
    "main_pc_code/agents/needtoverify/error_handler.py",
    "main_pc_code/agents/needtoverify/command_queue.py",
    "main_pc_code/agents/needtoverify/command_suggestion.py",
    "main_pc_code/agents/needtoverify/fixed_streaming_translation.py",
    "main_pc_code/agents/needtoverify/context_bridge_agent.py",
    "main_pc_code/agents/needtoverify/command_suggestion_optimized.py",
    "main_pc_code/agents/needtoverify/distributed_launcher.py",
    "main_pc_code/agents/needtoverify/agent_utils.py",
    "main_pc_code/agents/needtoverify/auto_fixer_agent.py",
    "main_pc_code/agents/needtoverify/code_command_handler.py",
    "main_pc_code/agents/needtoverify/SessionAgent.py",
    "main_pc_code/agents/needtoverify/command_confirmation.py",
    "main_pc_code/agents/needtoverify/autogen_framework.py",
    "main_pc_code/agents/needtoverify/discovery_service.py",
    "main_pc_code/agents/needtoverify/coordinator.py",
    "main_pc_code/agents/needtoverify/command_clustering.py",
    "main_pc_code/agents/needtoverify/TimelineUIServer.py",
    "main_pc_code/agents/needtoverify/ai_studio_assistant.py",
    "main_pc_code/agents/vram_manager copy.py",
    "main_pc_code/agents/digital_twin_agent.py",
    "main_pc_code/agents/unified_system_agent_backup.py",
    "main_pc_code/agents/model_voting_adapter.py",
    "main_pc_code/agents/core_memory/context_summarizer_agent.py",
    "main_pc_code/agents/streaming_partial_transcripts.py",
    "main_pc_code/agents/personality_engine.py",
    "main_pc_code/agents/lazy_voting.py",
    "main_pc_code/agents/self_healing_agent.py",
    "main_pc_code/agents/vad_agent.py",
    "main_pc_code/agents/UnifiedSystemAgent.py",
    "main_pc_code/agents/voicemeeter_control_agent.py",
    "main_pc_code/agents/streaming_whisper_asr.py",
    "main_pc_code/agents/speech_processor.py",

    # Files using 'from main_pc_code.agents.base_agent import BaseAgent' (wrong)
    "main_pc_code/agents/unified_system_agent.py",
]

# Import patterns to fix
IMPORT_FIXES = [
    # Fix wrong BaseAgent imports
    (
        r'from main_pc_code\.src\.core\.base_agent import BaseAgent',
        'from common.core.base_agent import BaseAgent'
    ),
    (
        r'from main_pc_code\.agents\.base_agent import BaseAgent',
        'from common.core.base_agent import BaseAgent'
    ),
    # Fix any remaining old patterns
    (
        r'from src\.core\.base_agent import BaseAgent',
        'from common.core.base_agent import BaseAgent'
    ),
]

def fix_imports_in_file(file_path: str) -> bool:
    """Fix imports in a single file."""
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Apply import fixes
        for pattern, replacement in IMPORT_FIXES:
            content = re.sub(pattern, replacement, content)

        # Check if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed imports in: {file_path}")
            return True
        else:
            print(f"ℹ️  No changes needed: {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main execution function."""
    print("🔧 BaseAgent Import Standardization Script")
    print("=" * 50)

    total_files = len(FILES_TO_FIX)
    files_fixed = 0
    files_errors = 0

    for file_path in FILES_TO_FIX:
        if fix_imports_in_file(file_path):
            files_fixed += 1

    print("\n" + "=" * 50)
    print(f"📊 SUMMARY:")
    print(f"   Total files processed: {total_files}")
    print(f"   Files fixed: {files_fixed}")
    print(f"   Files with errors: {files_errors}")

    # Also remove the duplicate base_agent.py
    duplicate_base_agent = "main_pc_code/agents/base_agent.py"
    if os.path.exists(duplicate_base_agent):
        print(f"\n🗑️  Removing duplicate BaseAgent: {duplicate_base_agent}")
        try:
            os.remove(duplicate_base_agent)
            print("✅ Duplicate BaseAgent removed")
        except Exception as e:
            print(f"❌ Error removing duplicate: {e}")

    print("\n✅ BaseAgent import standardization complete!")
    print("📌 All agents now use: from common.core.base_agent import BaseAgent")

if __name__ == "__main__":
    main()
