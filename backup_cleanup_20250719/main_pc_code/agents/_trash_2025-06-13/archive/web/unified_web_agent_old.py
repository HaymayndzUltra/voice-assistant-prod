from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Unified Web Agent
- Combines web scraping, search, and browser automation
- Handles dynamic websites with JavaScript rendering
- Supports authentication and session management
- Implements rate limiting and respects robots.txt
- Extracts structured data with intelligent parsing
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading
import tempfile
import hashlib
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import sqlite3
from playwright.sync_api import sync_playwright

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config

# Import from web_automation package
from web_automation import (
    WebController,
    VoiceProcessor,
    AudioManager
)
from web_automation.utils import setup_logger
from web_automation.utils.task_memory import TaskMemory

# Global singleton instance for TaskMemory
GLOBAL_TASK_MEMORY = TaskMemory()

# Configure logging
logger = setup_logger(__name__)

# Get ZMQ ports from config
WEB_AGENT_PORT = config.get('zmq.web_agent_port', 5560)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)
EXECUTOR_PORT = config.get('zmq.executor_port', 5613)

class UnifiedWebAgent(BaseAgent):
    """Unified agent for web operations including scraping, search, and browser automation"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="UnifiedWebAgentOld")
        """Initialize the unified web agent."""
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.bind(f"tcp://127.0.0.1:{WEB_AGENT_PORT}")
        logger.info(f"Unified Web Agent bound to port {WEB_AGENT_PORT}")
        
        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.connect(f"tcp://localhost:{MODEL_MANAGER_PORT}")
        logger.info(f"Connected to Model Manager on port {MODEL_MANAGER_PORT}")
        
        # Socket to communicate with executor agent
        self.executor = self.context.socket(zmq.REQ)
        self.executor.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.executor.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.executor.connect(f"tcp://localhost:{EXECUTOR_PORT}")
        logger.info(f"Connected to Executor Agent on port {EXECUTOR_PORT}")
        
        # Setup cache directory
        self.cache_dir = Path(config.get('system.cache_dir', 'cache')) / "web_agent"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup output directory
        self.output_dir = Path(config.get('system.output_dir', 'output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database for caching and history
        self.db_path = self.cache_dir / "web_cache.sqlite"
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        
        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Browser automation setup
        self.browser = None
        self.page = None
        self._init_browser()
        
        # Running flag
        self.running = True
        
        # Import necessary libraries
        self._ensure_dependencies()
        
        # Initialize web automation components
        self.web_controller = WebController()
        self.voice_processor = VoiceProcessor()
        self.audio_manager = AudioManager()
        self.task_memory = TaskMemory()
        
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
        
        # Search history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY,
            query TEXT,
            timestamp REAL,
            result TEXT
        )
        ''')
        
        self.conn.commit()
    
    def _ensure_dependencies(self):
        """Ensure all required dependencies are installed"""
        try:
            import requests
    except ImportError as e:
        print(f"Import error: {e}")
            import bs4
            import pandas as pd
            import selenium
            from selenium import webdriver
            from playwright.sync_api import sync_playwright
            logger.info("All required dependencies are installed")
        except ImportError as e:
            logger.warning(f"Missing dependency: {e}")
            logger.warning("Some functionality may be limited")
    
    def _init_browser(self):
        """Initialize browser for automation"""
        try:
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()
            logger.info("Browser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            self.browser = None
            self.page = None
    
    def _send_to_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a request to the LLM through the model manager"""
        try:
            # Prepare request
            request = {
                "request_type": "generate",
                "model": "deepseek",  # Use DeepSeek Coder for code generation
                "prompt": prompt,
                "temperature": 0.2  # Lower temperature for more deterministic code generation
            }
            
            if system_prompt:
                request["system_prompt"] = system_prompt
            
            # Send request to model manager
            self.model_manager.send_string(json.dumps(request))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.model_manager, zmq.POLLIN)
            
            if poller.poll(30000):  # 30 second timeout
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
    
    def _execute_code(self, code: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute code using the executor agent"""
        try:
            # Prepare request
            request = {
                "request_type": "execute",
                "code": code,
                "parameters": parameters or {}
            }
            
            # Send request to executor agent
            self.executor.send_string(json.dumps(request))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.executor, zmq.POLLIN)
            
            if poller.poll(30000):  # 30 second timeout
                response_str = self.executor.recv_string()
                response = json.loads(response_str)
                
                if response["status"] == "success":
                    return response["result"]
                else:
                    logger.error(f"Error from executor agent: {response.get('error', 'Unknown error')}")
                    raise Exception(response.get("error", "Unknown error"))
            else:
                logger.error("Timeout waiting for response from executor agent")
                raise Exception("Timeout waiting for response from executor agent")
        
        except Exception as e:
            logger.error(f"Error executing code: {str(e)}")
            raise
    
    def _get_cached_page(self, url: str, max_age: int = 3600) -> Optional[Dict[str, Any]]:
        """Get a cached page if it exists and is not too old"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT content, timestamp, headers, status_code FROM cache WHERE url = ?",
            (url,)
        )
        row = cursor.fetchone()
        
        if row:
            content, timestamp, headers_json, status_code = row
            if time.time() - timestamp <= max_age:
                return {
                    "content": content,
                    "timestamp": timestamp,
                    "headers": json.loads(headers_json),
                    "status_code": status_code
                }
        
        return None
    
    def _cache_page(self, url: str, content: str, headers: Dict[str, str], status_code: int):
        """Cache a page for future use"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cache (url, content, timestamp, headers, status_code) VALUES (?, ?, ?, ?, ?)",
            (url, content, time.time(), json.dumps(headers), status_code)
        )
        self.conn.commit()
    
    def _fetch_page(self, url: str, use_cache: bool = True, render_js: bool = False) -> Dict[str, Any]:
        """Fetch a web page, with optional caching and JavaScript rendering"""
        if use_cache:
            cached = self._get_cached_page(url)
            if cached:
                return cached
        
        try:
            if render_js and self.page:
                # Use browser for JavaScript rendering
                self.page.goto(url)
                content = self.page.content()
                return {
                    "content": content,
                    "timestamp": time.time(),
                    "headers": dict(self.page.response.headers),
                    "status_code": self.page.response.status
                }
            else:
                # Use requests for simple fetching
                response = self.session.get(url, timeout=30)
                content = response.text
                result = {
                    "content": content,
                    "timestamp": time.time(),
                    "headers": dict(response.headers),
                    "status_code": response.status_code
                }
                if use_cache:
                    self._cache_page(url, content, dict(response.headers), response.status_code)
                return result
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            raise
    
    def _analyze_page_structure(self, html_content: str, url: str) -> Dict[str, Any]:
        """Analyze the structure of a web page to identify data patterns"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Analyze common data patterns
            patterns = {
                "tables": len(soup.find_all('table')),
                "lists": len(soup.find_all(['ul', 'ol'])),
                "articles": len(soup.find_all('article')),
                "products": len(soup.find_all(class_=re.compile(r'product|item|card'))),
                "pagination": len(soup.find_all(class_=re.compile(r'pagination|page|next|prev'))),
                "forms": len(soup.find_all('form')),
                "images": len(soup.find_all('img')),
                "links": len(soup.find_all('a')),
                "headings": {
                    "h1": len(soup.find_all('h1')),
                    "h2": len(soup.find_all('h2')),
                    "h3": len(soup.find_all('h3'))
                }
            }
            
            # Identify potential data containers
            containers = []
            for div in soup.find_all('div', class_=True):
                class_name = ' '.join(div['class'])
                if any(keyword in class_name.lower() for keyword in ['content', 'data', 'list', 'grid', 'container']):
                    containers.append({
                        "class": class_name,
                        "children": len(div.find_all(recursive=False))
                    })
            
            return {
                "patterns": patterns,
                "containers": containers,
                "url": url
            }
        except Exception as e:
            logger.error(f"Error analyzing page structure: {e}")
            raise
    
    def _generate_scraper_code(self, url: str, data_type: str, page_structure: Dict[str, Any]) -> str:
        """Generate scraping code based on URL and data type"""
        logger.info(f"Generating scraper code for URL: {url}, data type: {data_type}")
        
        # System prompt for the code generation LLM
        system_prompt = """You are a web scraping code generator. Your task is to generate Python code that scrapes data from a given URL based on the specified data type and page structure. The code should:

1. Use requests and BeautifulSoup for simple scraping
2. Use Selenium for JavaScript-heavy websites
3. Extract the specified data type (e.g., products, articles, prices)
4. Handle pagination if necessary
5. Format the data as specified (CSV, Excel, or JSON)
6. Include error handling and retries
7. Be efficient and respect website terms of service
8. Return the data as a pandas DataFrame

The code should be complete, well-commented, and ready to run. It should define a main function that takes parameters and returns the scraped data.

Use the following libraries:
- requests
- bs4 (BeautifulSoup)
- pandas
- selenium (if necessary)
- time
- re (if necessary)"""
        
        # Create the prompt for the code generation LLM
        prompt = f"""Generate Python code to scrape {data_type} from {url} and return the data as a pandas DataFrame.

Page structure analysis:
{json.dumps(page_structure, indent=2)}

The code should be complete and ready to run. It should define a function called `scrape_data` that takes the URL as a parameter and returns the scraped data as a pandas DataFrame.

Example function signature:
```python
def scrape_data(url, max_pages=5):
    # Scraping code here
    # ...
    return df
```"""
        
        try:
            # Get code from LLM
            response = self._send_to_llm(prompt, system_prompt)
            
            # Extract code from response
            code_match = re.search(r'```python(.*?)```', response, re.DOTALL)
            
            if code_match:
                code = code_match.group(1).strip()
                logger.info("Generated scraper code successfully")
                return code
            else:
                # If no code block found, try to use the entire response
                if "def scrape_data" in response:
                    logger.info("Generated scraper code (without code block markers)")
                    return response
                else:
                    logger.error("Could not extract valid code from LLM response")
                    raise Exception("Could not extract valid code from LLM response")
        
        except Exception as e:
            logger.error(f"Error generating scraper code: {str(e)}")
            raise
    
    def _prepare_scraper_code(self, code: str, url: str, output_format: str) -> str:
        """Prepare the scraper code for execution by adding imports and wrapper code"""
        # Add necessary imports if they're not already in the code
        imports = """
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import os
from pathlib import Path
from common.env_helpers import get_env
"""
        
        # Add wrapper code
        wrapper = f"""
def main():
    url = "{url}"
    df = scrape_data(url)
    
    # Save the data
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    if "{output_format}" == "csv":
        output_path = output_dir / "scraped_data.csv"
        df.to_csv(output_path, index=False)
    elif "{output_format}" == "excel":
        output_path = output_dir / "scraped_data.xlsx"
        df.to_excel(output_path, index=False)
    else:  # json
        output_path = output_dir / "scraped_data.json"
        df.to_json(output_path, orient="records")
    
    return {{
        "status": "success",
        "output_path": str(output_path),
        "row_count": len(df),
        "columns": list(df.columns)
    }}

if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
"""
        
        # Combine everything
        full_code = imports + "\n" + code + "\n" + wrapper

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
        return full_code
    
    def scrape_website(self, url: str, data_type: str, output_format: str = "csv", render_js: bool = False) -> Dict[str, Any]:
        """Scrape data from a website"""
        try:
            # Fetch the page
            page_data = self._fetch_page(url, use_cache=True, render_js=render_js)
            
            # Analyze page structure
            page_structure = self._analyze_page_structure(page_data["content"], url)
            
            # Generate scraping code
            code = self._generate_scraper_code(url, data_type, page_structure)
            
            # Prepare code for execution
            full_code = self._prepare_scraper_code(code, url, output_format)
            
            # Execute the code
            result = self._execute_code(full_code)
            
            # Log the scraping operation
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO scraping_history (url, data_type, output_format, timestamp, success, output_path) VALUES (?, ?, ?, ?, ?, ?)",
                (url, data_type, output_format, time.time(), True, result.get("output_path"))
            )
            self.conn.commit()
            
            return result
        
        except Exception as e:
            logger.error(f"Error scraping website: {e}")
            
            # Log the error
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO scraping_history (url, data_type, output_format, timestamp, success, error) VALUES (?, ?, ?, ?, ?, ?)",
                (url, data_type, output_format, time.time(), False, str(e))
            )
            self.conn.commit()
            
            raise
    
    def search_web(self, query: str, max_results: int = 3) -> str:
        """Perform a web search using DuckDuckGo"""
        if not query or not query.strip():
            logger.warning('No query provided for DuckDuckGo search (skipped).')
            return 'No query provided (skipped).'
        
        url = (
            f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}"
            f"&format=json&no_redirect=1&no_html=1&skip_disambig=1"
        )
        
        logger.info(f"Searching DuckDuckGo: {query}")
        
        try:
            resp = self.session.get(url, timeout=5)
            if resp.status_code != 200 or not resp.content:
                logger.error(f'DuckDuckGo API returned status {resp.status_code}')
                return f'DuckDuckGo API error: {resp.status_code}'
            
            data = resp.json()
            
            # Log the search
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO search_history (query, timestamp, result) VALUES (?, ?, ?)",
                (query, time.time(), json.dumps(data))
            )
            self.conn.commit()
            
            if data.get("AbstractText"):
                logger.info(f"Found AbstractText result for query '{query}'")
                return data["AbstractText"]
            elif data.get("Answer"):
                logger.info(f"Found Answer result for query '{query}'")
                return data["Answer"]
            elif data.get("RelatedTopics"):
                for topic in data["RelatedTopics"]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        logger.info(f"Found RelatedTopics result for query '{query}'")
                        return topic["Text"]
            
            logger.warning(f"No relevant answer found for query '{query}'")
            return "Sorry, I couldn't find an answer."
        
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return f"Web search error: {e}"
    
    def browser_automation(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle browser automation commands"""
        if not self.page:
            self._init_browser()
            if not self.page:
                return {"status": "error", "reason": "Browser not initialized"}
        
        action = command.get("action")
        try:
            logger.info(f"Received browser action: {action}")
            
            if action == "goto":
                url = command["url"]
                self.page.goto(url)
                logger.info(f"Navigated to {url}")
                return {"status": "ok", "msg": f"Navigated to {url}"}
            
            elif action == "login":
                url = command["url"]
                username = command["username"]
                password = command["password"]
                username_selector = command["username_selector"]
                password_selector = command["password_selector"]
                submit_selector = command["submit_selector"]
                
                self.page.goto(url)
                self.page.fill(username_selector, username)
                self.page.fill(password_selector, password)
                self.page.click(submit_selector)
                logger.info(f"Login attempted at {url}")
                return {"status": "ok", "msg": "Login attempted"}
            
            elif action == "fill_form":
                url = command["url"]
                fields = command["fields"]
                
                self.page.goto(url)
                for selector, value in fields.items():
                    self.page.fill(selector, value)
                logger.info(f"Form filled at {url}")
                return {"status": "ok", "msg": "Form filled"}
            
            elif action == "click":
                selector = command["selector"]
                self.page.click(selector)
                logger.info(f"Clicked {selector}")
                return {"status": "ok", "msg": f"Clicked {selector}"}
            
            elif action == "scrape":
                selector = command["selector"]
                content = self.page.inner_text(selector)
                logger.info(f"Scraped content from {selector}")
                return {"status": "ok", "content": content}
            
            elif action == "download":
                url = command["url"]
                save_path = command["save_path"]
                
                self.page.goto(url)
                with self.page.expect_download() as download_info:
                    self.page.click(command["download_selector"])
                download = download_info.value
                download.save_as(save_path)
                logger.info(f"Downloaded file to {save_path}")
                return {"status": "ok", "msg": f"Downloaded to {save_path}"}
            
            elif action == "upload":
                url = command["url"]
                file_selector = command["file_selector"]
                file_path = command["file_path"]
                
                if not os.path.exists(file_path):
                    logger.error(f"Upload failed: file not found: {file_path}")
                    return {"status": "error", "reason": f"File not found: {file_path}"}
                
                self.page.goto(url)
                self.page.set_input_files(file_selector, file_path)
                logger.info(f"Uploaded {file_path}")
                return {"status": "ok", "msg": f"Uploaded {file_path}"}
            
            elif action == "submit_form":
                selector = command["selector"]
                self.page.click(selector)
                logger.info(f"Form submitted via {selector}")
                return {"status": "ok", "msg": "Form submitted"}
            
            else:
                logger.warning(f"Unknown action: {action}")
                return {"status": "error", "reason": "Unknown action"}
        
        except Exception as e:
            logger.error(f"Error handling browser action '{action}': {e}")
            return {"status": "error", "reason": str(e)}
    
    def handle_requests(self):
        """Handle incoming ZMQ requests"""
        while self.running:
            try:
                # Wait for next request from client
                message = self.receiver.recv_string()
                request = json.loads(message)
                
                action = request.get("action")
                logger.info(f"Received request with action: {action}")
                
                try:
                    if action == "scrape":
                        result = self.scrape_website(
                            request["url"],
                            request["data_type"],
                            request.get("output_format", "csv"),
                            request.get("render_js", False)
                        )
                    elif action == "search":
                        result = self.search_web(
                            request["query"],
                            request.get("max_results", 3)
                        )
                    elif action == "browser":
                        result = self.browser_automation(request)
                    else:
                        result = {"status": "error", "reason": f"Unknown action: {action}"}
                    
                    # Send reply back to client
                    self.receiver.send_string(json.dumps(result))
                
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
                    error_response = {
                        "status": "error",
                        "reason": str(e)
                    }
                    self.receiver.send_string(json.dumps(error_response))
            
            except Exception as e:
                logger.error(f"Error in request handling loop: {e}")
                continue
    
    def run(self):
        """Run the agent"""
        try:
            logger.info("Starting Unified Web Agent")
            self.handle_requests()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.browser:
                self.browser.close()
            if self.conn:
                self.conn.close()
            if self.receiver:
                self.receiver.close()
            if self.model_manager:
                self.model_manager.close()
            if self.executor:
                self.executor.close()
            if self.context:
                self.context.term()
            logger.info("Unified Web Agent cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    agent = UnifiedWebAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        agent.cleanup()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise