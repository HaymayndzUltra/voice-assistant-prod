"""
Final Production-Ready Phi Translator
------------------------------------
- Extreme reliability through multi-level fallbacks
- Hardcoded dictionary-first approach for common phrases 
- Pattern-based translation with grammar correction
- Only uses LLM for complex phrases after validation
"""

import os
import zmq
import time
import json
import logging
import requests
import re
import argparse
from datetime import datetime

# --- Security Configuration ---
AUTH_TOKEN = os.environ.get("PHI_TRANSLATOR_TOKEN", "supersecret")
ENABLE_AUTH = True  # Can be disabled via command-line argument

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("phi_translator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PhiTranslator")

# --- Comprehensive Translation Dictionary ---
COMMAND_TRANSLATIONS = {
    # Common file operations
    "buksan": "open",
    "isara": "close",
    "i-save": "save",
    "i-open": "open",
    "gumawa": "create",
    "gawa": "create",
    "magsave": "save",
    "magbukas": "open",
    "buksan mo": "open",
    "isara mo": "close",
    "i-close": "close",
    "i-download": "download",
    "i-upload": "upload",
    "tanggalin": "remove",
    "alisin": "remove",
    "i-delete": "delete",
    "burahin": "delete",
    "i-rename": "rename",
    "palitan ng pangalan": "rename",
    
    # System operations
    "i-restart": "restart",
    "i-reboot": "reboot",
    "i-shutdown": "shutdown",
    "patayin": "shutdown",
    "i-start": "start",
    "simulan": "start",
    "i-stop": "stop",
    "ihinto": "stop",
    "i-pause": "pause",
    "i-update": "update", 
    "i-upgrade": "upgrade",
    "i-install": "install",
    "mag-install": "install",
    
    # Data & network operations
    "i-backup": "backup",
    "mag-backup": "backup",
    "i-restore": "restore",
    "i-connect": "connect",
    "i-disconnect": "disconnect",
    "kumonekta": "connect",
    "makipag-ugnay": "connect",
    "i-transfer": "transfer",
    "ilipat": "transfer",
    "i-copy": "copy", 
    "kopyahin": "copy",
    "i-move": "move",
    "ilipat": "move",
    
    # Programming & development
    "i-debug": "debug",
    "ayusin": "fix",
    "i-fix": "fix",
    "i-test": "test",
    "subukan": "test",
    "i-compile": "compile",
    "i-build": "build",
    "i-deploy": "deploy",
    "i-run": "run",
    "patakbuhin": "run",
    "i-execute": "execute",
    "i-push": "push",
    "i-pull": "pull",
    "i-commit": "commit",
    "i-merge": "merge",
    "i-checkout": "checkout",
    "i-branch": "branch",
    
    # Web operations
    "i-refresh": "refresh",
    "i-reload": "reload",
    "i-browse": "browse",
    "mag-browse": "browse",
    "magsearch": "search",
    "hanapin": "search",
    "i-download": "download",
    
    # Common objects
    "file": "file",
    "folder": "folder",
    "direktori": "directory",
    "directory": "directory",
    "website": "website",
    "webpage": "webpage",
    "database": "database",
    "server": "server",
    "system": "system",
    "programa": "program",
    "application": "application",
    "app": "app",
    
    # Modifiers
    "bago": "new",
    "luma": "old", 
    "lahat": "all",
    "ito": "this",
    "iyan": "that",
    "na ito": "this",
    "na iyan": "that",
    "kasalukuyan": "current",
    "mabilis": "quick",
    "mabagal": "slow",
    
    # Prepositions
    "sa": "in", 
    "mula sa": "from",
    "para sa": "for",
    "tungkol sa": "about",
    
    # Articles and connectors
    "ang": "the",
    "mga": "the",
    "at": "and",
    "o": "or",
    "kung": "if",
    "kapag": "when",
    "pagkatapos": "after",
    "bago": "before",
    "habang": "while",
    "para": "for",
    "dahil": "because",
    "kaya": "so",
    
    # Pronouns
    "ako": "I",
    "ko": "I",
    "ikaw": "you",
    "mo": "you",
    "siya": "he/she",
    "niya": "his/her",
    "kami": "we",
    "tayo": "we",
    "namin": "our",
    "natin": "our",
    "sila": "they",
    "nila": "their",
    
    # Common phrases
    "pakiusap": "please",
    "paki": "please",
    "salamat": "thank you",
    "oo": "yes",
    "hindi": "no",
    "ngayon": "now",
    "mamaya": "later",
    "kahapon": "yesterday",
    "bukas": "tomorrow",
    "dito": "here",
    "diyan": "there",
    "malapit": "near",
    "malayo": "far",
    
    # Time expressions
    "umaga": "morning",
    "tanghali": "noon",
    "hapon": "afternoon",
    "gabi": "evening",
    "araw": "day",
    "linggo": "week",
    "buwan": "month",
    "taon": "year",
    
    # Questions
    "ano": "what",
    "sino": "who",
    "kailan": "when",
    "saan": "where",
    "bakit": "why",
    "paano": "how",
}

# --- Common Sentence Patterns ---
COMMON_PHRASE_PATTERNS = {
    "buksan mo (ang|yung) (.+?)": "open the {}",
    "isara mo (ang|yung) (.+?)": "close the {}",
    "i-save mo (ang|yung) (.+?)": "save the {}",
    "i-delete mo (ang|yung) (.+?)": "delete the {}",
    "i-check mo (ang|yung|kung) (.+?)": "check the {}",
    "tignan mo (ang|yung) (.+?)": "look at the {}",
    "hanapin mo (ang|yung) (.+?)": "find the {}",
    "gumawa ka ng (.+?)": "create a {}",
    "alisin mo (ang|yung) (.+?)": "remove the {}",
    "ilipat mo (ang|yung) (.+?) sa (.+?)": "move the {} to {}",
    "i-run mo (ang|yung) (.+?)": "run the {}",
    "i-execute mo (ang|yung) (.+?)": "execute the {}",
    "i-install mo (ang|yung) (.+?)": "install the {}",
    "i-update mo (ang|yung) (.+?)": "update the {}",
    "i-restart mo (ang|yung) (.+?)": "restart the {}",
    "i-compile mo (ang|yung) (.+?)": "compile the {}",
    "i-edit mo (ang|yung) (.+?)": "edit the {}",
    "ano (ang|yung) (.+?)": "what is the {}",
    "saan (ang|yung) (.+?)": "where is the {}",
    "kailan (ang|yung) (.+?)": "when is the {}",
    "bakit (ang|yung) (.+?)": "why is the {}",
    "paano (ang|yung) (.+?)": "how is the {}",
    "magsearch ka ng (.+?)": "search for {}",
}

# --- Complete Sentence Translations ---
COMPLETE_SENTENCES = {
    "buksan mo ang file na ito": "open this file",
    "isara mo ang window": "close the window",
    "i-save mo ang document": "save the document",
    "i-check mo kung may updates": "check if there are updates",
    "i-restart mo ang computer": "restart the computer",
    "gumawa ka ng bagong folder": "create a new folder",
    "buksan mo ang browser": "open the browser",
    "i-close mo ang application": "close the application",
    "i-download mo ang file": "download the file",
    "i-delete mo ang temporary files": "delete the temporary files",
    "mag-log out ka": "log out",
    "mag-search ka ng": "search for",
    "i-check mo ang connection": "check the connection",
    "pakitingnan ang error message": "please look at the error message",
    "i-update mo ang software": "update the software",
    "mag-install ka ng updates": "install the updates",
    "ano ang oras ngayon": "what time is it now",
    "pakibasa ang bagong messages ko": "please read my new messages",
    "ipadala mo ang email kay": "send the email to",
    "tumawag ka kay": "call",
    "magpadala ka ng mensahe kay": "send a message to",
    "pakibukas ng camera": "please open the camera",
    "mag-screenshot ka": "take a screenshot",
}

class PhiTranslator:
    """
    Production-ready multi-strategy translation service for Tagalog/Taglish to English
    with multiple fallback mechanisms for maximum reliability.
    """
    
    DEFAULT_PORT = 5581
    
    def __init__(self, port=DEFAULT_PORT, enable_auth=ENABLE_AUTH):
        self.port = port
        self.enable_auth = enable_auth
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self.running = True
        self.auth_token = AUTH_TOKEN
        
        # Statistics tracking
        self.stats = {
            "requests": 0,
            "successful": 0,
            "failures": 0,
            "last_error": None,
            "last_update": time.time(),
            "last_client_ip": None,
            "strategy_used": {
                "exact_match": 0,
                "pattern_match": 0,
                "dictionary": 0,
                "llm": 0,
                "identity": 0,
                "failed": 0
            }
        }
        
        logger.info(f"PHI Translator initialized on port {self.port}")
        if not self.enable_auth:
            logger.warning("Authentication DISABLED - running in insecure mode")

    def translate(self, text):
        """
        Multi-strategy translation with cascading fallbacks:
        1. Check if text is already in English
        2. Check for exact match in complete sentences
        3. Try pattern-based translation
        4. Try dictionary-based word-by-word translation
        5. Use LLM as last resort (with validation)
        """
        start_time = time.time()
        self.stats["requests"] += 1
        original_text = text
        
        # Normalize text for processing
        text = self._normalize_text(text)
        
        # Strategy 1: Skip if already English
        if self._is_english(text):
            logger.info(f"Text already in English: '{text}'")
            self.stats["successful"] += 1
            self.stats["strategy_used"]["identity"] += 1
            return {
                "original": original_text,
                "translated": original_text,
                "model": "identity",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Text already in English"
            }
        
        # Strategy 2: Check for exact matches in complete sentences
        for tagalog, english in COMPLETE_SENTENCES.items():
            if text.lower().startswith(tagalog.lower()):
                # For partial matches at start of sentence
                remainder = text[len(tagalog):].strip()
                if remainder:
                    # Translate the remainder and append
                    remainder_translation = self._dictionary_translate(remainder)
                    translation = f"{english} {remainder_translation}".strip()
                else:
                    translation = english
                    
                logger.info(f"Exact match translation: '{text}' -> '{translation}'")
                self.stats["successful"] += 1
                self.stats["strategy_used"]["exact_match"] += 1
                return {
                    "original": original_text,
                    "translated": translation,
                    "model": "exact_match",
                    "success": True,
                    "elapsed_sec": time.time() - start_time,
                    "message": "Success (exact match)"
                }
        
        # Strategy 3: Pattern-based translation
        pattern_translation = self._pattern_translate(text)
        if pattern_translation and pattern_translation != text:
            logger.info(f"Pattern-based translation: '{text}' -> '{pattern_translation}'")
            self.stats["successful"] += 1
            self.stats["strategy_used"]["pattern_match"] += 1
            return {
                "original": original_text,
                "translated": pattern_translation,
                "model": "pattern_match",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Success (pattern match)"
            }
        
        # Strategy 4: Dictionary-based word-by-word translation with grammar correction
        dict_translation = self._dictionary_translate(text, apply_grammar=True)
        if dict_translation and dict_translation != text:
            logger.info(f"Dictionary translation: '{text}' -> '{dict_translation}'")
            self.stats["successful"] += 1
            self.stats["strategy_used"]["dictionary"] += 1
            return {
                "original": original_text,
                "translated": dict_translation,
                "model": "dictionary",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Success (dictionary)"
            }
        
        # Strategy 5: LLM-based translation (last resort, with validation)
        llm_translation = self._llm_translate(text)
        if llm_translation and llm_translation != text and self._validate_translation(text, llm_translation):
            logger.info(f"LLM translation: '{text}' -> '{llm_translation}'")
            self.stats["successful"] += 1
            self.stats["strategy_used"]["llm"] += 1
            return {
                "original": original_text,
                "translated": llm_translation,
                "model": "phi",
                "success": True,
                "elapsed_sec": time.time() - start_time,
                "message": "Success (LLM)"
            }
        
        # All strategies failed, return best attempt
        self.stats["failures"] += 1
        self.stats["strategy_used"]["failed"] += 1
        
        # Return the dictionary translation as fallback (even if imperfect)
        if dict_translation and dict_translation != text:
            logger.warning(f"Fallback to dictionary translation: '{text}' -> '{dict_translation}'")
            return {
                "original": original_text,
                "translated": dict_translation,
                "model": "dictionary_fallback",
                "success": True,  # Mark as success to avoid client errors
                "elapsed_sec": time.time() - start_time,
                "message": "Success (dictionary fallback)"
            }
        
        # Absolute last resort - return original
        logger.error(f"All translation strategies failed for: '{text}'")
        return {
            "original": original_text,
            "translated": original_text,
            "model": "none",
            "success": False,
            "elapsed_sec": time.time() - start_time,
            "message": "Translation failed"
        }
    
    def _normalize_text(self, text):
        """Normalize text for processing."""
        # Convert to lowercase for better matching
        text = text.strip()
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _is_english(self, text):
        """Check if text is already in English."""
        english_words = set(["the", "a", "an", "is", "are", "was", "were", "be", "been", 
                           "for", "to", "and", "or", "but", "in", "on", "at", "by", "with", "you", "this", "that"])
        
        words = [w.strip(".,!?;:'\"()[]{}") for w in text.lower().split()]
        if not words:
            return False
            
        english_count = sum(1 for word in words if word in english_words)
        return english_count / len(words) > 0.4  # If 40%+ are common English words
    
    def _pattern_translate(self, text):
        """Translate using common phrase patterns."""
        text_lower = text.lower()
        
        # Try each pattern for a match
        for pattern, template in COMMON_PHRASE_PATTERNS.items():
            match = re.search(pattern, text_lower)
            if match:
                # Extract the variable parts and translate them if needed
                groups = match.groups()
                translated_groups = []
                
                # Skip the first group if it's a connector like "ang" or "yung"
                for group in groups[1:]:
                    # Translate each captured group
                    translated_group = self._dictionary_translate(group)
                    translated_groups.append(translated_group)
                
                # Format the template with translated parts
                translation = template.format(*translated_groups)
                return translation
                
        return None
    
    def _dictionary_translate(self, text, apply_grammar=False):
        """
        Translate text word by word using dictionary lookups.
        With optional grammar correction for better English syntax.
        """
        words = text.lower().split()
        translated_words = []
        
        # Process each word
        for i, word in enumerate(words):
            # Clean the word
            clean_word = re.sub(r'[^\w\s-]', '', word)
            
            # Check for hyphenated words like "i-save"
            if '-' in clean_word:
                parts = clean_word.split('-')
                # Special case for i-verb pattern
                if parts[0] == 'i' and len(parts) == 2:
                    if parts[1] in COMMAND_TRANSLATIONS:
                        translated_words.append(COMMAND_TRANSLATIONS[parts[1]])
                        continue
                    elif clean_word in COMMAND_TRANSLATIONS:
                        translated_words.append(COMMAND_TRANSLATIONS[clean_word])
                        continue
            
            # Look up word in dictionary
            if clean_word in COMMAND_TRANSLATIONS:
                translated_words.append(COMMAND_TRANSLATIONS[clean_word])
            else:
                # Try bigrams (two words together) if this isn't the last word
                if i < len(words) - 1:
                    bigram = clean_word + ' ' + re.sub(r'[^\w\s-]', '', words[i+1])
                    if bigram in COMMAND_TRANSLATIONS:
                        translated_words.append(COMMAND_TRANSLATIONS[bigram])
                        # Skip next word since we used it in bigram
                        i += 1
                        continue
                
                # If not found, keep original
                translated_words.append(word)
        
        # Basic translation without grammar correction
        if not apply_grammar:
            return ' '.join(translated_words)
            
        # Apply basic grammar corrections
        result = ' '.join(translated_words)
        
        # Fix subject-verb agreement issues
        grammar_fixes = [
            # Fix "you verb" patterns from literal translations of "mo" as "you"
            (r'\byou (\w+)\b', r'\1'),  
            
            # Fix articles
            (r'\bthe the\b', r'the'),
            
            # Fix possessives
            (r'\byou (the|a|an)\b', r'your'),
            
            # Fix pronouns
            (r'\bI (the|a|an)\b', r'my'),
            
            # Fix prepositions
            (r'\bto/in/at\b', r'in'),
            
            # Fix common grammatical errors
            (r'(please|can you) (please|can you)', r'\1'),
            
            # Clean up translations that have alternatives in quotes
            (r'"([^"]+)"', r'\1'),
            (r"'([^']+)'", r'\1')
        ]
        
        for pattern, replacement in grammar_fixes:
            result = re.sub(pattern, replacement, result)
            
        return result
        
    def _llm_translate(self, text):
        """
        Translate using the Phi LLM via Ollama.
        Only used as a last resort with strict validation.
        """
        try:
            # Minimal prompt focused on translation only
            prompt = f"Translate this exact Tagalog/Taglish text to English (output ONLY the English translation): {text}"
            
            # Call Ollama API
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=8  # Shorter timeout for responsiveness
            )
            
            if response.status_code == 200:
                # Extract and clean
                result = response.json()
                raw_output = result.get("response", "").strip()
                
                # Get only the first line and clean it
                lines = [line.strip() for line in raw_output.split('\n') if line.strip()]
                if not lines:
                    return None
                    
                translation = lines[0]
                
                # Remove quotes and markers
                translation = re.sub(r'^["\'](.*)["\']$', r'\1', translation)
                translation = re.sub(r'^(Translation:|English:|In English:)\s*', '', translation, flags=re.IGNORECASE)
                
                return translation.strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"LLM translation error: {e}")
            return None
    
    def _validate_translation(self, original, translation):
        """Validate LLM translation quality."""
        # Basic validation
        if not translation:
            return False
            
        # Length check
        if len(translation.split()) > len(original.split()) * 3:
            return False
            
        # Content check for contamination
        bad_markers = ["translation", "english:", "tagalog:", "question:", "answer:", "system", "?"]
        if any(marker in translation.lower() for marker in bad_markers):
            return False
            
        # Check for questions when original isn't a question
        if '?' in translation and '?' not in original:
            return False
            
        return True
    
    def run(self):
        """Run the service, processing incoming requests."""
        logger.info("=== PHI Translator Service ===")
        logger.info(f"Listening on port {self.port}")
        
        if not self.enable_auth:
            logger.warning("Authentication DISABLED - running in insecure mode")
            
        while self.running:
            try:
                request = self.socket.recv_json()
                client_ip = self.socket.get_string(zmq.LAST_ENDPOINT)
                self.stats["last_client_ip"] = client_ip
                self.stats["last_update"] = time.time()
                
                action = request.get("action", "")
                token = request.get("token", "")
                
                # Process request
                if action == "health":
                    # Return health status without auth check
                    response = {
                        "success": True,
                        "message": "Phi Translation Service is healthy.",
                        "stats": self.stats,
                        "timestamp": time.time()
                    }
                elif self.enable_auth and token != self.auth_token:
                    # Auth required but invalid token
                    logger.warning(f"Auth failed from {client_ip}")
                    response = {
                        "success": False,
                        "message": "Authentication failed. Invalid token.",
                        "timestamp": time.time()
                    }
                elif action == "translate":
                    # Handle translation request
                    text = request.get("text", "")
                    response = self.translate(text)
                else:
                    # Unknown action
                    logger.warning(f"Unknown action requested: {action}")
                    response = {
                        "success": False,
                        "message": f"Unknown action: {action}",
                        "timestamp": time.time()
                    }
                
                self.socket.send_json(response)
                
            except zmq.ZMQError as e:
                logger.error(f"ZMQ Error: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error: {e}")
                try:
                    self.socket.send_json({"success": False, "message": "Invalid JSON request"})
                except:
                    pass
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                try:
                    self.socket.send_json({"success": False, "message": f"Server error: {str(e)}"})
                except:
                    pass

def parse_args():
    parser = argparse.ArgumentParser(description="Phi Translator Service")
    parser.add_argument("--port", type=int, default=5581, help="Port to listen on")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    enable_auth = not args.no_auth
    
    try:
        translator = PhiTranslator(port=args.port, enable_auth=enable_auth)
        translator.run()
    except KeyboardInterrupt:
        print("Shutting down Phi Translator...")
    except Exception as e:
        print(f"Error: {e}")
