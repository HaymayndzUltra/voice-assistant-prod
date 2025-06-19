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
import pandas as pd
from pathlib import Path
from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import base64
from bs4 import BeautifulSoup
import urllib.parse
import tempfile

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config
from config.pc2_connections import get_connection_string

# Configure logging
LOG_PATH = Path(config.get('system.logs_dir', 'logs')) / "unified_web_agent.log"
LOG_PATH.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config.get('system.log_level', 'INFO')),
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UnifiedWebAgent")

# ZMQ Configuration
UNIFIED_WEB_PORT = 5604  # Main port
HEALTH_CHECK_PORT = 5605  # Health check port
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)
MODEL_MANAGER_HOST = config.get('zmq.model_manager_host', '192.168.1.1')
AUTOGEN_FRAMEWORK_PORT = config.get('zmq.autogen_framework_port', 5600)
EXECUTOR_PORT = config.get('zmq.executor_port', 5603)
CONTEXT_SUMMARIZER_PORT = 5610
MEMORY_AGENT_PORT = 5596

# Browser automation settings
MIN_DELAY_BETWEEN_REQUESTS = 2  # seconds
MAX_RETRIES = 3
TIMEOUT = 30  # seconds

class UnifiedWebAgent:
    """Unified web agent combining autonomous assistance, scraping, and automation"""
    
    def __init__(self):
        """Initialize the unified web agent"""
        # ZMQ setup
        self.context = zmq.Context()
        
        # Main socket for requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{UNIFIED_WEB_PORT}")
        logger.info(f"Unified Web Agent bound to port {UNIFIED_WEB_PORT}")
        
        # Health check socket
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://0.0.0.0:{HEALTH_CHECK_PORT}")
        logger.info(f"Health check bound to port {HEALTH_CHECK_PORT}")
        
        # Connect to Model Manager
        self.model_manager = self.context.socket(zmq.REQ)
        try:
            self.model_manager.connect(f"tcp://{MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}")
            logger.info(f"Connected to Model Manager on {MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Model Manager: {e}")
            raise
        
        # Connect to AutoGen Framework
        self.framework = self.context.socket(zmq.REQ)
        self.framework.connect(f"tcp://localhost:{AUTOGEN_FRAMEWORK_PORT}")
        logger.info(f"Connected to AutoGen Framework on port {AUTOGEN_FRAMEWORK_PORT}")
        
        # Connect to Executor Agent
        self.executor = self.context.socket(zmq.REQ)
        self.executor.connect(f"tcp://localhost:{EXECUTOR_PORT}")
        logger.info(f"Connected to Executor Agent on port {EXECUTOR_PORT}")
        
        # Connect to Context Summarizer
        self.context_summarizer = self.context.socket(zmq.REQ)
        try:
            self.context_summarizer.connect(get_connection_string("context_summarizer"))
            logger.info("Connected to Context Summarizer on PC2")
        except (ImportError, ValueError):
            self.context_summarizer.connect(f"tcp://localhost:{CONTEXT_SUMMARIZER_PORT}")
            logger.info(f"Connected to local Context Summarizer on port {CONTEXT_SUMMARIZER_PORT}")
        
        # Connect to Memory Agent
        self.memory_agent = self.context.socket(zmq.REQ)
        try:
            self.memory_agent.connect(get_connection_string("contextual_memory"))
            logger.info("Connected to Memory Agent on PC2")
        except (ImportError, ValueError):
            self.memory_agent.connect(f"tcp://localhost:{MEMORY_AGENT_PORT}")
            logger.info(f"Connected to local Memory Agent on port {MEMORY_AGENT_PORT}")
        
        # Setup directories
        self.cache_dir = Path(config.get('system.cache_dir', 'cache')) / "web_agent"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.output_dir = Path(config.get('system.output_dir', 'output'))
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
        
        logger.info("Unified Web Agent initialized")
    
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
            error TEXT,
            output_path TEXT
        )
        ''')
        
        # Form submission history
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
        
        # Conversation context table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_context (
            id INTEGER PRIMARY KEY,
            timestamp REAL,
            context TEXT,
            summary TEXT,
            relevance_score REAL
        )
        ''')
        
        self.conn.commit()
    
    def _send_to_llm(self, prompt: str, system_prompt: Optional[str] = None, model: str = "deepseek") -> str:
        """Send a request to the LLM through the model manager"""
        try:
            request = {
                "request_type": "generate",
                "model": model,
                "prompt": prompt,
                "temperature": 0.2
            }
            
            if system_prompt:
                request["system_prompt"] = system_prompt
            
            self.model_manager.send_string(json.dumps(request))
            
            poller = zmq.Poller()
            poller.register(self.model_manager, zmq.POLLIN)
            
            if poller.poll(30000):
                response_str = self.model_manager.recv_string()
                response = json.loads(response_str)
                
                if response["status"] == "success":
                    return response["text"]
                else:
                    logger.error(f"Error from model manager: {response.get('error', 'Unknown error')}")
                    raise Exception(response.get("error", "Unknown error"))
            else:
                logger.error("Timeout waiting for response from model manager")
                raise Exception("Timeout waiting for response from model manager")
        
        except Exception as e:
            logger.error(f"Error sending to LLM: {str(e)}")
            raise
    
    def _get_conversation_context(self) -> str:
        """Get relevant conversation context from memory agent"""
        try:
            request = {
                "action": "get_recent_context",
                "limit": 5  # Get last 5 interactions
            }
            
            self.memory_agent.send_string(json.dumps(request))
            
            poller = zmq.Poller()
            poller.register(self.memory_agent, zmq.POLLIN)
            
            if poller.poll(5000):  # 5 second timeout
                response_str = self.memory_agent.recv_string()
                response = json.loads(response_str)
                
                if response["status"] == "success":
                    return response["context"]
                else:
                    logger.warning(f"Failed to get conversation context: {response.get('error', 'Unknown error')}")
                    return ""
            else:
                logger.warning("Timeout getting conversation context")
                return ""
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return ""
    
    def _enhance_search_query(self, query: str) -> str:
        """Enhance the search query using context and LLM"""
        try:
            # Get conversation context
            context = self._get_conversation_context()
            
            # Create enhancement prompt
            prompt = f"""
            Given the following search query and conversation context, enhance the query to be more specific and effective:
            
            Original Query: {query}
            
            Conversation Context:
            {context}
            
            Enhanced Query:
            """
            
            # Get enhanced query from LLM
            enhanced_query = self._send_to_llm(prompt)
            
            return enhanced_query.strip()
            
        except Exception as e:
            logger.error(f"Error enhancing search query: {str(e)}")
            return query
    
    def _rank_search_results(self, results: List[Dict[str, Any]], original_query: str) -> List[Dict[str, Any]]:
        """Rank search results by relevance"""
        try:
            # Create ranking prompt
            prompt = f"""
            Rank the following search results by relevance to the query: "{original_query}"
            
            Results:
            {json.dumps(results, indent=2)}
            
            Ranked Results:
            """
            
            # Get ranked results from LLM
            ranked_results = self._send_to_llm(prompt)
            
            # Parse and return ranked results
            return json.loads(ranked_results)
            
        except Exception as e:
            logger.error(f"Error ranking search results: {str(e)}")
            return results
    
    def search_web(self, query: str) -> Dict[str, Any]:
        """Search the web using multiple strategies"""
        try:
            # First try to use the context summarizer to enhance the query
            enhanced_query = self._enhance_search_query(query)
            
            # Then perform the search
            search_results = self._perform_search(enhanced_query)
            
            # Finally, analyze and rank the results
            ranked_results = self._rank_search_results(search_results, query)
            
            return {
                "status": "success",
                "query": query,
                "enhanced_query": enhanced_query,
                "results": ranked_results
            }
            
        except Exception as e:
            logger.error(f"Error searching web: {str(e)}")
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }
    
    def _perform_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform the actual web search"""
        # This is a placeholder - in a real implementation, you would:
        # 1. Use a search API (Google, Bing, etc.)
        # 2. Scrape search results
        # 3. Combine results from multiple sources
        return []
    
    def analyze_conversation(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze conversation history to identify information needs"""
        try:
            # Convert conversation to text
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in conversation_history
            ])
            
            # Create analysis prompt
            prompt = f"""
            Analyze the following conversation and identify:
            1. Key topics discussed
            2. Information gaps or questions that need answers
            3. Potential web searches that could help
            4. Suggested actions to take
            
            Conversation:
            {conversation_text}
            
            Analysis:
            """
            
            # Get analysis from LLM
            analysis = self._send_to_llm(prompt)
            
            # Store in conversation context
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_context (timestamp, context, summary) VALUES (?, ?, ?)",
                (time.time(), conversation_text, analysis)
            )
            self.conn.commit()
            
            return {
                "status": "success",
                "analysis": analysis,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def proactive_info_gathering(self, user_message: str) -> Dict[str, Any]:
        """Proactively gather information based on user message"""
        try:
            # Analyze the message
            analysis = self.analyze_conversation([{"role": "user", "content": user_message}])
            
            if analysis["status"] != "success":
                return analysis
            
            # Extract potential search queries
            prompt = f"""
            Based on this analysis, generate 2-3 specific search queries to gather relevant information:
            
            {analysis['analysis']}
            
            Search Queries:
            """
            
            queries = self._send_to_llm(prompt).strip().split('\n')
            
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
            
            if action == "navigate":
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
        logger.info("Starting Unified Web Agent")
        
        # Start health check thread
        health_thread = threading.Thread(target=self._health_check_loop)
        health_thread.daemon = True
        health_thread.start()
        
        while self.running:
            try:
                # Wait for request
                message = self.socket.recv_string()
                request = json.loads(message)
                
                # Handle request
                response = self.handle_request(request)
                
                # Send response
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                traceback.print_exc()
    
    def _health_check_loop(self):
        """Health check loop"""
        while self.running:
            try:
                # Wait for health check request
                message = self.health_socket.recv_string()
                request = json.loads(message)
                
                if request.get("action") == "health_check":
                    self.health_check_requests += 1
                    response = self.get_status()
                else:
                    response = {
                        "status": "error",
                        "error": "Invalid health check request"
                    }
                
                # Send response
                self.health_socket.send_string(json.dumps(response))
                
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
        if hasattr(self, 'model_manager'):
            self.model_manager.close()
        if hasattr(self, 'framework'):
            self.framework.close()
        if hasattr(self, 'executor'):
            self.executor.close()
        if hasattr(self, 'context_summarizer'):
            self.context_summarizer.close()
        if hasattr(self, 'memory_agent'):
            self.memory_agent.close()
        
        # Close ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("Unified Web Agent cleaned up")

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