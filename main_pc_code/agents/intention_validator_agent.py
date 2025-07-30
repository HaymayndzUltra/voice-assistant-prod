#!/usr/bin/env python3
"""
IntentionValidatorAgent - Validates and confirms user intentions
Enhanced with modern BaseAgent infrastructure and unified error handling
"""

import asyncio
import json
import re
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import zmq

# Modern imports using BaseAgent infrastructure
from common.core.base_agent import BaseAgent
from common.utils.path_manager import PathManager
from common.utils.data_models import ErrorSeverity
from common.config_manager import get_service_ip, get_service_url

class IntentionType(Enum):
    """Types of user intentions"""
    QUESTION = "question"
    COMMAND = "command"
    REQUEST = "request"
    CLARIFICATION = "clarification"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"

class ConfidenceLevel(Enum):
    """Confidence levels for intention validation"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCLEAR = "unclear"

@dataclass
class ValidationResult:
    """Result of intention validation"""
    intention_type: IntentionType
    confidence: ConfidenceLevel
    key_entities: List[str]
    requires_clarification: bool
    suggested_response: Optional[str] = None
    metadata: Dict[str, Any] = None

class IntentionValidatorAgent(BaseAgent):
    """
    Modern IntentionValidatorAgent using BaseAgent infrastructure
    Validates user intentions with high accuracy and confidence scoring
    """
    
    def __init__(self, name="IntentionValidatorAgent", port=5701):
        super().__init__(name, port)
        
        # Validation patterns and rules
        self.intention_patterns = {
            IntentionType.QUESTION: [
                r'\b(what|who|when|where|why|how|which|can|could|would|will|is|are|do|does|did)\b',
                r'\?',
                r'\b(tell me|explain|describe)\b'
            ],
            IntentionType.COMMAND: [
                r'\b(please|can you|could you|would you)\s+(do|make|create|generate|write|build)\b',
                r'\b(run|execute|start|stop|restart|launch)\b',
                r'\b(open|close|save|delete|remove)\b'
            ],
            IntentionType.REQUEST: [
                r'\b(I need|I want|I would like|help me|assist me)\b',
                r'\b(can you help|please help|I require)\b'
            ],
            IntentionType.CLARIFICATION: [
                r'\b(what do you mean|I don\'t understand|can you clarify|elaborate)\b',
                r'\b(confused|unclear|not sure)\b'
            ],
            IntentionType.GREETING: [
                r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b',
                r'\b(greetings|salutations)\b'
            ],
            IntentionType.GOODBYE: [
                r'\b(goodbye|bye|see you|farewell|talk to you later|gtg)\b',
                r'\b(thanks|thank you|that\'s all)\b'
            ]
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'person': r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            'location': r'\b(in|at|to|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
            'time': r'\b(today|tomorrow|yesterday|now|later|morning|afternoon|evening|night)\b',
            'number': r'\b(\d+)\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'file': r'\b[\w\-. ]+\.(txt|pdf|doc|docx|jpg|png|mp3|mp4|csv|json|xml|py|js|html|css)\b'
        }
        
        # Confidence thresholds
        self.confidence_thresholds = {
            'high': 0.8,
            'medium': 0.5,
            'low': 0.2
        }
        
        # ZMQ setup for communication
        self.context = zmq.Context()
        self.validation_publisher = self.context.socket(zmq.PUB)
        self.validation_publisher.bind(f"tcp://*:{port + 100}")  # Validation updates port
        
        # Background processing
        self.validation_queue = []
        self.queue_lock = threading.Lock()
        self.processing_thread = None
        self.running = False
        
        # Statistics
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'avg_confidence': 0.0,
            'intention_distribution': {intent.value: 0 for intent in IntentionType}
        }
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text using pattern matching"""
        entities = {}
        
        try:
            for entity_type, pattern in self.entity_patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if entity_type == 'location':
                        # For location pattern, we want the second group (actual location)
                        entities[entity_type] = [match[1] if isinstance(match, tuple) else match for match in matches]
                    else:
                        entities[entity_type] = matches
            
            return entities
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Entity extraction failed", {"error": str(e), "text": text[:100]})
            return {}
    
    def calculate_intention_confidence(self, text: str, intention_type: IntentionType) -> float:
        """Calculate confidence score for a specific intention type"""
        try:
            patterns = self.intention_patterns.get(intention_type, [])
            matches = 0
            total_patterns = len(patterns)
            
            if total_patterns == 0:
                return 0.0
            
            text_lower = text.lower()
            
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    matches += 1
            
            # Base confidence from pattern matches
            pattern_confidence = matches / total_patterns
            
            # Adjust based on text characteristics
            length_factor = min(len(text.split()) / 10, 1.0)  # Longer text can be more confident
            question_mark_bonus = 0.2 if '?' in text and intention_type == IntentionType.QUESTION else 0.0
            
            final_confidence = min(pattern_confidence + length_factor * 0.1 + question_mark_bonus, 1.0)
            
            return final_confidence
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Confidence calculation failed", {"error": str(e)})
            return 0.0
    
    def validate_intention(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate user intention with comprehensive analysis"""
        try:
            if not user_input or not user_input.strip():
                return ValidationResult(
                    intention_type=IntentionType.UNKNOWN,
                    confidence=ConfidenceLevel.UNCLEAR,
                    key_entities=[],
                    requires_clarification=True,
                    suggested_response="I didn't receive any input. Could you please tell me what you need?"
                )
            
            # Calculate confidence for each intention type
            intention_scores = {}
            for intention_type in IntentionType:
                if intention_type != IntentionType.UNKNOWN:
                    score = self.calculate_intention_confidence(user_input, intention_type)
                    intention_scores[intention_type] = score
            
            # Determine best intention match
            if intention_scores:
                best_intention = max(intention_scores, key=intention_scores.get)
                best_score = intention_scores[best_intention]
            else:
                best_intention = IntentionType.UNKNOWN
                best_score = 0.0
            
            # Determine confidence level
            if best_score >= self.confidence_thresholds['high']:
                confidence = ConfidenceLevel.HIGH
            elif best_score >= self.confidence_thresholds['medium']:
                confidence = ConfidenceLevel.MEDIUM
            elif best_score >= self.confidence_thresholds['low']:
                confidence = ConfidenceLevel.LOW
            else:
                confidence = ConfidenceLevel.UNCLEAR
                best_intention = IntentionType.UNKNOWN
            
            # Extract entities
            entities = self.extract_entities(user_input)
            key_entities = []
            for entity_list in entities.values():
                key_entities.extend(entity_list)
            
            # Determine if clarification is needed
            requires_clarification = (
                confidence in [ConfidenceLevel.LOW, ConfidenceLevel.UNCLEAR] or
                (best_intention == IntentionType.UNKNOWN) or
                (best_intention == IntentionType.CLARIFICATION)
            )
            
            # Generate suggested response
            suggested_response = self._generate_suggested_response(
                best_intention, confidence, key_entities, requires_clarification
            )
            
            # Create result
            result = ValidationResult(
                intention_type=best_intention,
                confidence=confidence,
                key_entities=key_entities,
                requires_clarification=requires_clarification,
                suggested_response=suggested_response,
                metadata={
                    'all_scores': {intent.value: score for intent, score in intention_scores.items()},
                    'entities': entities,
                    'input_length': len(user_input),
                    'word_count': len(user_input.split()),
                    'context': context
                }
            )
            
            # Update statistics
            self._update_statistics(result)
            
            # Publish validation result
            self._publish_validation_result(user_input, result)
            
            return result
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Intention validation failed", {"error": str(e), "input": user_input[:100]})
            
            return ValidationResult(
                intention_type=IntentionType.UNKNOWN,
                confidence=ConfidenceLevel.UNCLEAR,
                key_entities=[],
                requires_clarification=True,
                suggested_response="I encountered an error while processing your request. Could you please try again?"
            )
    
    def _generate_suggested_response(self, intention: IntentionType, confidence: ConfidenceLevel, 
                                   entities: List[str], requires_clarification: bool) -> str:
        """Generate appropriate response suggestion"""
        try:
            if requires_clarification:
                if intention == IntentionType.UNKNOWN:
                    return "I'm not sure what you're asking for. Could you please provide more details?"
                elif confidence == ConfidenceLevel.LOW:
                    return f"I think you're asking about {intention.value}, but I'm not entirely sure. Could you clarify?"
                else:
                    return "Could you provide more specific information about what you need?"
            
            # High confidence responses
            response_templates = {
                IntentionType.QUESTION: "I understand you have a question. Let me help you find the answer.",
                IntentionType.COMMAND: "I understand you want me to perform an action. I'll process your command.",
                IntentionType.REQUEST: "I understand you need assistance. I'm here to help.",
                IntentionType.GREETING: "Hello! How can I assist you today?",
                IntentionType.GOODBYE: "Goodbye! Feel free to return if you need more assistance.",
                IntentionType.CLARIFICATION: "I understand you need clarification. Let me explain that better."
            }
            
            base_response = response_templates.get(intention, "I understand your request.")
            
            # Add entity context if relevant
            if entities and len(entities) <= 3:
                entity_text = ", ".join(entities[:3])
                base_response += f" I noticed you mentioned: {entity_text}."
            
            return base_response
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Response generation failed", {"error": str(e)})
            return "I understand your request and will do my best to help."
    
    def _update_statistics(self, result: ValidationResult):
        """Update validation statistics"""
        try:
            self.validation_stats['total_validations'] += 1
            
            if result.confidence != ConfidenceLevel.UNCLEAR:
                self.validation_stats['successful_validations'] += 1
            else:
                self.validation_stats['failed_validations'] += 1
            
            # Update intention distribution
            self.validation_stats['intention_distribution'][result.intention_type.value] += 1
            
            # Update average confidence (simplified calculation)
            confidence_values = {'high': 0.9, 'medium': 0.7, 'low': 0.4, 'unclear': 0.1}
            current_avg = self.validation_stats['avg_confidence']
            total = self.validation_stats['total_validations']
            new_value = confidence_values.get(result.confidence.value, 0.1)
            self.validation_stats['avg_confidence'] = ((current_avg * (total - 1)) + new_value) / total
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Statistics update failed", {"error": str(e)})
    
    def _publish_validation_result(self, input_text: str, result: ValidationResult):
        """Publish validation result to interested services"""
        try:
            validation_event = {
                'timestamp': time.time(),
                'input': input_text[:100],  # Truncate for privacy
                'intention_type': result.intention_type.value,
                'confidence': result.confidence.value,
                'entities_count': len(result.key_entities),
                'requires_clarification': result.requires_clarification
            }
            
            self.validation_publisher.send_string(f"VALIDATION_RESULT {json.dumps(validation_event)}")
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Validation result publishing failed", {"error": str(e)})
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get current validation statistics"""
        return {
            'statistics': self.validation_stats.copy(),
            'timestamp': time.time(),
            'agent_name': self.name
        }
    
    def process_batch_validation(self, inputs: List[str]) -> List[ValidationResult]:
        """Process multiple validation requests in batch"""
        results = []
        
        try:
            for user_input in inputs:
                result = self.validate_intention(user_input)
                results.append(result)
            
            self.logger.info(f"Processed batch validation for {len(inputs)} inputs")
            return results
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Batch validation failed", {"error": str(e), "batch_size": len(inputs)})
            return results
    
    async def start(self):
        """Start the IntentionValidatorAgent service"""
        try:
            self.logger.info(f"Starting IntentionValidatorAgent on port {self.port}")
            
            # Start background processing
            self.running = True
            self.processing_thread = threading.Thread(target=self._background_processing, daemon=True)
            self.processing_thread.start()
            
            self.logger.info("IntentionValidatorAgent started successfully")
            
            # Keep the service running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.report_error(ErrorSeverity.CRITICAL, "Failed to start IntentionValidatorAgent", {"error": str(e)})
            raise
    
    def _background_processing(self):
        """Background processing for queued validations"""
        while self.running:
            try:
                # Process any queued items
                with self.queue_lock:
                    if self.validation_queue:
                        # Process queue items if needed
                        pass
                
                # Periodic statistics logging
                if self.validation_stats['total_validations'] % 100 == 0 and self.validation_stats['total_validations'] > 0:
                    self.logger.info(f"Validation statistics: {self.get_validation_statistics()}")
                
                time.sleep(1)
                
            except Exception as e:
                self.report_error(ErrorSeverity.WARNING, "Background processing error", {"error": str(e)})
                time.sleep(5)
    
    def cleanup(self):
        """Modern cleanup using try...finally pattern"""
        self.logger.info("Starting IntentionValidatorAgent cleanup...")
        cleanup_errors = []
        
        try:
            # Stop background processing
            self.running = False
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5)
            
            # Close ZMQ resources
            try:
                if hasattr(self, 'validation_publisher'):
                    self.validation_publisher.close()
                if hasattr(self, 'context'):
                    self.context.term()
            except Exception as e:
                cleanup_errors.append(f"ZMQ cleanup error: {e}")
                
        finally:
            # Always call parent cleanup for BaseAgent resources
            try:
                super().cleanup()
                self.logger.info("✅ IntentionValidatorAgent cleanup completed")
            except Exception as e:
                cleanup_errors.append(f"BaseAgent cleanup error: {e}")
        
        if cleanup_errors:
            self.logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors: {cleanup_errors}")

if __name__ == "__main__":
    import asyncio
    
    agent = IntentionValidatorAgent()
    
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        agent.logger.info("IntentionValidatorAgent interrupted by user")
    except Exception as e:
        agent.logger.error(f"IntentionValidatorAgent error: {e}")
    finally:
        agent.cleanup()
