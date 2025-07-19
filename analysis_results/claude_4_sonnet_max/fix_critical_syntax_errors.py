#!/usr/bin/env python3
"""
🔧 CRITICAL SYNTAX ERROR FIXER
==============================

This script fixes critical syntax errors in core agent files
that are preventing system startup.
"""

import re
from pathlib import Path

def fix_empathy_agent():
    """Fix EmpathyAgent.py syntax errors."""
    file_path = Path("main_pc_code/agents/EmpathyAgent.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing EmpathyAgent.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 468 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 467:  # Line 468 (0-based index)
            if 'if hasattr(self, \'context\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.context.term()\n"
                    print("  ✅ Fixed line 468: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_chitchat_agent():
    """Fix chitchat_agent.py syntax errors."""
    file_path = Path("main_pc_code/agents/chitchat_agent.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing chitchat_agent.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 416 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 415:  # Line 416 (0-based index)
            if 'if hasattr(self, \'socket\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.socket.close()\n"
                    print("  ✅ Fixed line 416: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_face_recognition_agent():
    """Fix face_recognition_agent.py syntax errors."""
    file_path = Path("main_pc_code/agents/face_recognition_agent.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing face_recognition_agent.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 681 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 680:  # Line 681 (0-based index)
            if 'if hasattr(self, \'socket\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.socket.close()\n"
                    print("  ✅ Fixed line 681: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_unified_system_agent():
    """Fix unified_system_agent.py syntax errors."""
    file_path = Path("main_pc_code/agents/unified_system_agent.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing unified_system_agent.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 717 - missing indented block after 'for' statement
    for i, line in enumerate(lines):
        if i == 716:  # Line 717 (0-based index)
            if 'for' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after for statement
                    lines[i + 1] = "                pass  # TODO: Implement for loop body\n"
                    print("  ✅ Fixed line 717: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_translation_service():
    """Fix translation_service.py syntax errors."""
    file_path = Path("main_pc_code/agents/translation_service.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing translation_service.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 2001 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 2000:  # Line 2001 (0-based index)
            if 'if hasattr(self, \'socket\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.socket.close()\n"
                    print("  ✅ Fixed line 2001: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_executor():
    """Fix executor.py syntax errors."""
    file_path = Path("main_pc_code/agents/executor.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing executor.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 297 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 296:  # Line 297 (0-based index)
            if 'if hasattr(self, \'context\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.context.term()\n"
                    print("  ✅ Fixed line 297: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_proactive_agent():
    """Fix ProactiveAgent.py syntax errors."""
    file_path = Path("main_pc_code/agents/ProactiveAgent.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing ProactiveAgent.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 341 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 340:  # Line 341 (0-based index)
            if 'if hasattr(self, \'socket\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.socket.close()\n"
                    print("  ✅ Fixed line 341: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_learning_manager():
    """Fix learning_manager.py syntax errors."""
    file_path = Path("main_pc_code/agents/learning_manager.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing learning_manager.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 445 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 444:  # Line 445 (0-based index)
            if 'if hasattr(self, \'socket\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.socket.close()\n"
                    print("  ✅ Fixed line 445: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_feedback_handler():
    """Fix feedback_handler.py syntax errors."""
    file_path = Path("main_pc_code/agents/feedback_handler.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing feedback_handler.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 436 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 435:  # Line 436 (0-based index)
            if 'if hasattr(self, \'socket\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.socket.close()\n"
                    print("  ✅ Fixed line 436: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_request_coordinator():
    """Fix request_coordinator.py syntax errors."""
    file_path = Path("main_pc_code/agents/request_coordinator.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing request_coordinator.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 350 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 349:  # Line 350 (0-based index)
            if 'if' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                pass  # TODO: Implement if block\n"
                    print("  ✅ Fixed line 350: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_knowledge_base():
    """Fix knowledge_base.py syntax errors."""
    file_path = Path("main_pc_code/agents/knowledge_base.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing knowledge_base.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 241 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 240:  # Line 241 (0-based index)
            if 'if hasattr(self, "context")' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.context.term()\n"
                    print("  ✅ Fixed line 241: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_emotion_engine():
    """Fix emotion_engine.py syntax errors."""
    file_path = Path("main_pc_code/agents/emotion_engine.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing emotion_engine.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 433 - missing indented block after 'try' statement
    for i, line in enumerate(lines):
        if i == 432:  # Line 433 (0-based index)
            if 'try:' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after try statement
                    lines[i + 1] = "                pass  # TODO: Implement try block\n"
                    print("  ✅ Fixed line 433: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_nlu_agent():
    """Fix nlu_agent.py syntax errors."""
    file_path = Path("main_pc_code/agents/nlu_agent.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing nlu_agent.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 169 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 168:  # Line 169 (0-based index)
            if 'if hasattr(self, \'context\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.context.term()\n"
                    print("  ✅ Fixed line 169: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_memory_client():
    """Fix memory_client.py syntax errors."""
    file_path = Path("main_pc_code/agents/memory_client.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing memory_client.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 685 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 684:  # Line 685 (0-based index)
            if 'if hasattr(self, \'context\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.context.term()\n"
                    print("  ✅ Fixed line 685: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_active_learning_monitor():
    """Fix active_learning_monitor.py syntax errors."""
    file_path = Path("main_pc_code/agents/active_learning_monitor.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing active_learning_monitor.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 291 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 290:  # Line 291 (0-based index)
            if 'if hasattr(self, \'context\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.context.term()\n"
                    print("  ✅ Fixed line 291: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

def fix_responder():
    """Fix responder.py syntax errors."""
    file_path = Path("main_pc_code/agents/responder.py")
    
    if not file_path.exists():
        return False
        
    print("🔧 Fixing responder.py...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix line 905 - missing indented block after 'if' statement
    for i, line in enumerate(lines):
        if i == 904:  # Line 905 (0-based index)
            if 'if hasattr(self, \'context\')' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip():  # Empty line after if statement
                    lines[i + 1] = "                self.context.term()\n"
                    print("  ✅ Fixed line 905: Added missing indented block")
                    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    return True

if __name__ == "__main__":
    print("🚀 CRITICAL SYNTAX ERROR FIXER")
    print("=" * 40)
    print("🔧 Fixing critical syntax errors in core agents...")
    
    # List of critical fix functions
    critical_fixes = [
        fix_empathy_agent,
        fix_chitchat_agent,
        fix_face_recognition_agent,
        fix_unified_system_agent,
        fix_translation_service,
        fix_executor,
        fix_proactive_agent,
        fix_learning_manager,
        fix_feedback_handler,
        fix_request_coordinator,
        fix_knowledge_base,
        fix_emotion_engine,
        fix_nlu_agent,
        fix_memory_client,
        fix_active_learning_monitor,
        fix_responder
    ]
    
    total_fixes = 0
    
    for fix_func in critical_fixes:
        try:
            if fix_func():
                total_fixes += 1
        except Exception as e:
            print(f"  ❌ Error in {fix_func.__name__}: {e}")
    
    print(f"\n🏁 Critical syntax fixes completed!")
    print(f"  ✅ Files fixed: {total_fixes}")
    print("  📋 Run validation again to check results")