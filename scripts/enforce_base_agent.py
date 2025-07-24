#!/usr/bin/env python3
"""
enforce_base_agent.py

This script enforces BaseAgent inheritance on all agent classes that should inherit from it.
It uses Python's ast module for safe code manipulation.

Usage:
    python3 scripts/enforce_base_agent.py
"""

import ast
import os
import sys
import logging
from typing import List, Tuple, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# List of files to process (from the health check audit report)
TARGET_FILES = [
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/src/core/task_router.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/ChainOfThoughtAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/GOT_TOTAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vram_optimizer_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/coordinator_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/GoalOrchestratorAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/IntentionValidatorAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/DynamicIdentityAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/EmpathyAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/ProactiveAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/predictive_loader.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/EnhancedModelRouter.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/NLLBAdapter.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/LearningAdjusterAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/LocalFineTunerAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/CognitiveModelAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/FORMAINPC/consolidated_translator.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/emotion_engine.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/mood_tracker_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/human_awareness_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/emotion_synthesis_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tone_detector.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/voice_profiling_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/nlu_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/advanced_command_handler.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/chitchat_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/feedback_handler.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_language_analyzer.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/session_memory_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/memory_manager.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/src/memory/memory_orchestrator.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/src/memory/memory_client.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/learning_manager.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/knowledge_base.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/MetaCognitionAgent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/active_learning_monitor.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/MultiAgentSwarmManager.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_connector.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_cache.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_tts_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_interrupt_handler.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/code_generator_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_audio_capture.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/src/audio/fused_audio_preprocessor.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_speech_recognition.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/language_and_translation_coordinator.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/src/vision/vision_capture_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/face_recognition_agent.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/predictive_health_monitor.py",
    "/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/system_digital_twin.py"
]

class BaseAgentEnforcer(ast.NodeVisitor):
    """AST visitor to enforce BaseAgent inheritance on agent classes."""
    
    def __init__(self):
        self.imports = set()
        self.class_nodes = []
        self.has_base_agent_import = False
        self.has_base_agent_inheritance = False
        self.modified_class_name = None
    
    def visit_Import(self, node):
        """Process import statements."""
        for name in node.names:
            self.imports.add(name.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Process from-import statements."""
        if node.module:
            # Check if BaseAgent is already imported (with any import path)
            if node.module.endswith('base_agent') and any(alias.name == 'BaseAgent' for alias in node.names):
                self.has_base_agent_import = True
            
            # Add all imports to our tracking set
            for name in node.names:
                self.imports.add(f"{node.module}.{name.name}")
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Process class definitions."""
        self.class_nodes.append(node)
        
        # Check if this class already inherits from BaseAgent
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseAgent':
                self.has_base_agent_inheritance = True
            elif isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                # Handle cases like src.core.base_agent.BaseAgent
                if base.attr == 'BaseAgent':
                    self.has_base_agent_inheritance = True
        
        self.generic_visit(node)

def find_main_agent_class(tree) -> Optional[ast.ClassDef]:
    """
    Find the main agent class in the file.
    Strategy: Look for classes with 'Agent' in the name.
    """
    visitor = BaseAgentEnforcer()
    visitor.visit(tree)
    
    # If there are no classes, return None
    if not visitor.class_nodes:
        return None
    
    # First, look for classes with 'Agent' in the name
    agent_classes = [node for node in visitor.class_nodes if 'Agent' in node.name]
    
    # If we found some, return the first one
    if agent_classes:
        return agent_classes[0]
    
    # Otherwise, return the first class (best guess)
    return visitor.class_nodes[0]

def enforce_base_agent(file_path: str) -> Tuple[bool, str]:
    """
    Enforce BaseAgent inheritance on the main class in the file.
    
    Args:
        file_path: Path to the Python file to process
        
    Returns:
        Tuple of (success, message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Parse the source code into an AST
        tree = ast.parse(source)
        
        # Analyze the file
        visitor = BaseAgentEnforcer()
        visitor.visit(tree)
        
        # If the file already has BaseAgent inheritance, we're done
        if visitor.has_base_agent_inheritance:
            return True, f"SKIPPED: {os.path.basename(file_path)} already inherits from BaseAgent"
        
        # Find the main agent class
        main_class = find_main_agent_class(tree)
        if not main_class:
            return False, f"ERROR: No suitable class found in {os.path.basename(file_path)}"
        
        # Add BaseAgent to the class's bases
        main_class.bases.append(ast.Name(id='BaseAgent', ctx=ast.Load()))
        visitor.modified_class_name = main_class.name
        
        # Add BaseAgent import if needed
        if not visitor.has_base_agent_import:
            # Create an import statement with the correct import path
            import_node = ast.ImportFrom(
                module='main_pc_code.src.core.base_agent',
                names=[ast.alias(name='BaseAgent', asname=None)],
                level=0
            )
            
            # Insert the import at the beginning of the file
            # (after any docstrings or other imports)
            insert_pos = 0
            for i, node in enumerate(tree.body):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    insert_pos = i + 1
                elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                    # This is a docstring
                    insert_pos = i + 1
                else:
                    break
            
            tree.body.insert(insert_pos, import_node)
        
        # Generate the modified source code
        modified_source = ast.unparse(tree)
        
        # Write the modified source back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_source)
        
        return True, f"SUCCESS: Enforced BaseAgent inheritance on {visitor.modified_class_name} in {os.path.basename(file_path)}"
    
    except SyntaxError as e:
        return False, f"SYNTAX ERROR: {os.path.basename(file_path)}: {str(e)}"
    except Exception as e:
        return False, f"ERROR: {os.path.basename(file_path)}: {str(e)}"

def main():
    """Main entry point."""
    logger.info("Starting BaseAgent inheritance enforcement")
    logger.info(f"Processing {len(TARGET_FILES)} files")
    
    results = {
        'success': 0,
        'skipped': 0,
        'error': 0,
        'syntax_error': 0
    }
    
    error_files = []
    
    # Process each file
    for file_path in TARGET_FILES:
        success, message = enforce_base_agent(file_path)
        
        if success:
            if "SKIPPED" in message:
                results['skipped'] += 1
            else:
                results['success'] += 1
            logger.info(message)
        else:
            if "SYNTAX ERROR" in message:
                results['syntax_error'] += 1
            else:
                results['error'] += 1
            logger.error(message)
            error_files.append(os.path.basename(file_path))
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("ENFORCEMENT SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total files processed: {len(TARGET_FILES)}")
    logger.info(f"Successfully modified: {results['success']}")
    logger.info(f"Already compliant: {results['skipped']}")
    logger.info(f"Syntax errors: {results['syntax_error']}")
    logger.info(f"Other errors: {results['error']}")
    
    if error_files:
        logger.info("\nFiles with errors:")
        for file in error_files:
            logger.info(f"  - {file}")
    
    logger.info("=" * 80)
    
    return 0 if results['error'] + results['syntax_error'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 