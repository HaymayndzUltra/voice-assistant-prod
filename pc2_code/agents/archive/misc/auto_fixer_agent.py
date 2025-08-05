from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
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
from common.env_helpers import get_env

# Configurable parameters
CODE_GENERATOR_PORT = 5605
EXECUTOR_PORT = 5603
MAX_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("AutoFixerAgent")

class AutoFixerAgent(BaseAgent):
    def __init__(self, code_gen_port=CODE_GENERATOR_PORT, executor_port=EXECUTOR_PORT, max_attempts=MAX_ATTEMPTS):

        super().__init__(*args, **kwargs)        self.context = zmq.Context()
        # Code generator
        self.code_gen = self.context.socket(zmq.REQ)
        self.code_gen.connect(f"tcp://localhost:{code_gen_port}")
        # Executor
        self.executor = self.context.socket(zmq.REQ)
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
        })
        gen_response = json.loads(self.code_gen.recv_string()
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
            })
            exec_response = json.loads(self.executor.recv_string()
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
                })
                fix_response = json.loads(self.code_gen.recv_string()
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
        print(json.dumps(result, indent=2)
    else:
        parser.print_help()
