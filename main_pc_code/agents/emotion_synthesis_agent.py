# ✅ Path patch fix for src/ and utils/ imports
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.base_agent import BaseAgent
import zmq
import json
import logging
import random
from datetime import datetime
from typing import Dict
from utils.config_loader import parse_agent_args
import time
import psutil
from datetime import datetime
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('emotion_synthesis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmotionSynthesisAgent(BaseAgent):
    def __init__(self):
        self.port = _agent_args.get('port')
        super().__init__(_agent_args)
        
        # Emotional markers for different emotions
        self.emotion_markers = {
            'happy': {
                'interjections': ['Great!', 'Wonderful!', 'Excellent!', 'Fantastic!'],
                'sentence_starters': ['I\'m glad to', 'I\'m happy to', 'I\'m excited to'],
                'sentence_enders': ['!', '...', '!'],
                'modifiers': ['really', 'truly', 'absolutely']
            },
            'empathetic': {
                'interjections': ['I understand', 'I see', 'I hear you'],
                'sentence_starters': ['I can imagine', 'I understand that', 'I know that'],
                'sentence_enders': ['.', '...'],
                'modifiers': ['deeply', 'truly', 'sincerely']
            },
            'curious': {
                'interjections': ['Interesting!', 'Fascinating!', 'Tell me more'],
                'sentence_starters': ['I wonder', 'I\'m curious about', 'Could you tell me more about'],
                'sentence_enders': ['?', '...'],
                'modifiers': ['really', 'quite', 'particularly']
            },
            'calm': {
                'interjections': ['Alright', 'Okay', 'I see'],
                'sentence_starters': ['Let\'s', 'We can', 'I can'],
                'sentence_enders': ['.'],
                'modifiers': ['gently', 'calmly', 'peacefully']
            },
            'concerned': {
                'interjections': ['I\'m concerned', 'I notice', 'I see that'],
                'sentence_starters': ['It seems', 'I notice that', 'I can see that'],
                'sentence_enders': ['.', '...'],
                'modifiers': ['slightly', 'somewhat', 'rather']
            }
        }
        
        logger.info(f"EmotionSynthesisAgent initialized on port {self.port}")
    
    def _add_emotional_markers(self, text, emotion, intensity=0.5):
        """Add emotional markers to the text based on the emotion and intensity"""
        if emotion not in self.emotion_markers:
            return text
        
        markers = self.emotion_markers[emotion]
        
        # Split into sentences
        sentences = text.split('. ')
        modified_sentences = []
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Add interjection with probability based on intensity
            if random.random() < intensity:
                interjection = random.choice(markers['interjections'])
                sentence = f"{interjection}, {sentence}"
            
            # Add sentence starter with probability based on intensity
            if random.random() < intensity:
                starter = random.choice(markers['sentence_starters'])
                sentence = f"{starter} {sentence.lower()}"
            
            # Add modifier with probability based on intensity
            if random.random() < intensity:
                modifier = random.choice(markers['modifiers'])
                words = sentence.split()
                if len(words) > 3:
                    insert_pos = random.randint(1, len(words) - 1)
                    words.insert(insert_pos, modifier)
                    sentence = ' '.join(words)
            
            # Add sentence ender
            sentence = sentence.rstrip('.') + random.choice(markers['sentence_enders'])
            
            modified_sentences.append(sentence)
        
        return '. '.join(modified_sentences)
    
    def synthesize_emotion(self, text, emotion, intensity=0.5):
        """Add emotional nuance to the text"""
        try:
            modified_text = self._add_emotional_markers(text, emotion, intensity)
            return {
                'status': 'success',
                'original_text': text,
                'modified_text': modified_text,
                'emotion': emotion,
                'intensity': intensity
            }
        except Exception as e:
            logger.error(f"Error synthesizing emotion: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'synthesize_emotion':
            return self.synthesize_emotion(
                request.get('text', ''),
                request.get('emotion', 'neutral'),
                request.get('intensity', 0.5)
            )
        else:
            return super().handle_request(request)
    
    def shutdown(self):
        """Gracefully shutdown the agent"""
        logger.info("Shutting down EmotionSynthesisAgent")
        # No call to super().stop() since BaseAgent does not have it
        # Add any additional cleanup here if needed

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "synthesis_status": "active",
            "last_synthesis_time": getattr(self, 'last_synthesis_time', 'N/A'),
            "processed_emotions_count": getattr(self, 'processed_emotions_count', 0)
        }
        base_status.update(specific_metrics)
        return base_status


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    agent = EmotionSynthesisAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        agent.shutdown()