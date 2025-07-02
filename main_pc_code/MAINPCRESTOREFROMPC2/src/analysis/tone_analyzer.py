"""
Tone Analyzer Component using TagaBERTa
"""

import time
import logging
from typing import Dict, Any
from dataclasses import dataclass
from transformers import AutoTokenizer, AutoModel
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class ToneAnalysis:
    """Class for storing tone analysis results."""
    sentiment: str
    confidence: float
    emotions: Dict[str, float]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sentiment": self.sentiment,
            "confidence": self.confidence,
            "emotions": self.emotions,
            "timestamp": self.timestamp
        }

class TagaBERTaAnalyzer:
    """Tone analyzer using TagaBERTa model."""
    
    def __init__(self):
        """Initialize the tone analyzer."""
        logger.info("Initializing TagaBERTa Analyzer")
        self.tokenizer = AutoTokenizer.from_pretrained("jabberwocky/tagaberta-base")
        self.model = AutoModel.from_pretrained("jabberwocky/tagaberta-base")
        self.emotion_labels = ['happy', 'sad', 'angry', 'neutral', 'excited']
        
    def analyze_tone(self, text: str) -> ToneAnalysis:
        """Analyze the tone of given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            ToneAnalysis object with results
        """
        try:
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1)
            
            # Simple emotion classification (replace with proper classifier)
            emotion_scores = {label: float(np.random.random()) for label in self.emotion_labels}
            dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])
            
            return ToneAnalysis(
                sentiment=dominant_emotion[0],
                confidence=float(dominant_emotion[1]),
                emotions=emotion_scores,
                timestamp=time.time()
            )
        except Exception as e:
            logger.error(f"Error in tone analysis: {e}")
            return ToneAnalysis(
                sentiment="neutral",
                confidence=0.0,
                emotions={label: 0.0 for label in self.emotion_labels},
                timestamp=time.time()
            ) 