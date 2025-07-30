"""
WP-05 HTTP Connection Pool
High-performance HTTP connection pooling with retry logic and session management
"""

import asyncio
import aiohttp
import threading
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import ssl
from urllib.parse import urlparse

try:
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import requests
    from requests import adapters as requests_adapters
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests_adapters = None

from common.env_helpers import get_env

logger = logging.getLogger(__name__)

@dataclass
class HTTPConfig:
    """Configuration for HTTP connections"""
    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    headers: Dict[str, str] = field(default_factory=dict)
    auth: Optional[tuple] = None
    verify_ssl: bool = True
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0
    
    def __post_init__(self):
        if not self.base_url.startswith(('http://', 'https://')):
            self.base_url = f"https://{self.base_url}"

@dataclass
class HTTPResponse:
    """Wrapper for HTTP response with metadata"""
    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    json_data: Optional[Dict[str, Any]] = None
    request_time: float = 0.0
    retries: int = 0

class HTTPConnectionPool:
    """High-performance HTTP connection pool with async and sync support"""
    
    def __init__(self,
                 max_sessions: int = 10,
                 session_timeout: float = 300.0,  # 5 minutes
                 health_check_interval: int = 60,
                 cleanup_interval: int = 120):
        
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.health_check_interval = health_check_interval
        self.cleanup_interval = cleanup_interval
        
        # Session pools
        self._async_sessions: Dict[str, aiohttp.ClientSession] = {}
        self._sync_sessions: Dict[str, requests.Session] = {} if REQUESTS_AVAILABLE else {}
        self._session_last_used: Dict[str, float] = {}
        self._session_configs: Dict[str, HTTPConfig] = {}
        
        # Connection management
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = True
        
        # Metrics
        self._metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retries': 0,
            'session_hits': 0,
            'session_misses': 0,
            'cleanup_count': 0,
            'avg_response_time': 0.0
        }
        
        # Response times for average calculation
        self._response_times: List[float] = []
        
        # Start background cleanup
        self._start_cleanup_thread()
        
        logger.info(f"HTTPConnectionPool initialized - max_sessions: {max_sessions}")
    
    def _get_session_key(self, config: HTTPConfig) -> str:
        """Generate unique key for session configuration"""
        parsed = urlparse(config.base_url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    async def _create_async_session(self, config: HTTPConfig) -> aiohttp.ClientSession:
        """Create new async HTTP session"""
        # SSL context
        ssl_context = None
        if not config.verify_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        # Connection limits
        connector = aiohttp.TCPConnector(
            limit=config.max_connections,
            limit_per_host=config.max_keepalive_connections,
            ttl_dns_cache=300,
            use_dns_cache=True,
            ssl=ssl_context,
            keepalive_timeout=config.keepalive_expiry,
            enable_cleanup_closed=True
        )
        
        # Timeout configuration
        timeout = aiohttp.ClientTimeout(
            total=config.timeout,
            connect=config.timeout / 3,
            sock_read=config.timeout / 2
        )
        
        # Authentication
        auth = None
        if config.auth:
            auth = aiohttp.BasicAuth(config.auth[0], config.auth[1])
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=config.headers,
            auth=auth,
            raise_for_status=False
        )
        
        logger.debug(f"Created async HTTP session for {config.base_url}")
        return session
    
    def _create_sync_session(self, config: HTTPConfig) -> requests.Session:
        """Create new sync HTTP session"""
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests library not available")
        
        session = requests.Session()
        
        # Headers
        session.headers.update(config.headers)
        
        # Authentication
        if config.auth:
            session.auth = config.auth
        
        # SSL verification
        session.verify = config.verify_ssl
        
        # Connection pooling
        if hasattr(requests, 'adapters'):
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=config.max_keepalive_connections,
                pool_maxsize=config.max_connections,
                max_retries=0  # We handle retries manually
            )
            session.mount('http://', adapter)
            session.mount('https://', adapter)
        
        logger.debug(f"Created sync HTTP session for {config.base_url}")
        return session
    
    async def get_async_session(self, config: HTTPConfig) -> aiohttp.ClientSession:
        """Get or create async HTTP session"""
        session_key = self._get_session_key(config)
        
        with self._lock:
            # Check if session exists and is not expired
            if session_key in self._async_sessions:
                last_used = self._session_last_used.get(session_key, 0)
                if (time.time() - last_used) < self.session_timeout:
                    self._session_last_used[session_key] = time.time()
                    self._metrics['session_hits'] += 1
                    return self._async_sessions[session_key]
                else:
                    # Session expired, close and remove
                    await self._close_async_session(session_key)
            
            # Create new session
            session = await self._create_async_session(config)
            self._async_sessions[session_key] = session
            self._session_last_used[session_key] = time.time()
            self._session_configs[session_key] = config
            self._metrics['session_misses'] += 1
            
            return session
    
    def get_sync_session(self, config: HTTPConfig) -> requests.Session:
        """Get or create sync HTTP session"""
        session_key = self._get_session_key(config)
        
        with self._lock:
            # Check if session exists and is not expired
            if session_key in self._sync_sessions:
                last_used = self._session_last_used.get(session_key, 0)
                if (time.time() - last_used) < self.session_timeout:
                    self._session_last_used[session_key] = time.time()
                    self._metrics['session_hits'] += 1
                    return self._sync_sessions[session_key]
                else:
                    # Session expired, close and remove
                    self._close_sync_session(session_key)
            
            # Create new session
            session = self._create_sync_session(config)
            self._sync_sessions[session_key] = session
            self._session_last_used[session_key] = time.time()
            self._session_configs[session_key] = config
            self._metrics['session_misses'] += 1
            
            return session
    
    async def request_async(self, config: HTTPConfig, method: str, url: str, **kwargs) -> HTTPResponse:
        """Make async HTTP request with retry logic"""
        start_time = time.time()
        full_url = f"{config.base_url.rstrip('/')}/{url.lstrip('/')}" if url else config.base_url
        
        session = await self.get_async_session(config)
        retries = 0
        last_exception = None
        
        for attempt in range(config.max_retries + 1):
            try:
                async with session.request(method, full_url, **kwargs) as response:
                    content = await response.read()
                    text = await response.text()
                    
                    # Try to parse JSON
                    json_data = None
                    if response.headers.get('content-type', '').startswith('application/json'):
                        try:
                            json_data = await response.json()
                        except Exception:
                            pass
                    
                    request_time = time.time() - start_time
                    self._update_metrics(request_time, response.status < 400, retries)
                    
                    return HTTPResponse(
                        status_code=response.status,
                        headers=dict(response.headers),
                        content=content,
                        text=text,
                        json_data=json_data,
                        request_time=request_time,
                        retries=retries
                    )
                    
            except Exception as e:
                last_exception = e
                retries += 1
                
                if attempt < config.max_retries:
                    await asyncio.sleep(config.retry_delay * (2 ** attempt))  # Exponential backoff
                    logger.warning(f"HTTP request failed, retrying ({attempt + 1}/{config.max_retries}): {e}")
        
        # All retries failed
        request_time = time.time() - start_time
        self._update_metrics(request_time, False, retries)
        raise last_exception or RuntimeError("Request failed after all retries")
    
    def request_sync(self, config: HTTPConfig, method: str, url: str, **kwargs) -> HTTPResponse:
        """Make sync HTTP request with retry logic"""
        start_time = time.time()
        full_url = f"{config.base_url.rstrip('/')}/{url.lstrip('/')}" if url else config.base_url
        
        session = self.get_sync_session(config)
        retries = 0
        last_exception = None
        
        # Set timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = config.timeout
        
        for attempt in range(config.max_retries + 1):
            try:
                response = session.request(method, full_url, **kwargs)
                
                # Try to parse JSON
                json_data = None
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        json_data = response.json()
                    except Exception:
                        pass
                
                request_time = time.time() - start_time
                self._update_metrics(request_time, response.status_code < 400, retries)
                
                return HTTPResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content=response.content,
                    text=response.text,
                    json_data=json_data,
                    request_time=request_time,
                    retries=retries
                )
                
            except Exception as e:
                last_exception = e
                retries += 1
                
                if attempt < config.max_retries:
                    time.sleep(config.retry_delay * (2 ** attempt))  # Exponential backoff
                    logger.warning(f"HTTP request failed, retrying ({attempt + 1}/{config.max_retries}): {e}")
        
        # All retries failed
        request_time = time.time() - start_time
        self._update_metrics(request_time, False, retries)
        raise last_exception or RuntimeError("Request failed after all retries")
    
    def _update_metrics(self, request_time: float, success: bool, retries: int):
        """Update request metrics"""
        with self._lock:
            self._metrics['total_requests'] += 1
            if success:
                self._metrics['successful_requests'] += 1
            else:
                self._metrics['failed_requests'] += 1
            
            self._metrics['retries'] += retries
            
            # Update response time average
            self._response_times.append(request_time)
            if len(self._response_times) > 1000:  # Keep only last 1000 requests
                self._response_times = self._response_times[-1000:]
            
            self._metrics['avg_response_time'] = sum(self._response_times) / len(self._response_times)
    
    async def _close_async_session(self, session_key: str):
        """Close async session"""
        if session_key in self._async_sessions:
            try:
                await self._async_sessions[session_key].close()
                del self._async_sessions[session_key]
                logger.debug(f"Closed async session: {session_key}")
            except Exception as e:
                logger.warning(f"Error closing async session {session_key}: {e}")
    
    def _close_sync_session(self, session_key: str):
        """Close sync session"""
        if session_key in self._sync_sessions:
            try:
                self._sync_sessions[session_key].close()
                del self._sync_sessions[session_key]
                logger.debug(f"Closed sync session: {session_key}")
            except Exception as e:
                logger.warning(f"Error closing sync session {session_key}: {e}")
    
    async def _cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        current_time = time.time()
        cleanup_count = 0
        
        # Cleanup async sessions
        expired_async = []
        for session_key, last_used in self._session_last_used.items():
            if (current_time - last_used) > self.session_timeout:
                if session_key in self._async_sessions:
                    expired_async.append(session_key)
        
        for session_key in expired_async:
            await self._close_async_session(session_key)
            cleanup_count += 1
        
        # Cleanup sync sessions
        expired_sync = []
        for session_key, last_used in self._session_last_used.items():
            if (current_time - last_used) > self.session_timeout:
                if session_key in self._sync_sessions:
                    expired_sync.append(session_key)
        
        for session_key in expired_sync:
            self._close_sync_session(session_key)
            cleanup_count += 1
        
        # Clean up tracking data
        for session_key in expired_async + expired_sync:
            self._session_last_used.pop(session_key, None)
            self._session_configs.pop(session_key, None)
        
        if cleanup_count > 0:
            self._metrics['cleanup_count'] += cleanup_count
            logger.info(f"Cleaned up {cleanup_count} expired HTTP sessions")
        
        return cleanup_count
    
    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self._running:
            try:
                await self._cleanup_expired_sessions()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in HTTP pool cleanup loop: {e}")
                await asyncio.sleep(10)  # Sleep on error
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            def run_cleanup():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._cleanup_loop())
                finally:
                    loop.close()
            
            self._cleanup_thread = threading.Thread(
                target=run_cleanup,
                daemon=True,
                name="HTTPPool-Cleanup"
            )
            self._cleanup_thread.start()
            logger.info("Started HTTP pool cleanup thread")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._lock:
            return {
                'metrics': self._metrics.copy(),
                'active_async_sessions': len(self._async_sessions),
                'active_sync_sessions': len(self._sync_sessions),
                'total_sessions': len(self._session_last_used),
                'cleanup_thread_alive': self._cleanup_thread and self._cleanup_thread.is_alive()
            }
    
    async def close_all(self):
        """Close all sessions and cleanup"""
        logger.info("Closing all HTTP sessions...")
        
        self._running = False
        
        # Close all async sessions
        for session_key in list(self._async_sessions.keys()):
            await self._close_async_session(session_key)
        
        # Close all sync sessions
        for session_key in list(self._sync_sessions.keys()):
            self._close_sync_session(session_key)
        
        # Clear tracking data
        self._session_last_used.clear()
        self._session_configs.clear()
        
        # Wait for cleanup thread
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        logger.info("HTTP connection pool closed")


# Global HTTP pool instance
_http_pool: Optional[HTTPConnectionPool] = None

def get_http_pool() -> HTTPConnectionPool:
    """Get global HTTP connection pool"""
    global _http_pool
    if _http_pool is None:
        _http_pool = HTTPConnectionPool(
            max_sessions=int(get_env("HTTP_POOL_MAX_SESSIONS", "10")),
            session_timeout=float(get_env("HTTP_POOL_SESSION_TIMEOUT", "300.0")),
            health_check_interval=int(get_env("HTTP_POOL_HEALTH_CHECK_INTERVAL", "60")),
            cleanup_interval=int(get_env("HTTP_POOL_CLEANUP_INTERVAL", "120"))
        )
    return _http_pool

# Convenience functions
async def get_async(url: str, config: Optional[HTTPConfig] = None, **kwargs) -> HTTPResponse:
    """Async GET request"""
    pool = get_http_pool()
    config = config or HTTPConfig(base_url=url)
    return await pool.request_async(config, "GET", "", **kwargs)

async def post_async(url: str, config: Optional[HTTPConfig] = None, **kwargs) -> HTTPResponse:
    """Async POST request"""
    pool = get_http_pool()
    config = config or HTTPConfig(base_url=url)
    return await pool.request_async(config, "POST", "", **kwargs)

def get_sync(url: str, config: Optional[HTTPConfig] = None, **kwargs) -> HTTPResponse:
    """Sync GET request"""
    pool = get_http_pool()
    config = config or HTTPConfig(base_url=url)
    return pool.request_sync(config, "GET", "", **kwargs)

def post_sync(url: str, config: Optional[HTTPConfig] = None, **kwargs) -> HTTPResponse:
    """Sync POST request"""
    pool = get_http_pool()
    config = config or HTTPConfig(base_url=url)
    return pool.request_sync(config, "POST", "", **kwargs) 