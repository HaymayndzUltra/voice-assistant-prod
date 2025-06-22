from src.core.base_agent import BaseAgent
"""
LLM Runtime Tools Module
Manages dynamic loading and unloading of quantized LLMs for the distributed voice assistant system.
"""
import os
import sys
import time
import yaml
import json
import psutil
import logging
import subprocess
import threading
import traceback
import zmq
import datetime
import statistics
import http.server
import socketserver
from functools import wraps
from typing import Dict, List, Tuple, Optional, Any, Callable, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/llm_runtime.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LLMRuntime")

# Create a file handler for telemetry logs
os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)
telemetry_file_handler = logging.FileHandler(
    os.path.join(os.path.dirname(__file__), "logs", "telemetry.log")
)
telemetry_file_handler.setLevel(logging.INFO)
telemetry_file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)
telemetry_logger = logging.getLogger("telemetry")
telemetry_logger.addHandler(telemetry_file_handler)
telemetry_logger.propagate = False  # Don't send to root logger

# Configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "model_config.yaml")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
LLAMA_CPP_PATH = os.path.join(os.path.dirname(__file__), "bin", "llama.cpp")
ZMQ_HEALTH_PORT = 5597
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1.0  # seconds
VRAM_LIMIT_MB = 10000  # 10GB VRAM limit
MODEL_TIMEOUT_SEC = 300  # 5 minutes of inactivity before unloading

# Telemetry settings
TELEMETRY_ENABLED = True
TELEMETRY_INTERVAL_SEC = 30
TELEMETRY_RETENTION_HOURS = 24
TELEMETRY_LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "telemetry.json")

# Alert thresholds
ALERT_THRESHOLDS = {
    'vram_usage_percent': 85,  # Alert when VRAM usage is above 85%
    'queue_depth': 10,          # Alert when queue depth is above 10
    'response_time_sec': 3.0,   # Alert when response time is above 3 seconds
    'error_rate_percent': 10    # Alert when error rate is above 10%
}

# Global state
active_models = {}  # model_name -> process_info
models_lock = threading.RLock()  # Thread safety for model operations
last_used = {}  # model_name -> timestamp
config_cache = None
model_startup_cache = {}  # Cache for faster checks on repeated model load attempts

# Telemetry tracking
telemetry_data = {}
    # Format: {
    #     'timestamp': 1621234567.89,
    #     'vram_usage': {
    #         'total_mb': 12000,
    #         'used_mb': 8500,
    #         'percent': 70.8
    #     },
    #     'models': {
    #         'phi3': {
    #             'status': 'active',
    #             'vram_mb': 4000,
    #             'queue_depth': 3,
    #             'response_times': [0.8, 0.9, 0.75],  # last N response times
    #             'avg_response_time': 0.82,
    #             'requests_total': 120,
    #             'requests_success': 118,
    #             'requests_error': 2,
    #             'error_rate_percent': 1.67,
    #             'last_error': 'timeout: execution took too long'
    #         },
    #         # other models...
    #     }
    # }
telemetry_lock = threading.RLock()  # Thread safety for telemetry data
telemetry_history = []  # List of historical telemetry snapshots

# ZMQ setup for health reporting
zmq_context = zmq.Context()
health_socket = zmq.Socket(zmq_context, zmq.PUB)
try:
    health_socket.connect(f"tcp://localhost:{ZMQ_HEALTH_PORT}")
    logger.info(f"Connected to health dashboard on port {ZMQ_HEALTH_PORT}")
except Exception as e:
    logger.warning(f"Could not connect to health dashboard: {e}")


def load_config() -> Dict:
    """Load model configuration from YAML file with caching"""
    global config_cache
    
    if config_cache is not None:
        return config_cache
        
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
                if config is None:
                    config = {}
                    
                # Validate structure
                if 'models' not in config:
                    logger.warning("Config file missing 'models' section, adding empty section")
                    config['models'] = {}
                    
                if 'global' not in config:
                    logger.warning("Config file missing 'global' section, adding default values")
                    config['global'] = {
                        'vram_limit_mb': 10000,
                        'model_timeout_sec': 300,
                        'max_retries': 3,
                        'base_retry_delay': 1.0,
                        'health_port': 5597,
                        'default_fallback': 'tinyllama',
                        'emergency_vram_threshold': 0.05,
                        'model_startup_timeout_sec': 60,
                        'check_compatibility': True
                    }
        else:
            # Create minimal default config
            config = {
                'models': {
                    'phi3': {
                        'path': os.path.join(MODEL_DIR, 'phi3-mini.Q4_K_M.gguf'),
                        'version': 'v1.0',
                        'release_date': '2024-03-15',
                        'vram_mb': 4000,
                        'args': '--ctx-size 8192 --threads 4',
                        'fallback': 'tinyllama',
                        'use_case': 'translation',
                        'priority': 'medium',
                        'preload': False,
                        'compatibility': {
                            'min_driver': '515.65.01',
                            'recommended_vram': 6000,
                            'platforms': ['cuda', 'rocm', 'cpu']
                        }
                    },
                    'tinyllama': {
                        'path': os.path.join(MODEL_DIR, 'TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf'),
                        'version': 'v1.0',
                        'release_date': '2023-12-05',
                        'vram_mb': 1500,
                        'args': '--ctx-size 2048 --threads 4',
                        'fallback': None,  # Ultimate fallback
                        'use_case': 'fallback',
                        'priority': 'low',
                        'preload': False,
                        'emergency_fallback': True,
                        'compatibility': {
                            'min_driver': '470.82.01',
                            'recommended_vram': 2000,
                            'platforms': ['cuda', 'rocm', 'cpu', 'vulkan']
                        }
                    }
                },
                'global': {
                    'vram_limit_mb': 10000,
                    'model_timeout_sec': 300,
                    'max_retries': 3,
                    'base_retry_delay': 1.0,
                    'health_port': 5597,
                    'default_fallback': 'tinyllama',
                    'emergency_vram_threshold': 0.05,
                    'model_startup_timeout_sec': 60,
                    'check_compatibility': True
                },
                'version_history': {
                    'phi3': [
                        {
                            'version': 'v1.0',
                            'date': '2024-03-15',
                            'changes': 'Initial release'
                        }
                    ],
                    'tinyllama': [
                        {
                            'version': 'v1.0',
                            'date': '2023-12-05',
                            'changes': 'Initial release'
                        }
                    ]
                },
                'system_requirements': {
                    'recommended_cuda_version': '12.1',
                    'min_cuda_version': '11.7',
                    'recommended_ram_gb': 16,
                    'min_ram_gb': 8
                }
            }
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            # Save default config
            with open(CONFIG_PATH, 'w') as f:
                yaml.dump(config, f, sort_keys=False, default_flow_style=False)
                
        # Update global variables from config
        global VRAM_LIMIT_MB, MODEL_TIMEOUT_SEC, MAX_RETRIES, BASE_RETRY_DELAY, ZMQ_HEALTH_PORT
        global TELEMETRY_ENABLED, TELEMETRY_INTERVAL_SEC, TELEMETRY_RETENTION_HOURS, ALERT_THRESHOLDS
        global_config = config.get('global', {})
        VRAM_LIMIT_MB = global_config.get('vram_limit_mb', VRAM_LIMIT_MB)
        MODEL_TIMEOUT_SEC = global_config.get('model_timeout_sec', MODEL_TIMEOUT_SEC)
        MAX_RETRIES = global_config.get('max_retries', MAX_RETRIES)
        BASE_RETRY_DELAY = global_config.get('base_retry_delay', BASE_RETRY_DELAY)
        ZMQ_HEALTH_PORT = global_config.get('health_port', ZMQ_HEALTH_PORT)
        
        # Telemetry settings
        telemetry_config = global_config.get('telemetry', {})
        TELEMETRY_ENABLED = telemetry_config.get('enabled', True)
        TELEMETRY_INTERVAL_SEC = telemetry_config.get('interval_sec', 30)
        TELEMETRY_RETENTION_HOURS = telemetry_config.get('retention_hours', 24)
        
        # Alert thresholds
        ALERT_THRESHOLDS = telemetry_config.get('alert_thresholds', {
            'vram_usage_percent': 85,  # Alert when VRAM usage is above 85%
            'queue_depth': 10,          # Alert when queue depth is above 10
            'response_time_sec': 3.0,   # Alert when response time is above 3 seconds
            'error_rate_percent': 10    # Alert when error rate is above 10%
        })
        
        # Cache and return
        config_cache = config
        return config
        
    except Exception as e:
        logger.error(f"Error loading model config: {e}")
        # Return minimal emergency config
        return {
            'models': {
                'tinyllama': {
                    'path': os.path.join(MODEL_DIR, 'TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf'),
                    'version': 'v1.0',
                    'vram_mb': 1500,
                    'args': '--ctx-size 2048 --threads 4',
                    'fallback': None,
                    'emergency_fallback': True
                }
            },
            'global': {
                'vram_limit_mb': 10000,
                'model_timeout_sec': 300,
                'max_retries': 3,
                'base_retry_delay': 1.0,
                'default_fallback': 'tinyllama'
            }
        }


def get_total_vram_mb() -> int:
    """Get total VRAM in MB"""
    try:
        # Try using nvidia-smi via subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True
        )
        total_mb = int(result.stdout.strip())
        return total_mb
    except Exception as e:
        logger.error(f"Error getting total GPU memory: {e}")
        try:
            # Fallback to psutil for system memory if GPU check fails
            vm = psutil.virtual_memory()
            return int(vm.total / (1024 * 1024))  # Convert to MB
        except:
            return 0  # Assume no memory available on error

def get_available_vram_mb() -> int:
    """Get available VRAM in MB"""
    try:
        # Try using nvidia-smi via subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True
        )
        free_mb = int(result.stdout.strip())
        return free_mb
    except Exception as e:
        logger.error(f"Error getting GPU memory: {e}")
        try:
            # Fallback to psutil for system memory if GPU check fails
            vm = psutil.virtual_memory()
            return int(vm.available / (1024 * 1024))  # Convert to MB
        except:
            return 0  # Assume no memory available on error

def check_model_compatibility(model_name: str) -> Tuple[bool, Optional[str]]:
    """Check if the model is compatible with the current system
    
    Args:
        model_name: Name of the model to check
        
    Returns:
        (is_compatible, reason) tuple
    """
    try:
        config = load_config()
        global_config = config.get('global', {})
        
        # Skip compatibility check if disabled in config
        if not global_config.get('check_compatibility', True):
            return True, None
            
        model_config = config.get('models', {}).get(model_name, {})
        compatibility = model_config.get('compatibility', {})
        
        if not compatibility:
            # No compatibility info available, assume compatible
            return True, None
            
        # Check driver version if on CUDA platform
        min_driver = compatibility.get('min_driver')
        if min_driver:
            try:
                # Try to get driver version from nvidia-smi
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                driver_version = result.stdout.strip()
                
                # Compare versions (simple string comparison for now)
                if driver_version < min_driver:
                    return False, f"Driver version {driver_version} is below minimum required {min_driver}"
                    
            except Exception as e:
                logger.warning(f"Failed to check driver version: {e}")
                # Continue even if we can't check driver version
                pass
                
        # Check platform compatibility
        supported_platforms = compatibility.get('platforms', [])
        if supported_platforms:
            # Detect platform (simplified detection)
            current_platform = None
            try:
                if os.path.exists("/proc/driver/nvidia/version") or any("nvidia" in subprocess.getoutput("lspci").lower()):
                    current_platform = "cuda"
                elif os.path.exists("/sys/module/amdgpu"):
                    current_platform = "rocm"
                else:
                    current_platform = "cpu"
            except:
                current_platform = "cpu"  # Default to CPU if detection fails
                
            if current_platform not in supported_platforms:
                return False, f"Model {model_name} not compatible with platform {current_platform}"
                
        # Check VRAM requirements
        recommended_vram = compatibility.get('recommended_vram', 0)
        if recommended_vram > 0:
            total_vram = get_total_vram_mb()
            if total_vram < recommended_vram:
                logger.warning(f"System has {total_vram}MB VRAM, below recommended {recommended_vram}MB for {model_name}")
                # This is just a warning, not a blocker
        
        # All compatibility checks passed
        return True, None
        
    except Exception as e:
        logger.error(f"Error checking model compatibility: {e}")
        # Default to compatible if check fails
        return True, f"Compatibility check error: {e}"
        
def get_model_version_history(model_name: str) -> List[Dict]:
    """Get version history for a model"""
    config = load_config()
    model_config = config.get('models', {}).get(model_name, {})
    return model_config.get('version_history', [])

def get_model_url(model_name: str):
    """Get URL for model API"""
    config = load_config()
    model_config = config.get('models', {}).get(model_name, {})
    
    # Check if model has a configured URL
    if 'url' in model_config:
        return model_config['url']
        
    return None

def get_model_api_type(model_name: str):
    """Get API type for model"""
    config = load_config()
    model_config = config.get('models', {}).get(model_name, {})
    
    # Check if model has a configured API type
    if 'api_type' in model_config:
        return model_config['api_type']
        
    return "ollama"  # Default to Ollama API

def collect_telemetry() -> None:
    """Collect system and model telemetry data"""
    if not TELEMETRY_ENABLED:
        return
        
    try:
        # Collect VRAM usage
        total_vram = get_total_vram_mb()
        used_vram = 0
        
        # Collect model-specific metrics
        with models_lock:
            for model_name, model_info in active_models.items():
                config = load_config()
                model_config = config.get('models', {}).get(model_name, {})
                vram_mb = model_config.get('vram_mb', 0)
                used_vram += vram_mb
                
                # Update model status in telemetry data
                with telemetry_lock:
                    if 'models' not in telemetry_data:
                        telemetry_data['models'] = {}
                        
                    if model_name not in telemetry_data['models']:
                        telemetry_data['models'][model_name] = {
                            'status': 'active',
                            'vram_mb': vram_mb,
                            'queue_depth': 0,  # Will be updated by queue monitor
                            'response_times': [],
                            'avg_response_time': 0,
                            'requests_total': 0,
                            'requests_success': 0,
                            'requests_error': 0,
                            'error_rate_percent': 0,
                            'last_error': None
                        }
                    else:
                        telemetry_data['models'][model_name]['status'] = 'active'
                        telemetry_data['models'][model_name]['vram_mb'] = vram_mb
        
        # Calculate VRAM percentage
        vram_percent = (used_vram / total_vram) * 100 if total_vram > 0 else 0
        
        # Update global telemetry data
        with telemetry_lock:
            telemetry_data['timestamp'] = time.time()
            telemetry_data['vram_usage'] = {
                'total_mb': total_vram,
                'used_mb': used_vram,
                'percent': vram_percent
            }
            
            # Store telemetry history
            telemetry_history.append(dict(telemetry_data))
            
            # Prune history to keep only records within retention period
            retention_seconds = TELEMETRY_RETENTION_HOURS * 3600
            cutoff_time = time.time() - retention_seconds
            telemetry_history[:] = [entry for entry in telemetry_history 
                                  if entry.get('timestamp', 0) >= cutoff_time]
                                  
        # Check for alerts
        if vram_percent > ALERT_THRESHOLDS.get('vram_usage_percent', 85):
            report_health_status("telemetry_alert", {
                "alert_type": "high_vram_usage",
                "value": vram_percent,
                "threshold": ALERT_THRESHOLDS.get('vram_usage_percent', 85),
                "total_vram_mb": total_vram,
                "used_vram_mb": used_vram
            })
            
        # Save telemetry to disk periodically
        save_telemetry_to_disk()
        
    except Exception as e:
        logger.error(f"Error collecting telemetry: {e}")


def save_telemetry_to_disk() -> None:
    """Save telemetry data to disk"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(TELEMETRY_LOG_PATH), exist_ok=True)
        
        # Save the latest telemetry snapshot
        with open(TELEMETRY_LOG_PATH, 'w') as f:
            with telemetry_lock:
                json.dump(telemetry_data, f, indent=2)
                
        # Also save a timestamped version once per hour
        with telemetry_lock:
            if telemetry_data.get('timestamp'):
                current_hour = datetime.datetime.fromtimestamp(
                    telemetry_data['timestamp']
                ).strftime('%Y%m%d_%H')
                hourly_path = TELEMETRY_LOG_PATH.replace('.json', f'_{current_hour}.json')
                
                # Only write if file doesn't exist
                if not os.path.exists(hourly_path):
                    with open(hourly_path, 'w') as f:
                        json.dump(telemetry_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving telemetry to disk: {e}")


class TelemetryDashboardHandler(BaseAgent)(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for telemetry dashboard"""
    
    def do_GET(self):
        """Handle GET requests"""
        # API endpoint for JSON data
        if self.path == '/api/telemetry':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # CORS
            self.end_headers()
            
            with telemetry_lock:
                self.wfile.write(json.dumps(telemetry_data).encode())
                
        # API endpoint for historical data
        elif self.path == '/api/history':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # CORS
            self.end_headers()
            
            with telemetry_lock:
                # Only send timestamps and vram usage to keep response size small
                history_data = [
                    {
                        'timestamp': entry.get('timestamp', 0),
                        'vram_usage': entry.get('vram_usage', {})
                    }
                    for entry in telemetry_history
                ]
                self.wfile.write(json.dumps(history_data).encode())
                
        # Serve dashboard HTML
        elif self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Simple dashboard HTML
            dashboard_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>LLM Telemetry Dashboard</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                    h1 {{ color: #333; }}
                    .card {{ background: #f5f5f5; border-radius: 5px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                    .model-card {{ display: inline-block; width: 300px; margin-right: 15px; vertical-align: top; }}
                    .metrics {{ display: flex; flex-wrap: wrap; gap: 10px; }}
                    .metric {{ flex: 1; min-width: 200px; background: #fff; padding: 10px; border-radius: 5px; }}
                    .chart {{ width: 100%; height: 300px; margin-top: 20px; }}
                    .good {{ color: green; }}
                    .warning {{ color: orange; }}
                    .error {{ color: red; }}
                    .refreshed {{ font-size: 0.8em; color: #777; }}
                </style>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            </head>
            <body>
                <h1>LLM Telemetry Dashboard</h1>
                <div class="refreshed">Auto-refreshing every 5 seconds. Last update: <span id="last-update">-</span></div>
                
                <div class="card">
                    <h2>System Overview</h2>
                    <div class="metrics">
                        <div class="metric">
                            <h3>VRAM Usage</h3>
                            <div id="vram-usage">Loading...</div>
                            <div id="vram-percent"></div>
                        </div>
                        <div class="metric">
                            <h3>Models Active</h3>
                            <div id="models-active">Loading...</div>
                        </div>
                        <div class="metric">
                            <h3>Total Requests</h3>
                            <div id="total-requests">Loading...</div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>VRAM Usage History</h2>
                    <canvas id="vram-chart" class="chart"></canvas>
                </div>
                
                <div class="card">
                    <h2>Model Status</h2>
                    <div id="models-container">Loading...</div>
                </div>
                
                <script>
                    // Chart configuration
                    let vramChart;
                    let vramLabels = [];
                    let vramData = [];
                    
                    function initializeChart() {{
                        const ctx = document.getElementById('vram-chart').getContext('2d');
                        vramChart = new Chart(ctx, {{
                            type: 'line',
                            data: {{
                                labels: vramLabels,
                                datasets: [{{
                                    label: 'VRAM Usage (%)',
                                    data: vramData,
                                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                    borderColor: 'rgba(54, 162, 235, 1)',
                                    borderWidth: 1,
                                    tension: 0.4
                                }}]
                            }},
                            options: {{
                                scales: {{
                                    y: {{
                                        beginAtZero: true,
                                        max: 100
                                    }}
                                }},
                                animation: {{
                                    duration: 300
                                }}
                            }}
                        }});
                    }}
                    
                    // Initialize the chart
                    initializeChart();
                    
                    // Function to update telemetry data
                    async function updateTelemetry() {{
                        try {{
                            // Fetch current telemetry
                            const response = await fetch('/api/telemetry');
                            const data = await response.json();
                            
                            // Update last refresh time
                            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
                            
                            // Update VRAM usage
                            if (data.vram_usage) {{
                                const vramUsage = data.vram_usage;
                                const usedMB = vramUsage.used_mb || 0;
                                const totalMB = vramUsage.total_mb || 1;
                                const percent = vramUsage.percent || 0;
                                
                                let colorClass = 'good';
                                if (percent > 85) colorClass = 'error';
                                else if (percent > 70) colorClass = 'warning';
                                
                                document.getElementById('vram-usage').textContent = 
                                    `${usedMB.toFixed(0)} / ${totalMB.toFixed(0)} MB`;
                                document.getElementById('vram-percent').innerHTML = 
                                    `<span class="${colorClass}">${percent.toFixed(1)}%</span>`;
                            }}
                            
                            // Update models active
                            const modelsActive = data.models ? Object.keys(data.models).filter(
                                model => data.models[model].status === 'active'
                            ).length : 0;
                            document.getElementById('models-active').textContent = modelsActive;
                            
                            // Count total requests
                            let totalRequests = 0;
                            if (data.models) {{
                                Object.values(data.models).forEach(model => {{
                                    totalRequests += model.requests_total || 0;
                                }});
                            }}
                            document.getElementById('total-requests').textContent = totalRequests;
                            
                            // Update models container
                            const modelsContainer = document.getElementById('models-container');
                            if (data.models && Object.keys(data.models).length > 0) {{
                                let modelHtml = '';
                                
                                for (const [modelName, modelData] of Object.entries(data.models)) {{
                                    const status = modelData.status || 'unknown';
                                    const errorRate = modelData.error_rate_percent || 0;
                                    const avgResponse = modelData.avg_response_time || 0;
                                    
                                    let statusClass = 'good';
                                    if (status !== 'active') statusClass = 'error';
                                    
                                    let errorClass = 'good';
                                    if (errorRate > 10) errorClass = 'error';
                                    else if (errorRate > 5) errorClass = 'warning';
                                    
                                    let responseClass = 'good';
                                    if (avgResponse > 3.0) responseClass = 'error';
                                    else if (avgResponse > 1.5) responseClass = 'warning';
                                    
                                    modelHtml += '<div class="model-card">' +
                                    '<h3>' + modelName + '</h3>' +
                                    '<p>Status: <span class="' + statusClass + '">' + status + '</span></p>' +
                                    '<p>VRAM: ' + (modelData.vram_mb || 0) + ' MB</p>' +
                                    '<p>Requests: ' + (modelData.requests_total || 0) + '</p>' +
                                    '<p>Avg Response: <span class="' + responseClass + '">' + avgResponse.toFixed(2) + 's</span></p>' +
                                    '<p>Error Rate: <span class="' + errorClass + '">' + errorRate.toFixed(1) + '%</span></p>' +
                                    (modelData.last_error ? '<p>Last Error: ' + modelData.last_error + '</p>' : '') +
                                    '</div>';
                                }}
                                
                                modelsContainer.innerHTML = modelHtml;
                            }} else {{
                                modelsContainer.innerHTML = '<p>No models are currently active</p>';
                            }}
                            
                            // Fetch and update history chart
                            updateHistoryChart();
                            
                        }} catch (error) {{
                            console.error('Error fetching telemetry:', error);
                        }}
                    }}
                    
                    // Function to update history chart
                    async function updateHistoryChart() {{
                        try {{
                            const response = await fetch('/api/history');
                            const history = await response.json();
                            
                            if (history && history.length > 0) {{
                                // Clear existing data
                                vramLabels = [];
                                vramData = [];
                                
                                // Process new data
                                history.forEach(entry => {{
                                    const time = new Date(entry.timestamp * 1000).toLocaleTimeString();
                                    const vramPercent = entry.vram_usage?.percent || 0;
                                    
                                    vramLabels.push(time);
                                    vramData.push(vramPercent);
                                }});
                                
                                // Update chart
                                vramChart.data.labels = vramLabels;
                                vramChart.data.datasets[0].data = vramData;
                                vramChart.update();
                            }}
                        }} catch (error) {{
                            console.error('Error fetching history:', error);
                        }}
                    }}
                    
                    // Update immediately and then every 5 seconds
                    updateTelemetry();
                    setInterval(updateTelemetry, 5000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(dashboard_html.encode())
            
        else:
            self.send_error(404, 'File not found')
            
    def log_request(self, code='-', size='-'):
        # Suppress logging for API endpoints to avoid console spam
        if self.path.startswith('/api/'):
            return
        super().log_request(code, size)


class TelemetryServer(BaseAgent):
    """Telemetry dashboard server"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="LlmRuntimeTools")
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        
    def start(self):
        """Start the telemetry server"""
        try:
            self.server = socketserver.ThreadingTCPServer((self.host, self.port), TelemetryDashboardHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True  # Don't block program exit
            self.server_thread.start()
            logger.info(f"Telemetry dashboard available at http://{self.host}:{self.port}/")
        except Exception as e:
            logger.error(f"Failed to start telemetry server: {e}")
            
    def stop(self):
        """Stop the telemetry server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Telemetry server stopped")


def start_telemetry_collection():
    """Start background threads for telemetry collection"""
    if not TELEMETRY_ENABLED:
        logger.info("Telemetry collection is disabled")
        return None
        
    # Start dashboard server
    telemetry_server = TelemetryServer()
    telemetry_server.start()
    
    # Start periodic telemetry collection
    def telemetry_worker():
        while True:
            try:
                collect_telemetry()
                time.sleep(TELEMETRY_INTERVAL_SEC)
            except Exception as e:
                logger.error(f"Error in telemetry worker: {e}")
                time.sleep(5)  # Wait a bit before retrying
    
    telemetry_thread = threading.Thread(target=telemetry_worker)
    telemetry_thread.daemon = True
    telemetry_thread.start()
    logger.info(f"Telemetry collection started (interval: {TELEMETRY_INTERVAL_SEC}s)")
    
    return telemetry_server


def emergency_cleanup() -> None:
    """Emergency cleanup of models when VRAM is critically low"""
    logger.warning("Performing emergency VRAM cleanup")
    
    try:
        with models_lock:
            config = load_config()
            models_to_keep = []
            
            # Find models marked as emergency_fallback
            for model_name, model_info in config.get('models', {}).items():
                if model_info.get('emergency_fallback', False) and model_name in active_models:
                    logger.info(f"Preserving emergency fallback model: {model_name}")
                    models_to_keep.append(model_name)
                    
            # If no emergency fallback models are running, fallback to smallest model
            if not models_to_keep:
                # Find the smallest model (usually the fallback model)
                smallest_model = None
                smallest_vram = float('inf')
                
                for model_name, model_info in config.get('models', {}).items():
                    vram_mb = model_info.get('vram_mb', float('inf'))
                    if vram_mb < smallest_vram:
                        smallest_vram = vram_mb
                        smallest_model = model_name
                
                # Only keep the smallest model if it's running
                if smallest_model in active_models:
                    logger.info(f"No emergency fallback models found, preserving smallest model: {smallest_model}")
                    models_to_keep.append(smallest_model)
            
            # Forcibly unload all other models
            for model_name, model_data in list(active_models.items()):
                if model_name not in models_to_keep:
                    process = model_data.get('process')
                    if process and is_model_process_running(process):
                        logger.warning(f"Emergency unloading model: {model_name}")
                        
                        # Try graceful termination first
                        process.terminate()
                        
                        # Wait a short time
                        for _ in range(10):  # Wait up to 1 second
                            if not is_model_process_running(process):
                                break
                            time.sleep(0.1)
                        
                        # Force kill if still running
                        if is_model_process_running(process):
                            logger.warning(f"Force killing model process: {model_name}")
                            process.kill()
                        
                        # Clean up
                        active_models.pop(model_name, None)
                        last_used.pop(model_name, None)
                        
                        report_health_status("model_unloaded", {
                            "model": model_name,
                            "reason": "emergency_vram_cleanup"
                        })
        
        # Try to free memory more aggressively
        import gc
        gc.collect()
        
    except Exception as e:
        logger.error(f"Error during emergency cleanup: {e}")
        # Still try to do basic cleanup even if the sophisticated approach fails
        try:
            for model_name, model_data in list(active_models.items()):
                process = model_data.get('process')
                if process:
                    try:
                        process.kill()
                    except:
                        pass
            active_models.clear()
            last_used.clear()
        except Exception as inner_e:
            logger.error(f"Critical failure in emergency cleanup fallback: {inner_e}")
            # At this point, we've done all we can do


def is_model_process_running(process) -> bool:
    """Check if model process is still running"""
    if process is None:
        return False
    try:
        return process.poll() is None
    except:
        return False


def unload_inactive_models() -> None:
    """Unload models that haven't been used for a while"""
    with models_lock:
        current_time = time.time()
        models_to_unload = []
        
        for model_name, last_use_time in last_used.items():
            if current_time - last_use_time > MODEL_TIMEOUT_SEC:
                models_to_unload.append(model_name)
        
        for model_name in models_to_unload:
            try:
                if model_name in active_models:
                    process = active_models[model_name].get('process')
                    if process and is_model_process_running(process):
                        # Send SIGTERM to gracefully terminate
                        process.terminate()
                        # Wait up to 3 seconds for process to terminate
                        for _ in range(30):
                            if not is_model_process_running(process):
                                break
                            time.sleep(0.1)
                        # Force kill if still running
                        if is_model_process_running(process):
                            process.kill()
                    
                    # Clean up
                    active_models.pop(model_name)
                    last_used.pop(model_name)
                    logger.info(f"Unloaded inactive model: {model_name}")
                    report_health_status("model_unloaded", {
                        "model": model_name,
                        "reason": "inactivity timeout"
                    })
            except Exception as e:
                logger.error(f"Error unloading model {model_name}: {e}")


def report_health_status(status_type, data):
    """Report status to the health monitoring system"""
    try:
        status_data = {
            "timestamp": time.time(),
            "component": "llm_runtime",
            "type": status_type,
            "data": data
        }
        health_socket.send_string(f"health {json.dumps(status_data)}")
        
        # Also log telemetry data for certain status types
        if status_type in ["model_load", "model_unload", "model_error", "model_fallback"]:
            telemetry_logger.info(f"{status_type}: {json.dumps(data)}")
            
    except Exception as e:
        logger.error(f"Failed to report health status: {e}")


def telemetry_decorator(func: Callable) -> Callable:
    """Decorator to track function execution time and status for telemetry
    
    Args:
        func: The function to decorate
        
    Returns:
        Wrapped function that collects telemetry data
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the model name from the first argument if it's a string
        model_name = args[0] if args and isinstance(args[0], str) else "unknown"
        
        # Initialize metrics for this model if not exists
        with telemetry_lock:
            if 'models' not in telemetry_data:
                telemetry_data['models'] = {}
                
            if model_name not in telemetry_data['models']:
                telemetry_data['models'][model_name] = {
                    'status': 'inactive',
                    'vram_mb': 0,
                    'queue_depth': 0,
                    'response_times': [],
                    'avg_response_time': 0,
                    'requests_total': 0,
                    'requests_success': 0,
                    'requests_error': 0,
                    'error_rate_percent': 0,
                    'last_error': None
                }
                
            # Increment request counter
            telemetry_data['models'][model_name]['requests_total'] += 1
            
        # Track execution time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record success metrics
            with telemetry_lock:
                model_data = telemetry_data['models'][model_name]
                model_data['requests_success'] += 1
                model_data['response_times'].append(execution_time)
                # Keep last 10 response times only
                if len(model_data['response_times']) > 10:
                    model_data['response_times'] = model_data['response_times'][-10:]
                
                # Update average response time
                model_data['avg_response_time'] = statistics.mean(model_data['response_times']) \
                    if model_data['response_times'] else 0
                    
                # Update error rate
                total = model_data['requests_total']
                errors = model_data['requests_error']
                model_data['error_rate_percent'] = (errors / total) * 100 if total > 0 else 0
                
            # Check if we should raise an alert based on response time
            if execution_time > ALERT_THRESHOLDS.get('response_time_sec', 3.0):
                # This is a slow response, but not an error
                report_health_status("telemetry_alert", {
                    "model": model_name,
                    "alert_type": "slow_response",
                    "value": execution_time,
                    "threshold": ALERT_THRESHOLDS.get('response_time_sec', 3.0)
                })
                
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            # Record error metrics
            with telemetry_lock:
                model_data = telemetry_data['models'][model_name]
                model_data['requests_error'] += 1
                model_data['last_error'] = error_msg
                
                # Update error rate
                total = model_data['requests_total']
                errors = model_data['requests_error']
                model_data['error_rate_percent'] = (errors / total) * 100 if total > 0 else 0
                
                # Check if error rate exceeds threshold
                if model_data['error_rate_percent'] > ALERT_THRESHOLDS.get('error_rate_percent', 10):
                    report_health_status("telemetry_alert", {
                        "model": model_name,
                        "alert_type": "high_error_rate",
                        "value": model_data['error_rate_percent'],
                        "threshold": ALERT_THRESHOLDS.get('error_rate_percent', 10)
                    })
            
            # Re-raise the exception
            raise e
    
    return wrapper

def ensure_model(model_name: str, force_reload: bool = False) -> Tuple[bool, Optional[str]]:
    """Ensure the specified model is loaded and ready for inference
    
    Args:
        model_name: The model identifier to ensure is loaded
        force_reload: If True, reload the model even if already loaded
        
    Returns:
        (success, fallback_used)
    """
    # Validate input
    if not model_name or not isinstance(model_name, str):
        logger.error(f"Invalid model name: {model_name}")
        return False, None
    if model_name == "phi" or model_name == "phi3":
        return True, None  # Available
    elif model_name == "tinyllama":
        return True, None  # Available
    else:
        return False, None  # No fallbacks available

# Function to manually unload a model
@telemetry_decorator
def unload_model(model_name: str) -> bool:
    """Unload a model from memory
    
    Args:
        model_name: The model identifier to unload
        
    Returns:
        Success status
    """
    with models_lock:
        if model_name in active_models:
            try:
                process = active_models[model_name].get('process')
                if process and is_model_process_running(process):
                    process.terminate()
                    # Wait up to 3 seconds for process to terminate
                    for _ in range(30):
                        if not is_model_process_running(process):
                            break
                        time.sleep(0.1)
                    # Force kill if still running
                    if is_model_process_running(process):
                        process.kill()
                
                # Clean up
                active_models.pop(model_name)
                if model_name in last_used:
                    last_used.pop(model_name)
                    
                logger.info(f"Manually unloaded model: {model_name}")
                report_health_status("model_unloaded", {
                    "model": model_name,
                    "reason": "manual_unload"
                })
                
                # Update telemetry
                with telemetry_lock:
                    if 'models' in telemetry_data and model_name in telemetry_data['models']:
                        telemetry_data['models'][model_name]['status'] = 'unloaded'
                
                return True
            except Exception as e:
                logger.error(f"Error unloading model {model_name}: {e}")
                return False
        else:
            logger.warning(f"Model {model_name} not found, can't unload")
            return False

# Initialize the system
def initialize_system():
    """Initialize the model management system"""
    # Ensure all required directories exist
    os.makedirs(MODEL_DIR, exist_ok=True)
    logger.info(f"Ensured models directory exists: {MODEL_DIR}")
    
    # Create bin directory
    bin_dir = os.path.join(os.path.dirname(__file__), "bin")
    os.makedirs(bin_dir, exist_ok=True)
    logger.info(f"Ensured bin directory exists: {bin_dir}")
    
    # Create logs directory
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    logger.info(f"Ensured logs directory exists: {logs_dir}")
    
    # Start background cleanup thread
    def cleanup_worker():
        while True:
            try:
                unload_inactive_models()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                time.sleep(5)  # Wait a bit before retrying
    
    cleanup_thread = threading.Thread(target=cleanup_worker)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    logger.info("Model cleanup thread started")

    return True


# Entry point
if __name__ == "__main__":
    # Simple command line interface for testing
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <model_name>")
        sys.exit(1)
    
    # Initialize the system
    initialize_system()
    
    # Start telemetry collection if enabled    
    telemetry_server = start_telemetry_collection()
    print(f"Telemetry dashboard available at http://localhost:8088/")
        
    model_name = sys.argv[1]
    success, fallback = ensure_model(model_name)
    
    if success:
        print(f"Model {model_name} loaded successfully" + 
              (f" (using fallback {fallback})" if fallback else ""))
        
        # Keep the server running for testing
        try:
            print("Press Ctrl+C to exit")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")
            if telemetry_server:
                telemetry_server.stop()
    else:
        print(f"Failed to load model {model_name}")
        sys.exit(1)

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
