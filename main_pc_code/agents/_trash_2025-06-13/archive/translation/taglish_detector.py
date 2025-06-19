from src.core.base_agent import BaseAgent
import re
from typing import Tuple

# Expanded Filipino and English word lists for better detection
FILIPINO_WORDS = set([
    # Common Filipino words
    "ang", "ng", "sa", "ako", "ikaw", "siya", "kami", "kayo", "sila", "ito", "iyan", "doon", "dito", 
    "bakit", "paano", "hindi", "oo", "wala", "meron", "may", "gusto", "kailangan", "pwede", "bawal", 
    "maganda", "pangit", "malaki", "maliit", "bata", "matanda", "kumain", "uminom", "trabaho", "bahay", 
    "paaralan", "kaibigan", "pamilya", "asawa", "anak", "magulang", "lolo", "lola",
    # Additional common words
    "naman", "lang", "na", "po", "ko", "mo", "niya", "namin", "natin", "nila", "amin", "akin", "iyo", 
    "kanila", "kaniya", "yung", "yun", "mga", "pag", "kung", "pero", "at", "para", "dahil", "kasi", "tulad", 
    "ganyan", "ganito", "punta", "hanap", "bili", "benta", "tawag", "kwento", "usap", "ayaw", "gusto", 
    "mahal", "salamat", "pasensya", "patawad", "kamusta", "ingat", "matulog", "gising", "laro", "kain",
    # Common verb forms
    "mag", "nag", "nagpa", "magpa", "naka", "maka", "nakaka", "makaka", "nakapa", "makapa", "napaka", 
    "mapapa", "pina", "pinapa", "napa", "napapa", "mapa", "mapapa", "ipa", "ipina", "ipinapa",
    # Common Filipino expressions
    "talaga", "siguro", "baka", "sana", "nga", "naman", "eh", "ano", "ba", "daw", "raw", "din", "rin", 
    "muna", "lang", "pala", "kaya", "halos", "kahit", "lamang", "tayo", "agad", "palagi", "lagi", "medyo",
    # Negations
    "di", "huwag", "wala", "ayaw"
])

ENGLISH_WORDS = set([
    # Common English words
    "the", "and", "is", "are", "am", "you", "he", "she", "it", "we", "they", "this", "that", "why", "how", 
    "not", "yes", "no", "none", "have", "has", "want", "need", "can", "cannot", "good", "bad", "big", "small", 
    "child", "old", "eat", "drink", "work", "house", "school", "friend", "family", "wife", "husband", "child", 
    "parent", "grandfather", "grandmother",
    # Additional common words
    "a", "an", "of", "in", "on", "at", "to", "for", "with", "by", "from", "about", "as", "into", "like", 
    "through", "after", "over", "between", "out", "under", "before", "up", "down", "off", "above", 
    "below", "use", "because", "during", "without", "within", "along", "around", "than", "since", 
    "until", "while", "where", "when", "why", "how", "what", "who", "whom", "whose", "which", 
    "there", "here", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", 
    "myself", "yourself", "himself", "herself", "itself", "ourselves", "yourselves", "themselves",
    # Common verbs
    "do", "does", "did", "done", "go", "goes", "went", "gone", "make", "makes", "made", "see", "sees", 
    "saw", "seen", "know", "knows", "knew", "known", "take", "takes", "took", "taken", "think", "thinks", 
    "thought", "come", "comes", "came", "give", "gives", "gave", "given", "find", "finds", "found", 
    "tell", "tells", "told", "call", "calls", "called", "try", "tries", "tried", "ask", "asks", "asked",
    # Common auxiliary verbs
    "will", "would", "shall", "should", "can", "could", "may", "might", "must"
])

def detect_taglish(text: str, threshold: float = 0.15) -> Tuple[bool, float, float]:
    """
    Detects if the text is Taglish (mixed Tagalog and English).
    Returns (is_taglish, filipino_ratio, english_ratio)
    
    Args:
        text: Text to analyze
        threshold: Minimum ratio of words from each language to consider as Taglish
        
    Returns:
        Tuple of (is_taglish, filipino_ratio, english_ratio)
    """
    # Clean and tokenize text
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return False, 0.0, 0.0
        
    # Count words from each language
    filipino_count = sum(1 for w in words if w in FILIPINO_WORDS)
    english_count = sum(1 for w in words if w in ENGLISH_WORDS)
    total = len(words)
    
    # Calculate ratios
    filipino_ratio = filipino_count / total
    english_ratio = english_count / total
    
    # Determine if text is Taglish (mixed Filipino and English)
    # Lower threshold (0.15) makes detection more sensitive to mixed language
    is_taglish = filipino_ratio >= threshold and english_ratio >= threshold
    
    # Log detection for debugging
    if filipino_ratio > 0 or english_ratio > 0:
        print(f"DEBUG: Text '{text[:20]}...', Filipino: {filipino_ratio:.2f}, English: {english_ratio:.2f}, Taglish: {is_taglish}")
    
    return is_taglish, filipino_ratio, english_ratio

if __name__ == "__main__":
    # Simple test/demo
    samples = [
        "Punta tayo sa mall later, gusto mo?",
        "Can you open the ilaw sa kitchen?",
        "Mag-aral ka na, don't be lazy!",
        "Kumain ka na ba?",
        "Let's go to the park.",
    ]
    for s in samples:
        taglish, fil, eng = detect_taglish(s)
        print(f"'{s}' => Taglish: {taglish} (Filipino: {fil:.2f}, English: {eng:.2f})")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
