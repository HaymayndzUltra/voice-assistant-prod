from main_pc_code.src.core.base_agent import BaseAgent
#!/usr/bin/env python3
"""
Unified Web Agent
----------------
Handles all web-related tasks including:
- Web search
- Web scraping
- Web navigation
- Web content extraction
- Web automation
"""

import sys
import logging
import json
import time
from pathlib import Path
from typing import Dict, Optional, List
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import psutil
from datetime import datetime

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class UnifiedWebAgent(BaseAgent):
    """
    Unified Web Agent that handles all web-related tasks
    """
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="UnifiedWebAgentMainPc")
        """
        Initialize the web agent with configuration
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger("UnifiedWebAgent")
        self._setup_logging()
        self._init_selenium()
        
    def _setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handler
        file_handler = logging.FileHandler(
            log_dir / str(PathManager.get_logs_dir() / "web_agent.log"),
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
        
    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Selenium: {e}")
            raise
            
    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Perform web search and return results
        Args:
            query (str): Search query
            num_results (int): Number of results to return
        Returns:
            List of search results with title, url, and snippet
        """
        try:
            # Use DuckDuckGo API for privacy-focused search
            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(url)
            data = response.json()
            
            results = []
            for result in data.get('Results', [])[:num_results]:
                results.append({
                    'title': result.get('Text', ''),
                    'url': result.get('FirstURL', ''),
                    'snippet': result.get('Text', '')
                })
                
            self.logger.info(f"Web search completed for query: {query}")
            return results
        except Exception as e:
            self.logger.error(f"Web search failed: {e}")
            return []
            
    def scrape_webpage(self, url: str) -> Dict:
        """
        Scrape content from a webpage
        Args:
            url (str): URL to scrape
        Returns:
            Dictionary containing scraped content
        """
        try:
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Get page content
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract main content
            content = {
                'title': soup.title.string if soup.title else '',
                'text': soup.get_text(separator='\n', strip=True),
                'links': [a.get('href') for a in soup.find_all('a', href=True)],
                'images': [img.get('src') for img in soup.find_all('img', src=True)]
            }
            
            self.logger.info(f"Webpage scraped successfully: {url}")
            return content
        except Exception as e:
            self.logger.error(f"Web scraping failed: {e}")
            return {}
            
    def navigate_web(self, url: str) -> bool:
        """
        Navigate to a webpage
        Args:
            url (str): URL to navigate to
        Returns:
            bool: True if navigation successful
        """
        try:
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            self.logger.info(f"Navigated to: {url}")
            return True
        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            return False
            
    def extract_content(self, selector: str) -> Optional[str]:
        """
        Extract content from current page using CSS selector
        Args:
            selector (str): CSS selector
        Returns:
            Extracted content or None if not found
        """
        try:
            element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element.text
        except Exception as e:
            self.logger.error(f"Content extraction failed: {e}")
            return None
            
    def automate_web_task(self, task: Dict) -> bool:
        """
        Perform automated web task
        Args:
            task (dict): Task configuration with steps
        Returns:
            bool: True if task completed successfully
        """
        try:
            for step in task.get('steps', []):
                action = step.get('action')
                selector = step.get('selector')
                value = step.get('value')
                
                if action == 'click':
                    element = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    element.click()
                elif action == 'type':
                    element = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    element.clear()
                    element.send_keys(value)
                elif action == 'wait':
                    time.sleep(value)
                    
            self.logger.info("Web automation task completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Web automation failed: {e}")
            return False
            
    def close(self):
        """Clean up resources"""
        try:
            self.driver.quit()
            self.logger.info("Web agent resources cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")


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
    # Example usage
    agent = UnifiedWebAgent()
    
    # Search example
    results = agent.search_web("Python web scraping")
    print("Search results:", json.dumps(results, indent=2))
    
    # Scraping example
    content = agent.scrape_webpage("https://example.com")
    print("Scraped content:", json.dumps(content, indent=2))
    
    # Automation example
    task = {
        'steps': [
            {'action': 'navigate', 'url': 'https://example.com'},
            {'action': 'wait', 'value': 2},
            {'action': 'click', 'selector': 'a.more-info'}
        ]
    }
    success = agent.automate_web_task(task)
    print("Task success:", success)
    
    agent.close()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise