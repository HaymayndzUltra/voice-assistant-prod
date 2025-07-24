"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
Web Scraper Agent
- Handles web scraping and data extraction
- Generates and executes scraping code
- Supports multiple output formats (CSV, Excel, JSON)
- Integrates with the AutoGen framework
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

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from pc2_code.config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / str(PathManager.get_logs_dir() / "web_scraper_agent.log")
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WebScraperAgent")

# Get ZMQ ports from config
WEB_SCRAPER_PORT = config.get('zmq.web_scraper_port', 5602)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)
MODEL_MANAGER_HOST = config.get('zmq.model_manager_host', '192.168.1.1')  # Main PC's IP address
AUTOGEN_FRAMEWORK_PORT = config.get('zmq.autogen_framework_port', 5600)
EXECUTOR_PORT = config.get('zmq.executor_port', 5603)

class WebScraperAgent:
    """Agent for web scraping and data extraction"""
    def __init__(self):
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.bind(f"tcp://0.0.0.0:{WEB_SCRAPER_PORT}")
        logger.info(f"Web Scraper Agent bound to port {WEB_SCRAPER_PORT}")
        
        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.connect(f"tcp://{MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}")
        logger.info(f"Connected to Model Manager on {MODEL_MANAGER_HOST}:{MODEL_MANAGER_PORT}")
        
        # Socket to communicate with autogen framework
        self.framework = self.context.socket(zmq.REQ)
        self.framework.connect(f"tcp://localhost:{AUTOGEN_FRAMEWORK_PORT}")
        logger.info(f"Connected to AutoGen Framework on port {AUTOGEN_FRAMEWORK_PORT}")
        
        # Socket to communicate with executor agent
        self.executor = self.context.socket(zmq.REQ)
        self.executor.connect(f"tcp://localhost:{EXECUTOR_PORT}")
        logger.info(f"Connected to Executor Agent on port {EXECUTOR_PORT}")
        
        # Setup cache directory
        self.cache_dir = Path(config.get('system.cache_dir', 'cache')) / "web_scraper"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup output directory
        self.output_dir = Path(config.get('system.output_dir', 'output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Running flag
        self.running = True
        
        # Import necessary libraries
        self._ensure_dependencies()
        
        logger.info("Web Scraper Agent initialized")
    
    def _ensure_dependencies(self):
        """Ensure all required dependencies are installed"""
        try:
            import requests
    except ImportError as e:
        print(f"Import error: {e}")
            import bs4
            import pandas as pd
            import selenium
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
            
            if poller.poll(60000):  # 60 second timeout (scraping can take time)
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
    
    def _generate_scraper_code(self, url: str, data_type: str, output_format: str = "csv") -> str:
        """Generate scraping code based on URL and data type"""
        logger.info(f"Generating scraper code for URL: {url}, data type: {data_type}, output format: {output_format}")
        
        # System prompt for the code generation LLM
        system_prompt = """You are a web scraping code generator. Your task is to generate Python code that scrapes data from a given URL based on the specified data type. The code should:

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

The output format should be {output_format}.

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
"""
        
        # Add selenium imports if selenium is used in the code
        if "selenium" in code:
            imports += """
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from common.env_helpers import get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
"""
        
        # Add wrapper code to call the scrape_data function and save the results
        wrapper = f"""
def main(url="{url}", output_format="{output_format}"):
    try:
        # Call the scrape_data function
        df = scrape_data(url)
        
        # Return the data as a dictionary
        result = {{
            "status": "success",
            "data": df.to_dict(orient="records"),
            "columns": df.columns.tolist(),
            "row_count": len(df)
        }}
        
        return result
    except Exception as e:
        return {{"status": "error", "error": str(e)}}

# Call the main function if this script is run directly
if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
"""
        
        # Combine the code
        full_code = imports + "\n" + code + "\n" + wrapper
        
        return full_code
    
    def scrape_website(self, url: str, data_type: str, output_format: str = "csv") -> Dict[str, Any]:
        """Scrape a website and return the data"""
        logger.info(f"Scraping website: {url}, data type: {data_type}, output format: {output_format}")
        
        try:
            # Generate scraper code
            code = self._generate_scraper_code(url, data_type, output_format)
            
            # Prepare code for execution
            full_code = self._prepare_scraper_code(code, url, output_format)
            
            # Execute the code
            result = self._execute_code(full_code)
            
            if result.get("status") == "success":
                # Process the data
                data = result.get("data", [])
                columns = result.get("columns", [])
                row_count = result.get("row_count", 0)
                
                logger.info(f"Scraped {row_count} rows of data")
                
                # Create a DataFrame
                df = pd.DataFrame(data, columns=columns)
                
                # Save the data to a file
                timestamp = int(time.time())
                filename = f"scraped_{data_type}_{timestamp}.{output_format}"
                file_path = self.output_dir / filename
                
                if output_format == "csv":
                    df.to_csv(file_path, index=False)
                elif output_format == "excel":
                    df.to_excel(file_path, index=False)
                elif output_format == "json":
                    df.to_json(file_path, orient="records", indent=2)
                
                logger.info(f"Saved scraped data to {file_path}")
                
                return {
                    "status": "success",
                    "data": data,
                    "columns": columns,
                    "row_count": row_count,
                    "file_path": str(file_path)
                }
            else:
                logger.error(f"Error executing scraper code: {result.get('error', 'Unknown error')}")
                raise Exception(result.get("error", "Unknown error"))
        
        except Exception as e:
            logger.error(f"Error scraping website: {str(e)}")
            raise
    
    def handle_requests(self):
        """Main loop to handle incoming requests"""
        logger.info("Starting request handler")
        
        while self.running:
            try:
                # Set timeout to allow checking running flag
                poller = zmq.Poller()
                poller.register(self.receiver, zmq.POLLIN)
                
                if poller.poll(1000):  # 1 second timeout
                    # Receive request
                    request_str = self.receiver.recv_string()
                    
                    try:
                        request = json.loads(request_str)
                        request_type = request.get("request_type")
                        
                        logger.info(f"Received request: {request_type}")
                        
                        if request_type == "scrape":
                            # Handle scraping request
                            url = request.get("url")
                            data_type = request.get("data_type")
                            output_format = request.get("output_format", "csv")
                            
                            if not url or not data_type:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameters: url and data_type"
                                }
                            else:
                                try:
                                    result = self.scrape_website(url, data_type, output_format)
                                    response = result
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error scraping website: {str(e)}"
                                    }
                        
                        elif request_type == "generate_code":
                            # Handle code generation request
                            url = request.get("url")
                            data_type = request.get("data_type")
                            output_format = request.get("output_format", "csv")
                            
                            if not url or not data_type:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameters: url and data_type"
                                }
                            else:
                                try:
                                    code = self._generate_scraper_code(url, data_type, output_format)
                                    full_code = self._prepare_scraper_code(code, url, output_format)
                                    
                                    response = {
                                        "status": "success",
                                        "code": full_code
                                    }
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error generating scraper code: {str(e)}"
                                    }
                        
                        elif request_type == "task_step":
                            # Handle task step request from AutoGen framework
                            content = request.get("content", {})
                            step = content.get("step", {})
                            
                            if not step:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameter: step"
                                }
                            else:
                                try:
                                    # Extract parameters from step
                                    description = step.get("description", "")
                                    parameters = step.get("parameters", {})
                                    
                                    # Extract specific parameters for scraping
                                    url = parameters.get("url", "")
                                    data_type = parameters.get("data_type", "")
                                    output_format = parameters.get("output_format", "csv")
                                    
                                    if not url or not data_type:
                                        response = {
                                            "status": "error",
                                            "error": "Missing required parameters: url and data_type"
                                        }
                                    else:
                                        result = self.scrape_website(url, data_type, output_format)
                                        response = {
                                            "status": "success",
                                            "result": result
                                        }
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error executing task step: {str(e)}"
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
        """Run the web scraper agent"""
        try:
            # Register with AutoGen framework
            self.framework.send_string(json.dumps({
                "request_type": "register_agent",
                "agent_id": "web_scraper",
                "endpoint": f"tcp://localhost:{WEB_SCRAPER_PORT}",
                "capabilities": ["web_scraping", "data_extraction", "web_automation"]
            }))
            
            # Wait for response
            response_str = self.framework.recv_string()
            response = json.loads(response_str)
            
            if response["status"] != "success":
                logger.error(f"Error registering with AutoGen framework: {response.get('error', 'Unknown error')}")
            else:
                logger.info("Registered with AutoGen framework")
            
            # Main request handling loop
            self.handle_requests()
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        # Unregister from AutoGen framework
        try:
            self.framework.send_string(json.dumps({
                "request_type": "unregister_agent",
                "agent_id": "web_scraper"
            }))
            
            # Wait for response
            response_str = self.framework.recv_string()
        except:
            pass
        
        self.receiver.close()
        self.model_manager.close()
        self.framework.close()
        self.executor.close()
        self.context.term()
        
        logger.info("Web Scraper Agent stopped")


# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting Web Scraper Agent...")
        agent = WebScraperAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Web Scraper Agent interrupted by user")
    except Exception as e:
        logger.error(f"Error running Web Scraper Agent: {str(e)}")
        traceback.print_exc()
