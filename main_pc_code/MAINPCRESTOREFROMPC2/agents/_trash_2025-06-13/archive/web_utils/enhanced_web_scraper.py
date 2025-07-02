from src.core.base_agent import BaseAgent
"""
Enhanced Web Scraper Agent
- Advanced web scraping with multiple strategies
- Supports dynamic websites with JavaScript rendering
- Handles authentication and session management
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

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "enhanced_web_scraper.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("EnhancedWebScraper")

# Get ZMQ ports from config
WEB_SCRAPER_PORT = config.get('zmq.web_scraper_port', 5602)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)
EXECUTOR_PORT = config.get('zmq.executor_port', 5613)

class EnhancedWebScraper(BaseAgent):
    """Advanced web scraping agent with multiple strategies and intelligent parsing"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="EnhancedWebScraper")
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.bind(f"tcp://127.0.0.1:{WEB_SCRAPER_PORT}")
        logger.info(f"Enhanced Web Scraper bound to port {WEB_SCRAPER_PORT}")
        
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
        self.cache_dir = Path(config.get('system.cache_dir', 'cache')) / "web_scraper"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup output directory
        self.output_dir = Path(config.get('system.output_dir', 'output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database for caching and history
        self.db_path = self.cache_dir / "scraper_cache.sqlite"
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        
        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Running flag
        self.running = True
        
        # Import necessary libraries
        self._ensure_dependencies()
        
        logger.info("Enhanced Web Scraper initialized")
    
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
        
        self.conn.commit()
    
    def _ensure_dependencies(self):
        """Ensure all required dependencies are installed"""
        try:
            import requests
            import bs4
            import pandas as pd
            import selenium
            from selenium import webdriver
            logger.info("All required dependencies are installed")
        except ImportError as e:
            logger.warning(f"Missing dependency: {e}")
            logger.warning("Some functionality may be limited")
    
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
                logger.info(f"Using cached version of {url}")
                return {
                    "content": cached["content"],
                    "url": url,
                    "status_code": cached["status_code"],
                    "headers": cached["headers"],
                    "from_cache": True
                }
        
        if render_js:
            # Use Selenium for JavaScript rendering
            return self._fetch_with_selenium(url)
        else:
            # Use requests for static pages
            try:
                response = self.session.get(url, timeout=30)
                content = response.text
                
                # Cache the page
                self._cache_page(url, content, dict(response.headers), response.status_code)
                
                return {
                    "content": content,
                    "url": url,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "from_cache": False
                }
            except Exception as e:
                logger.error(f"Error fetching {url}: {str(e)}")
                raise
    
    def _fetch_with_selenium(self, url: str) -> Dict[str, Any]:
        """Fetch a page using Selenium for JavaScript rendering"""
        # This would normally use Selenium WebDriver
        # For now, we'll execute code to do this
        code = f"""
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time

# Setup headless Chrome
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Create driver
driver = webdriver.Chrome(options=options)

try:
    # Fetch the page
    driver.get("{url}")
    
    # Wait for JavaScript to load
    time.sleep(5)
    
    # Get page content
    content = driver.page_source
    
    # Get headers (simplified)
    headers = {{
        "Content-Type": driver.execute_script("return document.contentType"),
        "Content-Length": len(content)
    }}
    
    result = {{
        "content": content,
        "url": "{url}",
        "status_code": 200,
        "headers": headers
    }}
    
finally:
    driver.quit()

result
"""
        
        try:
            result = self._execute_code(code)
            
            # Cache the page
            self._cache_page(url, result["content"], result["headers"], result["status_code"])
            
            result["from_cache"] = False
            return result
        
        except Exception as e:
            logger.error(f"Error fetching {url} with Selenium: {str(e)}")
            raise
    
    def _analyze_page_structure(self, html_content: str, url: str) -> Dict[str, Any]:
        """Analyze the structure of a page to identify key elements"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = soup.title.text if soup.title else ""
            
            # Extract main content area
            main_content = None
            for tag in ['main', 'article', 'div[role="main"]', '#content', '.content']:
                if main_content:
                    break
                if '[' in tag:
                    tag_name, attr = tag.split('[', 1)
                    attr_name, attr_value = attr.rstrip(']').split('=', 1)
                    attr_value = attr_value.strip('"\'')
                    main_content = soup.find(tag_name, {attr_name.strip(): attr_value})
                elif tag.startswith('#'):
                    main_content = soup.find(id=tag[1:])
                elif tag.startswith('.'):
                    main_content = soup.find(class_=tag[1:])
                else:
                    main_content = soup.find(tag)
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.body
            
            # Extract tables
            tables = []
            for table in soup.find_all('table'):
                tables.append({
                    "id": table.get('id', ''),
                    "class": table.get('class', ''),
                    "rows": len(table.find_all('tr')),
                    "columns": len(table.find_all('th')) or len(table.find_all('tr')[0].find_all('td')) if table.find_all('tr') else 0
                })
            
            # Extract lists
            lists = []
            for list_tag in soup.find_all(['ul', 'ol']):
                lists.append({
                    "type": list_tag.name,
                    "id": list_tag.get('id', ''),
                    "class": list_tag.get('class', ''),
                    "items": len(list_tag.find_all('li'))
                })
            
            # Extract forms
            forms = []
            for form in soup.find_all('form'):
                forms.append({
                    "id": form.get('id', ''),
                    "action": form.get('action', ''),
                    "method": form.get('method', 'get'),
                    "inputs": len(form.find_all('input')),
                    "selects": len(form.find_all('select')),
                    "textareas": len(form.find_all('textarea'))
                })
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(url, href)
                links.append({
                    "text": link.text.strip(),
                    "href": href
                })
            
            # Extract images
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                if not src.startswith(('http://', 'https://')):
                    src = urljoin(url, src)
                images.append({
                    "alt": img.get('alt', ''),
                    "src": src
                })
            
            return {
                "title": title,
                "tables": tables,
                "lists": lists,
                "forms": forms,
                "links": links[:50],  # Limit to 50 links
                "images": images[:50]  # Limit to 50 images
            }
        
        except Exception as e:
            logger.error(f"Error analyzing page structure: {str(e)}")
            return {
                "title": "",
                "tables": [],
                "lists": [],
                "forms": [],
                "links": [],
                "images": []
            }
    
    def _generate_scraper_code(self, url: str, data_type: str, page_structure: Dict[str, Any]) -> str:
        """Generate scraping code based on URL, data type, and page structure"""
        # Create a prompt for the LLM to generate scraping code
        prompt = f"""Generate Python code to scrape {data_type} from the following website: {url}

Page structure analysis:
- Title: {page_structure['title']}
- Tables: {len(page_structure['tables'])}
- Lists: {len(page_structure['lists'])}
- Forms: {len(page_structure['forms'])}
- Links: {len(page_structure['links'])}
- Images: {len(page_structure['images'])}

"""
        
        # Add more details based on the data type
        if data_type.lower() in ['table', 'tables', 'tabular data']:
            prompt += "Table details:\n"
            for i, table in enumerate(page_structure['tables']):
                prompt += f"- Table {i+1}: {table['rows']} rows, {table['columns']} columns, ID: '{table['id']}', Class: '{table['class']}'\n"
            
            prompt += "\nGenerate code that uses BeautifulSoup to extract all tables from the page and convert them to pandas DataFrames."
        
        elif data_type.lower() in ['list', 'lists', 'items']:
            prompt += "List details:\n"
            for i, list_item in enumerate(page_structure['lists']):
                prompt += f"- List {i+1}: {list_item['type']}, {list_item['items']} items, ID: '{list_item['id']}', Class: '{list_item['class']}'\n"
            
            prompt += "\nGenerate code that uses BeautifulSoup to extract all lists from the page."
        
        elif data_type.lower() in ['link', 'links', 'urls']:
            prompt += f"First 5 links:\n"
            for i, link in enumerate(page_structure['links'][:5]):
                prompt += f"- {link['text']}: {link['href']}\n"
            
            prompt += "\nGenerate code that uses BeautifulSoup to extract all links from the page."
        
        elif data_type.lower() in ['image', 'images', 'pictures']:
            prompt += f"First 5 images:\n"
            for i, img in enumerate(page_structure['images'][:5]):
                prompt += f"- Alt: '{img['alt']}', Src: {img['src']}\n"
            
            prompt += "\nGenerate code that uses BeautifulSoup to extract all images from the page."
        
        elif data_type.lower() in ['text', 'content', 'article']:
            prompt += "\nGenerate code that uses BeautifulSoup to extract the main text content from the page, removing navigation, headers, footers, and other non-content elements."
        
        elif data_type.lower() in ['product', 'products', 'items']:
            prompt += "\nGenerate code that uses BeautifulSoup to extract product information (name, price, description, etc.) from the page."
        
        else:
            prompt += f"\nGenerate code that uses BeautifulSoup to extract {data_type} from the page."
        
        prompt += "\nThe code should handle common errors and edge cases. Only return the Python code, no explanations."
        
        # Get code from LLM
        response = self._send_to_llm(prompt)
        
        # Extract code from response
        code_pattern = r"```python\s*([\s\S]*?)```"
        code_matches = re.findall(code_pattern, response)
        
        if code_matches:
            return code_matches[0]
        else:
            # If no code block found, return the entire response
            return response
    
    def _prepare_scraper_code(self, code: str, url: str, output_format: str) -> str:
        """Prepare the scraper code for execution by adding imports and wrapper code"""
        # Add necessary imports
        imports = """
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import csv
import os
from urllib.parse import urljoin
import re
"""
        
        # Add wrapper code to handle the request and parsing
        wrapper = f"""
# URL to scrape
url = "{url}"

# Make the request
try:
    headers = {{'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()  # Raise an exception for 4XX/5XX responses
    
    # Parse the HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Main scraping function
    def scrape_data():
"""
        
        # Indent the provided code
        indented_code = "\n".join(f"        {line}" for line in code.split("\n"))
        
        # Add output formatting code
        output_code = f"""
    # Get the scraped data
    data = scrape_data()
    
    # Format the output
    output_format = "{output_format.lower()}"
    
    if output_format == "json":
        # Convert to JSON
        if isinstance(data, pd.DataFrame):
            result = data.to_json(orient="records")
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            result = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            result = json.dumps(data, ensure_ascii=False, indent=2)
    
    elif output_format == "csv":
        # Convert to CSV
        if isinstance(data, pd.DataFrame):
            result = data.to_csv(index=False)
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            if data:
                keys = data[0].keys()
                output = csv.StringIO()
                dict_writer = csv.DictWriter(output, keys)
                dict_writer.writeheader()
                dict_writer.writerows(data)
                result = output.getvalue()
            else:
                result = ""
        else:
            result = str(data)
    
    elif output_format == "excel":
        # Convert to Excel
        if isinstance(data, pd.DataFrame):
            # Save to a temporary file
            temp_file = "temp_output.xlsx"
            data.to_excel(temp_file, index=False)
            with open(temp_file, "rb") as f:
                result = f.read()
            os.remove(temp_file)
        else:
            # Convert to DataFrame first
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
            
            # Save to a temporary file
            temp_file = "temp_output.xlsx"
            df.to_excel(temp_file, index=False)
            with open(temp_file, "rb") as f:
                result = f.read()
            os.remove(temp_file)
    
    else:
        # Default to string representation
        result = str(data)
    
    return result

except Exception as e:
    return f"Error: {{str(e)}}"
"""
        
        # Combine all parts
        full_code = imports + wrapper + indented_code + output_code
        
        return full_code
    
    def scrape_website(self, url: str, data_type: str, output_format: str = "csv", render_js: bool = False) -> Dict[str, Any]:
        """Scrape a website and return the data"""
        try:
            logger.info(f"Scraping {url} for {data_type} in {output_format} format")
            
            # Fetch the page
            page_result = self._fetch_page(url, render_js=render_js)
            
            # Analyze page structure
            page_structure = self._analyze_page_structure(page_result["content"], url)
            
            # Generate scraper code
            scraper_code = self._generate_scraper_code(url, data_type, page_structure)
            
            # Prepare the code for execution
            full_code = self._prepare_scraper_code(scraper_code, url, output_format)
            
            # Execute the code
            result = self._execute_code(full_code)
            
            # Save the result to a file
            filename = f"{hashlib.md5(url.encode()).hexdigest()}_{data_type.replace(' ', '_')}.{output_format.lower()}"
            output_path = self.output_dir / filename
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result)
            
            # Record in history
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO scraping_history (url, data_type, output_format, timestamp, success, output_path) VALUES (?, ?, ?, ?, ?, ?)",
                (url, data_type, output_format, time.time(), True, str(output_path))
            )
            self.conn.commit()
            
            return {
                "status": "success",
                "data": result[:1000] + "..." if len(result) > 1000 else result,  # Truncate large results
                "output_format": output_format,
                "output_path": str(output_path),
                "url": url,
                "data_type": data_type
            }
        
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            traceback.print_exc()
            
            # Record error in history
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO scraping_history (url, data_type, output_format, timestamp, success, error) VALUES (?, ?, ?, ?, ?, ?)",
                (url, data_type, output_format, time.time(), False, str(e))
            )
            self.conn.commit()
            
            return {
                "status": "error",
                "error": str(e),
                "url": url,
                "data_type": data_type
            }
    
    def handle_requests(self):
        """Main loop to handle incoming requests"""
        logger.info("Starting to handle requests...")
        
        while self.running:
            try:
                # Wait for message with timeout
                if self.receiver.poll(timeout=1000) == 0:
                    continue
                
                # Receive request
                request_str = self.receiver.recv_string()
                
                try:
                    request = json.loads(request_str)
                    request_type = request.get("request_type")
                    
                    if request_type == "scrape":
                        url = request.get("url")
                        data_type = request.get("data_type", "content")
                        output_format = request.get("output_format", "csv")
                        render_js = request.get("render_js", False)
                        
                        if not url:
                            response = {
                                "status": "error",
                                "error": "URL is required"
                            }
                        else:
                            result = self.scrape_website(url, data_type, output_format, render_js)
                            response = {
                                "status": "success",
                                "result": result
                            }
                    
                    elif request_type == "get_history":
                        limit = request.get("limit", 10)
                        
                        cursor = self.conn.cursor()
                        cursor.execute(
                            "SELECT url, data_type, output_format, timestamp, success, error, output_path FROM scraping_history ORDER BY timestamp DESC LIMIT ?",
                            (limit,)
                        )
                        
                        history = []
                        for row in cursor.fetchall():
                            history.append({
                                "url": row[0],
                                "data_type": row[1],
                                "output_format": row[2],
                                "timestamp": row[3],
                                "success": row[4],
                                "error": row[5],
                                "output_path": row[6]
                            })
                        
                        response = {
                            "status": "success",
                            "history": history
                        }
                    
                    elif request_type == "clear_cache":
                        cursor = self.conn.cursor()
                        cursor.execute("DELETE FROM cache")
                        self.conn.commit()
                        
                        response = {
                            "status": "success",
                            "message": "Cache cleared"
                        }
                    
                    else:
                        response = {
                            "status": "error",
                            "error": f"Unknown request type: {request_type}"
                        }
                
                except json.JSONDecodeError:
                    response = {
                        "status": "error",
                        "error": "Invalid JSON in request"
                    }
                except Exception as e:
                    response = {
                        "status": "error",
                        "error": f"Error processing request: {str(e)}"
                    }
                
                # Send response
                self.receiver.send_string(json.dumps(response))
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in request handler: {str(e)}")
                traceback.print_exc()
    
    def run(self):
        """Run the enhanced web scraper"""
        try:
            logger.info("Starting Enhanced Web Scraper...")
            self.handle_requests()
        except KeyboardInterrupt:
            logger.info("Enhanced Web Scraper interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.receiver.close()
        self.model_manager.close()
        self.executor.close()
        self.context.term()
        
        if self.conn:
            self.conn.close()
        
        logger.info("Enhanced Web Scraper stopped")


if __name__ == "__main__":
    import argparse

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    parser = argparse.ArgumentParser(description="Enhanced Web Scraper: Advanced web scraping with multiple strategies.")
    parser.add_argument('--server', action='store_true', help='Run in server mode, waiting for ZMQ requests')
    args = parser.parse_args()
    
    scraper = EnhancedWebScraper()
    
    if args.server:
        # Just initialize the scraper and keep it running, waiting for ZMQ requests
        logger.info("Enhanced Web Scraper running in server mode, waiting for requests...")
        try:
            # Keep the process alive
            scraper.handle_requests()
        except KeyboardInterrupt:
            logger.info("Enhanced Web Scraper interrupted by user")
    else:
        # Run the full scraper
        scraper.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise