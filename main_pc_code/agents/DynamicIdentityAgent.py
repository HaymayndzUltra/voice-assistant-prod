#!/usr/bin/env python3
"""
DynamicIdentityAgent - Manages the AI's dynamic personality and identity
Handles context-aware identity switching and personality adaptation
Modern implementation using BaseAgent infrastructure
"""

import json
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import zmq
from dataclasses import dataclass, field
from enum import Enum

# Modern imports - using BaseAgent infrastructure
from common.core.base_agent import BaseAgent
from common.utils.path_manager import PathManager
from common.utils.data_models import ErrorSeverity
from common.config_manager import get_service_ip, get_service_url

@dataclass
class IdentityProfile:
    """Data class for identity profiles"""
    name: str
    personality_traits: Dict[str, float] = field(default_factory=dict)
    communication_style: Dict[str, Any] = field(default_factory=dict)
    knowledge_domains: List[str] = field(default_factory=list)
    context_triggers: List[str] = field(default_factory=list)
    active_duration: int = 300  # seconds
    usage_count: int = 0
    last_used: float = field(default_factory=time.time)

class IdentityContext(Enum):
    """Available identity contexts"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    EDUCATIONAL = "educational"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    SUPPORTIVE = "supportive"

class DynamicIdentityAgent(BaseAgent):
    """
    Modern DynamicIdentityAgent using BaseAgent infrastructure
    """
    
    def __init__(self, name="DynamicIdentityAgent", port=5802):
        super().__init__(name, port)
        
        # Identity management
        self.current_identity: Optional[IdentityProfile] = None
        self.identity_profiles: Dict[str, IdentityProfile] = {}
        self.context_history: List[Dict[str, Any]] = []
        self.identity_lock = threading.Lock()
        
        # Configuration using modern path management
        self.profiles_file = PathManager.get_project_root() / "data" / "identity_profiles.json"
        self.profiles_file.parent.mkdir(parents=True, exist_ok=True)
        
        # ZMQ setup for communication
        self.context = zmq.Context()
        self.identity_broadcaster = self.context.socket(zmq.PUB)
        self.identity_broadcaster.bind(f"tcp://*:{port + 100}")  # Identity updates port
        
        # Load initial profiles
        self.load_identity_profiles()
        self.initialize_default_profiles()
        
        # Background tasks
        self.identity_monitor_thread = None
        self.running = False
        
    def load_identity_profiles(self):
        """Load identity profiles from storage"""
        try:
            if self.profiles_file.exists():
                with open(self.profiles_file, 'r') as f:
                    profiles_data = json.load(f)
                    
                for name, data in profiles_data.items():
                    profile = IdentityProfile(
                        name=name,
                        personality_traits=data.get('personality_traits', {}),
                        communication_style=data.get('communication_style', {}),
                        knowledge_domains=data.get('knowledge_domains', []),
                        context_triggers=data.get('context_triggers', []),
                        active_duration=data.get('active_duration', 300),
                        usage_count=data.get('usage_count', 0),
                        last_used=data.get('last_used', time.time())
                    )
                    self.identity_profiles[name] = profile
                    
                self.logger.info(f"Loaded {len(self.identity_profiles)} identity profiles")
            else:
                self.logger.info("No existing identity profiles found, will create defaults")
                
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Failed to load identity profiles", {"error": str(e)})
    
    def initialize_default_profiles(self):
        """Initialize default identity profiles if none exist"""
        if not self.identity_profiles:
            default_profiles = {
                "Professional": IdentityProfile(
                    name="Professional",
                    personality_traits={
                        "formality": 0.8,
                        "precision": 0.9,
                        "empathy": 0.6,
                        "creativity": 0.4
                    },
                    communication_style={
                        "tone": "formal",
                        "verbosity": "concise",
                        "technical_level": "high"
                    },
                    knowledge_domains=["business", "technology", "research"],
                    context_triggers=["work", "meeting", "presentation", "analysis"]
                ),
                
                "Casual": IdentityProfile(
                    name="Casual",
                    personality_traits={
                        "formality": 0.3,
                        "precision": 0.6,
                        "empathy": 0.8,
                        "creativity": 0.7
                    },
                    communication_style={
                        "tone": "friendly",
                        "verbosity": "conversational",
                        "technical_level": "moderate"
                    },
                    knowledge_domains=["general", "entertainment", "lifestyle"],
                    context_triggers=["chat", "casual", "personal", "relaxed"]
                ),
                
                "Educational": IdentityProfile(
                    name="Educational",
                    personality_traits={
                        "formality": 0.6,
                        "precision": 0.9,
                        "empathy": 0.8,
                        "creativity": 0.6
                    },
                    communication_style={
                        "tone": "encouraging",
                        "verbosity": "detailed",
                        "technical_level": "adaptive"
                    },
                    knowledge_domains=["education", "science", "mathematics", "literature"],
                    context_triggers=["learn", "teach", "explain", "study", "homework"]
                ),
                
                "Creative": IdentityProfile(
                    name="Creative",
                    personality_traits={
                        "formality": 0.4,
                        "precision": 0.5,
                        "empathy": 0.7,
                        "creativity": 0.9
                    },
                    communication_style={
                        "tone": "inspiring",
                        "verbosity": "expressive",
                        "technical_level": "moderate"
                    },
                    knowledge_domains=["art", "design", "writing", "music"],
                    context_triggers=["create", "design", "write", "art", "story"]
                )
            }
            
            self.identity_profiles.update(default_profiles)
            self.save_identity_profiles()
            self.logger.info("Initialized default identity profiles")
    
    def save_identity_profiles(self):
        """Save identity profiles to storage"""
        try:
            profiles_data = {}
            for name, profile in self.identity_profiles.items():
                profiles_data[name] = {
                    'personality_traits': profile.personality_traits,
                    'communication_style': profile.communication_style,
                    'knowledge_domains': profile.knowledge_domains,
                    'context_triggers': profile.context_triggers,
                    'active_duration': profile.active_duration,
                    'usage_count': profile.usage_count,
                    'last_used': profile.last_used
                }
            
            with open(self.profiles_file, 'w') as f:
                json.dump(profiles_data, f, indent=2)
                
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Failed to save identity profiles", {"error": str(e)})
    
    def analyze_context(self, user_input: str, conversation_history: List[Dict[str, Any]]) -> IdentityContext:
        """Analyze context to determine appropriate identity"""
        try:
            # Simple keyword-based analysis (can be enhanced with ML)
            text_lower = user_input.lower()
            
            # Technical context
            if any(word in text_lower for word in ["code", "programming", "technical", "system", "debug"]):
                return IdentityContext.TECHNICAL
            
            # Educational context
            if any(word in text_lower for word in ["learn", "teach", "explain", "study", "homework"]):
                return IdentityContext.EDUCATIONAL
            
            # Creative context
            if any(word in text_lower for word in ["create", "design", "write", "story", "art"]):
                return IdentityContext.CREATIVE
            
            # Professional context
            if any(word in text_lower for word in ["work", "business", "meeting", "project", "analysis"]):
                return IdentityContext.PROFESSIONAL
            
            # Supportive context
            if any(word in text_lower for word in ["help", "support", "problem", "issue", "stuck"]):
                return IdentityContext.SUPPORTIVE
            
            # Default to casual
            return IdentityContext.CASUAL
            
        except Exception as e:
            self.report_error(ErrorSeverity.WARNING, "Context analysis failed", {"error": str(e)})
            return IdentityContext.CASUAL
    
    def select_identity(self, context: IdentityContext, user_preferences: Optional[Dict[str, Any]] = None) -> Optional[IdentityProfile]:
        """Select appropriate identity based on context"""
        try:
            with self.identity_lock:
                # Find profiles matching the context
                matching_profiles = []
                
                for profile in self.identity_profiles.values():
                    if context.value in profile.context_triggers:
                        matching_profiles.append(profile)
                
                if not matching_profiles:
                    # Fallback to default profiles based on context
                    context_mapping = {
                        IdentityContext.PROFESSIONAL: "Professional",
                        IdentityContext.CASUAL: "Casual",
                        IdentityContext.EDUCATIONAL: "Educational",
                        IdentityContext.CREATIVE: "Creative",
                        IdentityContext.TECHNICAL: "Professional",
                        IdentityContext.SUPPORTIVE: "Educational"
                    }
                    
                    fallback_name = context_mapping.get(context, "Casual")
                    if fallback_name in self.identity_profiles:
                        matching_profiles = [self.identity_profiles[fallback_name]]
                
                if matching_profiles:
                    # Select the most appropriate profile (can be enhanced with scoring)
                    selected_profile = matching_profiles[0]
                    
                    # Update usage statistics
                    selected_profile.usage_count += 1
                    selected_profile.last_used = time.time()
                    
                    return selected_profile
                
                return None
                
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Identity selection failed", {"error": str(e)})
            return None
    
    def switch_identity(self, target_identity: IdentityProfile):
        """Switch to a new identity profile"""
        try:
            with self.identity_lock:
                old_identity = self.current_identity.name if self.current_identity else "None"
                self.current_identity = target_identity
                
                # Broadcast identity change
                identity_update = {
                    "timestamp": time.time(),
                    "old_identity": old_identity,
                    "new_identity": target_identity.name,
                    "personality_traits": target_identity.personality_traits,
                    "communication_style": target_identity.communication_style
                }
                
                self.identity_broadcaster.send_string(f"IDENTITY_UPDATE {json.dumps(identity_update)}")
                
                # Log the switch
                self.context_history.append(identity_update)
                self.logger.info(f"Identity switched from {old_identity} to {target_identity.name}")
                
                # Save updated profiles
                self.save_identity_profiles()
                
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Identity switch failed", {"error": str(e)})
    
    def get_current_identity_info(self) -> Dict[str, Any]:
        """Get current identity information"""
        if self.current_identity:
            return {
                "name": self.current_identity.name,
                "personality_traits": self.current_identity.personality_traits,
                "communication_style": self.current_identity.communication_style,
                "knowledge_domains": self.current_identity.knowledge_domains,
                "usage_count": self.current_identity.usage_count,
                "last_used": self.current_identity.last_used
            }
        return {"name": "None", "message": "No active identity"}
    
    def process_request(self, user_input: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process user request and adapt identity accordingly"""
        try:
            if conversation_history is None:
                conversation_history = []
            
            # Analyze context
            context = self.analyze_context(user_input, conversation_history)
            
            # Select appropriate identity
            target_identity = self.select_identity(context)
            
            if target_identity and (not self.current_identity or target_identity.name != self.current_identity.name):
                self.switch_identity(target_identity)
            
            # Return response with current identity info
            return {
                "status": "success",
                "context_detected": context.value,
                "current_identity": self.get_current_identity_info(),
                "adaptation_made": target_identity is not None,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.report_error(ErrorSeverity.ERROR, "Request processing failed", {"error": str(e)})
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def start_monitoring(self):
        """Start background monitoring tasks"""
        self.running = True
        self.identity_monitor_thread = threading.Thread(target=self._monitor_identity_usage, daemon=True)
        self.identity_monitor_thread.start()
        self.logger.info("Identity monitoring started")
    
    def _monitor_identity_usage(self):
        """Monitor identity usage and performance"""
        while self.running:
            try:
                # Clean up old context history (keep last 100 entries)
                if len(self.context_history) > 100:
                    self.context_history = self.context_history[-100:]
                
                # Save profiles periodically
                self.save_identity_profiles()
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.report_error(ErrorSeverity.WARNING, "Identity monitoring error", {"error": str(e)})
                time.sleep(10)
    
    async def start(self):
        """Start the DynamicIdentityAgent service"""
        try:
            self.logger.info(f"Starting DynamicIdentityAgent on port {self.port}")
            
            # Start monitoring
            self.start_monitoring()
            
            # Set default identity
            if not self.current_identity and "Casual" in self.identity_profiles:
                self.current_identity = self.identity_profiles["Casual"]
                self.logger.info("Set default identity to Casual")
            
            self.logger.info("DynamicIdentityAgent started successfully")
            
            # Keep the service running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.report_error(ErrorSeverity.CRITICAL, "Failed to start DynamicIdentityAgent", {"error": str(e)})
            raise
    
    def cleanup(self):
        """Modern cleanup using try...finally pattern"""
        self.logger.info("Starting DynamicIdentityAgent cleanup...")
        cleanup_errors = []
        
        try:
            # Stop monitoring
            self.running = False
            if self.identity_monitor_thread and self.identity_monitor_thread.is_alive():
                self.identity_monitor_thread.join(timeout=5)
            
            # Save final state
            try:
                self.save_identity_profiles()
            except Exception as e:
                cleanup_errors.append(f"Profile save error: {e}")
            
            # Close ZMQ resources
            try:
                if hasattr(self, 'identity_broadcaster'):
                    self.identity_broadcaster.close()
                if hasattr(self, 'context'):
                    self.context.term()
            except Exception as e:
                cleanup_errors.append(f"ZMQ cleanup error: {e}")
                
        finally:
            # Always call parent cleanup for BaseAgent resources
            try:
                super().cleanup()
                self.logger.info("✅ DynamicIdentityAgent cleanup completed")
            except Exception as e:
                cleanup_errors.append(f"BaseAgent cleanup error: {e}")
        
        if cleanup_errors:
            self.logger.warning(f"Cleanup completed with {len(cleanup_errors)} errors: {cleanup_errors}")

if __name__ == "__main__":
    import asyncio
    
    agent = DynamicIdentityAgent()
    
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        agent.logger.info("DynamicIdentityAgent interrupted by user")
    except Exception as e:
        agent.logger.error(f"DynamicIdentityAgent error: {e}")
    finally:
        agent.cleanup()
