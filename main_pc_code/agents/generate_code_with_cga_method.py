from main_pc_code.src.core.base_agent import zmq
import BaseAgent
from common.env_helpers import get_env
def generate_code_with_cga(self, request_data):
    """Send a code generation request to the Code Generator Agent and return the response.
    
    Args:
        request_data: Dictionary containing the code generation request parameters.
            Must include 'description' and 'language' fields.
            May include 'model_id' field for GGUF models.
    
    Returns:
        Dictionary containing the generated code or error message.
    """
    try:
        # Get Code Generator Agent port from config
        cga_port = config.get('zmq.code_generator_port', 5604)
        zmq_address = f"tcp://localhost:{cga_port}"
        
        # Determine if this is a GGUF model request
        model_id = request_data.get('model_id')
        is_gguf = model_id is not None and model_id in self.models and \
                 self.models[model_id].get('serving_method') in ['gguf_direct', 'gguf_service']
        
        # Prepare the request to CGA
        description = request_data.get('description')
        language = request_data.get('language', 'python')
        save_to_file = request_data.get('save_to_file', False)
        filename = request_data.get('filename')
        request_id = request_data.get('request_id', f"mma_req_{int(time.time())}")
        
        if is_gguf:
            # For GGUF models, we need to load the model first
            logger.info(f"Preparing GGUF code generation with model '{model_id}'")
            
            # Attempt to load the model if not already loaded
            if model_id not in self.loaded_model_instances:
                logger.info(f"Loading GGUF model '{model_id}' for code generation")
                load_success = self.load_model(model_id)
                if not load_success:
                    return {
                        'status': 'error',
                        'message': f"Failed to load GGUF model '{model_id}'",
                        'request_id': request_id
                    }
            
            # Create GGUF generation request
            cga_request = {
                'action': 'generate_with_gguf',
                'model_id': model_id,
                'prompt': description,
                'system_prompt': "You are a helpful coding assistant. Generate concise, working code based on the user's description.",
                'max_tokens': request_data.get('max_tokens', 2048),
                'temperature': request_data.get('temperature', 0.7),
                'request_id': request_id,
                'timestamp': time.time()
            }
            
            # Use longer timeout for GGUF generation (120 seconds)
            timeout_ms = 120000
        else:
            # Regular code generation (using Ollama models)
            cga_request = {
                'action': 'generate_code',
                'description': description,
                'language': language,
                'save_to_file': save_to_file,
                'filename': filename,
                'request_id': request_id,
                'timestamp': time.time()
            }
            
            # Standard timeout for Ollama models (30 seconds)
            timeout_ms = 30000
        
        logger.info(f"Sending code generation request to CGA at {zmq_address}: {json.dumps(cga_request)[:200]}...")
        
        # Create a socket with appropriate timeout
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
        socket.connect(zmq_address)
        
        # Send request
        socket.send_string(json.dumps(cga_request))
        
        # Receive response
        try:
            response = socket.recv_string()
            # Parse JSON response
            response_data = json.loads(response)
            
            # Update model usage timestamp
            if model_id:
                self.model_last_used_timestamp[model_id] = time.time()
                
            # If using GGUF, transform the response format to match standard code generation
            if is_gguf and 'text' in response_data:
                # Extract code from the model output
                generated_text = response_data.get('text', '')
                
                # For GGUF models, we need to extract the code from the generated text
                # This is a simple extraction method and might need refinement
                code_blocks = re.findall(r'```(?:\w+)?\n(.+?)\n```', generated_text, re.DOTALL)
                if code_blocks:
                    code = code_blocks[0].strip()
                else:
                    # If no code blocks found, use the whole text
                    code = generated_text
                
                return {
                    'status': 'success',
                    'code': code,
                    'model_id': model_id,
                    'request_id': request_id
                }
            
            return response_data
            
        except zmq.Again:
            logger.error(f"Timeout waiting for CGA response (timeout: {timeout_ms}ms)")
            return {
                'status': 'error',
                'message': 'Timeout waiting for Code Generator Agent response',
                'request_id': request_id
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from CGA: {e}")
            return {
                'status': 'error',
                'message': f'Invalid JSON response from Code Generator Agent: {e}',
                'request_id': request_id
            }
    except Exception as e:
        logger.error(f"Error generating code with CGA: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Error generating code: {str(e)}',
            'request_id': request_data.get('request_id', 'unknown')
        }
    finally:
        try:
            socket.close()
            context.term()
        except:
            pass

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise