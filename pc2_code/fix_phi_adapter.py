"""
Emergency Fix Script for phi_adapter.py
This script will fix the syntax errors in phi_adapter.py using a simplified, minimal implementation
"""

import re
import os
import sys
import logging

def fix_phi_adapter_file():
    # Read the existing file
    input_path = 'd:/DISKARTE/Voice Assistant/phi_adapter.py'
    backup_path = 'd:/DISKARTE/Voice Assistant/phi_adapter.py.backup'
    
    # Make a backup first
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
            
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(original_content)
        
        print(f"Backup saved to {backup_path}")
    except Exception as e:
        print(f"Error making backup: {e}")
        return
    
    # Core minimal fixes - the bare essentials
    minimal_translation_prompt = '''    DEFAULT_PROMPT_TEMPLATE = """Translate to English:

{INPUT}
"""

    # Build minimal prompt for clean translation output
    @staticmethod
    def dynamic_prompt_builder(input_text, sample_size=0, debug=False):
        """Build an ultra-minimal prompt for Tagalog/Taglish→English translation."""
        # Ultra-minimal prompt for clean output
        return f"Translate to English:\\n\\n{input_text}"
        
    def build_translation_prompt(self, text, source_lang="tl", target_lang="en"):
        """Build a minimal prompt for Tagalog/Taglish→English translation."""
        # Ultra-minimal prompt for clean output
        return self.DEFAULT_PROMPT_TEMPLATE.format(INPUT=text)
'''

    # Apply fixes
    try:
        # Find the DEFAULT_PROMPT_TEMPLATE section and replace it
        pattern_start = r"DEFAULT_PORT = 5581\n\s+# Default prompt template for translations"
        pattern_end = r"# Pool of prompt examples for Tagalog/Taglish"
        
        # Find the section to replace
        match = re.search(f"{pattern_start}.*?{pattern_end}", original_content, re.DOTALL)
        
        if match:
            start_idx = match.start()
            end_idx = match.end() - len(pattern_end)
            
            # Replace the section
            modified_content = (
                original_content[:start_idx] + 
                "DEFAULT_PORT = 5581\n    # Default prompt template for translations\n" +
                minimal_translation_prompt +
                "    # Pool of prompt examples for Tagalog/Taglish" +
                original_content[end_idx + len(pattern_end):]
            )
            
            # Write the fixed content back
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
                
            print("Fixed phi_adapter.py successfully!")
            return True
        else:
            print("Could not find the section to replace. Manual fix required.")
            return False
            
    except Exception as e:
        print(f"Error applying fixes: {e}")
        return False

if __name__ == "__main__":
    if fix_phi_adapter_file():
        print("PHI ADAPTER FIXED SUCCESSFULLY!")
        print("Please restart the service to apply changes.")
    else:
        print("Fix attempt failed. Please check the backup and fix manually.")
