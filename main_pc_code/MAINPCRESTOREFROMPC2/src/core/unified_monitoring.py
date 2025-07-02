"""
Unified Monitoring Agent
- Monitors system metrics and performance
- Extracts and analyzes parameters from system data
- Provides unified monitoring interface for all system components
"""
import logging
import re
import zmq
import platform
import psutil
import os
from typing import Any, Dict, List, Union, cast, TypedDict
from pathlib import Path

from main_pc_code.MAINPCRESTOREFROMPC2.src.core.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class DiskUsageInfo(TypedDict):
    total: int
    used: int
    free: int
    percent: float

class UnifiedMonitor(BaseAgent):
    """Unified Monitoring Agent for system-wide monitoring and parameter extraction."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the Unified Monitor Agent."""
        super().__init__(*args, **kwargs)
        
        # Initialize monitoring attributes
        self.metrics: Dict[str, Any] = {}
        self.thresholds: Dict[str, Any] = {}
        self.alert_history: Dict[str, Any] = {}
        self.parameter_cache: Dict[str, Any] = {}
        self.extraction_rules: Dict[str, Any] = {}
        
        # Initialize psutil availability
        self.psutil_available = True
        try:
            import psutil
        except ImportError:
            logger.warning("psutil is not installed. Some functionality will be limited.")
            logger.warning("Install psutil with: pip install psutil")
            self.psutil_available = False
        
        # Load configuration
        self._load_configuration()
        
        # Initialize ZMQ
        self._init_zmq()
        
        # Load parameter extraction rules
        self._load_extraction_rules()
        
        logger.info("Unified Monitor Agent initialized successfully")

    def _load_configuration(self):
        """Load agent configuration."""
        try:
            # Load configuration from file or environment
            self.config = {
                'parameter_extraction': {
                    'cpu_usage': {
                        'pattern': 'system.cpu.usage',
                        'type': 'float',
                        'validation': {'min': 0, 'max': 100},
                        'transform': {'round': 2}
                    },
                    'memory_usage': {
                        'pattern': 'system.memory.usage',
                        'type': 'float',
                        'validation': {'min': 0, 'max': 100},
                        'transform': {'round': 2}
                    }
                }
            }
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = {}

    def _init_zmq(self):
        """Initialize ZMQ sockets for monitoring."""
        try:
            # Initialize monitoring socket
            self.monitor_socket = self.context.socket(zmq.SUB)
            self.monitor_socket.setsockopt(zmq.SUBSCRIBE, b"")
            self.monitor_socket.connect("tcp://localhost:5555")  # Connect to metrics publisher
            
            # Initialize alert socket
            self.alert_socket = self.context.socket(zmq.PUB)
            self.alert_socket.bind("tcp://*:5556")  # Bind for alert publishing
            
            logger.info("ZMQ sockets initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {e}")
            raise

    def _load_extraction_rules(self):
        """Load parameter extraction rules from configuration."""
        try:
            rules_config = self.config.get('parameter_extraction', {})
            for rule_name, rule in rules_config.items():
                self.extraction_rules[rule_name] = {
                    'pattern': rule.get('pattern'),
                    'type': rule.get('type', 'string'),
                    'validation': rule.get('validation'),
                    'transform': rule.get('transform')
                }
            logger.info(f"Loaded {len(self.extraction_rules)} parameter extraction rules")
        except Exception as e:
            logger.error(f"Error loading parameter extraction rules: {e}")

    def extract_parameters(self, data: dict) -> dict:
        """Extract parameters from system data using configured rules.
        
        Args:
            data: Dictionary containing system data
            
        Returns:
            dict: Extracted parameters
        """
        extracted = {}
        
        for rule_name, rule in self.extraction_rules.items():
            try:
                # Get the value using the pattern
                value = self._get_value_by_pattern(data, rule['pattern'])
                if value is None:
                    continue
                    
                # Apply type conversion
                value = self._convert_type(value, rule['type'])
                
                # Apply validation
                if not self._validate_value(value, rule['validation']):
                    logger.warning(f"Parameter {rule_name} failed validation")
                    continue
                    
                # Apply transformation
                if rule['transform']:
                    value = self._apply_transform(value, rule['transform'])
                    
                extracted[rule_name] = value
                
            except Exception as e:
                logger.error(f"Error extracting parameter {rule_name}: {e}")
                
        return extracted

    def _get_value_by_pattern(self, data: dict, pattern: str) -> Any:
        """Get value from data using dot notation pattern.
        
        Args:
            data: Dictionary containing data
            pattern: Dot notation pattern (e.g. 'system.cpu.usage')
            
        Returns:
            Any: Extracted value or None if not found
        """
        try:
            current = data
            for key in pattern.split('.'):
                if isinstance(current, dict):
                    current = current.get(key)
                else:
                    return None
            return current
        except Exception:
            return None

    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type.
        
        Args:
            value: Value to convert
            target_type: Target type name
            
        Returns:
            Any: Converted value
        """
        try:
            if target_type == 'int':
                return int(value)
            elif target_type == 'float':
                return float(value)
            elif target_type == 'bool':
                return bool(value)
            elif target_type == 'string':
                return str(value)
            return value
        except Exception:
            return value

    def _validate_value(self, value: Any, validation: dict) -> bool:
        """Validate value against validation rules.
        
        Args:
            value: Value to validate
            validation: Validation rules dictionary
            
        Returns:
            bool: True if validation passes, False otherwise
        """
        if not validation:
            return True
            
        try:
            if 'min' in validation and value < validation['min']:
                return False
            if 'max' in validation and value > validation['max']:
                return False
            if 'pattern' in validation and not re.match(validation['pattern'], str(value)):
                return False
            return True
        except Exception:
            return False

    def _apply_transform(self, value: Any, transform: dict) -> Any:
        """Apply transformation to value.
        
        Args:
            value: Value to transform
            transform: Transformation rules dictionary
            
        Returns:
            Any: Transformed value
        """
        try:
            if transform.get('multiply'):
                value *= transform['multiply']
            if transform.get('divide'):
                value /= transform['divide']
            if transform.get('round'):
                value = round(value, transform['round'])
            return value
        except Exception:
            return value

    def process_metrics(self, metrics: dict) -> dict:
        """Process metrics and extract parameters.
        
        Args:
            metrics: Dictionary containing system metrics
            
        Returns:
            dict: Processed metrics with extracted parameters
        """
        # Extract parameters
        parameters = self.extract_parameters(metrics)
        
        # Update parameter cache
        self.parameter_cache.update(parameters)
        
        # Add parameters to metrics
        metrics['parameters'] = parameters
        
        return metrics 

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information.
        
        Returns:
            dict: System information including platform, memory, CPU, and disk usage
        """
        info: Dict[str, Any] = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
        
        if self.psutil_available:
            disk_usage: Dict[str, DiskUsageInfo] = {}
            for part in psutil.disk_partitions():
                if part.fstype:
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        disk_usage[str(part.mountpoint)] = {
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent
                        }
                    except PermissionError:
                        disk_usage[str(part.mountpoint)] = {
                            "total": 0,
                            "used": 0,
                            "free": 0,
                            "percent": 0.0
                        }
            
            info.update({
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": disk_usage
            })
        
        return info

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage information.
        
        Returns:
            dict: Memory usage statistics
        """
        if not self.psutil_available:
            return {"error": "psutil is not available"}
        
        memory = psutil.virtual_memory()
        
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "free": memory.free,
            "percent": memory.percent
        }

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get detailed disk usage information.
        
        Returns:
            dict: Disk usage statistics for all mounted partitions
        """
        if not self.psutil_available:
            return {"error": "psutil is not available"}
        
        disk_usage = {}
        for part in psutil.disk_partitions():
            if part.fstype:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disk_usage[part.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    }
                except PermissionError:
                    disk_usage[part.mountpoint] = {"error": "Permission denied"}
        
        return disk_usage

    def get_process_info(self, sort_by: str = "memory_percent", limit: int = 10) -> List[Dict[str, Any]]:
        """Get information about running processes.
        
        Args:
            sort_by: Attribute to sort processes by (default: memory_percent)
            limit: Maximum number of processes to return (default: 10)
            
        Returns:
            list: List of process information dictionaries
        """
        if not self.psutil_available:
            return [{"error": "psutil is not available"}]
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort processes by the specified attribute
        processes.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
        
        # Limit the number of processes returned
        return processes[:limit]

    def get_dir_size(self, path: str) -> int:
        """Get the size of a directory in bytes.
        
        Args:
            path: Path to the directory
            
        Returns:
            int: Total size in bytes
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                try:
                    fp = os.path.join(dirpath, f)
                    if os.path.isfile(fp):
                        total_size += os.path.getsize(fp)
                except:
                    pass
        return total_size

    def format_bytes(self, bytes: Union[int, float]) -> str:
        """Format bytes in a human-readable format.
        
        Args:
            bytes: Number of bytes
            
        Returns:
            str: Formatted string (e.g., "1.5 MB")
        """
        bytes_float = float(bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_float < 1024:
                return f"{bytes_float:.2f} {unit}"
            bytes_float /= 1024
        return f"{bytes_float:.2f} PB" 