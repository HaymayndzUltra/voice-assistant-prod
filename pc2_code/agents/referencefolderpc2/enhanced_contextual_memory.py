"""
Enhanced Contextual Memory Agent
- Provides advanced context management for conversations
- Implements hierarchical memory organization
- Features intelligent compression and summarization
- Supports project-specific contexts
- Includes memory optimization and cleanup
"""
import zmq
import json
import os
import threading
import time
import logging
import hashlib
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import deque
import re

# Configure logging
LOG_PATH = "logs/enhanced_contextual_memory.log"
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EnhancedContextualMemory")

class MemoryType(Enum):
    """Types of memory entries"""
    CODE = "code"
    QUERY = "query"
    RESPONSE = "response"
    ERROR = "error"
    DECISION = "decision"
    SUMMARY = "summary"

class MemoryPriority(Enum):
    """Priority levels for memory entries"""
    HIGH = 3
    MEDIUM = 2
    LOW = 1

@dataclass
class MemoryEntry:
    """Memory entry with metadata"""
    content: str
    type: MemoryType
    priority: MemoryPriority
    timestamp: float
    metadata: Optional[Dict] = None
    importance_score: float = 0.0
    last_accessed: float = 0.0
    access_count: int = 0

class MemoryHierarchy:
    """Manages hierarchical memory organization"""
    
    def __init__(self):
        self.short_term = deque(maxlen=50)  # Recent, high detail
        self.medium_term = deque(maxlen=200)  # Less recent, moderate detail
        self.long_term = deque(maxlen=1000)  # Oldest, highly summarized
        self.summaries = {}  # Session summaries
        self.lock = threading.Lock()
    
    def add_entry(self, entry: MemoryEntry):
        """Add entry to appropriate memory level"""
        with self.lock:
            # Update access tracking
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            # Add to short-term memory
            self.short_term.appendleft(entry)
            
            # Check if entry should be promoted
            self._promote_entries()
    
    def _promote_entries(self):
        """Promote entries based on importance and access patterns"""
        with self.lock:
            # Promote from short-term to medium-term
            while len(self.short_term) > self.short_term.maxlen:
                entry = self.short_term.pop()
                if self._should_promote(entry):
                    self.medium_term.appendleft(entry)
                else:
                    # Summarize and add to long-term
                    summary = self._summarize_entry(entry)
                    self.long_term.appendleft(summary)
            
            # Promote from medium-term to long-term
            while len(self.medium_term) > self.medium_term.maxlen:
                entry = self.medium_term.pop()
                summary = self._summarize_entry(entry)
                self.long_term.appendleft(summary)
    
    def _should_promote(self, entry: MemoryEntry) -> bool:
        """Determine if entry should be promoted based on importance"""
        return (
            entry.importance_score > 0.7 or
            entry.access_count > 5 or
            entry.priority == MemoryPriority.HIGH
        )
    
    def _summarize_entry(self, entry: MemoryEntry) -> MemoryEntry:
        """Create a summary of the entry"""
        if entry.type == MemoryType.CODE:
            summary = self._summarize_code(entry.content)
        elif entry.type in [MemoryType.QUERY, MemoryType.RESPONSE]:
            summary = self._summarize_conversation(entry.content)
        else:
            summary = entry.content
        
        return MemoryEntry(
            content=summary,
            type=entry.type,
            priority=entry.priority,
            timestamp=entry.timestamp,
            metadata=entry.metadata,
            importance_score=entry.importance_score * 0.8,  # Reduce importance in summary
            last_accessed=time.time(),
            access_count=entry.access_count
        )
    
    def _summarize_code(self, code: str) -> str:
        """Summarize code with domain detection"""
        try:
            # Basic code analysis
            lines = code.splitlines()
            total_lines = len(lines)
            
            # Detect domains
            domains = []
            code_lower = code.lower()
            
            if re.search(r"database|sql|sqlite", code_lower):
                domains.append("database")
            if re.search(r"web|http|flask|api|route", code_lower):
                domains.append("web")
            if re.search(r"concurrency|thread|async", code_lower):
                domains.append("concurrency")
            
            # Create summary
            summary = f"Code Summary ({total_lines} lines):\n"
            if domains:
                summary += f"Domains: {', '.join(domains)}\n"
            
            # Add key function/class names
            functions = re.findall(r"def\s+(\w+)", code)
            classes = re.findall(r"class\s+(\w+)", code)
            
            if functions:
                summary += f"Functions: {', '.join(functions[:5])}\n"
            if classes:
                summary += f"Classes: {', '.join(classes[:5])}\n"
            
            return summary
        except Exception as e:
            logger.error(f"Error summarizing code: {e}")
            return f"Error summarizing code: {str(e)}"
    
    def _summarize_conversation(self, text: str) -> str:
        """Summarize conversation text"""
        try:
            # Basic summarization
            sentences = text.split('.')
            if len(sentences) <= 3:
                return text
            
            # Keep first and last sentences, summarize middle
            summary = sentences[0] + '. '
            if len(sentences) > 2:
                summary += f"[{len(sentences)-2} sentences summarized]. "
            summary += sentences[-1] + '.'
            
            return summary
        except Exception as e:
            logger.error(f"Error summarizing conversation: {e}")
            return text

class EnhancedContextualMemory:
    """Enhanced contextual memory management"""
    
    def __init__(self, zmq_port=5596):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
        
        self.memory = MemoryHierarchy()
        self.running = True
        
        # Performance tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = time.time()
        
        logger.info(f"Enhanced Contextual Memory started on port {zmq_port}")
    
    def add_memory(self, content: str, memory_type: MemoryType, 
                  priority: MemoryPriority = MemoryPriority.MEDIUM,
                  metadata: Optional[Dict] = None) -> bool:
        """Add new memory entry"""
        try:
            entry = MemoryEntry(
                content=content,
                type=memory_type,
                priority=priority,
                timestamp=time.time(),
                metadata=metadata
            )
            
            # Calculate importance score
            entry.importance_score = self._calculate_importance(entry)
            
            # Add to memory hierarchy
            self.memory.add_entry(entry)
            return True
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return False
    
    def _calculate_importance(self, entry: MemoryEntry) -> float:
        """Calculate importance score for memory entry"""
        base_score = 0.5
        
        # Adjust based on type
        if entry.type == MemoryType.ERROR:
            base_score += 0.3
        elif entry.type == MemoryType.DECISION:
            base_score += 0.2
        
        # Adjust based on priority
        if entry.priority == MemoryPriority.HIGH:
            base_score += 0.2
        elif entry.priority == MemoryPriority.LOW:
            base_score -= 0.1
        
        # Adjust based on content length
        content_length = len(entry.content)
        if content_length > 1000:
            base_score += 0.1
        elif content_length < 50:
            base_score -= 0.1
        
        return min(max(base_score, 0.0), 1.0)
    
    def get_context(self, max_tokens: Optional[int] = None) -> Dict:
        """Get current context summary"""
        try:
            context = {
                "short_term": [],
                "medium_term": [],
                "long_term": [],
                "timestamp": time.time()
            }
            
            # Collect entries from each level
            with self.memory.lock:
                for entry in self.memory.short_term:
                    context["short_term"].append({
                        "content": entry.content,
                        "type": entry.type.value,
                        "timestamp": entry.timestamp
                    })
                
                for entry in self.memory.medium_term:
                    context["medium_term"].append({
                        "content": entry.content,
                        "type": entry.type.value,
                        "timestamp": entry.timestamp
                    })
                
                for entry in self.memory.long_term:
                    context["long_term"].append({
                        "content": entry.content,
                        "type": entry.type.value,
                        "timestamp": entry.timestamp
                    })
            
            return context
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return {"error": str(e)}
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests"""
        try:
            action = request.get("action")
            if not action:
                return {"error": "No action specified"}
            
            if action == "add_memory":
                return self._handle_add_memory(request)
            elif action == "get_context":
                return self._handle_get_context(request)
            elif action == "health_check":
                return self._handle_health_check()
            else:
                return {"error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {"error": str(e)}
    
    def _handle_add_memory(self, request: Dict) -> Dict:
        """Handle add_memory action"""
        try:
            content = request.get("content")
            memory_type = request.get("type")
            priority = request.get("priority", "MEDIUM")
            metadata = request.get("metadata")
            
            if not content or not memory_type:
                return {"error": "Missing required parameters"}
            
            success = self.add_memory(
                content=content,
                memory_type=MemoryType(memory_type),
                priority=MemoryPriority[priority],
                metadata=metadata
            )
            
            return {
                "status": "success" if success else "error",
                "message": "Memory added" if success else "Failed to add memory"
            }
        except Exception as e:
            logger.error(f"Error in add_memory: {e}")
            return {"error": str(e)}
    
    def _handle_get_context(self, request: Dict) -> Dict:
        """Handle get_context action"""
        try:
            max_tokens = request.get("max_tokens")
            context = self.get_context(max_tokens)
            return {"status": "success", "context": context}
        except Exception as e:
            logger.error(f"Error in get_context: {e}")
            return {"error": str(e)}
    
    def _handle_health_check(self) -> Dict:
        """Handle health check request"""
        uptime = time.time() - self.start_time
        return {
            "status": "ok",
            "service": "enhanced_contextual_memory",
            "uptime_seconds": uptime,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests
        }
    
    def run(self):
        """Run the memory service"""
        try:
            logger.info("Starting Enhanced Contextual Memory service")
            while self.running:
                try:
                    request = self.socket.recv_json()
                    self.total_requests += 1
                    
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                    
                    if response.get("status") == "success":
                        self.successful_requests += 1
                    else:
                        self.failed_requests += 1
                except zmq.error.Again:
                    continue
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    self.socket.send_json({"error": str(e)})
                    self.failed_requests += 1
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.socket.close()
        self.context.term()

def main():
    """Main entry point"""
    try:
        memory = EnhancedContextualMemory()
        memory.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 