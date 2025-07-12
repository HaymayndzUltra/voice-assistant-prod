import zmq
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(join_path("logs", "unified_error_agent.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('UnifiedErrorAgent')

class UnifiedErrorAgent:
    """Unified Error Agent for system-wide error handling and analysis."""
    
    def __init__(self, port=None, host="0.0.0.0"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{port if port else 7041}")
        
        # Initialize error tracking
        self.error_history = []
        self.error_patterns = {}
        self.error_thresholds = {
            'critical': 1,
            'high': 3,
            'medium': 5,
            'low': 10
        }
        
        # Start error analysis thread
        self.running = True
        self.analysis_thread = threading.Thread(target=self._analyze_errors_loop)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        
        logger.info("Unified Error Agent initialized")
    
    def _analyze_errors_loop(self):
        """Background thread for analyzing errors."""
        while self.running:
            try:
                self._analyze_error_patterns()
                self._check_error_thresholds()
                time.sleep(60)  # Analyze every minute
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
    
    def _analyze_error_patterns(self):
        """Analyze error patterns in the history."""
        # Group errors by type
        error_groups = {}
        for error in self.error_history:
            error_type = error.get('type', 'unknown')
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)
        
        # Update patterns
        self.error_patterns = {
            error_type: {
                'count': len(errors),
                'last_occurrence': max(e['timestamp'] for e in errors),
                'severity': self._determine_severity(errors)
            }
            for error_type, errors in error_groups.items()
        }
    
    def _determine_severity(self, errors: List[Dict]) -> str:
        """Determine the severity of a group of errors."""
        if any(e.get('severity') == 'critical' for e in errors):
            return 'critical'
        elif any(e.get('severity') == 'high' for e in errors):
            return 'high'
        elif any(e.get('severity') == 'medium' for e in errors):
            return 'medium'
        return 'low'
    
    def _check_error_thresholds(self):
        """Check if any error patterns exceed thresholds."""
        for error_type, pattern in self.error_patterns.items():
            threshold = self.error_thresholds.get(pattern['severity'], float('inf'))
            if pattern['count'] >= threshold:
                logger.warning(f"Error threshold exceeded for {error_type}: {pattern['count']} occurrences")
                self._trigger_alert(error_type, pattern)
    
    def _trigger_alert(self, error_type: str, pattern: Dict):
        """Trigger an alert for exceeded error threshold."""
        alert = {
            'type': 'error_threshold',
            'error_type': error_type,
            'count': pattern['count'],
            'severity': pattern['severity'],
            'timestamp': datetime.now().isoformat()
        }
        logger.warning(f"Alert triggered: {json.dumps(alert)}")
        # TODO: Implement alert notification system
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action', '')
        
        if action == 'report_error':
            return self._handle_error_report(request)
        elif action == 'get_error_stats':
            return self._get_error_stats()
        elif action == 'health_check':
            return self._health_check()
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def _handle_error_report(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle error report requests."""
        try:
            error_data = {
                'type': request.get('error_type', 'unknown'),
                'message': request.get('message', ''),
                'severity': request.get('severity', 'low'),
                'timestamp': datetime.now().isoformat(),
                'source': request.get('source', 'unknown'),
                'details': request.get('details', {})
            }
            
            self.error_history.append(error_data)
            # Keep only last 1000 errors
            self.error_history = self.error_history[-1000:]
            
            return {'status': 'success', 'message': 'Error reported successfully'}
        except Exception as e:
            logger.error(f"Error handling error report: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            'status': 'success',
            'error_patterns': self.error_patterns,
            'total_errors': len(self.error_history),
            'recent_errors': self.error_history[-10:] if self.error_history else []
        }
    
    def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'status': 'success',
            'agent': 'UnifiedErrorAgent',
            'timestamp': datetime.now().isoformat(),
            'error_count': len(self.error_history),
            'analysis_thread_alive': self.analysis_thread.is_alive()
        }
    
    def stop(self):
        """Stop the agent gracefully."""
        self.running = False
        if self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=5)
        self.socket.close()
        self.context.term()
        logger.info("Unified Error Agent stopped") 