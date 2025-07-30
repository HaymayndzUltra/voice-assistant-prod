#!/usr/bin/env python3
"""
🤖 Barok to High-Level Prompt Converter
Converts informal Filipino/English input into professional Cursor AI prompts
"""

import re
import json
from typing import Dict, List, Tuple
from datetime import datetime

class BarokToPromptConverter:
    def __init__(self):
        # Common Filipino tech terms and their formal equivalents
        self.filipino_tech_mapping = {
            # Common shortcuts
            "gawa": "create",
            "gumawa": "create", 
            "gawin": "implement",
            "ayusin": "fix",
            "ifix": "fix",
            "baguhin": "modify",
            "palitan": "replace",
            "tanggalin": "remove",
            "idagdag": "add",
            "dagdagan": "add more",
            "i-update": "update",
            "i-check": "check",
            "tignan": "inspect",
            "hanapin": "search",
            "kopyahin": "copy",
            "ilipat": "move",
            "i-test": "test",
            "i-debug": "debug",
            "i-refactor": "refactor",
            "linisin": "clean",
            "i-optimize": "optimize",
            
            # Common words
            "yung": "the",
            "ung": "the",
            "ng": "of",
            "sa": "in",
            "para": "for",
            "kung": "if",
            "tapos": "then",
            "tsaka": "and",
            "at": "and",
            "o": "or",
            "lahat": "all",
            "mga": "multiple",
            "ito": "this",
            "yan": "that",
            "yun": "that",
            "dito": "here",
            "dun": "there",
            "bakit": "why",
            "paano": "how",
            "saan": "where",
            "ano": "what",
            "kailan": "when",
            "pag": "when",
            "mo": "",  # possessive, often not needed in English
            "ka": "",  # you (informal), often contextual
            
            # Additional common terms
            "bago": "new",
            "bagong": "new",
            "luma": "old",
            "mabilis": "fast",
            "mas mabilis": "faster",
            "mabagal": "slow",
            "malaki": "large",
            "maliit": "small",
            "marami": "many",
            "konti": "few",
            "hindi": "not",
            "gumagana": "working",
            "sira": "broken",
            "mali": "wrong",
            "tama": "correct",
            "kulang": "missing",
            "sobra": "excess",
            
            # Tech-specific
            "function": "function",
            "fungksyon": "function",
            "klase": "class", 
            "variable": "variable",
            "baryabol": "variable",
            "database": "database",
            "file": "file",
            "folder": "folder",
            "code": "code",
            "error": "error",
            "bug": "bug",
            "feature": "feature",
            "button": "button",
            "form": "form",
            "table": "table",
            "api": "API",
            "backend": "backend",
            "frontend": "frontend",
            "server": "server",
            "client": "client",
            
            # Action phrases
            "i-save": "save",
            "i-load": "load",
            "i-download": "download",
            "i-upload": "upload",
            "i-delete": "delete",
            "i-edit": "edit",
            "i-run": "run",
            "i-stop": "stop",
            "i-start": "start",
            "i-restart": "restart"
        }
        
        # Intent patterns
        self.intent_patterns = {
            "create": ["gawa", "gumawa", "create", "new", "bagong"],
            "fix": ["ayusin", "fix", "repair", "debug", "solve"],
            "modify": ["baguhin", "change", "modify", "update", "edit"],
            "add": ["dagdag", "add", "include", "insert"],
            "remove": ["tanggal", "delete", "remove", "clear"],
            "search": ["hanap", "find", "search", "look"],
            "test": ["test", "check", "verify", "validate"],
            "refactor": ["refactor", "improve", "optimize", "clean"],
            "implement": ["gawin", "implement", "build", "develop"],
            "analyze": ["analyze", "check", "review", "inspect"]
        }
        
        # Component patterns
        self.component_patterns = {
            "gui": ["gui", "interface", "ui", "screen", "window"],
            "database": ["database", "db", "data", "storage"],
            "api": ["api", "endpoint", "service", "backend"],
            "function": ["function", "method", "fungksyon", "proseso"],
            "class": ["class", "klase", "object"],
            "file": ["file", "document", "script"],
            "feature": ["feature", "functionality", "kakayahan"],
            "button": ["button", "btn", "pindutan"],
            "form": ["form", "input", "entry"],
            "view": ["view", "page", "screen", "display"]
        }
        
        # Context enhancers
        self.context_enhancers = {
            "gui": "in the GUI application",
            "database": "in the database layer",
            "api": "in the API endpoints",
            "frontend": "in the frontend components",
            "backend": "in the backend services",
            "test": "with proper unit tests",
            "async": "using asynchronous operations",
            "error": "with comprehensive error handling"
        }

    def detect_intent(self, text: str) -> str:
        """Detect the primary intent from the text"""
        text_lower = text.lower()
        
        for intent, keywords in self.intent_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return intent
        
        return "implement"  # default intent

    def detect_components(self, text: str) -> List[str]:
        """Detect what components/areas are mentioned"""
        text_lower = text.lower()
        detected = []
        
        for component, keywords in self.component_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected.append(component)
                    break
        
        return detected

    def extract_specifics(self, text: str) -> Dict[str, any]:
        """Extract specific details from the text"""
        specifics = {
            "has_urgency": any(word in text.lower() for word in ["asap", "urgent", "now", "agad", "important"]),
            "has_testing": any(word in text.lower() for word in ["test", "validate", "check"]),
            "has_error_handling": any(word in text.lower() for word in ["error", "exception", "handle"]),
            "has_multiple_items": any(word in text.lower() for word in ["mga", "lahat", "all", "multiple"]),
            "is_question": text.strip().endswith("?") or any(word in text.lower() for word in ["bakit", "paano", "why", "how"])
        }
        return specifics

    def translate_filipino_terms(self, text: str) -> str:
        """Replace Filipino terms with English equivalents"""
        result = text
        
        # Create a boundary-aware replacement to avoid partial matches
        for filipino, english in self.filipino_tech_mapping.items():
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(filipino) + r'\b'
            result = re.sub(pattern, english, result, flags=re.IGNORECASE)
        
        return result

    def enhance_prompt(self, base_prompt: str, intent: str, components: List[str], 
                      specifics: Dict[str, any]) -> str:
        """Enhance the prompt with professional structure"""
        
        # Handle questions differently
        if specifics.get("is_question"):
            enhanced = f"Analyze and answer: {base_prompt}"
            if components:
                enhanced += f"\n\nFocus on:"
                for comp in components:
                    enhanced += f"\n- {comp.title()} implementation and issues"
            enhanced += "\n\nProvide detailed explanation and potential solutions."
            return enhanced
        
        # Start with intent-based prefix
        intent_prefixes = {
            "create": "Create and implement",
            "fix": "Debug and fix",
            "modify": "Modify and update", 
            "add": "Add and integrate",
            "remove": "Remove and clean up",
            "search": "Search and locate",
            "test": "Test and validate",
            "refactor": "Refactor and optimize",
            "implement": "Implement",
            "analyze": "Analyze and review"
        }
        
        # Clean up base prompt
        base_prompt = re.sub(r'\s+', ' ', base_prompt).strip()
        
        # Remove empty words from translation
        words = base_prompt.split()
        cleaned_words = [w for w in words if w]
        base_prompt = ' '.join(cleaned_words)
        
        # Remove redundant intent words from base prompt
        intent_words = ["create", "fix", "modify", "add", "remove", "search", "test", 
                       "refactor", "implement", "analyze", "debug", "update", "integrate"]
        
        # Split base prompt and filter out intent words at the beginning
        prompt_words = base_prompt.split()
        if prompt_words and prompt_words[0].lower() in intent_words:
            prompt_words = prompt_words[1:]  # Remove first word if it's an intent word
            base_prompt = ' '.join(prompt_words)
        
        enhanced = f"{intent_prefixes.get(intent, 'Implement')} {base_prompt}"
        
        # Add context based on components
        if components:
            contexts = []
            for comp in components:
                if comp in self.context_enhancers:
                    contexts.append(self.context_enhancers[comp])
            if contexts:
                enhanced += f" {' and '.join(contexts)}"
        
        # Add requirements based on specifics
        requirements = []
        
        if specifics.get("has_testing"):
            requirements.append("Include comprehensive unit tests")
        
        if specifics.get("has_error_handling"):
            requirements.append("Implement proper error handling and validation")
            
        if specifics.get("has_multiple_items"):
            requirements.append("Handle multiple items/batch operations")
            
        if specifics.get("has_urgency"):
            requirements.append("Priority: HIGH - Implement immediately")
        
        if requirements:
            enhanced += f"\n\nRequirements:\n" + "\n".join(f"- {req}" for req in requirements)
        
        # Add best practices reminder
        enhanced += "\n\nFollow best practices for code quality, documentation, and maintainability."
        
        return enhanced

    def convert_to_prompt(self, barok_input: str) -> Dict[str, any]:
        """Main conversion function"""
        # Clean input
        cleaned = barok_input.strip()
        
        # Detect intent and components
        intent = self.detect_intent(cleaned)
        components = self.detect_components(cleaned)
        specifics = self.extract_specifics(cleaned)
        
        # Translate Filipino terms
        translated = self.translate_filipino_terms(cleaned)
        
        # Clean up the translated text (less aggressive)
        translated = re.sub(r'\s+', ' ', translated)  # Multiple spaces to single
        translated = translated.strip()
        
        # Enhance the prompt
        enhanced_prompt = self.enhance_prompt(translated, intent, components, specifics)
        
        # Create structured output
        result = {
            "original": barok_input,
            "intent": intent,
            "components": components,
            "translated": translated,
            "enhanced_prompt": enhanced_prompt,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "detected_language": "filipino-english" if any(term in barok_input.lower() 
                                                              for term in self.filipino_tech_mapping) else "english",
                "urgency": specifics.get("has_urgency", False),
                "complexity": len(components)
            }
        }
        
        return result

    def generate_cursor_prompt(self, conversion_result: Dict[str, any]) -> str:
        """Generate the final Cursor AI prompt"""
        prompt_parts = []
        
        # Add task description
        prompt_parts.append(f"## Task: {conversion_result['enhanced_prompt']}")
        
        # Add component context
        if conversion_result['components']:
            prompt_parts.append(f"\n## Focus Areas:")
            for component in conversion_result['components']:
                prompt_parts.append(f"- {component.title()}")
        
        # Add implementation notes
        prompt_parts.append("\n## Implementation Guidelines:")
        prompt_parts.append("1. Analyze the current codebase structure")
        prompt_parts.append("2. Implement the solution following existing patterns")
        prompt_parts.append("3. Ensure backward compatibility")
        prompt_parts.append("4. Add appropriate documentation")
        
        if "test" in conversion_result['intent'] or conversion_result['metadata'].get('has_testing'):
            prompt_parts.append("5. Create comprehensive test cases")
        
        # Add urgency note if needed
        if conversion_result['metadata'].get('urgency'):
            prompt_parts.append("\n**⚡ URGENT: This task requires immediate attention**")
        
        return "\n".join(prompt_parts)


# Example usage and testing
if __name__ == "__main__":
    converter = BarokToPromptConverter()
    
    # Test examples
    test_inputs = [
        "gawa ka ng button para sa pag save ng data",
        "ayusin mo yung error sa login function",
        "dagdagan ng validation yung form tapos i-test",
        "bakit hindi gumagana yung API endpoint?",
        "i-refactor mo lahat ng database queries para mas mabilis",
        "gumawa ng bagong feature para sa pag upload ng file with error handling"
    ]
    
    print("🤖 Barok to Prompt Converter Demo\n")
    print("=" * 80)
    
    for barok_input in test_inputs:
        result = converter.convert_to_prompt(barok_input)
        cursor_prompt = converter.generate_cursor_prompt(result)
        
        print(f"\n📝 Original (Barok): {barok_input}")
        print(f"🎯 Intent: {result['intent']}")
        print(f"🔧 Components: {', '.join(result['components'])}")
        print(f"🌐 Translated: {result['translated']}")
        print(f"\n💡 Cursor AI Prompt:")
        print("-" * 40)
        print(cursor_prompt)
        print("=" * 80)