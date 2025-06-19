#!/usr/bin/env python3
"""
Unified Web Agent
----------------
Combines features from:
1. Autonomous Web Assistant
2. Enhanced Web Scraper
3. Web Scraper Agent

Features:
- Proactive information gathering
- Advanced web scraping with multiple strategies
- Form filling and navigation
- Caching and database storage
- AutoGen framework integration
- Conversation analysis
- Dynamic browsing with context awareness
- Real-time reference provision
- Autonomous decision-making
"""

import zmq
import json
import time
import logging
import sys
import os
import traceback
import threading
import requests
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import base64
from bs4 import BeautifulSoup
import urllib.parse
import tempfile

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility with fallback
try:
    from agents.utils.config_parser import parse_agent_args
    _agent_args = parse_agent_args()
except ImportError:
    class DummyArgs:
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = 'logs/unified_web_agent.log'
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UnifiedWebAgent")

# ZMQ Configuration
UNIFIED_WEB_PORT = 7126  # Main port
HEALTH_CHECK_PORT = 7127  # Health check port

# Browser automation settings
MIN_DELAY_BETWEEN_REQUESTS = 2  # seconds
MAX_RETRIES = 3
TIMEOUT = 30  # seconds

class UnifiedWebAgent:
    """Unified web agent combining autonomous assistance, scraping, and automation"""
    
    def __init__(self, port=None):
        """Initialize the unified web agent"""
        # Set up ports
        self.main_port = port if port else UNIFIED_WEB_PORT
        self.health_port = self.main_port + 1
        
        # ZMQ setup
        self.context = zmq.Context()
        
        # Main socket for requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.main_port}")
        logger.info(f"Unified Web Agent bound to port {self.main_port}")
        
        # Health check socket
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://*:{self.health_port}")
        logger.info(f"Health check bound to port {self.health_port}")
        
        # Setup directories
        self.cache_dir = Path('cache') / "web_agent"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.output_dir = Path('output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = self.cache_dir / "web_agent_cache.sqlite"
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        
        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # State tracking
        self.current_url = None
        self.page_content = None
        self.last_request_time = 0
        self.conversation_context = []
        self.running = True
        
        # Decision-making parameters
        self.proactive_mode = True
        self.confidence_threshold = 0.7
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_requests = 0
        self.start_time = time.time()
        
        logger.info(f"Unified Web Agent initialized on port {self.main_port}")
    
    def _create_tables(self):
        """Create necessary database tables"""
        cursor = self.conn.cursor()
        
        # Cache table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            url TEXT PRIMARY KEY,
            content TEXT,
            timestamp REAL,
            headers TEXT,
            status_code INTEGER
        )
        ''')
        
        # Scraping history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraping_history (
            id INTEGER PRIMARY KEY,
            url TEXT,
            data_type TEXT,
            output_format TEXT,
            timestamp REAL,
            success BOOLEAN,
            error TEXT
        )
        ''')
        
        # Form history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS form_history (
            id INTEGER PRIMARY KEY,
            url TEXT,
            form_data TEXT,
            timestamp REAL,
            success BOOLEAN,
            error TEXT
        )
        ''')
        
        self.conn.commit()
        logger.info("Database tables created")

    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'UnifiedWebAgent',
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time() - self.start_time,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'health_check_requests': self.health_check_requests,
            'cache_size': self._get_cache_size(),
            'scraping_history_size': self._get_scraping_history_size(),
            'form_history_size': self._get_form_history_size(),
            'current_url': self.current_url,
            'proactive_mode': self.proactive_mode,
            'port': self.main_port
        }

    def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL and return the page content"""
        try:
            self.total_requests += 1
            
            # Check cache first
            cached_content = self._get_cached_content(url)
            if cached_content:
                self.current_url = url
                self.page_content = cached_content
                self.successful_requests += 1
                return {
                    "status": "success",
                    "url": url,
                    "content": cached_content,
                    "cached": True
                }
            
            # Respect rate limiting
            time_since_last = time.time() - self.last_request_time
            if time_since_last < MIN_DELAY_BETWEEN_REQUESTS:
                time.sleep(MIN_DELAY_BETWEEN_REQUESTS - time_since_last)
            
            # Make request
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            
            # Parse content
            soup = BeautifulSoup(response.content, 'html.parser')
            content = soup.get_text()
            
            # Cache the content
            self._cache_content(url, content, response.headers, response.status_code)
            
            # Update state
            self.current_url = url
            self.page_content = content
            self.last_request_time = time.time()
            self.successful_requests += 1
            
            return {
                "status": "success",
                "url": url,
                "content": content,
                "cached": False
            }
            
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"Error navigating to {url}: {str(e)}")
            return {
                "status": "error",
                "url": url,
                "error": str(e)
            }

    def fill_form(self, url: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fill and submit a form on a webpage"""
        try:
            # First navigate to the URL
            nav_result = self.navigate_to_url(url)
            if nav_result["status"] != "success":
                return nav_result
            
            # Parse the page to find forms
            soup = BeautifulSoup(self.page_content, 'html.parser')
            forms = soup.find_all('form')
            
            if not forms:
                return {
                    "status": "error",
                    "error": "No forms found on the page"
                }
            
            # For now, just log the form data
            # In a full implementation, this would actually fill and submit the form
            logger.info(f"Form data to fill: {form_data}")
            
            # Record in database
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO form_history (url, form_data, timestamp, success, error)
            VALUES (?, ?, ?, ?, ?)
            ''', (url, json.dumps(form_data), time.time(), True, None))
            self.conn.commit()
            
            return {
                "status": "success",
                "url": url,
                "message": "Form data processed (simulated)",
                "forms_found": len(forms)
            }
            
        except Exception as e:
            logger.error(f"Error filling form on {url}: {str(e)}")
            return {
                "status": "error",
                "url": url,
                "error": str(e)
            }

    def _get_cached_content(self, url: str) -> Optional[str]:
        """Get cached content for a URL"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT content FROM cache WHERE url = ?
            ''', (url,))
            result = cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting cached content: {e}")
            return None

    def _cache_content(self, url: str, content: str, headers: Dict, status_code: int):
        """Cache content for a URL"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO cache (url, content, timestamp, headers, status_code)
            VALUES (?, ?, ?, ?, ?)
            ''', (url, content, time.time(), json.dumps(dict(headers)), status_code))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error caching content: {e}")

    def _send_to_llm(self, prompt: str, system_prompt: Optional[str] = None, model: str = "deepseek") -> str:
        """Send a prompt to the LLM (simulated)"""
        # In a full implementation, this would connect to an actual LLM
        # For now, return a simulated response
        return f"Simulated LLM response for: {prompt[:100]}..."

    def _get_conversation_context(self) -> str:
        """Get the current conversation context"""
        if not self.conversation_context:
            return "No conversation context available."
        
        context_parts = []
        for i, entry in enumerate(self.conversation_context[-5:]):  # Last 5 entries
            context_parts.append(f"{entry['role']}: {entry['content']}")
        
        return "\n".join(context_parts)

    def _enhance_search_query(self, query: str) -> str:
        """Enhance a search query with context"""
        context = self._get_conversation_context()
        enhanced_query = f"{query} (context: {context[:200]}...)" if context else query
        return enhanced_query

    def _rank_search_results(self, results: List[Dict[str, Any]], original_query: str) -> List[Dict[str, Any]]:
        """Rank search results by relevance"""
        # Simple ranking based on query term frequency
        for result in results:
            score = 0
            query_terms = original_query.lower().split()
            content = result.get('content', '').lower()
            
            for term in query_terms:
                score += content.count(term)
            
            result['relevance_score'] = score
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return results

    def search_web(self, query: str) -> Dict[str, Any]:
        """Search the web for information"""
        try:
            self.total_requests += 1
            
            # Enhance the query
            enhanced_query = self._enhance_search_query(query)
            
            # Perform search (simulated)
            results = self._perform_search(enhanced_query)
            
            # Rank results
            ranked_results = self._rank_search_results(results, query)
            
            # Record in database
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO scraping_history (url, data_type, output_format, timestamp, success, error)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (f"search:{query}", "search", "json", time.time(), True, None))
            self.conn.commit()
            
            self.successful_requests += 1
            
            return {
                "status": "success",
                "query": query,
                "enhanced_query": enhanced_query,
                "results": ranked_results[:10],  # Top 10 results
                "total_results": len(ranked_results)
            }
            
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"Error searching web: {str(e)}")
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }

    def _perform_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform actual web search (simulated)"""
        # In a full implementation, this would use a real search API
        # For now, return simulated results
        return [
            {
                "title": f"Result for: {query}",
                "url": f"https://example.com/search?q={query}",
                "content": f"This is a simulated search result for the query: {query}",
                "snippet": f"Simulated snippet containing {query}..."
            }
        ]

    def analyze_conversation(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze conversation history for insights"""
        try:
            if not conversation_history:
                return {
                    "status": "error",
                    "error": "No conversation history provided"
                }
            
            # Analyze conversation patterns
            user_messages = [msg["content"] for msg in conversation_history if msg["role"] == "user"]
            assistant_messages = [msg["content"] for msg in conversation_history if msg["role"] == "assistant"]
            
            analysis = {
                "total_messages": len(conversation_history),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "average_user_message_length": sum(len(msg) for msg in user_messages) / len(user_messages) if user_messages else 0,
                "average_assistant_message_length": sum(len(msg) for msg in assistant_messages) / len(assistant_messages) if assistant_messages else 0,
                "topics": self._extract_topics(conversation_history),
                "sentiment": "neutral"  # Simplified sentiment analysis
            }
            
            return {
                "status": "success",
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _extract_topics(self, conversation_history: List[Dict[str, str]]) -> List[str]:
        """Extract topics from conversation history"""
        # Simple topic extraction based on common words
        all_text = " ".join([msg["content"] for msg in conversation_history])
        words = re.findall(r'\b\w+\b', all_text.lower())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        topics = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Count frequency and return top topics
        from collections import Counter
        topic_counts = Counter(topics)
        return [topic for topic, count in topic_counts.most_common(5)]

    def proactive_info_gathering(self, user_message: str) -> Dict[str, Any]:
        """Proactively gather information based on user message"""
        try:
            # Analyze the message to identify potential information needs
            queries = self._generate_search_queries(user_message)
            
            # Execute searches
            results = []
            for query in queries:
                search_result = self.search_web(query)
                if search_result["status"] == "success":
                    results.extend(search_result["results"])
            
            # Summarize findings
            if results:
                summary_prompt = f"""
                Summarize the key findings from these search results:
                
                {json.dumps(results, indent=2)}
                
                Summary:
                """
                
                summary = self._send_to_llm(summary_prompt)
                
                return {
                    "status": "success",
                    "queries": queries,
                    "results": results,
                    "summary": summary
                }
            else:
                return {
                    "status": "success",
                    "message": "No relevant information found",
                    "queries": queries
                }
            
        except Exception as e:
            logger.error(f"Error in proactive info gathering: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _generate_search_queries(self, message: str) -> List[str]:
        """Generate search queries from a user message"""
        # Simple query generation - in a full implementation, this would use NLP
        words = message.lower().split()
        queries = []
        
        # Extract potential search terms
        for i in range(len(words)):
            for j in range(i + 1, min(i + 4, len(words) + 1)):
                query = " ".join(words[i:j])
                if len(query) > 3:
                    queries.append(query)
        
        return queries[:3]  # Return top 3 queries

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent"""
        return {
            "status": "success",
            "uptime": time.time() - self.start_time,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "health_check_requests": self.health_check_requests,
            "cache_size": self._get_cache_size(),
            "scraping_history_size": self._get_scraping_history_size(),
            "form_history_size": self._get_form_history_size(),
            "current_url": self.current_url,
            "proactive_mode": self.proactive_mode
        }
    
    def _get_cache_size(self) -> int:
        """Get the number of cached pages"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cache")
        return cursor.fetchone()[0]
    
    def _get_scraping_history_size(self) -> int:
        """Get the number of scraping history entries"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM scraping_history")
        return cursor.fetchone()[0]
    
    def _get_form_history_size(self) -> int:
        """Get the number of form history entries"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM form_history")
        return cursor.fetchone()[0]
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming request"""
        try:
            action = request.get("action")
            
            if action == "health_check":
                return self._health_check()
            elif action == "navigate":
                return self.navigate_to_url(request["url"])
            elif action == "search":
                return self.search_web(request["query"])
            elif action == "fill_form":
                return self.fill_form(request["url"], request["form_data"])
            elif action == "analyze_conversation":
                return self.analyze_conversation(request["conversation_history"])
            elif action == "proactive_gather":
                return self.proactive_info_gathering(request["message"])
            elif action == "get_status":
                return self.get_status()
            else:
                return {
                    "status": "error",
                    "error": f"Unknown action: {action}"
                }
            
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run(self):
        """Main run loop"""
        logger.info(f"Starting Unified Web Agent on port {self.main_port}")
        
        # Start health check thread
        health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        health_thread.start()
        
        while self.running:
            try:
                # Wait for request with timeout
                if self.socket.poll(1000) == 0:
                    continue
                
                # Receive and process message
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                response = self.handle_request(message)
                self.socket.send_json(response)
                
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue
                logger.error(f"ZMQ error in main loop: {e}")
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                traceback.print_exc()
    
    def _health_check_loop(self):
        """Health check loop"""
        logger.info("Starting health check loop")
        while self.running:
            try:
                # Wait for health check request with timeout
                if self.health_socket.poll(1000) == 0:
                    continue
                
                # Receive and process message
                message = self.health_socket.recv_json()
                
                if message.get("action") == "health_check":
                    self.health_check_requests += 1
                    response = self._health_check()
                else:
                    response = {
                        "status": "error",
                        "error": "Invalid health check request"
                    }
                
                # Send response
                self.health_socket.send_json(response)
                
            except zmq.error.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    continue
                logger.error(f"ZMQ error in health check loop: {e}")
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")
                traceback.print_exc()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Unified Web Agent")
        self.running = False
        
        # Close database connection
        if hasattr(self, 'conn'):
            self.conn.close()
        
        # Close ZMQ sockets
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        
        # Close ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("Unified Web Agent cleaned up")

    def stop(self):
        """Stop the agent gracefully."""
        self.running = False

def main():
    """Main entry point"""
    try:
        agent = UnifiedWebAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        traceback.print_exc()
    finally:
        if 'agent' in locals():
            agent.cleanup()

if __name__ == "__main__":
    main() 