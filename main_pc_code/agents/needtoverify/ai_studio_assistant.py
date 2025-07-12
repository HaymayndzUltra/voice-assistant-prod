from main_pc_code.src.core.base_agent import BaseAgent
"""
AI Studio Assistant
------------------
Specialized agent that interfaces with Google AI Studio to:
1. Navigate to AI Studio
2. Set temperature and other parameters
3. Input prompts and get AI responses
4. Process responses and feed them to other systems
5. Make decisions based on the outcomes

This agent uses Selenium for browser automation and integrates with the voice assistant system.
"""

import zmq
import json
import time
import logging
import sys
import os
import re
import threading
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
# Use Playwright for more robust browser automation
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.pc2_connections import get_connection_string

# Setup logging
LOG_PATH = join_path("logs", "ai_studio_assistant.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AIStudioAssistant")

# ZMQ port for this agent
AI_STUDIO_ASSISTANT_PORT = 5630
MODEL_MANAGER_PORT = 5556
CODE_GENERATOR_PORT = 5595

class AIStudioAssistant(BaseAgent):
    """
    AI Studio Assistant for interacting with Google AI Studio
    """
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AiStudioAssistant")
        """Initialize the AI Studio assistant"""
        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        logger.info(f"AI Studio Assistant bound to port {zmq_port}")
        
        # Connect to other agents
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            # Try to use PC2 connection if available
            self.model_manager.connect(get_connection_string("model_manager"))
            logger.info("Connected to Model Manager on PC2")
        except (ImportError, ValueError):
            # Fallback to local connection
            self.model_manager.connect(f"tcp://localhost:{MODEL_MANAGER_PORT}")
            logger.info(f"Connected to local Model Manager on port {MODEL_MANAGER_PORT}")
        
        # Connect to code generator
        self.code_generator = self.context.socket(zmq.REQ)
        self.code_generator.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.code_generator.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.code_generator.connect(get_connection_string("code_generator"))
            logger.info("Connected to Code Generator on PC2")
        except (ImportError, ValueError):
            self.code_generator.connect(f"tcp://localhost:{CODE_GENERATOR_PORT}")
            logger.info(f"Connected to local Code Generator on port {CODE_GENERATOR_PORT}")
        
        # Initialize browser
        self.setup_browser(use_user_profile)
        
        # State tracking
        self.current_url = None
        self.last_prompt = None
        self.last_response = None
        self.running = True
        
        logger.info("AI Studio Assistant initialized")
    
    def setup_browser(self, use_user_profile=True):
        """Setup the browser for automation"""
        chrome_options = Options()
        
        # Use existing Chrome user profile for logged-in state
        if use_user_profile:
            try:
                # Get the user's Chrome profile directory
                user_profile_dir = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "Google", "Chrome", "User Data")
                logger.info(f"Using Chrome profile from: {user_profile_dir}")
                
                # Use the default profile
                chrome_options.add_argument(f"--user-data-dir={user_profile_dir}")
                chrome_options.add_argument("--profile-directory=Default")
            except Exception as e:
                logger.warning(f"Could not set up user profile: {e}")
        
        # Other options
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--start-maximized")
        
        # Try to use webdriver_manager if installed
        try:
            from webdriver_manager.chrome import ChromeDriverManager
    except ImportError as e:
        print(f"Import error: {e}")
            service = Service(ChromeDriverManager().install())
            self.browser = webdriver.Chrome(service=service, options=chrome_options)
        except ImportError:
            # Fallback to using system chromedriver
            logger.warning("webdriver_manager not found, using system chromedriver")
            self.browser = webdriver.Chrome(options=chrome_options)
        
        # Set default timeout
        self.browser.implicitly_wait(10)
        self.wait = WebDriverWait(self.browser, 20)
        
        logger.info("Browser set up for automation")
    
    def navigate_to_ai_studio(self):
        """Navigate to Google AI Studio"""
        try:
            logger.info("Navigating to Google AI Studio")
            self.browser.get("https://aistudio.google.com/")
            self.current_url = self.browser.current_url
            
            # Wait for page to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Get page title and URL
            title = self.browser.title
            
            logger.info(f"Successfully navigated to AI Studio: {title}")
            return {
                "status": "success",
                "url": self.current_url,
                "title": title
            }
            
        except Exception as e:
            logger.error(f"Error navigating to AI Studio: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def change_model_settings(self, model_name=None, temperature=None, max_tokens=None):
        """Change model settings in AI Studio"""
        try:
            logger.info("Changing model settings")
            
            # Make sure we're on AI Studio
            if not self.current_url or "aistudio.google.com" not in self.current_url:
                self.navigate_to_ai_studio()
            
            # Change model if specified
            if model_name:
                logger.info(f"Setting model to: {model_name}")
                try:
                    # Click on model dropdown
                    model_dropdown = self.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//span[contains(text(), 'Model')]/following::button[1]")
                    ))
                    model_dropdown.click()
                    time.sleep(1)
                    
                    # Select model from dropdown
                    model_option = self.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, f"//span[contains(text(), '{model_name}')]")
                    ))
                    model_option.click()
                    time.sleep(1)
                    
                    logger.info(f"Model set to {model_name}")
                except (TimeoutException, NoSuchElementException) as e:
                    logger.error(f"Could not set model: {e}")
                    return {"status": "error", "error": f"Could not set model: {str(e)}"}
            
            # Change temperature if specified
            if temperature is not None:
                logger.info(f"Setting temperature to: {temperature}")
                try:
                    # Click settings button first (if not already expanded)
                    try:
                        settings_button = self.browser.find_element(By.XPATH, 
                            "//button[contains(@aria-label, 'settings') or contains(@aria-label, 'Settings')]")
                        settings_button.click()
                        time.sleep(1)
                    except:
                        # Settings might already be expanded
                        pass
                    
                    # Find temperature slider or input
                    temp_input = self.wait.until(EC.presence_of_element_located(
                        (By.XPATH, "//label[contains(text(), 'Temperature')]/following::input[1]")
                    ))
                    
                    # Clear and set new value
                    temp_input.clear()
                    temp_input.send_keys(str(temperature))
                    time.sleep(0.5)
                    
                    logger.info(f"Temperature set to {temperature}")
                except (TimeoutException, NoSuchElementException) as e:
                    logger.error(f"Could not set temperature: {e}")
                    return {"status": "error", "error": f"Could not set temperature: {str(e)}"}
            
            # Change max tokens if specified
            if max_tokens is not None:
                logger.info(f"Setting max tokens to: {max_tokens}")
                try:
                    # Click settings button first (if not already expanded)
                    try:
                        settings_button = self.browser.find_element(By.XPATH, 
                            "//button[contains(@aria-label, 'settings') or contains(@aria-label, 'Settings')]")
                        settings_button.click()
                        time.sleep(1)
                    except:
                        # Settings might already be expanded
                        pass
                    
                    # Find max tokens input
                    tokens_input = self.wait.until(EC.presence_of_element_located(
                        (By.XPATH, "//label[contains(text(), 'Max output tokens') or contains(text(), 'Response length')]/following::input[1]")
                    ))
                    
                    # Clear and set new value
                    tokens_input.clear()
                    tokens_input.send_keys(str(max_tokens))
                    time.sleep(0.5)
                    
                    logger.info(f"Max tokens set to {max_tokens}")
                except (TimeoutException, NoSuchElementException) as e:
                    logger.error(f"Could not set max tokens: {e}")
                    return {"status": "error", "error": f"Could not set max tokens: {str(e)}"}
            
            # Take screenshot of settings for confirmation
            screenshot_path = join_path("logs", "ai_studio_settings.png")
            self.browser.save_screenshot(screenshot_path)
            
            return {
                "status": "success",
                "message": "Model settings updated successfully",
                "screenshot": screenshot_path
            }
            
        except Exception as e:
            logger.error(f"Error changing model settings: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def send_prompt(self, prompt_text):
        """Send a prompt to the AI Studio chat interface and get the response"""
        try:
            logger.info(f"Sending prompt: {prompt_text[:30]}...")
            self.last_prompt = prompt_text
            
            # Make sure we're on AI Studio
            if not self.current_url or "aistudio.google.com" not in self.current_url:
                self.navigate_to_ai_studio()
            
            # Find the prompt input area
            prompt_input = self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//textarea[contains(@placeholder, 'Send a message') or contains(@placeholder, 'Enter your prompt')]")
            ))
            
            # Clear any existing text and send the new prompt
            prompt_input.clear()
            prompt_input.send_keys(prompt_text)
            time.sleep(1)
            
            # Find and click the send button
            send_button = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@aria-label, 'Send message') or contains(@aria-label, 'Send')]")
            ))
            send_button.click()
            
            # Wait for the response (looking for the AI's response message)
            logger.info("Waiting for AI response...")
            try:
                # Wait for a new message to appear
                time.sleep(2)  # Brief initial pause
                
                # Wait until the "thinking" indicator disappears
                try:
                    self.wait.until_not(EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'loading') or contains(@class, 'typing')]")
                    ))
                except:
                    # May not always have a visible loading indicator
                    pass
                
                # Wait a bit more for the response to fully appear
                time.sleep(3)
                
                # Find the most recent response
                response_elements = self.browser.find_elements(By.XPATH, 
                    "//div[contains(@class, 'message') or contains(@class, 'response')]//p")
                
                if response_elements:
                    # Collect all paragraphs from the response
                    response_text = "\n".join([elem.text for elem in response_elements[-5:]])
                else:
                    response_text = "Could not capture response text"
                
                # Store the response
                self.last_response = response_text
                
                # Take screenshot of the conversation
                screenshot_path = join_path("logs", "ai_studio_conversation.png")
                self.browser.save_screenshot(screenshot_path)
                
                logger.info(f"Received response. Screenshot saved to {screenshot_path}")
                
                return {
                    "status": "success",
                    "prompt": prompt_text,
                    "response": response_text,
                    "screenshot": screenshot_path
                }
                
            except TimeoutException:
                screenshot_path = join_path("logs", "ai_studio_timeout.png")
                self.browser.save_screenshot(screenshot_path)
                return {
                    "status": "error",
                    "error": "Timeout waiting for response",
                    "screenshot": screenshot_path
                }
            
        except Exception as e:
            logger.error(f"Error sending prompt: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_code_from_response(self, code_to_run=None, language="python"):
        """Extract code from response and run it using the code generator agent"""
        try:
            logger.info("Extracting and running code from response")
            
            # Get code from last response if not provided
            if not code_to_run and self.last_response:
                # Extract code blocks from markdown-style response
                code_blocks = re.findall(r'```(?:' + language + r'|)\s*([\s\S]*?)```', self.last_response)
                
                if not code_blocks:
                    # Try alternate format
                    code_blocks = re.findall(r'<pre><code>(?:' + language + r'|)\s*([\s\S]*?)</code></pre>', self.last_response)
                
                if code_blocks:
                    code_to_run = code_blocks[0].strip()
                else:
                    logger.error("No code blocks found in response")
                    return {
                        "status": "error",
                        "error": "No code blocks found in response"
                    }
            
            # Verify we have code to run
            if not code_to_run:
                return {
                    "status": "error",
                    "error": "No code to run"
                }
            
            # Prepare request for code generator
            request = {
                "action": "execute_code",
                "code": code_to_run,
                "language": language
            }
            
            # Send to code generator
            logger.info(f"Sending code to code generator agent")
            self.code_generator.send_string(json.dumps(request))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.code_generator, zmq.POLLIN)
            
            if poller.poll(60000):  # 60 second timeout
                response_str = self.code_generator.recv_string()
                response = json.loads(response_str)
                
                logger.info(f"Received code execution response")
                
                # Take screenshot of the execution result
                screenshot_path = join_path("logs", "code_execution_result.png")
                self.browser.save_screenshot(screenshot_path)
                
                return {
                    "status": response.get("status", "unknown"),
                    "result": response.get("result", "No result"),
                    "output": response.get("output", "No output"),
                    "screenshot": screenshot_path
                }
            else:
                logger.error("Timeout waiting for code execution")
                return {
                    "status": "error",
                    "error": "Timeout waiting for code execution"
                }
            
        except Exception as e:
            logger.error(f"Error running code from response: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def analyze_results(self, execution_result):
        """Analyze the results of code execution"""
        try:
            logger.info("Analyzing execution results")
            
            # Extract information from execution result
            status = execution_result.get("status", "unknown")
            result = execution_result.get("result", "")
            output = execution_result.get("output", "")
            
            # Prepare prompt for analysis
            system_prompt = """
            You are an expert code analyst. Analyze the results of code execution and provide clear, concise feedback.
            Focus on:
            1. Whether the code executed successfully
            2. Key outputs or results
            3. Any errors or issues
            4. Possible improvements
            Keep your analysis factual and helpful.
            """
            
            prompt = f"""
            ORIGINAL PROMPT TO AI STUDIO:
            {self.last_prompt or "N/A"}
            
            AI STUDIO RESPONSE (including code):
            {self.last_response or "N/A"}
            
            CODE EXECUTION STATUS: {status}
            
            CODE EXECUTION RESULT:
            {result}
            
            CODE EXECUTION OUTPUT:
            {output}
            
            Please analyze these results and provide a clear explanation of what happened.
            """
            
            # Send to model manager for analysis
            logger.info("Sending results to model for analysis")
            request = {
                "request_type": "generate",
                "model": "phi3",
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": 0.3
            }
            
            self.model_manager.send_string(json.dumps(request))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.model_manager, zmq.POLLIN)
            
            if poller.poll(30000):  # 30 second timeout
                response_str = self.model_manager.recv_string()
                response = json.loads(response_str)
                
                if response["status"] == "success":
                    analysis = response["text"]
                    logger.info("Analysis complete")
                    
                    return {
                        "status": "success",
                        "analysis": analysis,
                        "execution_status": status
                    }
                else:
                    logger.error(f"Error from model manager: {response.get('error', 'Unknown error')}")
                    return {
                        "status": "error",
                        "error": response.get("error", "Unknown error")
                    }
            else:
                logger.error("Timeout waiting for analysis")
                return {
                    "status": "error",
                    "error": "Timeout waiting for analysis"
                }
            
        except Exception as e:
            logger.error(f"Error analyzing results: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def handle_requests(self):
        """Main request handling loop"""
        while self.running:
            try:
                # Receive request
                request_str = self.socket.recv_string()
                request = json.loads(request_str)
                
                logger.info(f"Received request: {request.get('action', 'unknown')}")
                
                # Process request
                if request["action"] == "navigate":
                    response = self.navigate_to_ai_studio()
                
                elif request["action"] == "change_settings":
                    response = self.change_model_settings(
                        model_name=request.get("model_name"),
                        temperature=request.get("temperature"),
                        max_tokens=request.get("max_tokens")
                    )
                
                elif request["action"] == "send_prompt":
                    response = self.send_prompt(request["prompt"])
                
                elif request["action"] == "run_code":
                    response = self.run_code_from_response(
                        code_to_run=request.get("code"),
                        language=request.get("language", "python")
                    )
                
                elif request["action"] == "analyze_results":
                    response = self.analyze_results(request["execution_result"])
                
                elif request["action"] == "full_workflow":
                    # Complete workflow: navigate > set settings > send prompt > run code > analyze
                    
                    # Step 1: Navigate to AI Studio
                    nav_response = self.navigate_to_ai_studio()
                    if nav_response["status"] != "success":
                        response = nav_response
                    else:
                        # Step 2: Change settings if specified
                        if any(key in request for key in ["model_name", "temperature", "max_tokens"]):
                            settings_response = self.change_model_settings(
                                model_name=request.get("model_name"),
                                temperature=request.get("temperature"),
                                max_tokens=request.get("max_tokens")
                            )
                            if settings_response["status"] != "success":
                                response = settings_response
                        
                        # Step 3: Send prompt
                        if "prompt" in request:
                            prompt_response = self.send_prompt(request["prompt"])
                            if prompt_response["status"] != "success":
                                response = prompt_response
                            else:
                                # Step 4: Run code
                                code_response = self.run_code_from_response(
                                    language=request.get("language", "python")
                                )
                                if code_response["status"] == "error":
                                    response = code_response
                                else:
                                    # Step 5: Analyze results
                                    response = self.analyze_results(code_response)
                                    # Add the whole workflow result
                                    response["workflow"] = {
                                        "navigation": nav_response,
                                        "prompt_response": prompt_response,
                                        "code_execution": code_response
                                    }
                        else:
                            response = {
                                "status": "error",
                                "error": "No prompt specified for full workflow"
                            }
                
                else:
                    response = {"status": "error", "error": "Unknown action"}
                
                # Send response
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logger.error(f"Error handling request: {e}")
                
                # Try to send error response
                try:
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "error": str(e)
                    }))
                except:
                    pass  # Socket might be in bad state
    
    def run(self):
        """Run the assistant"""
        logger.info("Starting AI Studio Assistant")
        try:
            self.handle_requests()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.running = False
            self.browser.quit()
            logger.info("Shutting down AI Studio Assistant")

if __name__ == "__main__":
    # Check dependencies
    try:
        import selenium
    except ImportError:
        logger.error("Selenium not installed. Installing now...")
        import subprocess
        subprocess.call([sys.executable, "-m", "pip", "install", "selenium"])
        import selenium
    
    try:
        import webdriver_manager
    except ImportError:
        logger.warning("webdriver_manager not installed. Trying to install...")
        import subprocess
        try:
            subprocess.call([sys.executable, "-m", "pip", "install", "webdriver-manager"])
            import webdriver_manager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
        except:
            logger.warning("Failed to install webdriver_manager, will use system chromedriver")
    
    # Start the assistant
    assistant = AIStudioAssistant(use_user_profile=True)  # Use user profile for authentication
    assistant.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise