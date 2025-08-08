"""gRPC server implementation for ModelOps Coordinator."""

import grpc
import threading
from concurrent import futures
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from ..core.kernel import Kernel
from ..core.schemas import InferenceRequest
from ..core.errors import ModelOpsError
from ..adapters.local_worker import LocalWorkerAdapter
from ..model_ops_pb2_grpc import ModelOpsServicer, add_ModelOpsServicer_to_server
from ..model_ops_pb2 import (
    InferenceRequest as ProtoInferenceRequest,
    InferenceResponse as ProtoInferenceResponse,
    ModelLoadRequest, ModelLoadReply,
    ModelUnloadRequest, ModelUnloadReply,
    ModelList, ModelInfo,
    GpuLeaseRequest, GpuLeaseReply, GpuLeaseRelease, GpuLeaseReleaseAck,
)


class ModelOpsGRPCServicer(ModelOpsServicer):
    """gRPC servicer implementation for ModelOps."""
    
    def __init__(self, kernel: Kernel):
        """Initialize gRPC servicer."""
        self.kernel = kernel
        self.worker_adapter = LocalWorkerAdapter(kernel)
        
        # Statistics
        self._stats = {
            'requests_received': 0,
            'requests_processed': 0,
            'requests_failed': 0,
            'start_time': datetime.utcnow()
        }
        self._stats_lock = threading.Lock()
        
        # Simple in-memory lease tracker guarded by a lock
        self._lease_lock = threading.Lock()
        self._leases: Dict[str, Dict[str, Any]] = {}
    
    def Infer(self, request: ProtoInferenceRequest, context) -> ProtoInferenceResponse:
        """Handle inference requests."""
        try:
            with self._stats_lock:
                self._stats['requests_received'] += 1
            
            # Convert protobuf request to internal format
            inference_request = InferenceRequest(
                model_name=request.model_name,
                prompt=request.prompt,
                max_tokens=request.max_tokens if request.max_tokens > 0 else 100,
                temperature=request.temperature if request.temperature > 0 else 0.7
            )
            
            # Execute inference
            result = self.worker_adapter.execute_inference(inference_request)
            
            # Convert to protobuf response
            response = ProtoInferenceResponse(
                response_text=result.response_text,
                tokens_generated=result.tokens_generated,
                inference_time_ms=result.inference_time_ms,
                status=result.status,
                error_message=result.error_message or ""
            )
            
            with self._stats_lock:
                self._stats['requests_processed'] += 1
            
            return response
            
        except Exception as e:
            with self._stats_lock:
                self._stats['requests_failed'] += 1
            
            # Set gRPC error status
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Inference failed: {str(e)}')
            
            return ProtoInferenceResponse(
                response_text="",
                tokens_generated=0,
                inference_time_ms=0,
                status="error",
                error_message=str(e)
            )
    
    def LoadModel(self, request: ModelLoadRequest, context) -> ModelLoadReply:
        """Handle model load requests."""
        try:
            with self._stats_lock:
                self._stats['requests_received'] += 1
            
            # Execute model load
            result = self.worker_adapter.execute_model_load(
                model_name=request.model_name,
                model_path=request.model_path,
                shards=request.shards if request.shards > 0 else 1
            )
            
            # Convert to protobuf response
            response = ModelLoadReply(
                success=result.get('success', False),
                message=result.get('message', ''),
                error_message=result.get('error', '')
            )
            
            with self._stats_lock:
                self._stats['requests_processed'] += 1
            
            return response
            
        except Exception as e:
            with self._stats_lock:
                self._stats['requests_failed'] += 1
            
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Model load failed: {str(e)}')
            
            return ModelLoadReply(
                success=False,
                message="",
                error_message=str(e)
            )
    
    def UnloadModel(self, request: ModelUnloadRequest, context) -> ModelUnloadReply:
        """Handle model unload requests."""
        try:
            with self._stats_lock:
                self._stats['requests_received'] += 1
            
            # Execute model unload
            result = self.worker_adapter.execute_model_unload(
                model_name=request.model_name,
                force=request.force
            )
            
            # Convert to protobuf response
            response = ModelUnloadReply(
                success=result.get('success', False),
                message=result.get('message', ''),
                error_message=result.get('error', '')
            )
            
            with self._stats_lock:
                self._stats['requests_processed'] += 1
            
            return response
            
        except Exception as e:
            with self._stats_lock:
                self._stats['requests_failed'] += 1
            
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Model unload failed: {str(e)}')
            
            return ModelUnloadReply(
                success=False,
                message="",
                error_message=str(e)
            )
    
    def ListModels(self, request, context) -> ModelList:
        """Handle list models requests."""
        try:
            with self._stats_lock:
                self._stats['requests_received'] += 1
            
            # Get loaded models from lifecycle
            loaded_models = self.kernel.lifecycle.get_loaded_models()
            
            # Convert to protobuf format
            model_infos = []
            for model_name, model in loaded_models.items():
                model_info = ModelInfo(
                    name=model.name,
                    path=model.path,
                    vram_mb=model.vram_mb,
                    shards=model.shards,
                    loaded_at=model.loaded_at.isoformat(),
                    access_count=model.access_count
                )
                model_infos.append(model_info)
            
            response = ModelList(models=model_infos)
            
            with self._stats_lock:
                self._stats['requests_processed'] += 1
            
            return response
            
        except Exception as e:
            with self._stats_lock:
                self._stats['requests_failed'] += 1
            
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'List models failed: {str(e)}')
            
            return ModelList(models=[])
    
    # -----------------------------
    # GPU Lease API
    # -----------------------------
    def AcquireGpuLease(self, request: GpuLeaseRequest, context) -> GpuLeaseReply:
        """Centralized GPU lease acquisition to prevent VRAM contention."""
        try:
            with self._lease_lock:
                # Compute current available MB under soft limit
                vram = self.kernel.gpu_manager.get_vram_usage()
                cap_mb = min(vram.get('total_vram_mb', 0), vram.get('soft_limit_mb', 0))
                gpu_allocated_mb = vram.get('allocated_mb', 0)
                need_mb = int(request.vram_estimate_mb)
                now = datetime.utcnow()
                ttl = max(int(request.ttl_seconds), 1)
                
                # Reclaim expired leases
                expired_ids = []
                for lease_id, lease in list(self._leases.items()):
                    if lease['expires_at'] <= now:
                        expired_ids.append(lease_id)
                for lid in expired_ids:
                    del self._leases[lid]
                
                # Sum active reserved VRAM
                reserved_mb = sum(lease['vram_mb'] for lease in self._leases.values())
                used_total_mb = gpu_allocated_mb + reserved_mb
                
                # Check capacity
                if used_total_mb + need_mb <= cap_mb:
                    lease_id = f"{int(now.timestamp()*1000)}_{request.client}"
                    self._leases[lease_id] = {
                        'client': request.client,
                        'model_name': request.model_name,
                        'vram_mb': need_mb,
                        'priority': int(request.priority),
                        'expires_at': now + timedelta(seconds=ttl)
                    }
                    return GpuLeaseReply(granted=True, lease_id=lease_id, vram_reserved_mb=need_mb)
                else:
                    return GpuLeaseReply(granted=False, reason="Insufficient VRAM", retry_after_ms=250)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'Lease acquisition failed: {str(e)}')
            return GpuLeaseReply(granted=False, reason=str(e), retry_after_ms=500)

    def ReleaseGpuLease(self, request: GpuLeaseRelease, context) -> GpuLeaseReleaseAck:
        """Release a previously acquired GPU lease."""
        try:
            with self._lease_lock:
                if request.lease_id in self._leases:
                    del self._leases[request.lease_id]
            return GpuLeaseReleaseAck(success=True)
        except Exception:
            return GpuLeaseReleaseAck(success=False)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get servicer statistics."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        # Calculate uptime
        uptime = datetime.utcnow() - stats['start_time']
        stats['uptime_seconds'] = uptime.total_seconds()
        
        return stats


class GRPCServer:
    """
    gRPC server for ModelOps Coordinator.
    
    Provides gRPC interface for ModelOps operations using protobuf definitions
    from Phase 2.
    """
    
    def __init__(self, kernel: Kernel, bind_address: str = "[::]:7212",
                 max_workers: int = 10, max_message_length: int = 100 * 1024 * 1024):
        """
        Initialize gRPC server.
        
        Args:
            kernel: ModelOps Coordinator kernel
            bind_address: gRPC bind address
            max_workers: Maximum worker threads
            max_message_length: Maximum message length in bytes
        """
        self.kernel = kernel
        self.bind_address = bind_address
        self.max_workers = max_workers
        self.max_message_length = max_message_length
        
        # gRPC server
        self.server: Optional[grpc.Server] = None
        self.servicer: Optional[ModelOpsGRPCServicer] = None
        
        # Server state
        self._running = False
        self._start_time: Optional[datetime] = None
    
    def start(self):
        """Start the gRPC server."""
        if self._running:
            return
        
        try:
            # Create gRPC server with options
            options = [
                ('grpc.max_send_message_length', self.max_message_length),
                ('grpc.max_receive_message_length', self.max_message_length),
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 5000)
            ]
            
            self.server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=self.max_workers),
                options=options
            )
            
            # Create and add servicer
            self.servicer = ModelOpsGRPCServicer(self.kernel)
            add_ModelOpsServicer_to_server(self.servicer, self.server)
            
            # Bind and start server
            self.server.add_insecure_port(self.bind_address)
            self.server.start()
            
            self._running = True
            self._start_time = datetime.utcnow()
            
        except Exception as e:
            self._running = False
            if self.server:
                self.server.stop(0)
                self.server = None
            raise ModelOpsError(f"Failed to start gRPC server: {e}", "GRPC_START_ERROR")
    
    def stop(self, grace_period: int = 30):
        """
        Stop the gRPC server.
        
        Args:
            grace_period: Grace period for shutdown in seconds
        """
        if not self._running:
            return
        
        self._running = False
        
        if self.server:
            # Shutdown server with grace period
            shutdown_event = self.server.stop(grace_period)
            
            # Wait for shutdown
            shutdown_event.wait(timeout=grace_period + 5)
            
            self.server = None
        
        # Shutdown servicer's worker adapter
        if self.servicer:
            self.servicer.worker_adapter.shutdown()
            self.servicer = None
    
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        stats = {
            'running': self._running,
            'bind_address': self.bind_address,
            'max_workers': self.max_workers,
            'start_time': self._start_time.isoformat() if self._start_time else None
        }
        
        if self._start_time:
            uptime = datetime.utcnow() - self._start_time
            stats['uptime_seconds'] = uptime.total_seconds()
        
        # Add servicer stats if available
        if self.servicer:
            stats['servicer'] = self.servicer.get_stats()
        
        return stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status."""
        return {
            'server_running': self._running,
            'kernel_healthy': self.kernel.is_healthy(),
            'servicer_available': self.servicer is not None,
            'stats': self.get_server_stats()
        }
    
    def wait_for_termination(self):
        """Wait for server termination."""
        if self.server:
            self.server.wait_for_termination()
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()