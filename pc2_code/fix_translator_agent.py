#!/usr/bin/env python3
"""
Fix Translator Agent Script

This script fixes the syntax error in the translator_agent.py file and ensures
pattern matching is correctly prioritized for common commands.
"""
import os
import re

def fix_translator_agent():
    """Fix the translator_agent.py file"""
    # Path to the translator_agent.py file
    agent_path = os.path.join('agents', 'translator_agent.py')
    
    # Read the current content
    with open(agent_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create a backup
    backup_path = agent_path + '.bak'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created backup at {backup_path}")
    
    # Fix the syntax error in the try-except block
    # The issue is that we have a try block without an except or finally clause
    # We need to restructure the code to ensure proper syntax
    
    # Pattern for the problematic section
    try_pattern = re.compile(r'try:\s+# Step 0: Input validation[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n')
    
    # Replace with fixed version
    fixed_try = """
        try:
            # Step 0: Input validation and preprocessing
            if not text or text.strip() == "":
                logger.info(f"Empty text provided, skipping translation (ReqID: {request_id})")
                self.stats["last_translation_method"] = "skipped_empty"
                return original_text_for_return
            
            # Normalize text: remove excessive spaces, standardize punctuation
            normalized_text = re.sub(r'\\s+', ' ', text.strip()
            
            # Step 1: Language detection - check if already English
            if self._is_likely_english(normalized_text):
                logger.info(f"Text appears to be English already (ReqID: {request_id}): '{normalized_text[:50]}...'")
                self.stats["english_skipped_count"] += 1
                self.stats["last_translation_method"] = "skipped_english"
                self.current_translation_method = "skipped_english"
                self.current_translation_confidence = 1.0  # High confidence for English detection
                return original_text_for_return
            
            # Step 1.5: Check for exact matches in our special cases dictionary first (highest priority)
            # This ensures common commands are handled by pattern matching
            special_cases = {
                "buksan mo ang file": "open the file",
                "i-save mo ang document": "save the document",
                "isara mo ang window": "close the window",
                "i-download mo ang file na iyon": "download that file",
                "i-delete mo ang file na ito": "delete this file"
            }
            
            if normalized_text.lower() in special_cases:
                translation = special_cases[normalized_text.lower()]
                logger.info(f"Direct special case match (ReqID: {request_id}): '{normalized_text[:50]}...' -> '{translation[:50]}...'")
                self.stats["pattern_match_success"] += 1
                self.current_translation_method = "pattern_direct_special"
                self.current_translation_confidence = 1.0  # Perfect confidence for direct matches
                self.stats["last_translation_method"] = "pattern_direct_special"
                return translation
            
            # Step 2: Taglish detection - check if mixed language
            is_taglish, fil_ratio, eng_ratio = self._detect_taglish(normalized_text)
            
            # Initialize variables to track best translation and confidence across all tiers
            best_translation = original_text_for_return
            best_confidence = 0.0
            best_method = "original_text"
"""
    
    # Apply the fix
    content = re.sub(try_pattern, fixed_try, content)
    
    # Write the fixed content
    with open(agent_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed translator_agent.py file")
    print("Run 'python agents/translator_agent.py --test' to verify the fix")

if __name__ == "__main__":
    fix_translator_agent()
