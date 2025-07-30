#!/usr/bin/env python3
"""
NLU Agent Integration Service for Modern GUI Control Center
Connects the GUI to the Natural Language Understanding agent
"""

import threading
import time
import json
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NLUIntegration")

@dataclass
class NLURequest:
    """NLU request data structure"""
    text: str
    request_id: str
    timestamp: float

@dataclass 
class NLUResponse:
    """NLU response data structure"""
    intent: str
    entities: list
    confidence: float
    request_id: str
    processing_time: float

class NLUIntegrationService:
    """Service to integrate NLU agent with GUI"""
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.is_connected = False
        self.nlu_agent_status = "disconnected"
        self.last_response_time = 0
        self.response_cache = {}
        self.request_queue = []
        
        # Mock NLU patterns for demo (will connect to real agent later)
        self.intent_patterns = {
            # GUI Control intents
            "open dashboard": {"intent": "[GUI] Open Dashboard", "confidence": 0.95},
            "show tasks": {"intent": "[GUI] Show Tasks", "confidence": 0.95},
            "open memory": {"intent": "[GUI] Open Memory", "confidence": 0.95}, 
            "show monitoring": {"intent": "[GUI] Show Monitoring", "confidence": 0.95},
            "open agents": {"intent": "[GUI] Open Agents", "confidence": 0.95},
            "show automation": {"intent": "[GUI] Show Automation", "confidence": 0.95},
            
            # Task Management intents
            "create task": {"intent": "[Task] Create", "confidence": 0.9},
            "new task": {"intent": "[Task] Create", "confidence": 0.9},
            "add todo": {"intent": "[Task] Add TODO", "confidence": 0.9},
            "mark done": {"intent": "[Task] Complete", "confidence": 0.9},
            "complete task": {"intent": "[Task] Complete", "confidence": 0.9},
            
            # Agent Control intents
            "start agent": {"intent": "[Agent] Start", "confidence": 0.9},
            "stop agent": {"intent": "[Agent] Stop", "confidence": 0.9}, 
            "restart agent": {"intent": "[Agent] Restart", "confidence": 0.9},
            "agent status": {"intent": "[Agent] Status", "confidence": 0.9},
            
            # System intents
            "refresh": {"intent": "[System] Refresh", "confidence": 0.85},
            "help": {"intent": "[System] Help", "confidence": 0.85},
            "exit": {"intent": "[System] Exit", "confidence": 0.85},
        }
        
        logger.info("🤖 NLU Integration Service initialized")
    
    def start(self):
        """Start the NLU integration service"""
        logger.info("🚀 Starting NLU Integration Service...")
        
        # Start background connection monitoring
        self._start_connection_monitor()
        
        # Publish service start event
        if self.event_bus:
            self.event_bus.publish("nlu_service_started", {
                "status": "started",
                "timestamp": time.time()
            })
        
        logger.info("✅ NLU Integration Service started")
    
    def stop(self):
        """Stop the NLU integration service"""
        logger.info("🛑 Stopping NLU Integration Service...")
        self.is_connected = False
        
        if self.event_bus:
            self.event_bus.publish("nlu_service_stopped", {
                "status": "stopped", 
                "timestamp": time.time()
            })
        
        logger.info("✅ NLU Integration Service stopped")
    
    def process_text(self, text: str, callback: Optional[Callable] = None) -> NLUResponse:
        """Process natural language text and return intent/entities"""
        
        start_time = time.time()
        request_id = f"nlu_{int(start_time * 1000)}"
        
        logger.info(f"🔍 Processing text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        try:
            # Mock NLU processing for now (will connect to real agent later)
            intent, confidence = self._extract_intent_mock(text)
            entities = self._extract_entities_mock(text, intent)
            
            processing_time = time.time() - start_time
            
            response = NLUResponse(
                intent=intent,
                entities=entities,
                confidence=confidence,
                request_id=request_id,
                processing_time=processing_time
            )
            
            # Cache response
            self.response_cache[request_id] = response
            self.last_response_time = time.time()
            
            # Publish NLU result event
            if self.event_bus:
                self.event_bus.publish("nlu_result", {
                    "intent": intent,
                    "entities": entities,
                    "confidence": confidence,
                    "text": text,
                    "processing_time": processing_time
                })
            
            # Execute callback if provided
            if callback:
                callback(response)
            
            logger.info(f"✅ NLU Result: {intent} (confidence: {confidence:.2f})")
            return response
            
        except Exception as e:
            logger.error(f"❌ NLU processing error: {e}")
            
            error_response = NLUResponse(
                intent="[Error] Processing Failed",
                entities=[],
                confidence=0.0,
                request_id=request_id,
                processing_time=time.time() - start_time
            )
            
            if callback:
                callback(error_response)
                
            return error_response
    
    def _extract_intent_mock(self, text: str) -> tuple[str, float]:
        """Mock intent extraction (will be replaced with real NLU agent)"""
        
        text_lower = text.lower().strip()
        
        # Direct pattern matching
        for pattern, result in self.intent_patterns.items():
            if pattern in text_lower:
                return result["intent"], result["confidence"]
        
        # Fuzzy matching for common variations
        if any(word in text_lower for word in ["task", "todo", "create", "new"]):
            return "[Task] Create", 0.8
        elif any(word in text_lower for word in ["open", "show", "display"]):
            return "[GUI] Open View", 0.75
        elif any(word in text_lower for word in ["start", "run", "launch"]):
            return "[Agent] Start", 0.75
        elif any(word in text_lower for word in ["stop", "halt", "end"]):
            return "[Agent] Stop", 0.75
        elif any(word in text_lower for word in ["help", "assist", "support"]):
            return "[System] Help", 0.8
        
        # Default unknown intent
        return "[Unknown]", 0.3
    
    def _extract_entities_mock(self, text: str, intent: str) -> list:
        """Mock entity extraction (will be replaced with real NLU agent)"""
        
        entities = []
        text_lower = text.lower()
        
        # Extract entities based on intent
        if intent.startswith("[Task]"):
            # Extract task names or descriptions
            if "create" in text_lower or "new" in text_lower:
                # Look for text after "create" or "new"
                for keyword in ["create", "new", "add"]:
                    if keyword in text_lower:
                        parts = text_lower.split(keyword, 1)
                        if len(parts) > 1:
                            task_desc = parts[1].strip()
                            if task_desc:
                                entities.append({
                                    "entity": "task_description",
                                    "value": task_desc,
                                    "confidence": 0.8
                                })
                        break
        
        elif intent.startswith("[GUI]"):
            # Extract view names
            view_keywords = ["dashboard", "tasks", "memory", "monitoring", "agents", "automation"]
            for view in view_keywords:
                if view in text_lower:
                    entities.append({
                        "entity": "view_name", 
                        "value": view,
                        "confidence": 0.9
                    })
                    break
        
        elif intent.startswith("[Agent]"):
            # Extract agent names or IDs
            if "agent" in text_lower:
                # Look for agent names or numbers
                words = text.split()
                for i, word in enumerate(words):
                    if word.lower() == "agent" and i + 1 < len(words):
                        agent_ref = words[i + 1]
                        entities.append({
                            "entity": "agent_reference",
                            "value": agent_ref,
                            "confidence": 0.8
                        })
                        break
        
        return entities
    
    def _start_connection_monitor(self):
        """Start background thread to monitor NLU agent connection"""
        
        def monitor_connection():
            while True:
                try:
                    # Mock connection check (will implement real agent ping later)
                    self.is_connected = True
                    self.nlu_agent_status = "connected"
                    
                    # Publish status update
                    if self.event_bus:
                        self.event_bus.publish("nlu_status_update", {
                            "status": self.nlu_agent_status,
                            "is_connected": self.is_connected,
                            "last_response_time": self.last_response_time,
                            "timestamp": time.time()
                        })
                    
                except Exception as e:
                    logger.warning(f"NLU connection check failed: {e}")
                    self.is_connected = False
                    self.nlu_agent_status = "disconnected"
                
                time.sleep(30)  # Check every 30 seconds
        
        monitor_thread = threading.Thread(target=monitor_connection, daemon=True)
        monitor_thread.start()
        logger.info("🔍 NLU connection monitor started")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current NLU service status"""
        return {
            "is_connected": self.is_connected,
            "agent_status": self.nlu_agent_status, 
            "last_response_time": self.last_response_time,
            "cached_responses": len(self.response_cache),
            "queued_requests": len(self.request_queue),
            "available_intents": len(self.intent_patterns)
        }
    
    def clear_cache(self):
        """Clear response cache"""
        self.response_cache.clear()
        logger.info("🧹 NLU response cache cleared")
    
    def get_available_intents(self) -> list:
        """Get list of available intents"""
        return list(set(result["intent"] for result in self.intent_patterns.values()))

# Singleton instance
_nlu_service = None

def get_nlu_service(event_bus=None) -> NLUIntegrationService:
    """Get singleton NLU integration service instance"""
    global _nlu_service
    if _nlu_service is None:
        _nlu_service = NLUIntegrationService(event_bus)
    return _nlu_service
