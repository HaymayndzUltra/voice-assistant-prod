from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Autonomous Web Assistant
------------------------
This agent has autonomous decision-making capabilities to:
1. Provide real-time references during conversations
2. Navigate to websites and perform actions
3. Extract and summarize information on command
4. Make decisions about what information is relevant

It integrates with the voice assistant system but has autonomy
to fetch information proactively based on conversation context.
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
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import base64
from bs4 import BeautifulSoup
import urllib.parse


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.pc2_connections import get_connection_string
from common.env_helpers import get_env

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Setup logging
LOG_PATH = PathManager.join_path("logs", str(PathManager.get_logs_dir() / "autonomous_web_assistant.log"))
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logger = configure_logging(__name__)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AutonomousWebAssistant")

# ZMQ port for this agent
AUTONOMOUS_WEB_ASSISTANT_PORT = 5620
CONTEXT_SUMMARIZER_PORT = 5610
MODEL_MANAGER_PORT = 5556
MEMORY_AGENT_PORT = 5596

# Browser automation throttling to avoid rate limits
MIN_DELAY_BETWEEN_REQUESTS = 2  # seconds

class AutonomousWebAssistant(BaseAgent):
    """
    Autonomous Web Assistant for proactive information retrieval and web navigation
    """
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutonomousWebAssistant")
        """Initialize the autonomous web assistant"""
        # ZMQ setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        
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
            
        # Similarly for context summarizer
        self.context_summarizer = self.context.socket(zmq.REQ)
        self.context_summarizer.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.context_summarizer.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.context_summarizer.connect(get_connection_string("context_summarizer"))
            logger.info("Connected to Context Summarizer on PC2")
        except (ImportError, ValueError):
            self.context_summarizer.connect(f"tcp://localhost:{CONTEXT_SUMMARIZER_PORT}")
            logger.info(f"Connected to local Context Summarizer on port {CONTEXT_SUMMARIZER_PORT}")
        
        # Similarly for memory agent
        self.memory_agent = self.context.socket(zmq.REQ)
        self.memory_agent.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_agent.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.memory_agent.connect(get_connection_string("contextual_memory"))
            logger.info("Connected to Memory Agent on PC2")
        except (ImportError, ValueError):
            self.memory_agent.connect(f"tcp://localhost:{MEMORY_AGENT_PORT}")
            logger.info(f"Connected to local Memory Agent on port {MEMORY_AGENT_PORT}")
        
        # Browser session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # State tracking
        self.current_url = None
        self.page_content = None
        self.last_request_time = 0
        self.conversation_context = []
        self.cached_results = {}  # Simple cache for results
        self.running = True
        
        # Decision-making parameters
        self.proactive_mode = True  # Whether to proactively fetch information
        self.confidence_threshold = 0.7  # Threshold for making autonomous decisions
        
        logger.info("Autonomous Web Assistant initialized")
    
    def _send_to_llm(self, prompt: str, system_prompt: Optional[str] = None, model: str = "phi3") -> str:
        """Send a request to the LLM through the model manager"""
        try:
            # Prepare request
            request = {
                "request_type": "generate",
                "model": model,
                "prompt": prompt,
                "temperature": 0.3  # Lower temperature for more consistent results
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
    
    def _throttle_requests(self):
        """Throttle requests to avoid rate limiting"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < MIN_DELAY_BETWEEN_REQUESTS:
            sleep_time = MIN_DELAY_BETWEEN_REQUESTS - elapsed
            logger.debug(f"Throttling: Sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL and return the page content"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        self._throttle_requests()
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.current_url = url
            self.page_content = response.text
            
            # Parse content
            soup = BeautifulSoup(self.page_content, 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else "No title"
            
            # Extract main content (heuristic approach)
            main_content = ""
            main_tags = soup.find_all(['article', 'main', 'div', 'section'], class_=lambda c: c and ('content' in c.lower() or 'main' in c.lower()))
            if main_tags:
                # Use the largest content block
                main_tag = max(main_tags, key=lambda tag: len(tag.get_text()))
                main_content = main_tag.get_text(separator='\n', strip=True)
            else:
                # Fallback: just get the body text
                main_content = soup.body.get_text(separator='\n', strip=True) if soup.body else ""
            
            # Truncate if too long
            if len(main_content) > 10000:
                main_content = main_content[:10000] + "...(content truncated)"
            
            # Extract links
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)
                # Resolve relative links
                if href.startswith('/'):
                    base_url = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                    href = base_url + href
                if text and href.startswith(('http://', 'https://')):
                    links.append({"text": text[:100], "href": href})
            
            # Extract forms
            forms = []
            for form in soup.find_all('form'):
                form_data = {
                    "action": form.get('action', ''),
                    "method": form.get('method', 'get'),
                    "fields": []
                }
                
                for input_tag in form.find_all(['input', 'textarea', 'select']):
                    field = {
                        "name": input_tag.get('name', ''),
                        "type": input_tag.get('type', 'text'),
                        "placeholder": input_tag.get('placeholder', '')
                    }
                    form_data["fields"].append(field)
                
                forms.append(form_data)
            
            # Generate a summary of the page
            summary_prompt = f"Summarize the following web page content in 3-5 sentences:\nTitle: {title}\nContent: {main_content[:5000]}"
            summary = self._send_to_llm(summary_prompt)
            
            return {
                "status": "success",
                "url": url,
                "title": title,
                "summary": summary,
                "links": links[:30],  # Limit to 30 links
                "forms": forms[:5],   # Limit to 5 forms
                "has_full_content": True
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error navigating to {url}: {str(e)}")
            return {
                "status": "error",
                "url": url,
                "error": str(e)
            }
    
    def search_web(self, query: str) -> Dict[str, Any]:
        """Search the web for information"""
        self._throttle_requests()
        
        # URL encode the query
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded_query}"
        
        try:
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            self.current_url = search_url
            self.page_content = response.text
            
            # Parse content
            soup = BeautifulSoup(self.page_content, 'html.parser')
            
            # Extract search results
            results = []
            for result in soup.select("div.g"):
                title_elem = result.select_one("h3")
                link_elem = result.select_one("a")
                snippet_elem = result.select_one("div.VwiC3b")
                
                if title_elem and link_elem and "href" in link_elem.attrs:
                    title = title_elem.get_text(strip=True)
                    href = link_elem["href"]
                    if href.startswith("/url?q="):
                        href = href[7:]
                        href = href.split("&sa=")[0]
                    
                    snippet = ""
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                    
                    if title and href.startswith("http"):
                        results.append({
                            "title": title,
                            "url": href,
                            "snippet": snippet
                        })
            
            # If no results found, try to extract featured snippets
            if not results:
                featured_snippet = soup.select_one("div.kp-wholepage")
                if featured_snippet:
                    featured_text = featured_snippet.get_text(separator="\n", strip=True)
                    results.append({
                        "title": "Featured Snippet",
                        "url": search_url,
                        "snippet": featured_text[:500]
                    })
            
            # Extract "People also ask" questions
            related_questions = []
            question_elems = soup.select("div.related-question-pair")
            for question in question_elems:
                question_text = question.get_text(strip=True)
                if question_text:
                    related_questions.append(question_text)
            
            # Cache the search results
            cache_key = hashlib.md5(query.encode()).hexdigest()
            self.cached_results[cache_key] = {
                "query": query,
                "results": results,
                "timestamp": time.time()
            }
            
            return {
                "status": "success",
                "query": query,
                "results": results[:10],  # Limit to 10 results
                "related_questions": related_questions[:5]  # Limit to 5 related questions
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching for {query}: {str(e)}")
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }
    
    def fill_form(self, url: str, form_data: Dict[str, str]) -> Dict[str, Any]:
        """Fill a form on a web page and submit it"""
        self._throttle_requests()
        
        # First navigate to the page if not already there
        if self.current_url != url:
            nav_result = self.navigate_to_url(url)
            if nav_result["status"] == "error":
                return nav_result
        
        try:
            # Use BeautifulSoup to find the form
            soup = BeautifulSoup(self.page_content, 'html.parser')
            forms = soup.find_all('form')
            
            if not forms:
                return {
                    "status": "error",
                    "url": url,
                    "error": "No forms found on page"
                }
            
            # Identify which form to use (using heuristics)
            target_form = None
            for form in forms:
                # Check if form has all the field names from form_data
                fields = set()
                for field in form.find_all(['input', 'textarea', 'select']):
                    if 'name' in field.attrs:
                        fields.add(field['name'])
                
                # Check if this form has all the fields we want to fill
                form_fields = set(form_data.keys())
                if form_fields.issubset(fields):
                    target_form = form
                    break
            
            if not target_form:
                # If we couldn't find a perfect match, use the form with the most matching fields
                max_match_count = 0
                for form in forms:
                    fields = set()
                    for field in form.find_all(['input', 'textarea', 'select']):
                        if 'name' in field.attrs:
                            fields.add(field['name'])
                    
                    # Count matches
                    form_fields = set(form_data.keys())
                    match_count = len(form_fields.intersection(fields))
                    if match_count > max_match_count:
                        max_match_count = match_count
                        target_form = form
            
            if not target_form:
                return {
                    "status": "error",
                    "url": url,
                    "error": "Could not find a suitable form to fill"
                }
            
            # Build the form submission data
            submission_data = {}
            
            # First add any hidden fields
            for hidden_field in target_form.find_all('input', type='hidden'):
                if 'name' in hidden_field.attrs and 'value' in hidden_field.attrs:
                    submission_data[hidden_field['name']] = hidden_field['value']
            
            # Then add our custom form data
            for key, value in form_data.items():
                submission_data[key] = value
            
            # Determine the form method and action
            method = target_form.get('method', 'get').lower()
            action = target_form.get('action', '')
            
            # If action is a relative URL, convert to absolute
            if action.startswith('/'):
                base_url = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                action = base_url + action
            elif not action.startswith(('http://', 'https://')):
                # Relative to current page
                action = url + '/' + action
            
            # If action is empty, use the current URL
            if not action:
                action = url
            
            # Submit the form
            if method == 'post':
                response = self.session.post(action, data=submission_data, timeout=30)
            else:
                response = self.session.get(action, params=submission_data, timeout=30)
            
            response.raise_for_status()
            
            # Update our state
            self.current_url = response.url
            self.page_content = response.text
            
            # Parse and return the results
            soup = BeautifulSoup(self.page_content, 'html.parser')
            title = soup.title.string if soup.title else "No title"
            
            # Generate a summary of the response page
            summary_prompt = f"Summarize the result of this form submission in 2-3 sentences:\nTitle: {title}\nContent: {self.page_content[:5000]}"
            summary = self._send_to_llm(summary_prompt)
            
            return {
                "status": "success",
                "url": response.url,
                "title": title,
                "summary": summary,
                "form_data": form_data
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error submitting form at {url}: {str(e)}")
            return {
                "status": "error",
                "url": url,
                "error": str(e)
            }
    
    def analyze_conversation(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze conversation to decide when to proactively fetch information
        """
        # Extract the last few turns
        recent_turns = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        
        # Combine into a context
        context = "\n".join([f"{'User' if turn['role'] == 'user' else 'Assistant'}: {turn['content']}" for turn in recent_turns])
        
        # Ask the LLM to decide if we should fetch information
        system_prompt = """You are a decision-making agent that analyzes conversations.
Your goal is to determine:
1. If the conversation needs additional external information
2. What specific information would be most helpful
3. How to search for that information

Only output JSON in the format: 
{
  "should_fetch": true|false,
  "confidence": 0.0-1.0,
  "query": "search query",
  "reasoning": "brief explanation"
}
"""
        
        prompt = f"""Analyze this conversation and decide if external information would be helpful:

{context}

Output your decision as JSON.
"""
        
        try:
            response = self._send_to_llm(prompt, system_prompt=system_prompt)
            
            # Extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)
            else:
                # Try to find JSON without markdown formatting
                json_match = re.search(r'(\{\s*"should_fetch":.*\})', response, re.DOTALL)
                if json_match:
                    response = json_match.group(1)
            
            try:
                decision = json.loads(response)
                return decision
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from LLM response: {response}")
                return {
                    "should_fetch": False,
                    "confidence": 0.0,
                    "query": "",
                    "reasoning": "Failed to parse decision"
                }
                
        except Exception as e:
            logger.error(f"Error analyzing conversation: {str(e)}")
            return {
                "should_fetch": False,
                "confidence": 0.0,
                "query": "",
                "reasoning": f"Error: {str(e)}"
            }
    
    def proactive_info_gathering(self, user_message: str) -> Dict[str, Any]:
        """
        Proactively gather information based on the user's message
        """
        # Add message to conversation context
        self.conversation_context.append({"role": "user", "content": user_message})
        
        # Analyze conversation to decide if we should fetch information
        decision = self.analyze_conversation(self.conversation_context)
        
        if decision["should_fetch"] and decision["confidence"] >= self.confidence_threshold:
            # Perform the search
            search_results = self.search_web(decision["query"])
            
            # If successful, enhance results with analysis
            if search_results["status"] == "success" and search_results["results"]:
                # Ask LLM to analyze the results in context of the conversation
                context = "\n".join([f"{'User' if turn['role'] == 'user' else 'Assistant'}: {turn['content']}" 
                                     for turn in self.conversation_context[-3:]])
                
                results_text = "\n".join([
                    f"Source {i+1}: {result['title']}\nURL: {result['url']}\nSnippet: {result['snippet']}"
                    for i, result in enumerate(search_results["results"][:3])
                ])
                
                analysis_prompt = f"""You are analyzing search results in the context of a conversation.

Conversation context:
{context}

Search query: {decision["query"]}

Search results:
{results_text}

Provide a brief analysis of how these results relate to the conversation.
Focus on extracting the most relevant facts or information that would help answer the user's query.
"""
                
                analysis = self._send_to_llm(analysis_prompt)
                
                return {
                    "status": "success",
                    "query": decision["query"],
                    "results": search_results["results"][:3],
                    "analysis": analysis,
                    "reasoning": decision["reasoning"]
                }
            else:
                return {
                    "status": "error",
                    "query": decision["query"],
                    "error": "No relevant results found",
                    "reasoning": decision["reasoning"]
                }
        else:
            return {
                "status": "skip",
                "reasoning": decision["reasoning"],
                "confidence": decision["confidence"]
            }
    
    def handle_requests(self):
        """Main request handling loop"""
        while self.running:
            try:
                # Wait for a request with timeout
                try:
                    request_str = self.socket.recv_string(flags=zmq.NOBLOCK)
                except zmq.Again:
                    time.sleep(0.1)
                    continue
                
                logger.info("Received request")
                request = json.loads(request_str)
                
                # Process the request
                if request["action"] == "navigate":
                    response = self.navigate_to_url(request["url"])
                elif request["action"] == "search":
                    response = self.search_web(request["query"])
                elif request["action"] == "fill_form":
                    response = self.fill_form(request["url"], request["form_data"])
                elif request["action"] == "proactive_info":
                    response = self.proactive_info_gathering(request["message"])
                elif request["action"] == "set_proactive_mode":
                    self.proactive_mode = request["enabled"]
                    response = {"status": "success", "proactive_mode": self.proactive_mode}
                else:
                    response = {"status": "error", "error": "Unknown action"}
                
                # Send the response
                self.socket.send_string(json.dumps(response))
                
            except json.JSONDecodeError:
                logger.error("Invalid JSON in request")
                self.socket.send_string(json.dumps({"status": "error", "error": "Invalid JSON"}))
            except Exception as e:
                logger.error(f"Error handling request: {str(e)}")
                traceback.print_exc()
                try:
                    self.socket.send_string(json.dumps({"status": "error", "error": str(e)}))
                except zmq.ZMQError:
                    pass  # Socket might be in a bad state
    
    def run(self):
        """Run the autonomous web assistant"""
        logger.info("Starting Autonomous Web Assistant")
        try:
            # Start request handling in the main thread
            self.handle_requests()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.running = False
            logger.info("Shutting down Autonomous Web Assistant")

if __name__ == "__main__":
    assistant = AutonomousWebAssistant()
    assistant.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise