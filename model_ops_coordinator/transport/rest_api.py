"""REST API implementation using FastAPI for ModelOps Coordinator."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import threading
from typing import Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel

from ..core.kernel import Kernel
from ..core.schemas import InferenceRequest
from ..core.errors import ModelOpsError
from ..adapters.local_worker import LocalWorkerAdapter
import base64
import asyncio


# Request/Response models for OpenAPI documentation
class InferenceRequestModel(BaseModel):
    """Inference request model."""
    model_name: str
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.7
    
    class Config:
        schema_extra = {
            "example": {
                "model_name": "llama-7b-chat",
                "prompt": "What is the capital of France?",
                "max_tokens": 100,
                "temperature": 0.7
            }
        }


class InferenceResponseModel(BaseModel):
    """Inference response model."""
    response_text: str
    tokens_generated: int
    inference_time_ms: float
    status: str
    error_message: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "response_text": "The capital of France is Paris.",
                "tokens_generated": 7,
                "inference_time_ms": 156.2,
                "status": "success",
                "error_message": None
            }
        }


class ModelLoadRequestModel(BaseModel):
    """Model load request model."""
    model_name: str
    model_path: str
    shards: int = 1
    
    class Config:
        schema_extra = {
            "example": {
                "model_name": "llama-7b-chat",
                "model_path": "/models/llama-7b-chat.gguf",
                "shards": 1
            }
        }


class ModelUnloadRequestModel(BaseModel):
    """Model unload request model."""
    model_name: str
    force: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "model_name": "llama-7b-chat",
                "force": False
            }
        }


class LearningJobRequestModel(BaseModel):
    """Learning job request model."""
    job_type: str
    model_name: str
    dataset_path: str
    parameters: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "job_type": "fine_tune",
                "model_name": "base-model",
                "dataset_path": "/datasets/training_data.json",
                "parameters": {
                    "learning_rate": 0.001,
                    "epochs": 3
                }
            }
        }


class GoalCreateRequestModel(BaseModel):
    """Goal creation request model."""
    title: str
    description: str
    priority: str = "medium"
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Train customer service model",
                "description": "Fine-tune base model on customer service data",
                "priority": "high",
                "metadata": {
                    "department": "customer_service",
                    "deadline": "2024-01-15"
                }
            }
        }


class RESTAPIServer:
    """
    REST API server for ModelOps Coordinator using FastAPI.
    
    Provides HTTP REST endpoints for all ModelOps operations with
    comprehensive OpenAPI documentation.
    """
    
    def __init__(self, kernel: Kernel, host: str = "0.0.0.0", port: int = 8008,
                 api_key: Optional[str] = None, enable_cors: bool = True):
        """
        Initialize REST API server.
        
        Args:
            kernel: ModelOps Coordinator kernel
            host: Server host address
            port: Server port
            api_key: Optional API key for authentication
            enable_cors: Enable CORS middleware
        """
        self.kernel = kernel
        self.host = host
        self.port = port
        self.api_key = api_key
        self.enable_cors = enable_cors
        
        # Worker adapter for local operations
        self.worker_adapter = LocalWorkerAdapter(kernel)
        
        # FastAPI app
        self.app = FastAPI(
            title="ModelOps Coordinator API",
            description="REST API for ModelOps Coordinator - Unified model lifecycle, inference, and resource management",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json"
        )
        
        # Server state
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        self._start_time: Optional[datetime] = None
        
        # Statistics
        self._stats = {
            'requests_received': 0,
            'requests_processed': 0,
            'requests_failed': 0,
            'endpoint_stats': {}
        }
        self._stats_lock = threading.Lock()
        
        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()
        self._setup_authentication()
    
    def _setup_middleware(self):
        """Setup FastAPI middleware."""
        if self.enable_cors:
            # Fail-closed CORS: restrict to trusted origins via env or default-safe list
            import os as _os
            origins_env = _os.environ.get("MODEL_OPS_ALLOWED_ORIGINS")
            if origins_env:
                allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]
            else:
                # Default to localhost-only
                allowed_origins = ["http://localhost", "http://127.0.0.1"]
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=allowed_origins,
                allow_credentials=True,
                allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                allow_headers=["*"],
            )
        
        # Add request counting middleware
        @self.app.middleware("http")
        async def count_requests(request, call_next):
            with self._stats_lock:
                self._stats['requests_received'] += 1
                endpoint = request.url.path
                if endpoint not in self._stats['endpoint_stats']:
                    self._stats['endpoint_stats'][endpoint] = 0
                self._stats['endpoint_stats'][endpoint] += 1
            
            response = await call_next(request)
            
            if response.status_code < 400:
                with self._stats_lock:
                    self._stats['requests_processed'] += 1
            else:
                with self._stats_lock:
                    self._stats['requests_failed'] += 1
            
            return response
    
    def _setup_authentication(self):
        """Setup authentication; fail-closed if API key missing in non-dev env."""
        import os as _os
        env = _os.environ.get("ENV", "development").lower()
        if not self.api_key:
            if env in ("prod", "production", "staging"):  # fail-closed
                raise ModelOpsError("API key is required in production/staging environments", "REST_API_AUTH_CONFIG_ERROR")
            # In development, allow no auth dependency but log warning
            self._auth_dependency = None
            return
        
        security = HTTPBearer()
        
        def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
            if credentials.credentials != self.api_key:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return credentials.credentials
        
        # Apply to all protected routes
        self._auth_dependency = Depends(verify_api_key)
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/", tags=["System"])
        async def root():
            """Root endpoint with service information."""
            return {
                "service": "ModelOps Coordinator",
                "version": "1.0.0",
                "status": "running" if self._running else "stopped",
                "docs_url": "/docs",
                "health_url": "/health"
            }
        
        @self.app.get("/health", tags=["System"])
        async def health_check():
            """Health check endpoint."""
            # Check if service is healthy
            is_healthy = self.kernel.is_healthy() and self.worker_adapter.is_healthy()
            
            if is_healthy:
                # Return exactly {"status": "ok"} as per plan requirement
                return JSONResponse(content={"status": "ok"}, status_code=200)
            else:
                # Return unhealthy status with details
                health = {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "kernel_healthy": self.kernel.is_healthy(),
                    "worker_healthy": self.worker_adapter.is_healthy(),
                    "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0
                }
                return JSONResponse(content=health, status_code=503)
        
        @self.app.get("/stats", tags=["System"])
        async def get_stats(auth=self._auth_dependency):
            """Get API server statistics."""
            with self._stats_lock:
                stats = self._stats.copy()
            
            stats['server'] = {
                'running': self._running,
                'start_time': self._start_time.isoformat() if self._start_time else None,
                'host': self.host,
                'port': self.port
            }
            
            return stats
        
        @self.app.get("/status", tags=["System"])
        async def get_system_status(auth=self._auth_dependency):
            """Get comprehensive system status."""
            return self.kernel.get_system_status()
        
        # Inference endpoints
        @self.app.post("/inference", response_model=InferenceResponseModel, tags=["Inference"])
        async def inference(request: InferenceRequestModel, auth=self._auth_dependency):
            """Execute inference request."""
            try:
                # Convert to internal format
                inference_request = InferenceRequest(
                    model_name=request.model_name,
                    prompt=request.prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature
                )
                
                # Execute inference
                result = self.worker_adapter.execute_inference(inference_request)
                
                return InferenceResponseModel(
                    response_text=result.response_text,
                    tokens_generated=result.tokens_generated,
                    inference_time_ms=result.inference_time_ms,
                    status=result.status,
                    error_message=result.error_message
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
        
        # Hybrid Inference endpoints
        @self.app.post("/v1/stt", tags=["Hybrid"])
        async def hybrid_stt(audio_base64: str = None, language: str = "en-US", auth=self._auth_dependency):
            """Speech-to-text using hybrid routing."""
            try:
                if not audio_base64:
                    raise HTTPException(status_code=400, detail="No audio provided")
                
                audio_bytes = base64.b64decode(audio_base64)
                result = await self.kernel.hybrid.stt(audio_bytes, language)
                return result
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"STT failed: {str(e)}")
        
        @self.app.post("/v1/tts", tags=["Hybrid"])
        async def hybrid_tts(text: str, voice: str = None, language: str = "en-US", auth=self._auth_dependency):
            """Text-to-speech using hybrid routing."""
            try:
                result = await self.kernel.hybrid.tts(text, voice, language)
                
                # Convert audio bytes to base64 for JSON response
                if 'audio_bytes' in result:
                    result['audio_base64'] = base64.b64encode(result['audio_bytes']).decode()
                    del result['audio_bytes']
                
                return result
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")
        
        @self.app.post("/v1/reason", tags=["Hybrid"])
        async def hybrid_reason(prompt: str, model: str = None, temperature: float = 0.7, auth=self._auth_dependency):
            """Reasoning using hybrid routing."""
            try:
                result = await self.kernel.hybrid.reason(prompt, model, temperature)
                return result
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Reasoning failed: {str(e)}")
        
        @self.app.post("/v1/translate", tags=["Hybrid"])
        async def hybrid_translate(text: str, target: str, source: str = "auto", auth=self._auth_dependency):
            """Translation using hybrid routing."""
            try:
                result = await self.kernel.hybrid.translate(text, target, source)
                return result
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")
        
        # Model management endpoints
        @self.app.post("/models/load", tags=["Models"])
        async def load_model(request: ModelLoadRequestModel, auth=self._auth_dependency):
            """Load a model."""
            try:
                result = self.worker_adapter.execute_model_load(
                    model_name=request.model_name,
                    model_path=request.model_path,
                    shards=request.shards
                )
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error', 'Load failed'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Model load failed: {str(e)}")
        
        @self.app.post("/models/unload", tags=["Models"])
        async def unload_model(request: ModelUnloadRequestModel, auth=self._auth_dependency):
            """Unload a model."""
            try:
                result = self.worker_adapter.execute_model_unload(
                    model_name=request.model_name,
                    force=request.force
                )
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error', 'Unload failed'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Model unload failed: {str(e)}")
        
        @self.app.get("/models", tags=["Models"])
        async def list_models(auth=self._auth_dependency):
            """List loaded models."""
            try:
                loaded_models = self.kernel.lifecycle.get_loaded_models()
                
                models = []
                for model_name, model in loaded_models.items():
                    models.append({
                        'name': model.name,
                        'path': model.path,
                        'vram_mb': model.vram_mb,
                        'shards': model.shards,
                        'loaded_at': model.loaded_at.isoformat(),
                        'last_accessed': model.last_accessed.isoformat(),
                        'access_count': model.access_count
                    })
                
                return {'models': models}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")
        
        # Learning job endpoints
        @self.app.post("/learning/jobs", tags=["Learning"])
        async def submit_learning_job(request: LearningJobRequestModel, auth=self._auth_dependency):
            """Submit a learning job."""
            try:
                result = self.worker_adapter.submit_learning_job(
                    job_type=request.job_type,
                    model_name=request.model_name,
                    dataset_path=request.dataset_path,
                    parameters=request.parameters
                )
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error', 'Job submission failed'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Job submission failed: {str(e)}")
        
        @self.app.get("/learning/jobs", tags=["Learning"])
        async def list_learning_jobs(status: Optional[str] = None, auth=self._auth_dependency):
            """List learning jobs."""
            try:
                jobs = self.kernel.learning.list_jobs(status_filter=status)
                
                job_list = []
                for job in jobs:
                    job_list.append({
                        'job_id': job.job_id,
                        'job_type': job.job_type,
                        'model_name': job.model_name,
                        'dataset_path': job.dataset_path,
                        'status': job.status.value,
                        'progress': job.progress,
                        'created_at': job.created_at.isoformat(),
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'error_message': job.error_message
                    })
                
                return {'jobs': job_list}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")
        
        @self.app.get("/learning/jobs/{job_id}", tags=["Learning"])
        async def get_learning_job(job_id: str, auth=self._auth_dependency):
            """Get learning job status."""
            try:
                job = self.kernel.learning.get_job_status(job_id)
                
                if not job:
                    raise HTTPException(status_code=404, detail="Job not found")
                
                return {
                    'job_id': job.job_id,
                    'job_type': job.job_type,
                    'model_name': job.model_name,
                    'dataset_path': job.dataset_path,
                    'status': job.status.value,
                    'progress': job.progress,
                    'created_at': job.created_at.isoformat(),
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'error_message': job.error_message,
                    'result_path': job.result_path
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")
        
        # Goal management endpoints
        @self.app.post("/goals", tags=["Goals"])
        async def create_goal(request: GoalCreateRequestModel, auth=self._auth_dependency):
            """Create a goal."""
            try:
                result = self.worker_adapter.create_goal(
                    title=request.title,
                    description=request.description,
                    priority=request.priority,
                    metadata=request.metadata
                )
                
                if not result['success']:
                    raise HTTPException(status_code=400, detail=result.get('error', 'Goal creation failed'))
                
                return result
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Goal creation failed: {str(e)}")
        
        @self.app.get("/goals", tags=["Goals"])
        async def list_goals(status: Optional[str] = None, auth=self._auth_dependency):
            """List goals."""
            try:
                goals = self.kernel.goals.list_goals(status_filter=status)
                
                goal_list = []
                for goal in goals:
                    goal_list.append({
                        'goal_id': goal.goal_id,
                        'title': goal.title,
                        'description': goal.description,
                        'priority': goal.priority.value,
                        'status': goal.status,
                        'progress': goal.progress,
                        'created_at': goal.created_at.isoformat(),
                        'started_at': goal.started_at.isoformat() if goal.started_at else None,
                        'completed_at': goal.completed_at.isoformat() if goal.completed_at else None,
                        'error_message': goal.error_message,
                        'metadata': goal.metadata
                    })
                
                return {'goals': goal_list}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to list goals: {str(e)}")
    
    def start(self):
        """Start the REST API server."""
        if self._running:
            return
        
        self._running = True
        self._start_time = datetime.utcnow()
        
        # Start server in thread
        self._server_thread = threading.Thread(
            target=self._run_server,
            name="RESTAPIServer",
            daemon=True
        )
        self._server_thread.start()
    
    def _run_server(self):
        """Run the uvicorn server."""
        try:
            uvicorn.run(
                self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True
            )
        except Exception as e:
            self._running = False
            raise ModelOpsError(f"Failed to start REST API server: {e}", "REST_START_ERROR")
    
    def stop(self):
        """Stop the REST API server."""
        if not self._running:
            return
        
        self._running = False
        
        # Shutdown worker adapter
        self.worker_adapter.shutdown()
        
        # Note: uvicorn doesn't provide easy programmatic shutdown
        # In production, this would use process management
    
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        stats['server'] = {
            'running': self._running,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'host': self.host,
            'port': self.port,
            'api_key_enabled': self.api_key is not None
        }
        
        if self._start_time:
            uptime = datetime.utcnow() - self._start_time
            stats['server']['uptime_seconds'] = uptime.total_seconds()
        
        return stats