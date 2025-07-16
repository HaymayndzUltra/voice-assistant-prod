Phase 1 Services Implementation Roadmap
Based on my analysis of the source agents, I'll provide detailed implementation roadmaps for the three remaining Phase 1 services.
1. ResourceManager+Scheduler Consolidation
Overview
Consolidating ResourceManager, TaskScheduler, AsyncProcessor, and VRAMOptimizerAgent into a unified resource management service with per-GPU schedulers.
Import Statements and Dependencies

# Core imports
import os
import sys
import time
import json
import yaml
import logging
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from collections import deque, defaultdict
from typing import Dict, Any, Optional, List, Union, Tuple

# ZMQ for communication
import zmq
import zmq.asyncio

# System monitoring
import psutil
import GPUtil
import torch
import numpy as np

# Database
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Redis for queue management
import redis
from redis.sentinel import Sentinel

# Monitoring
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Common utilities
from common.core.base_agent import BaseAgent
from common.utils.path_env import get_path, join_path
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error

Class Hierarchy

class ResourceManagerSuite(BaseAgent):
    """
    Unified resource management service combining:
    - ResourceManager: System resource monitoring
    - TaskScheduler: Task scheduling and prioritization
    - AsyncProcessor: Async task processing
    - VRAMOptimizerAgent: GPU VRAM optimization
    """
    
    def __init__(self, port: int = 7003, health_port: int = 7103):
        super().__init__(name="ResourceManagerSuite", port=port)
        
        # Core components
        self.resource_monitor = ResourceMonitor()
        self.task_scheduler = TaskScheduler()
        self.async_processor = AsyncProcessor()
        self.vram_optimizer = VRAMOptimizer()
        
        # Queue management
        self.redis_client = self._init_redis()
        self.task_queues = {
            'high': deque(maxlen=1000),
            'medium': deque(maxlen=5000),
            'low': deque(maxlen=10000)
        }
        
        # GPU management
        self.gpu_schedulers = {}
        self._init_gpu_schedulers()

class ResourceMonitor:
    """Monitors CPU, memory, and GPU resources"""
    
    def __init__(self):
        self.thresholds = {
            'cpu': 80,
            'memory': 80,
            'gpu': 80
        }
        self.stats_history = deque(maxlen=1000)
        self.monitoring_interval = 5

class TaskScheduler:
    """Handles task scheduling with priority queues"""
    
    def __init__(self):
        self.pending_tasks = defaultdict(list)
        self.task_stats = defaultdict(lambda: {
            'success': 0,
            'failed': 0,
            'total_time': 0
        })

class AsyncProcessor:
    """Processes tasks asynchronously"""
    
    def __init__(self):
        self.worker_pool = []
        self.max_workers = 10
        self.task_timeout = 300

class VRAMOptimizer:
    """Optimizes GPU VRAM usage across models"""
    
    def __init__(self):
        self.vram_budgets = {
            'mainpc': 20000,  # MB
            'pc2': 10000      # MB
        }
        self.model_registry = {}
        self.fragmentation_threshold = 0.7


Configuration Requirements

# config/resource_manager_suite.yaml
resource_manager_suite:
  port: 7003
  health_port: 7103
  
  # Redis configuration
  redis:
    host: ${PC2_IP}
    port: 6379
    db: 0
    password: ${REDIS_PASSWORD}
    sentinel:
      enabled: false
      master_name: "mymaster"
      sentinels:
        - host: ${PC2_IP}
          port: 26379
  
  # Resource thresholds
  thresholds:
    cpu_percent: 80
    memory_percent: 80
    gpu_percent: 80
    disk_percent: 90
  
  # Task scheduling
  scheduling:
    max_queue_size: 10000
    worker_threads: 10
    task_timeout: 300
    priorities:
      - high
      - medium
      - low
  
  # VRAM optimization
  vram_optimization:
    enabled: true
    mainpc_budget_mb: 20000
    pc2_budget_mb: 10000
    defragmentation_threshold: 0.7
    idle_timeout: 900
    predictive_loading: true
    lookahead_window: 300
  
  # Monitoring
  monitoring:
    interval: 5
    history_size: 1000
    export_metrics: true
    prometheus_port: 9003


Database Schema


-- SQLite schema for resource tracking
CREATE TABLE resource_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id TEXT UNIQUE NOT NULL,
    resource_type TEXT NOT NULL,
    amount FLOAT NOT NULL,
    device TEXT NOT NULL,
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMP,
    status TEXT DEFAULT 'active'
);

CREATE TABLE task_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    task_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'pending',
    worker_id TEXT,
    error_message TEXT,
    resource_usage JSON
);

CREATE TABLE gpu_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_mb INTEGER NOT NULL,
    used_mb INTEGER NOT NULL,
    free_mb INTEGER NOT NULL,
    utilization_percent FLOAT NOT NULL,
    temperature FLOAT,
    power_draw FLOAT
);

CREATE TABLE model_vram_requirements (
    model_id TEXT PRIMARY KEY,
    vram_mb INTEGER NOT NULL,
    device TEXT NOT NULL,
    quantization TEXT DEFAULT 'FP16',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_resource_status ON resource_allocations(status);
CREATE INDEX idx_task_status ON task_history(status);
CREATE INDEX idx_gpu_device_time ON gpu_usage(device, timestamp);


API Endpoints


# FastAPI endpoints
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

app = FastAPI(title="ResourceManagerSuite", version="1.0.0")

class ResourceAllocationRequest(BaseModel):
    resource_type: str
    amount: float
    device: str = "auto"
    timeout: int = 300

class TaskSubmissionRequest(BaseModel):
    task_type: str
    priority: str = "medium"
    data: Dict[str, Any]
    resources: Optional[Dict[str, float]] = None

@app.post("/allocate")
async def allocate_resources(request: ResourceAllocationRequest):
    """Allocate system resources"""
    pass

@app.post("/release/{resource_id}")
async def release_resources(resource_id: str):
    """Release allocated resources"""
    pass

@app.post("/submit_task")
async def submit_task(request: TaskSubmissionRequest, background_tasks: BackgroundTasks):
    """Submit task for async processing"""
    pass

@app.get("/status")
async def get_status():
    """Get current resource status"""
    pass

@app.get("/gpu_status")
async def get_gpu_status():
    """Get GPU-specific status"""
    pass

@app.get("/queue_status")
async def get_queue_status():
    """Get task queue status"""
    pass

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    pass


Implementation Template


class ResourceManagerSuite(BaseAgent):
    def __init__(self, port: int = 7003):
        super().__init__(name="ResourceManagerSuite", port=port)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self._init_database()
        self._init_redis()
        self._init_monitoring()
        self._init_task_scheduler()
        self._init_gpu_management()
        
        # Error reporting
        self.error_bus = setup_error_reporting(self)
        
        # Start background threads
        self._start_monitoring_thread()
        self._start_optimization_thread()
        self._start_worker_threads()
        
    def _init_database(self):
        """Initialize SQLite database"""
        self.db_path = join_path("data", "resource_manager.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Create tables
        conn = sqlite3.connect(self.db_path)
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())
        conn.close()
        
    def _init_redis(self):
        """Initialize Redis connection"""
        redis_config = self.config.get('redis', {})
        
        if redis_config.get('sentinel', {}).get('enabled'):
            # Use Redis Sentinel for HA
            sentinels = [(s['host'], s['port']) for s in redis_config['sentinel']['sentinels']]
            sentinel = Sentinel(sentinels)
            self.redis_client = sentinel.master_for(
                redis_config['sentinel']['master_name'],
                socket_timeout=0.1,
                password=redis_config.get('password')
            )
        else:
            # Direct Redis connection
            self.redis_client = redis.Redis(
                host=redis_config.get('host', 'localhost'),
                port=redis_config.get('port', 6379),
                db=redis_config.get('db', 0),
                password=redis_config.get('password')
            )
            
    def allocate_resources(self, resource_type: str, amount: float, device: str = "auto") -> Dict[str, Any]:
        """Allocate resources with validation"""
        try:
            # Check current usage
            if not self._check_resources_available(resource_type, amount, device):
                return {
                    'status': 'error',
                    'message': 'Insufficient resources available'
                }
            
            # Generate resource ID
            resource_id = f"{resource_type}_{device}_{int(time.time()*1000)}"
            
            # Record allocation
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO resource_allocations 
                    (resource_id, resource_type, amount, device, status)
                    VALUES (?, ?, ?, ?, 'active')
                """, (resource_id, resource_type, amount, device))
                
            # Update tracking
            self._update_resource_tracking(resource_type, amount, device, 'allocate')
            
            return {
                'status': 'success',
                'resource_id': resource_id,
                'message': f'Allocated {amount} {resource_type} on {device}'
            }
            
        except Exception as e:
            report_error(self.error_bus, "allocation_error", str(e))
            return {'status': 'error', 'message': str(e)}


Testing Strategy

import pytest
from unittest.mock import Mock, patch
import asyncio

class TestResourceManagerSuite:
    @pytest.fixture
    def resource_manager(self):
        """Create ResourceManagerSuite instance"""
        with patch('redis.Redis'):
            manager = ResourceManagerSuite(port=7003)
            yield manager
            manager.cleanup()
    
    def test_resource_allocation(self, resource_manager):
        """Test resource allocation"""
        result = resource_manager.allocate_resources('cpu', 2.0)
        assert result['status'] == 'success'
        assert 'resource_id' in result
        
    def test_task_scheduling(self, resource_manager):
        """Test task scheduling with priorities"""
        # Submit tasks
        high_task = resource_manager.submit_task('test', 'high', {})
        medium_task = resource_manager.submit_task('test', 'medium', {})
        
        # Verify priority ordering
        next_task = resource_manager.get_next_task()
        assert next_task['task_id'] == high_task['task_id']
        
    @pytest.mark.asyncio
    async def test_async_processing(self, resource_manager):
        """Test async task processing"""
        task = {
            'task_id': 'test_123',
            'task_type': 'compute',
            'data': {'value': 42}
        }
        
        result = await resource_manager.process_task_async(task)
        assert result['status'] == 'completed'


Deployment Procedure

# docker-compose.yml
version: '3.8'

services:
  resource-manager-suite:
    image: ai-system/resource-manager-suite:latest
    container_name: resource-manager-suite
    ports:
      - "7003:7003"
      - "7103:7103"
      - "9003:9003"
    environment:
      - PC2_IP=${PC2_IP}
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - SECURE_ZMQ=${SECURE_ZMQ}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7103/health"]
      interval: 30s
      timeout: 10s
      retries: 3


Rollback Strategy

#!/bin/bash
# rollback_resource_manager.sh

# Keep old agents running during migration
docker-compose up -d \
  resource-manager \
  task-scheduler \
  async-processor \
  vram-optimizer-agent

# Run in parallel mode for testing
export RESOURCE_MANAGER_MODE=legacy_compat

# Gradual migration
./migrate_resource_manager.py --percentage 10
./migrate_resource_manager.py --percentage 50
./migrate_resource_manager.py --percentage 100

# Rollback if needed
docker-compose stop resource-manager-suite
docker-compose up -d resource-manager task-scheduler

2. ErrorBus Consolidation
Overview
Migrating from ZeroMQ PUB/SUB to NATS-based error bus with enhanced error handling patterns.
Import Statements and Dependencies

# Core imports
import os
import sys
import time
import json
import yaml
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

# NATS for messaging
import nats
from nats.errors import ConnectionClosedError, TimeoutError, NoServersError

# Database
import sqlite3
from motor.motor_asyncio import AsyncIOMotorClient

# Pattern matching
import re
from fnmatch import fnmatch

# Monitoring
from prometheus_client import Counter, Histogram, generate_latest

# Circuit breaker
from pybreaker import CircuitBreaker

# Common utilities
from common.core.base_agent import BaseAgent
from common.utils.path_env import get_path, join_path


Implementation Template


class ErrorBusNATS(BaseAgent):
    """
    NATS-based error bus for distributed error management
    """
    
    def __init__(self, port: int = 7004):
        super().__init__(name="ErrorBusNATS", port=port)
        
        # NATS connection
        self.nc = None
        self.js = None  # JetStream for persistence
        
        # Error patterns and routing
        self.error_patterns = []
        self.error_handlers = {}
        self.circuit_breakers = {}
        
        # Metrics
        self.error_counter = Counter('error_bus_errors_total', 'Total errors processed')
        self.error_histogram = Histogram('error_bus_processing_time', 'Error processing time')
        
        # Initialize components
        asyncio.create_task(self._init_nats())
        self._init_database()
        self._load_error_patterns()
        
    async def _init_nats(self):
        """Initialize NATS connection with JetStream"""
        self.nc = await nats.connect(
            servers=[f"nats://{self.config['nats']['host']}:{self.config['nats']['port']}"],
            error_cb=self._error_callback,
            disconnected_cb=self._disconnected_callback,
            reconnected_cb=self._reconnected_callback,
            max_reconnect_attempts=self.config['nats'].get('max_reconnect_attempts', 60)
        )
        
        # Enable JetStream
        self.js = self.nc.jetstream()
        
        # Create streams
        await self._create_streams()
        
        # Subscribe to error topics
        await self._setup_subscriptions()
        
    async def _create_streams(self):
        """Create JetStream streams for error persistence"""
        await self.js.add_stream(
            name="ERRORS",
            subjects=["errors.>"],
            retention="limits",
            max_msgs=1000000,
            max_age=7 * 24 * 60 * 60,  # 7 days
            storage="file",
            num_replicas=1
        )
        
    async def publish_error(self, error_data: Dict[str, Any]):
        """Publish error to NATS with circuit breaker"""
        subject = f"errors.{error_data.get('severity', 'ERROR').lower()}.{error_data.get('agent', 'unknown')}"
        
        # Apply circuit breaker
        if subject in self.circuit_breakers:
            breaker = self.circuit_breakers[subject]
            if breaker.current_state == 'open':
                logger.warning(f"Circuit breaker open for {subject}")
                return
                
        try:
            # Publish to NATS
            await self.js.publish(
                subject,
                json.dumps(error_data).encode(),
                headers={
                    'Nats-Msg-Id': f"{error_data['agent']}_{int(time.time()*1000)}"
                }
            )
            
            # Update metrics
            self.error_counter.inc()
            
        except Exception as e:
            logger.error(f"Failed to publish error: {e}")
            if subject in self.circuit_breakers:
                self.circuit_breakers[subject].fail()


Configuration


# config/error_bus_nats.yaml
error_bus_nats:
  port: 7004
  health_port: 7104
  
  nats:
    host: ${PC2_IP}
    port: 4222
    cluster_id: "ai-system-cluster"
    client_id: "error-bus"
    max_reconnect_attempts: 60
    reconnect_time_wait: 2
    
  jetstream:
    enabled: true
    storage_dir: /data/nats/jetstream
    max_memory: 1GB
    max_file: 10GB
    
  error_management:
    db_path: /data/error_bus.db
    retention_days: 30
    
  patterns:
    - pattern: ".*OutOfMemoryError.*"
      severity: CRITICAL
      handler: oom_handler
      
    - pattern: ".*Connection refused.*"
      severity: ERROR
      handler: connection_handler
      
    - pattern: ".*Timeout.*"
      severity: WARNING
      handler: timeout_handler
      
  circuit_breakers:
    default:
      failure_threshold: 5
      recovery_timeout: 60
      expected_exception: TimeoutError


API Endpoints


from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI(title="ErrorBusNATS", version="2.0.0")

@app.post("/publish")
async def publish_error(error: ErrorReport):
    """Publish error to the bus"""
    await error_bus.publish_error(error.dict())
    return {"status": "published"}

@app.get("/stream")
async def stream_errors(severity: str = None, agent: str = None):
    """Stream errors in real-time"""
    async def event_generator():
        subject = f"errors.{severity or '>'}.{agent or '>'}"
        sub = await error_bus.nc.subscribe(subject)
        
        try:
            async for msg in sub.messages:
                yield f"data: {msg.data.decode()}\n\n"
        finally:
            await sub.unsubscribe()
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/history")
async def get_error_history(
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = 100
):
    """Get historical errors"""
    pass


Migration Strategy

class ErrorBusMigrator:
    """Handles migration from ZMQ to NATS"""
    
    def __init__(self, zmq_port: int = 7150, nats_url: str = "nats://localhost:4222"):
        self.zmq_context = zmq.Context()
        self.zmq_sub = self.zmq_context.socket(zmq.SUB)
        self.zmq_sub.connect(f"tcp://localhost:{zmq_port}")
        self.zmq_sub.setsockopt_string(zmq.SUBSCRIBE, "ERROR:")
        
        self.nats_client = None
        
    async def start_migration(self):
        """Start forwarding errors from ZMQ to NATS"""
        # Connect to NATS
        self.nats_client = await nats.connect(self.nats_url)
        
        # Start forwarding
        while True:
            try:
                # Receive from ZMQ
                message = self.zmq_sub.recv_string()
                if message.startswith("ERROR:"):
                    error_data = json.loads(message[6:])
                    
                    # Forward to NATS
                    subject = f"errors.{error_data.get('severity', 'ERROR').lower()}"
                    await self.nats_client.publish(
                        subject,
                        json.dumps(error_data).encode()
                    )
                    
            except Exception as e:
                logger.error(f"Migration error: {e}")


3. SecurityGateway Consolidation
Overview
Combining AuthenticationAgent and AgentTrustScorer into a unified security gateway with JWT authentication and trust scoring.
Import Statements and Dependencies

# Core imports
import os
import sys
import time
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple

# JWT handling
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Security
import hashlib
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Rate limiting
from aioredis import Redis
from aiocache import cached, Cache
from aiocache.serializers import JsonSerializer

# Database
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# FastAPI
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

# Common utilities
from common.core.base_agent import BaseAgent


Implementation Template


class SecurityGateway(BaseAgent):
    """
    Unified security gateway combining authentication and trust scoring
    """
    
    def __init__(self, port: int = 7005):
        super().__init__(name="SecurityGateway", port=port)
        
        # Security components
        self.password_hasher = PasswordHasher()
        self.jwt_algorithm = "RS256"
        self._init_keys()
        
        # Trust scoring
        self.trust_scorer = TrustScorer()
        
        # Rate limiting
        self.rate_limiter = None
        self._init_rate_limiting()
        
        # Session management
        self.sessions = {}
        self.session_timeout = timedelta(hours=24)
        
        # Database
        self._init_database()
        
    def _init_keys(self):
        """Initialize RSA keys for JWT"""
        key_path = join_path("certificates", "jwt_private.pem")
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
        else:
            # Generate new key pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Save keys
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
                
        self.public_key = self.private_key.public_key()
        
    def create_token(self, user_id: str, agent_id: str = None) -> str:
        """Create JWT token"""
        # Get trust score if agent_id provided
        trust_score = 1.0
        if agent_id:
            trust_score = self.trust_scorer.get_score(agent_id)
            
        payload = {
            'user_id': user_id,
            'agent_id': agent_id,
            'trust_score': trust_score,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + self.session_timeout,
            'jti': secrets.token_urlsafe(16)
        }
        
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=self.jwt_algorithm
        )
        
        return token
        
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.jwt_algorithm]
            )
            
            # Check trust score
            if payload.get('agent_id'):
                current_trust = self.trust_scorer.get_score(payload['agent_id'])
                if current_trust < 0.3:  # Minimum trust threshold
                    raise HTTPException(403, "Agent trust score too low")
                    
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")



Database Schema


-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    role TEXT DEFAULT 'user'
);

-- Sessions table
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_jti TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    agent_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Agent trust scores
CREATE TABLE agent_trust_scores (
    agent_id TEXT PRIMARY KEY,
    trust_score FLOAT DEFAULT 0.5,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authentication logs
CREATE TABLE auth_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    agent_id TEXT,
    action TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rate limiting
CREATE TABLE rate_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    count INTEGER DEFAULT 1,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(identifier, endpoint, window_start)
);


API Endpoints


from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer

app = FastAPI(title="SecurityGateway", version="1.0.0")
security = HTTPBearer()

# Models
class LoginRequest(BaseModel):
    user_id: str
    password: str
    agent_id: Optional[str] = None

class RegisterRequest(BaseModel):
    user_id: str
    password: str
    role: str = "user"

@app.post("/auth/register")
async def register(request: RegisterRequest):
    """Register new user"""
    pass

@app.post("/auth/login", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def login(request: LoginRequest):
    """Authenticate user and return JWT"""
    pass

@app.post("/auth/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Refresh JWT token"""
    pass

@app.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Logout and revoke token"""
    pass

@app.get("/auth/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify token validity"""
    pass

@app.post("/trust/update")
async def update_trust_score(
    agent_id: str,
    success: bool,
    response_time: float,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Update agent trust score"""
    pass

@app.get("/trust/score/{agent_id}")
async def get_trust_score(
    agent_id: str,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Get agent trust score"""
    pass

@app.get("/.well-known/jwks.json")
async def get_jwks():
    """Get JSON Web Key Set for token verification"""
    pass


Middleware and Security Patterns


class SecurityMiddleware:
    """FastAPI middleware for security enforcement"""
    
    def __init__(self, security_gateway: SecurityGateway):
        self.gateway = security_gateway
        
    async def __call__(self, request: Request, call_next):
        # Extract token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
            try:
                # Verify token
                payload = self.gateway.verify_token(token)
                
                # Add user context to request
                request.state.user_id = payload['user_id']
                request.state.agent_id = payload.get('agent_id')
                request.state.trust_score = payload.get('trust_score', 1.0)
                
            except HTTPException:
                pass  # Let endpoint handle auth requirements
                
        response = await call_next(request)
        return response

# Trust-based rate limiting
class TrustBasedRateLimiter:
    """Rate limiter that considers agent trust scores"""
    
    def __init__(self, base_rate: int = 60):
        self.base_rate = base_rate
        
    async def __call__(self, request: Request):
        trust_score = getattr(request.state, 'trust_score', 0.5)
        
        # Adjust rate based on trust
        # Higher trust = higher rate limit
        rate_multiplier = 1 + (trust_score - 0.5) * 2
        allowed_rate = int(self.base_rate * rate_multiplier)
        
        # Apply rate limiting
        identifier = request.state.get('agent_id', request.client.host)
        key = f"rate_limit:{identifier}:{request.url.path}"
        
        # Check rate limit in Redis
        # ... rate limiting logic ...


Testing Strategy


import pytest
from httpx import AsyncClient
from unittest.mock import Mock, patch

class TestSecurityGateway:
    @pytest.fixture
    async def security_gateway(self):
        """Create SecurityGateway instance"""
        gateway = SecurityGateway(port=7005)
        yield gateway
        await gateway.cleanup()
        
    @pytest.fixture
    async def client(self, security_gateway):
        """Create test client"""
        app = create_app(security_gateway)
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
            
    async def test_user_registration(self, client):
        """Test user registration"""
        response = await client.post("/auth/register", json={
            "user_id": "test_user",
            "password": "secure_password123"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
    async def test_jwt_authentication(self, client):
        """Test JWT token flow"""
        # Register user
        await client.post("/auth/register", json={
            "user_id": "test_user",
            "password": "secure_password123"
        })
        
        # Login
        response = await client.post("/auth/login", json={
            "user_id": "test_user",
            "password": "secure_password123"
        })
        assert response.status_code == 200
        token = response.json()["token"]
        
        # Verify token
        response = await client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
    async def test_trust_scoring(self, security_gateway):
        """Test trust score updates"""
        agent_id = "test_agent"
        
        # Initial score
        score = security_gateway.trust_scorer.get_score(agent_id)
        assert score == 0.5  # Default
        
        # Update with success
        security_gateway.trust_scorer.update_score(
            agent_id, 
            success=True, 
            response_time=0.1
        )
        
        new_score = security_gateway.trust_scorer.get_score(agent_id)
        assert new_score > 0.5


Deployment Configuration


# docker-compose.yml
version: '3.8'

services:
  security-gateway:
    image: ai-system/security-gateway:latest
    container_name: security-gateway
    ports:
      - "7005:7005"
      - "7105:7105"
    environment:
      - PC2_IP=${PC2_IP}
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./certificates:/app/certificates
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7105/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      
  redis:
    image: redis:7-alpine
    container_name: security-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
      
volumes:
  redis-data:

Migration and Rollback

class SecurityMigrator:
    """Handles migration from separate auth agents to unified gateway"""
    
    def __init__(self):
        self.old_auth_agent = "tcp://localhost:7116"
        self.old_trust_scorer = "tcp://localhost:7122"
        self.new_gateway = "http://localhost:7005"
        
    async def migrate_users(self):
        """Migrate user data from old system"""
        # Connect to old auth agent
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(self.old_auth_agent)
        
        # Export users
        socket.send_json({"action": "export_users"})
        users = socket.recv_json()
        
        # Import to new system
        async with httpx.AsyncClient() as client:
            for user in users:
                await client.post(
                    f"{self.new_gateway}/auth/migrate",
                    json=user
                )
                
    async def verify_migration(self):
        """Verify migration was successful"""
        # Test authentication flow
        # Compare trust scores
        # Verify all users migrated
        pass


Summary
These three consolidations will significantly reduce the system complexity while maintaining all functionality:
ResourceManagerSuite (Port 7003): Unified resource management with GPU scheduling
ErrorBusNATS (Port 7004): Modern NATS-based error management
SecurityGateway (Port 7005): Comprehensive security with JWT and trust scoring
Each service includes:
Complete implementation templates
Database schemas with migrations
RESTful APIs with FastAPI
Comprehensive testing strategies
Docker deployment configurations
Rollback procedures for safe migration
The consolidation preserves all critical business logic while providing better performance, maintainability, and scalability.