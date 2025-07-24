"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
Ollama Bridge - HTTP API Server
- Creates a FastAPI server that forwards requests to Ollama
- Makes Ollama accessible over the network on port 8000
- Mimics the same API interface used by your Deepseek setup
"""
import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import os
import sys
from common.env_helpers import get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "ollama_bridge.log")),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("OllamaBridge")

# Create FastAPI app
app = FastAPI(title="Ollama Bridge")

# Ollama API endpoint (local)
OLLAMA_API = "http://localhost:11434/api"

# Models available through Ollama
models = {}

class GenerateRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    model: Optional[str] = "phi"

@app.get("/")
async def root():
    return {"status": "running", "service": "Ollama Bridge"}

@app.get("/models")
async def get_models():
    try:
        response = requests.get(f"{OLLAMA_API}/tags")
        if response.status_code == 200:
            model_data = response.json()
            models = {model["name"]: model for model in model_data.get("models", [])}
            return {"status": "success", "models": models}
        else:
            raise HTTPException(status_code=response.status_code, detail="Error fetching models from Ollama")
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching models: {str(e)}")

@app.post("/generate")
async def generate(request: GenerateRequest):
    logger.info(f"Received generation request with prompt: {request.prompt[:50]}...")
    
    try:
        # Create Ollama-compatible request
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False
        }
        
        logger.info(f"Forwarding request to Ollama for model: {request.model}")
        response = requests.post(f"{OLLAMA_API}/generate", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "")
            logger.info(f"Generated text ({len(generated_text)} chars): {generated_text[:50]}...")
            
            # Format response to match your existing API format
            return {
                "text": generated_text,
                "usage": {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                }
            }
        else:
            error_msg = f"Ollama API returned status code: {response.status_code}"
            logger.error(error_msg)
            raise HTTPException(status_code=response.status_code, detail=error_msg)
    except Exception as e:
        logger.error(f"Error generating text: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating text: {str(e)}")

@app.get("/health")
async def health_check():
    try:
        response = requests.get(f"{OLLAMA_API}/tags")
        if response.status_code == 200:
            return {"status": "healthy", "ollama_status": "connected"}
        else:
            return {"status": "unhealthy", "ollama_status": "disconnected", "error": f"Status code: {response.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "ollama_status": "disconnected", "error": str(e)}

if __name__ == "__main__":
    logger.info("Starting Ollama Bridge on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
