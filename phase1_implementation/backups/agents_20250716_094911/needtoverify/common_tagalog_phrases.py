from main_pc_code.src.core.base_agent import BaseAgent
"""
Common Tagalog Phrases Module
Pre-translated common phrases for Tagalog to English and English to Tagalog
"""
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CommonTagalogPhrases")

# Common Tagalog Phrases with English translations
# Format: "tagalog_phrase": "english_translation"
TAGALOG_TO_ENGLISH = {
    # Greetings
    "kumusta": "how are you",
    "kumusta ka": "how are you",
    "kumusta po": "how are you (respectful)",
    "kumusta po kayo": "how are you (respectful)",
    "magandang umaga": "good morning",
    "magandang tanghali": "good noon",
    "magandang hapon": "good afternoon",
    "magandang gabi": "good evening",
    
    # Thanks and pleasantries
    "salamat": "thank you",
    "salamat po": "thank you (respectful)",
    "maraming salamat": "thank you very much",
    "walang anuman": "you're welcome",
    "pasensya na": "sorry",
    "paumanhin": "excuse me",
    
    # Basic expressions
    "oo": "yes",
    "hindi": "no",
    "sige": "okay",
    "tama": "correct",
    "mali": "wrong",
    "totoo": "true",
    "hindi totoo": "not true",
    "paalam": "goodbye",
    
    # Questions
    "ano": "what",
    "sino": "who",
    "saan": "where",
    "kailan": "when",
    "bakit": "why",
    "paano": "how",
    "anong oras na": "what time is it",
    "ano ang pangalan mo": "what is your name",
    "nasaan ka": "where are you",
    
    # Commands
    "buksan": "open",
    "isara": "close",
    "hinto": "stop",
    "tama na": "stop/enough",
    "ulitin": "repeat",
    "ulit": "again",
    "patay": "turn off",
    "bukas": "turn on",
    "tuloy": "continue",
    "bilisan": "speed up",
    "bagalan": "slow down",
    
    # Help and info
    "tulong": "help",
    "tulungan mo ako": "help me",
    "kailangan ko ng tulong": "I need help",
    "hindi ko maintindihan": "I don't understand",
    "pwede mo bang ulitin": "can you repeat that",
    
    # Emotions
    "masaya ako": "I am happy",
    "malungkot ako": "I am sad",
    "pagod ako": "I am tired",
    "nagugutom ako": "I am hungry",
    "uhaw ako": "I am thirsty",
    
    # Voice assistant specific
    "makinig ka": "listen",
    "intindihin mo ako": "understand me",
    "ano ang kaya mong gawin": "what can you do",
    "magsalita ka": "speak",
    "wag kang magsalita": "don't speak",
    "tumahimik ka": "be quiet",
    "magpatugtog ng musika": "play music",
    "magtanong ako": "let me ask",
    "sagutin mo ako": "answer me",
    
    # Time expressions
    "ngayon": "now",
    "mamaya": "later",
    "kahapon": "yesterday",
    "bukas": "tomorrow",
    "kanina": "earlier",
    "mamayang gabi": "tonight",
    
    # Common phrases
    "nagkamali ako": "I made a mistake",
    "hindi ko alam": "I don't know",
    "naiintindihan ko": "I understand",
    "pakiulit": "please repeat",
    "hindi ko narinig": "I didn't hear",
    "saglit lang": "just a moment",
    "sandali lang": "just a moment",
    "teka muna": "wait a moment",
}

# Common English Phrases with Tagalog translations
# Format: "english_phrase": "tagalog_translation"
ENGLISH_TO_TAGALOG = {
    # Greetings
    "hello": "kumusta",
    "hi": "kumusta",
    "good morning": "magandang umaga",
    "good afternoon": "magandang hapon",
    "good evening": "magandang gabi",
    
    # Thanks and pleasantries
    "thank you": "salamat",
    "thanks": "salamat",
    "thank you very much": "maraming salamat",
    "you're welcome": "walang anuman",
    "excuse me": "paumanhin",
    "sorry": "pasensya",
    
    # Basic expressions
    "yes": "oo",
    "no": "hindi",
    "okay": "sige",
    "correct": "tama",
    "wrong": "mali",
    "true": "totoo",
    "false": "hindi totoo",
    "goodbye": "paalam",
    
    # Questions
    "what": "ano",
    "who": "sino",
    "where": "saan",
    "when": "kailan",
    "why": "bakit",
    "how": "paano",
    "what time is it": "anong oras na",
    "what is your name": "ano ang pangalan mo",
    "where are you": "nasaan ka",
    
    # Commands
    "open": "buksan",
    "close": "isara",
    "stop": "hinto",
    "repeat": "ulitin",
    "again": "ulit",
    "turn off": "patayin",
    "turn on": "buksan",
    "continue": "tuloy",
    "speed up": "bilisan",
    "slow down": "bagalan",
    
    # Voice assistant responses
    "I understand": "Naiintindihan ko",
    "I don't understand": "Hindi ko maintindihan",
    "can you repeat that": "Pwede mo bang ulitin",
    "I'm listening": "Nakikinig ako",
    "I'm processing your request": "Pinoproseso ko ang iyong kahilingan",
    "I'm thinking": "Nag-iisip ako",
    "processing": "Pinoproseso",
    "one moment please": "Sandali lang po",
    "just a moment": "Saglit lang",
    "I'll help you with that": "Tutulungan kita diyan",
    "is there anything else": "Mayroon pa bang iba",
    "do you need anything else": "Kailangan mo pa ba ng iba",
    "I'm sorry, I can't do that": "Pasensya na, hindi ko magagawa iyon",
    "I found this for you": "Nahanap ko ito para sa iyo",
    "here's what I found": "Ito ang nahanap ko",
    "I'm ready": "Handa na ako",
    
    # Common phrases
    "I made a mistake": "Nagkamali ako",
    "I don't know": "Hindi ko alam",
    "please repeat": "Pakiulit",
    "I didn't hear": "Hindi ko narinig",
    "just a moment": "Sandali lang",
    "wait a moment": "Teka muna",
}

# Combined phrases for easy lookup in both directions
ALL_PHRASES = {**TAGALOG_TO_ENGLISH, **{v: k for k, v in ENGLISH_TO_TAGALOG.items()}}

def translate_common_phrase(text, src_lang="tl", dest_lang="en"):
    """
    Translate a common phrase if it exists in our database.
    Returns (translated_text, was_translated_flag)
    
    Args:
        text (str): Text to translate
        src_lang (str): Source language code (tl for Tagalog, en for English)
        dest_lang (str): Destination language code
        
    Returns:
        tuple: (translated_text, was_translated_flag)
    """
    text_lower = text.lower().strip()
    
    # Choose the right dictionary based on source and destination languages
    if src_lang == "tl" and dest_lang == "en":
        translation_dict = TAGALOG_TO_ENGLISH
    elif src_lang == "en" and dest_lang == "tl":
        translation_dict = ENGLISH_TO_TAGALOG
    else:
        return text, False
    
    # Check for exact matches
    if text_lower in translation_dict:
        translated = translation_dict[text_lower]
        logger.info(f"Common phrase translated: '{text}' -> '{translated}'")
        return translated, True
    
    # No match found
    return text, False

def check_and_replace_common_phrases(text, src_lang="tl", dest_lang="en"):
    """
    Check if text contains any common phrases and replace them with translations.
    
    Args:
        text (str): Text to check for common phrases
        src_lang (str): Source language code
        dest_lang (str): Destination language code
        
    Returns:
        tuple: (processed_text, replacements)
    """
    if not text:
        return text, []
    
    # Choose dictionary based on direction
    if src_lang == "tl" and dest_lang == "en":
        translation_dict = TAGALOG_TO_ENGLISH
    elif src_lang == "en" and dest_lang == "tl":
        translation_dict = ENGLISH_TO_TAGALOG
    else:
        return text, []
    
    words = text.lower().split()
    replacements = []
    
    # Check for single word matches
    for i, word in enumerate(words):
        if word in translation_dict:
            replacements.append((word, translation_dict[word]))
    
    # Check for multi-word phrases
    for phrase in sorted(translation_dict.keys(), key=len, reverse=True):
        if len(phrase.split()) > 1 and phrase.lower() in text.lower():
            replacements.append((phrase, translation_dict[phrase]))
    
    # Apply replacements
    processed_text = text
    for original, translated in replacements:
        processed_text = processed_text.replace(original, translated)
    
    if replacements:
        logger.info(f"Replaced {len(replacements)} common phrases in text")
        
    return processed_text, replacements

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
