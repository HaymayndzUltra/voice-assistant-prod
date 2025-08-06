#!/usr/bin/env python3
"""
Fix missing error publisher imports specifically for agent files
"""
import pathlib
import re
import ast

ROOT = pathlib.Path(__file__).resolve().parent.parent

def add_error_publisher_import(file_path: pathlib.Path, agent_side: str) -> bool:
    """Add missing error publisher import to a file"""
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    
    # Check if already has the import
    if agent_side == "main":
        if "from main_pc_code.agents.error_publisher import ErrorPublisher" in content:
            return False
    else:
        if "from pc2_code.utils.pc2_error_publisher import PC2ErrorPublisher" in content:
            return False
    
    lines = content.split('\n')
    
    # Find the best place to insert imports (after existing imports)
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line.strip() and not line.startswith('#') and insert_idx > 0:
            break
    
    # Insert missing import
    if agent_side == "main":
        import_stmt = "from main_pc_code.agents.error_publisher import ErrorPublisher"
    else:
        import_stmt = "from pc2_code.utils.pc2_error_publisher import PC2ErrorPublisher"
    
    lines.insert(insert_idx, import_stmt)
    
    file_path.write_text('\n'.join(lines), encoding='utf-8')
    return True

def main():
    """Main function to fix missing error publisher imports"""
    print("Fixing missing error publisher imports...")
    
    # List of agent files that need fixing based on audit output
    agent_files = [
        ("main_pc_code/agents/model_orchestrator.py", "main"),
        ("main_pc_code/agents/session_memory_agent.py", "main"),
        ("main_pc_code/agents/nlu_agent.py", "main"),
        ("main_pc_code/agents/predictive_health_monitor.py", "main"),
        ("main_pc_code/agents/learning_manager.py", "main"),
        ("main_pc_code/agents/emotion_synthesis_agent.py", "main"),
        ("main_pc_code/agents/feedback_handler.py", "main"),
        ("main_pc_code/agents/cloud_translation_service.py", "main"),
        ("main_pc_code/agents/smart_home_agent.py", "main"),
        ("main_pc_code/agents/system_digital_twin.py", "main"),
        ("main_pc_code/agents/memory_client.py", "main"),
        ("main_pc_code/agents/fused_audio_preprocessor.py", "main"),
        ("main_pc_code/agents/knowledge_base.py", "main"),
        ("main_pc_code/agents/chitchat_agent.py", "main"),
        ("main_pc_code/agents/responder.py", "main"),
        ("main_pc_code/agents/goal_manager.py", "main"),
        ("main_pc_code/agents/emotion_engine.py", "main"),
        ("main_pc_code/agents/face_recognition_agent.py", "main"),
        ("main_pc_code/agents/streaming_tts_agent.py", "main"),
        ("main_pc_code/agents/wake_word_detector.py", "main"),
        ("main_pc_code/agents/streaming_speech_recognition.py", "main"),
        ("main_pc_code/agents/active_learning_monitor.py", "main"),
        ("main_pc_code/agents/advanced_command_handler.py", "main"),
        ("main_pc_code/agents/learning_orchestration_service.py", "main"),
        ("main_pc_code/agents/learning_opportunity_detector.py", "main"),
        ("main_pc_code/agents/request_coordinator.py", "main"),
        ("main_pc_code/agents/streaming_interrupt_handler.py", "main"),
        ("main_pc_code/agents/unified_system_agent.py", "main"),
    ]
    
    for file_path_str, agent_side in agent_files:
        file_path = ROOT / file_path_str
        if file_path.exists():
            fixed = add_error_publisher_import(file_path, agent_side)
            if fixed:
                print(f"  ✓ Added error publisher import to {file_path}")
            else:
                print(f"  - {file_path} already has import")
        else:
            print(f"  ! {file_path} not found")
    
    print("Error publisher import fix completed!")

if __name__ == "__main__":
    main()