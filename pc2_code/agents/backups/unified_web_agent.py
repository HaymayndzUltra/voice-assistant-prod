#!/usr/bin/env python3
"""
Unified Web Agent
----------------
An enhanced agent capable of proactive web browsing, information gathering,
and context-aware navigation, designed to run on PC2 and integrate with
the distributed AI system.

Features:
- Advanced web browsing with Selenium (headless mode)
- Proactive information gathering
- Context-aware navigation
- Secure communication with SystemDigitalTwin
- Integration with the memory system
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
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import hashlib
import base64
from bs4 import BeautifulSoup
import urllib.parse
import tempfile
import socket
import yaml
import pickle

# Import Selenium for browser automation
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException,
    StaleElementReferenceException
)

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import service discovery and network utilities
from main_pc_code.utils.service_discovery_client import register_service, discover_service, get_service_address
from main_pc_code.utils.network_utils import load_network_config, get_current_machine
from main_pc_code.utils.env_loader import get_env
from main_pc_code.src.network.secure_zmq import configure_secure_client, configure_secure_server

# Configure logging
log_file_path = os.path.join('logs', 'unified_web_agent.log')
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UnifiedWebAgent")

# Default ZMQ port configuration
UNIFIED_WEB_PORT = 7126  # Main port
HEALTH_CHECK_PORT = 7127  # Health check port
INTERRUPT_PORT = int(os.environ.get('INTERRUPT_PORT', 5576))  # Interrupt handler port

# Browser automation settings
MIN_DELAY_BETWEEN_REQUESTS = 2  # seconds
MAX_RETRIES = 3
TIMEOUT = 30  # seconds

# Get bind address from environment variables with default to 0.0.0.0 for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

class UnifiedWebAgent(BaseAgent):

    
    def __init__(self, port: int = None):

    
        super().__init__(name="UnifiedWebAgent", port=port)

    
        self.start_time = time.time()

    """Enhanced web agent with proactive information gathering and context-aware browsing"""
    
    def __init__(self):
        """Initialize the unified web agent with improved capabilities"""
        # Load configuration from startup_config.yaml
        self._load_config()
        
        # ZMQ setup
        self.context = zmq.Context()
        
        # Main socket for requests
        self.socket = self.context.socket(zmq.REP)
        
        # Secure ZMQ configuration
        self.secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        if self.secure_zmq:
            self.socket = configure_secure_server(self.socket)
            
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{BIND_ADDRESS}:{self.port}"
        try:
            self.socket.bind(bind_address)
            logger.info(f"Unified Web Agent bound to {bind_address}")
        except Exception as e:
            logger.error(f"Failed to bind to {bind_address}: {e}")
            raise
        
        # Health check socket
        self.health_socket = self.context.socket(zmq.REP)
        if self.secure_zmq:
            self.health_socket = configure_secure_server(self.health_socket)
            
        health_bind_address = f"tcp://{BIND_ADDRESS}:{self.health_port}"
        try:
            self.health_socket.bind(health_bind_address)
            logger.info(f"Health check bound to {health_bind_address}")
        except Exception as e:
            logger.error(f"Failed to bind health check to {health_bind_address}: {e}")
            raise
        
        # Memory agent connection socket (will be initialized later)
        self.memory_socket = None
        
        # Setup interrupt subscription
        self.interrupt_socket = self.context.socket(zmq.SUB)
        if self.secure_zmq:
            self.interrupt_socket = configure_secure_client(self.interrupt_socket)
            
        # Try to get the interrupt handler address from service discovery
        interrupt_address = get_service_address("StreamingInterruptHandler")
        if not interrupt_address:
            # Fall back to configured port
            interrupt_address = f"tcp://localhost:{INTERRUPT_PORT}"
            
        try:
            self.interrupt_socket.connect(interrupt_address)
            self.interrupt_socket.setsockopt(zmq.SUBSCRIBE, b"")
            logger.info(f"Connected to interrupt handler at {interrupt_address}")
        except Exception as e:
            logger.warning(f"Could not connect to interrupt handler: {e}")
        
        # Setup directories
        self.cache_dir = Path('cache') / "web_agent"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.output_dir = Path('output')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = self.cache_dir / "web_agent_cache.sqlite"
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        
        # Initialize web driver
        self.driver = None
        self._init_web_driver()
        
        # HTTP session for non-browser requests
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
        self.interrupted = False
        
        # Proactive settings
        self.proactive_mode = True
        self.proactive_topics = ["ai news", "technology updates", "machine learning breakthroughs"]
        self.confidence_threshold = 0.7
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_requests = 0
        self.start_time = time.time()
        
        # Register with SystemDigitalTwin
        self._register_with_service_discovery()
        
        # Initialize connection to memory agent
        self._init_memory_connection()
        
        # Start background threads
        self._start_proactive_thread()
        self._start_interrupt_thread()
        
        logger.info(f"Unified Web Agent initialized successfully")
    
    def _load_config(self):
        """Load configuration from startup_config.yaml"""
        try:
            config_path = project_root / "pc2_code" / "config" / "startup_config.yaml"
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                
            # Find UnifiedWebAgent configuration
            agent_config = None
            for service in config.get('pc2_services', []):
                if service.get('name') == 'UnifiedWebAgent':
                    agent_config = service
                    break
            
            if agent_config:
                self.host = agent_config.get('host', BIND_ADDRESS)
                self.port = agent_config.get('port', UNIFIED_WEB_PORT)
                self.health_port = agent_config.get('health_check_port', HEALTH_CHECK_PORT)
                logger.info(f"Loaded configuration for UnifiedWebAgent: {self.host}:{self.port}")
            else:
                logger.warning("UnifiedWebAgent configuration not found in startup_config.yaml")
                self.host = BIND_ADDRESS
                self.port = UNIFIED_WEB_PORT
                self.health_port = HEALTH_CHECK_PORT
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.host = BIND_ADDRESS
            self.port = UNIFIED_WEB_PORT
            self.health_port = HEALTH_CHECK_PORT

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
            query TEXT,
            timestamp REAL,
            success BOOLEAN,
            error TEXT,
            content_hash TEXT
        )
        ''')
        
        # Proactive information table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS proactive_info (
            id INTEGER PRIMARY KEY,
            topic TEXT,
            url TEXT,
            title TEXT,
            summary TEXT,
            timestamp REAL,
            sent_to_memory BOOLEAN
        )
        ''')
        
        # Context table for storing browsing context
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS browsing_context (
            id INTEGER PRIMARY KEY,
            context_key TEXT,
            context_value TEXT,
            timestamp REAL
        )
        ''')
        
        self.conn.commit()
        logger.info("Database tables created")

    def _start_interrupt_thread(self):
        """Start a thread to monitor for interrupt signals"""
        interrupt_thread = threading.Thread(target=self._interrupt_monitor_loop, daemon=True)
        interrupt_thread.start()
        logger.info("Started interrupt monitoring thread")
    
    def _interrupt_monitor_loop(self):
        """Background loop to monitor for interrupt signals"""
        logger.info("Interrupt monitor loop started")
        
        poller = zmq.Poller()
        poller.register(self.interrupt_socket, zmq.POLLIN)
        
        while self.running:
            try:
                # Check for interrupt signals with timeout
                if poller.poll(100):  # 100ms timeout
                    msg = self.interrupt_socket.recv()
                    data = pickle.loads(msg)
                    
                    if data.get('type') == 'interrupt':
                        logger.info("Received interrupt signal")
                        self.interrupted = True
                        
                        # Cancel any ongoing web operations
                        self._handle_interrupt()
                
                # Reset interrupt flag after a short delay
                if self.interrupted:
                    time.sleep(0.5)
                    self.interrupted = False
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in interrupt monitor loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _handle_interrupt(self):
        """Handle interrupt signal by stopping current operations"""
        try:
            logger.info("Handling interrupt signal")
            
            # Stop any ongoing browser automation
            if self.driver:
                try:
                    # Stop loading page
                    self.driver.execute_script("window.stop();")
                    logger.info("Stopped current page loading")
                except Exception as e:
                    logger.error(f"Error stopping browser: {e}")
            
            # Clear any ongoing operations or queues
            # Add any additional cleanup needed for interruption
            
            logger.info("Interrupt handling completed")
        except Exception as e:
            logger.error(f"Error handling interrupt: {e}")

    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        self.health_check_requests += 1
        
        # Check database connection
        db_ok = False
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            db_ok = cursor.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Check web driver
        driver_ok = self.driver is not None
        
        # Check memory connection
        memory_ok = False
        if hasattr(self, 'memory_socket') and self.memory_socket is not None:
            try:
                # Quick ping
                self.memory_socket.send_json({"command": "ping"})
                poller = zmq.Poller()
                poller.register(self.memory_socket, zmq.POLLIN)
                if poller.poll(1000):
                    memory_ok = True
            except Exception:
                memory_ok = False
        
        return {
            "status": "success",
            "agent": "UnifiedWebAgent",
            "timestamp": time.time(),
            "uptime": time.time() - self.start_time,
            "health": {
                "overall": all([db_ok, driver_ok]),
                "database": db_ok,
                "web_driver": driver_ok,
                "memory_connection": memory_ok
            },
            "metrics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "health_check_requests": self.health_check_requests
            }
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
            
            # Decide which method to use: Selenium or requests
            if self.driver:
                # Use Selenium for full browser automation
                try:
                    logger.info(f"Navigating to {url} with Selenium")
                    self.driver.get(url)
                    
                    # Wait for page to load
                    WebDriverWait(self.driver, TIMEOUT).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # Get page content
                    content = self.driver.page_source
                    text_content = self.driver.find_element(By.TAG_NAME, "body").text
                    
                    # Extract title
                    title = self.driver.title
                    
                    # Cache the content
                    self._cache_content(url, text_content, {"title": title}, 200)
                    
                    # Update state
                    self.current_url = url
                    self.page_content = text_content
                    self.last_request_time = time.time()
                    self.successful_requests += 1
                    
                    return {
                        "status": "success",
                        "url": url,
                        "content": text_content,
                        "title": title,
                        "cached": False,
                        "method": "selenium"
                    }
                except Exception as selenium_error:
                    logger.warning(f"Selenium navigation failed: {selenium_error}, falling back to requests")
                    # Fall back to requests
            
            # Use requests as fallback or primary method if no driver
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            
            # Parse content
            soup = BeautifulSoup(response.content, 'html.parser')
            content = soup.get_text()
            title = soup.title.string if soup.title else "No title"
            
            # Cache the content
            self._cache_content(url, content, dict(response.headers), response.status_code)
            
            # Update state
            self.current_url = url
            self.page_content = content
            self.last_request_time = time.time()
            self.successful_requests += 1
            
            return {
                "status": "success",
                "url": url,
                "content": content,
                "title": title,
                "cached": False,
                "method": "requests"
            }
            
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"Error navigating to {url}: {e}")
            return {
                "status": "error",
                "url": url,
                "message": str(e)
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
        """Get cached content for a URL if available and not expired"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT content, timestamp FROM cache WHERE url = ?",
                (url,)
            )
            result = cursor.fetchone()
            
            if result:
                content, timestamp = result
                # Check if cache is expired (older than 1 hour)
                if time.time() - timestamp < 3600:
                    logger.info(f"Using cached content for {url}")
                    return content
                else:
                    logger.info(f"Cache expired for {url}")
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def _cache_content(self, url: str, content: str, headers: Dict, status_code: int):
        """Cache content for a URL"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT OR REPLACE INTO cache (url, content, timestamp, headers, status_code)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    url,
                    content,
                    time.time(),
                    json.dumps(dict(headers)),
                    status_code
                )
            )
            self.conn.commit()
            logger.debug(f"Cached content for {url}")
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
        """Perform a search using a search engine"""
        # Alias for the search method to maintain compatibility with both naming conventions
        return self.search(query)

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
            "proactive_mode": self.proactive_mode,
            "proactive_topics": self.proactive_topics,
            "driver_available": self.driver is not None,
            "memory_connected": hasattr(self, 'memory_socket') and self.memory_socket is not None,
            "timestamp": time.time()
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
        """Handle incoming request from other agents"""
        try:
            command = request.get("command", "").lower()
            
            if command == "health_check":
                return self._health_check()
            
            elif command == "navigate":
                url = request.get("url")
                if not url:
                    return {"status": "error", "message": "URL is required"}
                return self.navigate_to_url(url)
            
            elif command == "extract_links":
                url = request.get("url")
                return self.extract_links(url)
            
            elif command == "search":
                query = request.get("query")
                if not query:
                    return {"status": "error", "message": "Query is required"}
                return self.search(query)
            
            elif command == "browse_with_context":
                context = request.get("context")
                if not context:
                    return {"status": "error", "message": "Context is required"}
                return self.browse_with_context(context)
            
            elif command == "send_to_memory":
                data = request.get("data")
                if not data:
                    return {"status": "error", "message": "Data is required"}
                return self.send_to_memory(data)
            
            elif command == "status":
                return self.get_status()
            
            elif command == "ping":
                return {
                    "status": "success",
                    "message": "pong",
                    "agent": "UnifiedWebAgent",
                    "timestamp": time.time()
                }
            
            else:
                logger.warning(f"Unknown command: {command}")
                return {
                    "status": "error",
                    "message": f"Unknown command: {command}"
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def run(self):
        """Main run loop"""
        logger.info("Starting UnifiedWebAgent main loop")
        
        # Start health check thread
        health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        health_thread.start()
        
        try:
            while self.running:
                try:
                    # Poll for requests with timeout
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    # Poll with timeout to allow checking for interrupts
                    if poller.poll(100):  # 100ms timeout
                        # Receive request
                        request_data = self.socket.recv_json()
                        logger.info(f"Received request: {request_data.get('action', 'unknown')}")
                        
                        # Handle request
                        if not self.interrupted:
                            response = self.handle_request(request_data)
                        else:
                            response = {"status": "error", "message": "Operation interrupted by user"}
                            self.interrupted = False
                            
                        # Send response
                        self.socket.send_json(response)
                    
                except zmq.ZMQError as e:
                    logger.error(f"ZMQ error in main loop: {e}")
                    time.sleep(0.5)  # Short sleep before retry
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Try to send error response if possible
                    try:
                        self.socket.send_json({"status": "error", "message": str(e)})
                    except:
                        pass
                        
                    time.sleep(1)  # Longer sleep on error
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        finally:
            self.stop()

    def _health_check_loop(self):
        """Background thread for handling health checks"""
        logger.info("Starting health check loop")
        
        while self.running:
            try:
                # Wait for a health check request with a timeout
                poller = zmq.Poller()
                poller.register(self.health_socket, zmq.POLLIN)
                
                # Poll with a 1 second timeout
                if poller.poll(1000):
                    # Receive the request
                    request_raw = self.health_socket.recv()
                    
                    # Perform health check
                    health_data = self._health_check()
                    
                    # Send the response
                    self.health_socket.send_json(health_data)
                
            except zmq.error.Again:
                # Timeout, continue the loop
                continue
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                try:
                    self.health_socket.send_json({"status": "error", "message": str(e)})
                except:
                    logger.error("Failed to send health check error response")
        
        logger.info("Health check loop exited")
    
    def cleanup(self):
        """Clean up resources before exit"""
        logger.info("Cleaning up resources")
        
        # Set running flag to false to stop all threads
        self.running = False
        
        # Close database connection
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
        
        # Close web driver
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                logger.info("Web driver closed")
        except Exception as e:
            logger.error(f"Error closing web driver: {e}")
        
        # Close all ZMQ sockets
        try:
            for socket_attr in ['socket', 'health_socket', 'memory_socket', 'interrupt_socket']:
                if hasattr(self, socket_attr) and getattr(self, socket_attr):
                    getattr(self, socket_attr).close()
                    logger.info(f"Closed {socket_attr}")
        except Exception as e:
            logger.error(f"Error closing ZMQ sockets: {e}")
        
        # Terminate ZMQ context
        try:
            if hasattr(self, 'context') and self.context:
                self.context.term()
                logger.info("ZMQ context terminated")
        except Exception as e:
            logger.error(f"Error terminating ZMQ context: {e}")
            
        logger.info("Cleanup completed")

    def stop(self):
        """Stop the agent"""
        logger.info("Stopping UnifiedWebAgent")
        self.running = False
        self.cleanup()

    def _init_web_driver(self):
        """Initialize the Selenium WebDriver in headless mode with fallbacks"""
        try:
            # Set up Chrome options for headless operation
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--mute-audio")
            
            # First try with webdriver-manager for automatic driver management
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service as ChromeService
                
                # Initialize with automatic driver management
                logger.info("Initializing Chrome WebDriver with webdriver-manager")
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.driver.set_page_load_timeout(TIMEOUT)
                logger.info("WebDriver initialized successfully with webdriver-manager")
                return
            except ImportError:
                logger.warning("webdriver-manager not available, trying fallback methods")
            except Exception as e:
                logger.warning(f"Failed to initialize WebDriver with webdriver-manager: {e}")
            
            # Second approach: Try the standard approach
            try:
                logger.info("Attempting to initialize Chrome WebDriver directly")
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(TIMEOUT)
                logger.info("WebDriver initialized successfully directly")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize Chrome WebDriver directly: {e}")
            
            # Third approach: Try Firefox if Chrome fails
            try:
                logger.info("Attempting to initialize Firefox WebDriver as fallback")
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                
                firefox_options = FirefoxOptions()
                firefox_options.add_argument("--headless")
                
                self.driver = webdriver.Firefox(options=firefox_options)
                self.driver.set_page_load_timeout(TIMEOUT)
                logger.info("Firefox WebDriver initialized successfully as fallback")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize Firefox WebDriver: {e}")
            
            # If all browser attempts fail, log error and continue without browser automation
            logger.error("All WebDriver initialization attempts failed")
            self.driver = None
            logger.warning("Continuing without WebDriver. Only HTTP requests will be available.")
            
        except Exception as e:
            logger.error(f"Unexpected error initializing WebDriver: {e}")
            self.driver = None
            logger.warning("Continuing without WebDriver. Only HTTP requests will be available.")
    
    def _register_with_service_discovery(self):
        """Register this agent with the service discovery system"""
        try:
            # Get IP address for registration
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))  # Doesn't have to be reachable
                my_ip = s.getsockname()[0]
                s.close()
            except Exception as e:
                logger.warning(f"Failed to determine IP address: {e}, using configured host")
                my_ip = self.host if self.host != '0.0.0.0' else 'localhost'
            
            # Prepare extra service information
            additional_info = {
                "api_version": "1.0",
                "supports_secure_zmq": self.secure_zmq,
                "capabilities": ["web_browsing", "information_gathering", "context_aware_navigation"],
                "last_started": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Register with service discovery
            register_result = register_service(
                name="UnifiedWebAgent",
                location="PC2",
                ip=my_ip,
                port=self.port,
                additional_info=additional_info
            )
            
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error registering with service discovery: {e}")
            logger.warning("Agent will continue to function locally, but won't be discoverable by other agents")

    def _init_memory_connection(self):
        """Initialize connection to the memory system using service discovery"""
        try:
            # Create memory socket
            self.memory_socket = self.context.socket(zmq.REQ)
            if self.secure_zmq:
                self.memory_socket = configure_secure_client(self.memory_socket)
                
            self.memory_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            self.memory_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout
            
            # Try to get memory agent address from service discovery
            memory_address = get_service_address("UnifiedMemoryReasoningAgent")
            if not memory_address:
                # Fall back to configured port
                memory_address = f"tcp://localhost:5596"
                
            self.memory_socket.connect(memory_address)
            logger.info(f"Connected to memory agent at {memory_address}")
            
            # Test connection
            self._send_ping_to_memory()
            
        except Exception as e:
            logger.error(f"Error initializing memory connection: {e}")
            logger.warning("Agent will continue to function without memory integration")
            self.memory_socket = None
    
    def _send_ping_to_memory(self):
        """Send a ping to the memory agent to test the connection"""
        if not hasattr(self, 'memory_socket') or self.memory_socket is None:
            logger.warning("No memory socket available for ping test")
            return False
        
        try:
            # Create a simple ping message
            message = {
                "command": "ping",
                "source": "UnifiedWebAgent",
                "timestamp": time.time()
            }
            
            # Send the message
            self.memory_socket.send_json(message)
            
            # Wait for a response with timeout
            poller = zmq.Poller()
            poller.register(self.memory_socket, zmq.POLLIN)
            
            # Poll for 5 seconds
            if poller.poll(5000):
                response = self.memory_socket.recv_json()
                if response.get("status") == "SUCCESS":
                    logger.info("Memory agent ping successful")
                    return True
                else:
                    logger.warning(f"Memory agent ping received unexpected response: {response}")
                    return False
            else:
                logger.warning("Memory agent ping timed out")
                return False
                
        except Exception as e:
            logger.error(f"Error pinging memory agent: {e}")
            return False

    def extract_links(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Extract all links from the current page or a specified URL"""
        try:
            # If URL is provided, navigate to it first
            if url and url != self.current_url:
                result = self.navigate_to_url(url)
                if result["status"] != "success":
                    return {
                        "status": "error",
                        "message": f"Failed to navigate to {url}: {result.get('message', 'Unknown error')}"
                    }
            
            links = []
            
            # Use Selenium if available
            if self.driver and (not url or url == self.current_url):
                try:
                    # Wait for links to be available
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "a"))
                    )
                    
                    # Get all link elements
                    link_elements = self.driver.find_elements(By.TAG_NAME, "a")
                    
                    # Extract href and text
                    for link in link_elements:
                        try:
                            href = link.get_attribute("href")
                            text = link.text.strip()
                            if href and text:
                                links.append({
                                    "url": href,
                                    "text": text
                                })
                        except StaleElementReferenceException:
                            continue
                        except Exception as link_error:
                            logger.debug(f"Error extracting link: {link_error}")
                            continue
                except Exception as selenium_error:
                    logger.warning(f"Selenium link extraction failed: {selenium_error}, falling back to BeautifulSoup")
                    # Fall back to BeautifulSoup
            
            # Use BeautifulSoup as fallback or primary method
            if not links and self.page_content:
                soup = BeautifulSoup(self.page_content, 'html.parser')
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    text = a_tag.get_text().strip()
                    
                    # Convert relative URLs to absolute
                    if href.startswith('/') and self.current_url:
                        base_url = urllib.parse.urlparse(self.current_url)
                        href = f"{base_url.scheme}://{base_url.netloc}{href}"
                    
                    if href and text:
                        links.append({
                            "url": href,
                            "text": text
                        })
            
            return {
                "status": "success",
                "url": self.current_url,
                "links": links,
                "count": len(links)
            }
            
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def search(self, query: str) -> Dict[str, Any]:
        """Perform a search using a search engine"""
        try:
            # Encode the query for URL
            encoded_query = urllib.parse.quote_plus(query)
            
            # Construct search URL (using Google)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            # Navigate to the search URL
            result = self.navigate_to_url(search_url)
            if result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Failed to navigate to search engine: {result.get('message', 'Unknown error')}"
                }
            
            # Extract search results
            search_results = self._extract_search_results()
            
            # Record the search in database
            self._record_search(query, search_url, len(search_results) > 0)
            
            return {
                "status": "success",
                "query": query,
                "results": search_results,
                "count": len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Error performing search for '{query}': {e}")
            return {
                "status": "error",
                "query": query,
                "message": str(e)
            }
    
    def _extract_search_results(self) -> List[Dict[str, Any]]:
        """Extract search results from the current page (assumed to be a search engine results page)"""
        results = []
        
        try:
            # Use Selenium if available
            if self.driver:
                try:
                    # Wait for results to load
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
                    )
                    
                    # Extract result elements (Google format)
                    result_elements = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
                    
                    for element in result_elements[:10]:  # Limit to top 10 results
                        try:
                            # Extract title, link and snippet
                            title_element = element.find_element(By.CSS_SELECTOR, "h3")
                            title = title_element.text if title_element else "No title"
                            
                            link_element = element.find_element(By.CSS_SELECTOR, "a")
                            link = link_element.get_attribute("href") if link_element else None
                            
                            snippet_element = element.find_element(By.CSS_SELECTOR, "div.VwiC3b")
                            snippet = snippet_element.text if snippet_element else "No snippet"
                            
                            if link:
                                results.append({
                                    "title": title,
                                    "url": link,
                                    "snippet": snippet
                                })
                        except Exception as result_error:
                            logger.debug(f"Error extracting search result: {result_error}")
                            continue
                            
                except Exception as selenium_error:
                    logger.warning(f"Selenium search result extraction failed: {selenium_error}, falling back to BeautifulSoup")
            
            # Fallback to BeautifulSoup
            if not results and self.page_content:
                soup = BeautifulSoup(self.page_content, 'html.parser')
                
                # Try to extract results (Google format)
                for result in soup.select('div.g')[:10]:  # Limit to top 10
                    title_element = result.select_one('h3')
                    title = title_element.get_text() if title_element else "No title"
                    
                    link_element = result.select_one('a')
                    link = link_element.get('href') if link_element else None
                    
                    snippet_element = result.select_one('div.VwiC3b')
                    snippet = snippet_element.get_text() if snippet_element else "No snippet"
                    
                    if link:
                        results.append({
                            "title": title,
                            "url": link,
                            "snippet": snippet
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting search results: {e}")
            return []
    
    def _record_search(self, query: str, url: str, success: bool) -> None:
        """Record search query and results in the database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO scraping_history (query, url, timestamp, success, error, content_hash)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    query,
                    url,
                    time.time(),
                    success,
                    "" if success else "Failed to get results",
                    hashlib.md5(query.encode()).hexdigest()
                )
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error recording search: {e}")
    
    def send_to_memory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send extracted web information to the memory agent"""
        if not hasattr(self, 'memory_socket') or self.memory_socket is None:
            logger.warning("No memory socket available")
            return {
                "status": "error",
                "message": "Memory agent connection not available"
            }
        
        try:
            # Prepare message
            message = {
                "command": "store_web_data",
                "source": "UnifiedWebAgent",
                "timestamp": time.time(),
                "data": data
            }
            
            # Send the message
            self.memory_socket.send_json(message)
            
            # Wait for a response with timeout
            poller = zmq.Poller()
            poller.register(self.memory_socket, zmq.POLLIN)
            
            # Poll for 5 seconds
            if poller.poll(5000):
                response = self.memory_socket.recv_json()
                logger.info(f"Memory agent response: {response}")
                return response
            else:
                logger.warning("Memory agent request timed out")
                return {
                    "status": "error",
                    "message": "Memory agent request timed out"
                }
                
        except Exception as e:
            logger.error(f"Error sending data to memory agent: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _start_proactive_thread(self):
        """Start the background thread for proactive information gathering"""
        if self.proactive_mode:
            self.proactive_thread = threading.Thread(
                target=self._proactive_info_gathering_loop,
                daemon=True
            )
            self.proactive_thread.start()
            logger.info("Started proactive information gathering thread")
    
    def _proactive_info_gathering_loop(self):
        """Background loop for proactive information gathering"""
        # Wait for initial startup to complete
        time.sleep(10)
        
        while self.running:
            try:
                logger.info("Running proactive information gathering cycle")
                
                # Process each predefined topic
                for topic in self.proactive_topics:
                    try:
                        # Skip if we've recently searched this topic
                        if self._recently_searched(topic):
                            logger.info(f"Skipping recent topic: {topic}")
                            continue
                        
                        logger.info(f"Proactively searching for: {topic}")
                        
                        # Perform search
                        search_result = self.search(topic)
                        
                        if search_result["status"] == "success" and search_result.get("results"):
                            # Get the top result
                            top_result = search_result["results"][0]
                            
                            # Navigate to the page
                            page_result = self.navigate_to_url(top_result["url"])
                            
                            if page_result["status"] == "success":
                                # Extract key information
                                title = top_result.get("title", "No title")
                                url = top_result.get("url", "")
                                content = page_result.get("content", "")
                                
                                # Create a summary (first 500 chars)
                                summary = content[:500] + "..." if len(content) > 500 else content
                                
                                # Store in database
                                self._store_proactive_info(topic, url, title, summary)
                                
                                # Send to memory
                                memory_data = {
                                    "type": "proactive_web_info",
                                    "topic": topic,
                                    "title": title,
                                    "url": url,
                                    "summary": summary,
                                    "timestamp": time.time()
                                }
                                
                                memory_result = self.send_to_memory(memory_data)
                                
                                # Update database with memory status
                                self._update_proactive_info_memory_status(
                                    topic, url, memory_result.get("status") == "SUCCESS"
                                )
                                
                                logger.info(f"Proactively gathered information about: {topic}")
                    except Exception as topic_error:
                        logger.error(f"Error gathering information for topic '{topic}': {topic_error}")
                
                # Wait before next cycle (30 minutes)
                logger.info("Proactive gathering cycle complete, sleeping for 30 minutes")
                time.sleep(1800)
                
            except Exception as e:
                logger.error(f"Error in proactive information gathering loop: {e}")
                # Wait before retry (1 minute)
                time.sleep(60)
    
    def _recently_searched(self, topic: str) -> bool:
        """Check if a topic was recently searched (within last 24 hours)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT timestamp FROM proactive_info WHERE topic = ? ORDER BY timestamp DESC LIMIT 1",
                (topic,)
            )
            result = cursor.fetchone()
            
            if result:
                # Check if search is from last 24 hours
                return time.time() - result[0] < 86400  # 24 hours in seconds
            
            return False
        except Exception as e:
            logger.error(f"Error checking recent searches: {e}")
            return False
    
    def _store_proactive_info(self, topic: str, url: str, title: str, summary: str):
        """Store proactively gathered information in the database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO proactive_info (topic, url, title, summary, timestamp, sent_to_memory)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    topic,
                    url,
                    title,
                    summary,
                    time.time(),
                    False
                )
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error storing proactive info: {e}")
    
    def _update_proactive_info_memory_status(self, topic: str, url: str, sent_to_memory: bool):
        """Update the memory status of proactively gathered information"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                UPDATE proactive_info
                SET sent_to_memory = ?
                WHERE topic = ? AND url = ? AND timestamp = (
                    SELECT MAX(timestamp) FROM proactive_info WHERE topic = ? AND url = ?
                )
                ''',
                (
                    sent_to_memory,
                    topic,
                    url,
                    topic,
                    url
                )
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating proactive info memory status: {e}")

    def browse_with_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Context-aware browsing based on a given context object.
        
        Args:
            context: A dictionary containing context information like:
                    - query: The main search query or task
                    - user_interests: List of user interests
                    - recent_topics: Recently discussed topics
                    - constraints: Any constraints to apply to the browsing
        
        Returns:
            A dictionary with browsing results and extracted information
        """
        try:
            # Extract the main query/topic from context
            main_query = context.get("query", "")
            if not main_query:
                return {
                    "status": "error",
                    "message": "No query provided in context"
                }
            
            # Store the context for future reference
            self._store_browsing_context(context)
            
            # Refine the query based on context
            refined_query = self._refine_query_from_context(context)
            
            logger.info(f"Context-aware browsing for: {refined_query}")
            
            # Perform search with the refined query
            search_result = self.search(refined_query)
            
            if search_result["status"] != "success" or not search_result.get("results"):
                return {
                    "status": "error",
                    "message": f"Search failed for query: {refined_query}",
                    "original_query": main_query,
                    "refined_query": refined_query
                }
            
            # Filter and prioritize results based on context
            prioritized_results = self._prioritize_results_with_context(
                search_result["results"], 
                context
            )
            
            # Gather information from top results
            browsed_data = []
            for result in prioritized_results[:3]:  # Limit to top 3 results
                try:
                    # Navigate to the page
                    page_result = self.navigate_to_url(result["url"])
                    
                    if page_result["status"] == "success":
                        # Extract relevant information based on context
                        extracted_data = self._extract_relevant_data(
                            page_result["content"],
                            context,
                            url=result["url"],
                            title=result.get("title", "")
                        )
                        
                        browsed_data.append(extracted_data)
                        
                        # Send to memory
                        memory_data = {
                            "type": "context_aware_browsing",
                            "query": main_query,
                            "refined_query": refined_query,
                            "url": result["url"],
                            "title": result.get("title", "No title"),
                            "extracted_data": extracted_data,
                            "context": context,
                            "timestamp": time.time()
                        }
                        
                        # Send the data to memory
                        self.send_to_memory(memory_data)
                        
                except Exception as page_error:
                    logger.error(f"Error processing search result: {page_error}")
                    continue
            
            return {
                "status": "success",
                "original_query": main_query,
                "refined_query": refined_query,
                "results_count": len(prioritized_results),
                "browsed_data": browsed_data,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error in context-aware browsing: {e}")
            return {
                "status": "error",
                "message": str(e),
                "context": context
            }
    
    def _refine_query_from_context(self, context: Dict[str, Any]) -> str:
        """Refine a search query based on context information"""
        query = context.get("query", "")
        
        # If we have specific refinements from the context, use them
        if "query_refinements" in context:
            refinements = context["query_refinements"]
            if isinstance(refinements, list) and refinements:
                return f"{query} {' '.join(refinements)}"
        
        # Add user interests if available
        if "user_interests" in context and isinstance(context["user_interests"], list):
            # Take the first two interests only to avoid overly specific queries
            interests = context["user_interests"][:2]
            if interests:
                query += f" {' '.join(interests)}"
        
        # Add recent topics if available for better context
        if "recent_topics" in context and isinstance(context["recent_topics"], list):
            recent = context["recent_topics"][:1]  # Just use the most recent topic
            if recent:
                query += f" {recent[0]}"
        
        # Add constraints if available
        if "constraints" in context and isinstance(context["constraints"], dict):
            constraints = []
            
            if "time_period" in context["constraints"]:
                time_period = context["constraints"]["time_period"]
                if time_period == "recent":
                    constraints.append("recent")
                elif time_period == "past_year":
                    constraints.append("past year")
                elif time_period == "past_month":
                    constraints.append("past month")
            
            if "content_type" in context["constraints"]:
                content_type = context["constraints"]["content_type"]
                if content_type == "news":
                    constraints.append("news")
                elif content_type == "research":
                    constraints.append("research paper")
                elif content_type == "tutorial":
                    constraints.append("tutorial guide")
            
            if constraints:
                query += f" {' '.join(constraints)}"
        
        return query
    
    def _prioritize_results_with_context(self, results: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize search results based on the given context"""
        if not results:
            return []
        
        # Create a copy of results to avoid modifying the original
        prioritized = results.copy()
        
        # If we have user interests, boost results that match them
        if "user_interests" in context and isinstance(context["user_interests"], list):
            interests = context["user_interests"]
            for result in prioritized:
                # Calculate interest score based on title and snippet matching
                interest_score = 0
                for interest in interests:
                    if interest.lower() in result.get("title", "").lower():
                        interest_score += 3  # Higher weight for title matches
                    if interest.lower() in result.get("snippet", "").lower():
                        interest_score += 1  # Lower weight for snippet matches
                
                # Add the score to the result
                result["interest_score"] = interest_score
        
        # If we have constraints on time period, apply them
        if "constraints" in context and "time_period" in context["constraints"]:
            time_period = context["constraints"]["time_period"]
            
            # This is a simple heuristic, in real-world we'd need more sophisticated time extraction
            for result in prioritized:
                # Look for date indicators in the snippet
                snippet = result.get("snippet", "").lower()
                recency_score = 0
                
                if time_period == "recent":
                    if any(term in snippet for term in ["today", "yesterday", "this week", "2025"]):
                        recency_score = 3
                    elif any(term in snippet for term in ["this month", "last month"]):
                        recency_score = 2
                    elif any(term in snippet for term in ["this year", "2024"]):
                        recency_score = 1
                elif time_period == "past_year":
                    if any(term in snippet for term in ["2024", "2025"]):
                        recency_score = 3
                elif time_period == "past_month":
                    if any(term in snippet for term in ["this month", "last month", "weeks ago"]):
                        recency_score = 3
                
                # Add the score to the result
                result["recency_score"] = recency_score
        
        # Calculate total priority score
        for result in prioritized:
            total_score = 0
            if "interest_score" in result:
                total_score += result["interest_score"]
            if "recency_score" in result:
                total_score += result["recency_score"]
            
            result["priority_score"] = total_score
        
        # Sort by priority score (higher is better)
        prioritized.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return prioritized
    
    def _extract_relevant_data(self, content: str, context: Dict[str, Any], url: str, title: str) -> Dict[str, Any]:
        """Extract data relevant to the context from page 
from main_pc_code.src.core.base_agent import BaseAgentcontent
from main_pc_code.utils.config_loader import load_config

# Load configuration at the module level
config = load_config()"""
        # Extract a summary (first 1000 chars)
        summary = content[:1000] + "..." if len(content) > 1000 else content
        
        # Extract key information based on query context
        main_query = context.get("query", "").lower()
        query_terms = set(main_query.split())
        
        # Find paragraphs most relevant to the query
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        relevant_paragraphs = []
        
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            # Calculate relevance score based on query term matches
            score = sum(1 for term in query_terms if term in paragraph_lower)
            if score > 0:
                relevant_paragraphs.append({
                    "text": paragraph,
                    "relevance": score
                })
        
        # Sort by relevance score and take top 3
        relevant_paragraphs.sort(key=lambda x: x["relevance"], reverse=True)
        top_paragraphs = [p["text"] for p in relevant_paragraphs[:3]]
        
        return {
            "url": url,
            "title": title,
            "summary": summary,
            "relevant_content": top_paragraphs,
            "timestamp": time.time()
        }
    
    def _store_browsing_context(self, context: Dict[str, Any]) -> None:
        """Store the browsing context in the database"""
        try:
            cursor = self.conn.cursor()
            
            # Store each context key-value pair
            for key, value in context.items():
                # Skip complex nested structures
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                elif not isinstance(value, str):
                    value = str(value)
                
                cursor.execute(
                    '''
                    INSERT INTO browsing_context (context_key, context_value, timestamp)
                    VALUES (?, ?, ?)
                    ''',
                    (key, value, time.time())
                )
            
            self.conn.commit()
            logger.debug("Stored browsing context in database")
        except Exception as e:
            logger.error(f"Error storing browsing context: {e}")



    
    def _get_health_status(self) -> dict:


    
        """Return health status information."""


    
        base_status = super()._get_health_status()


    
        # Add any additional health information specific to UnifiedWebAgent


    
        base_status.update({


    
            'service': 'UnifiedWebAgent',


    
            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,


    
            'additional_info': {}


    
        })


    
        return base_status

def main():
    """Main entry point"""
    try:
        logger.info("Initializing UnifiedWebAgent")
        agent = UnifiedWebAgent()
        
        logger.info("Starting UnifiedWebAgent")
        agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Make sure we clean up even if there's an error
        if 'agent' in locals():
            agent.cleanup()



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = UnifiedWebAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()