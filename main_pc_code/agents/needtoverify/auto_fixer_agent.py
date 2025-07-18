from common.core.base_agent import BaseAgent
"""
Auto-Fixer Agent
- Orchestrates auto-code correction and debugging loop
- Communicates with code_generator_agent and executor_agent via ZMQ
- Retries code generation and fixing up to a configurable max_attempts
- Returns final result (success or best effort with error details)
"""
import zmq
import json
import time
import logging
from typing import Optional, Dict, Any

# Added imports to ensure access to system configuration
import sys
from pathlib import Path

# Ensure project root is in PYTHONPATH so we can import config
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config

# Configurable parameters sourced from centralized configuration
CODE_GENERATOR_PORT = config.get('zmq.code_generator_port', 5604)
EXECUTOR_PORT = config.get('zmq.executor_port', 5613)
MAX_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("AutoFixerAgent")

# NOTE: All ports now come from system_config to ensure consistency across all agents.
# If the configuration file changes, AutoFixerAgent will automatically use the updated
# ports on next restart.

class AutoFixerAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AutoFixerAgent")
        self.context = zmq.Context()
        # Code generator
        self.code_gen = self.context.socket(zmq.REQ)
        self.code_gen.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.code_gen.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.code_gen.connect(f"tcp://localhost:{code_gen_port}")
        # Executor
        self.executor = self.context.socket(zmq.REQ)
        self.executor.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.executor.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.executor.connect(f"tcp://localhost:{executor_port}")
        self.max_attempts = max_attempts

    def auto_fix_loop(self, description: str, language: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main auto-fix loop: generate → execute → fix → repeat."""
        attempt = 0
        last_code = None
        last_error = None
        history = []
        
        # Initial code generation
        logger.info(f"[AutoFix] Attempt 1: Generating code for: {description}")
        self.code_gen.send_string(json.dumps({
            "request_type": "generate",
            "description": description,
            "language": language,
            "save_to_file": False,
            "use_voting": True
        }))
        gen_response = json.loads(self.code_gen.recv_string())
        code = gen_response.get("code")
        lang = gen_response.get("language")
        history.append({"attempt": 1, "code": code, "error": None})
        
        while attempt < self.max_attempts:
            attempt += 1
            logger.info(f"[AutoFix] Attempt {attempt}: Executing code...")
            self.executor.send_string(json.dumps({
                "request_type": "execute",
                "code": code,
                "language": lang,
                "parameters": parameters or {}
            }))
            exec_response = json.loads(self.executor.recv_string())
            if exec_response.get("status") == "success":
                logger.info(f"[AutoFix] Code executed successfully on attempt {attempt}.")
                return {
                    "status": "success",
                    "code": code,
                    "language": lang,
                    "attempts": attempt,
                    "history": history,
                    "result": exec_response.get("result")
                }
            else:
                error = exec_response.get("error") or exec_response.get("traceback") or "Unknown error"
                logger.warning(f"[AutoFix] Execution failed: {error}")
                history.append({"attempt": attempt+1, "code": code, "error": error})
                if attempt >= self.max_attempts:
                    break
                # Request fix from code generator
                logger.info(f"[AutoFix] Requesting code fix from code generator...")
                self.code_gen.send_string(json.dumps({
                    "request_type": "fix",
                    "code": code,
                    "error": error,
                    "language": lang,
                    "use_voting": True
                }))
                fix_response = json.loads(self.code_gen.recv_string())
                # Handle both response formats (with or without voting)
                code = fix_response.get("fixed_code") or fix_response.get("code")
                lang = fix_response.get("language")
                time.sleep(RETRY_DELAY)
        # If all attempts failed
        logger.error(f"[AutoFix] All attempts failed. Returning last error.")
        return {
            "status": "error",
            "code": code,
            "language": lang,
            "attempts": attempt,
            "history": history,
            "error": error
        }

if __name__ == "__main__":
    import argparse

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    parser = argparse.ArgumentParser(description="Auto-Fixer Agent: Auto-code correction and debugging loop.")
    parser.add_argument('--description', type=str, help='Task description for code generation')
    parser.add_argument('--language', type=str, default=None, help='Programming language (optional)')
    parser.add_argument('--server', action='store_true', help='Run in server mode, waiting for ZMQ requests')
    args = parser.parse_args()
    
    agent = AutoFixerAgent()
    
    if args.server:
        # Just initialize the agent and keep it running, waiting for ZMQ requests
        logger.info("Auto-Fixer Agent running in server mode, waiting for requests...")
        try:
            # Keep the process alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Auto-Fixer Agent interrupted by user")
    elif args.description:
        # Run the auto-fix loop with the provided description
        result = agent.auto_fix_loop(args.description, args.language)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise