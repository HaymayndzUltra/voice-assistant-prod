"""
Log Aggregation and Search System for AI System Monorepo

This module provides comprehensive log aggregation, search, and analysis capabilities:
- Multi-source log collection and parsing
- Real-time log streaming and indexing
- Advanced search with filters and full-text search
- Log correlation and pattern analysis
- Performance metrics and alerting
- Export capabilities for analysis tools

Author: AI System Monorepo Team
Created: 2025-07-31
Phase: 4.1 - Advanced Logging and Audit Trail
"""

import asyncio
import json
import re
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, asdict
from threading import Lock, Thread
import hashlib
import gzip

from common.config.unified_config_manager import Config
from common.logging.structured_logger import get_logger


@dataclass
class LogEntry:
    """Structured log entry for aggregation and search"""
    id: str
    timestamp: str
    level: str
    logger: str
    message: str
    correlation_id: Optional[str]
    source_file: str
    component: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def matches_filter(self, filters: Dict[str, Any]) -> bool:
        """Check if entry matches given filters"""
        for key, value in filters.items():
            if key == 'level':
                if self.level.lower() != value.lower():
                    return False
            elif key == 'logger':
                if value not in self.logger:
                    return False
            elif key == 'component':
                if value not in self.component:
                    return False
            elif key == 'message':
                if value.lower() not in self.message.lower():
                    return False
            elif key == 'start_time':
                if self.timestamp < value:
                    return False
            elif key == 'end_time':
                if self.timestamp > value:
                    return False
            elif key == 'correlation_id':
                if self.correlation_id != value:
                    return False
        return True


@dataclass
class SearchResult:
    """Search result with metadata"""
    entries: List[LogEntry]
    total_count: int
    search_time_ms: int
    filters_applied: Dict[str, Any]
    correlations: Dict[str, int]  # correlation_id -> count


class LogAggregator:
    """
    Comprehensive log aggregation system with real-time indexing,
    advanced search capabilities, and performance analytics.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize log aggregator
        
        Args:
            config: Optional configuration override
        """
        self.config = config or self._load_default_config()
        self.logger = get_logger("log_aggregator")
        
        # In-memory storage
        self.entries: deque = deque(maxlen=self.config.get("max_entries_in_memory", 1000))
        self.index_by_correlation: Dict[str, List[LogEntry]] = defaultdict(list)
        self.index_by_component: Dict[str, List[LogEntry]] = defaultdict(list)
        self.index_by_level: Dict[str, List[LogEntry]] = defaultdict(list)
        
        # Thread safety
        self._lock = Lock()
        
        # Database for persistent storage
        self.db_path = Path(self.config.get("db_path", "logs/aggregated_logs.db"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # File monitoring
        self.monitored_files: Set[Path] = set()
        self.file_positions: Dict[Path, int] = {}
        self._monitoring_thread: Optional[Thread] = None
        self._stop_monitoring = False
        
        # Performance metrics
        self.metrics = {
            "entries_processed": 0,
            "search_queries": 0,
            "average_search_time": 0.0,
            "files_monitored": 0,
            "errors_encountered": 0
        }
        
        # Start monitoring if enabled
        if self.config.get("enable_monitoring", True):
            self.start_monitoring()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load configuration from unified config"""
        try:
            config = Config.for_agent(__file__)
            return {
                "enabled": config.bool("log_aggregator.enabled", True),
                "db_path": config.str("log_aggregator.db_path", "logs/aggregator.db"),
                "max_entries_in_memory": config.int("log_aggregator.max_entries_in_memory", 100000),
                "enable_monitoring": config.bool("log_aggregator.enable_monitoring", True),
                "monitoring_interval": config.float("log_aggregator.monitoring_interval", 1.0),
                "log_directories": config.list("log_aggregator.log_directories", ["logs"]),
                "log_patterns": config.list("log_aggregator.log_patterns", ["*.log", "*.json.log"]),
                "enable_compression": config.bool("log_aggregator.enable_compression", True),
                "retention_days": config.int("log_aggregator.retention_days", 30),
                "batch_size": config.int("log_aggregator.batch_size", 1000),
                "enable_full_text_search": config.bool("log_aggregator.enable_full_text_search", True)
            }
        except Exception:
            # Fallback configuration
            return {
                "enabled": True,
                "db_path": "logs/aggregator.db",
                "max_entries_in_memory": 100000,
                "enable_monitoring": True,
                "monitoring_interval": 1.0,
                "log_directories": ["logs"],
                "log_patterns": ["*.log", "*.json.log"],
                "enable_compression": True,
                "retention_days": 30,
                "batch_size": 1000,
                "enable_full_text_search": True
            }
    
    def _init_database(self):
        """Initialize SQLite database for persistent log storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_entries (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    logger TEXT NOT NULL,
                    message TEXT NOT NULL,
                    correlation_id TEXT,
                    source_file TEXT NOT NULL,
                    component TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON log_entries(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_level ON log_entries(level)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_component ON log_entries(component)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_correlation_id ON log_entries(correlation_id)')
            
            # Full-text search index
            if self.config.get("enable_full_text_search", True):
                conn.execute('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS log_entries_fts 
                    USING fts5(id, message, metadata, content='log_entries', content_rowid='rowid')
                ''')
                
                # Trigger to keep FTS index in sync
                conn.execute('''
                    CREATE TRIGGER IF NOT EXISTS log_entries_fts_insert 
                    AFTER INSERT ON log_entries BEGIN
                        INSERT INTO log_entries_fts(rowid, id, message, metadata) 
                        VALUES (new.rowid, new.id, new.message, new.metadata);
                    END
                ''')
    
    def add_log_directory(self, directory: Union[str, Path]):
        """Add directory to monitor for log files"""
        directory = Path(directory)
        if directory.exists() and directory.is_dir():
            if "log_directories" not in self.config:
                self.config["log_directories"] = []
            self.config["log_directories"].append(str(directory))
            self.logger.info(f"Added log directory for monitoring: {directory}")
        else:
            self.logger.warning(f"Directory does not exist: {directory}")
    
    def start_monitoring(self):
        """Start monitoring log files for new entries"""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._stop_monitoring = False
            self._monitoring_thread = Thread(target=self._monitor_files, daemon=True)
            self._monitoring_thread.start()
            self.logger.info("Started log file monitoring")
    
    def stop_monitoring(self):
        """Stop monitoring log files"""
        self._stop_monitoring = True
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)
        self.logger.info("Stopped log file monitoring")
    
    def _monitor_files(self):
        """Monitor log files for new entries (runs in background thread)"""
        while not self._stop_monitoring:
            try:
                # Discover log files
                self._discover_log_files()
                
                # Process new log entries
                for log_file in self.monitored_files.copy():
                    if log_file.exists():
                        self._process_log_file(log_file)
                    else:
                        # File was deleted
                        self.monitored_files.discard(log_file)
                        self.file_positions.pop(log_file, None)
                
                time.sleep(self.config.get("monitoring_interval", 60))
                
            except Exception as e:
                self.logger.error(f"Error in file monitoring: {e}")
                self.metrics["errors_encountered"] += 1
                time.sleep(5.0)  # Back off on error
    
    def _discover_log_files(self):
        """Discover log files in configured directories"""
        for directory in self.config.get("log_directories", []):
            directory = Path(directory)
            if not directory.exists():
                continue
            
            for pattern in self.config.get("log_patterns", ["*.log", "*.txt"]):
                for log_file in directory.glob(pattern):
                    if log_file.is_file() and log_file not in self.monitored_files:
                        self.monitored_files.add(log_file)
                        self.file_positions[log_file] = 0
                        self.logger.debug(f"Discovered log file: {log_file}")
        
        self.metrics["files_monitored"] = len(self.monitored_files)
    
    def _process_log_file(self, log_file: Path):
        """Process new entries from a log file"""
        try:
            current_size = log_file.stat().st_size
            last_position = self.file_positions.get(log_file, 0)
            
            if current_size <= last_position:
                return  # No new content
            
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(last_position)
                new_lines = f.readlines()
                self.file_positions[log_file] = f.tell()
            
            # Parse and add new entries
            for line in new_lines:
                if line.strip():
                    entry = self._parse_log_line(line.strip(), str(log_file))
                    if entry:
                        self.add_entry(entry)
                        
        except Exception as e:
            self.logger.error(f"Error processing log file {log_file}: {e}")
            self.metrics["errors_encountered"] += 1
    
    def _parse_log_line(self, line: str, source_file: str) -> Optional[LogEntry]:
        """Parse a log line into a LogEntry"""
        try:
            # Try to parse as JSON first (structured logs)
            if line.startswith('{'):
                data = json.loads(line)
                return LogEntry(
                    id=data.get('id', self._generate_id(line)),
                    timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                    level=data.get('level', 'INFO'),
                    logger=data.get('logger', 'unknown'),
                    message=data.get('message', line),
                    correlation_id=data.get('correlation_id'),
                    source_file=source_file,
                    component=data.get('component', self._extract_component(source_file)),
                    metadata=data.get('metadata', {})
                )
            
            # Parse standard log format
            # Example: 2025-07-31 12:00:00 - agent_name - INFO - [correlation] - message
            parts = line.split(' - ', 4)
            if len(parts) >= 4:
                timestamp = parts[0]
                logger = parts[1]
                level = parts[2]
                
                # Extract correlation ID if present
                correlation_id = None
                message = parts[3] if len(parts) == 4 else parts[4]
                if message.startswith('[') and ']' in message:
                    end_bracket = message.find(']')
                    correlation_id = message[1:end_bracket]
                    message = message[end_bracket + 2:].strip()
                
                return LogEntry(
                    id=self._generate_id(line),
                    timestamp=timestamp,
                    level=level,
                    logger=logger,
                    message=message,
                    correlation_id=correlation_id,
                    source_file=source_file,
                    component=self._extract_component(source_file),
                    metadata={}
                )
            
            # Fallback for unstructured logs
            return LogEntry(
                id=self._generate_id(line),
                timestamp=datetime.now(timezone.utc).isoformat(),
                level='INFO',
                logger='unknown',
                message=line,
                correlation_id=None,
                source_file=source_file,
                component=self._extract_component(source_file),
                metadata={}
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing log line: {e}")
            return None
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for log entry"""
        return hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()
    
    def _extract_component(self, source_file: str) -> str:
        """Extract component name from source file path"""
        path = Path(source_file)
        # Extract component from path (e.g., logs/agent_name.log -> agent_name)
        if '_' in path.stem:
            return path.stem.split('_')[0]
        return path.stem
    
    def add_entry(self, entry: LogEntry):
        """Add a log entry to the aggregator"""
        with self._lock:
            # Add to in-memory storage
            self.entries.append(entry)
            
            # Update indexes
            if entry.correlation_id:
                self.index_by_correlation[entry.correlation_id].append(entry)
            self.index_by_component[entry.component].append(entry)
            self.index_by_level[entry.level].append(entry)
            
            # Persist to database
            self._persist_entry(entry)
            
            self.metrics["entries_processed"] += 1
    
    def _persist_entry(self, entry: LogEntry):
        """Persist entry to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO log_entries 
                    (id, timestamp, level, logger, message, correlation_id, source_file, component, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry.id,
                    entry.timestamp,
                    entry.level,
                    entry.logger,
                    entry.message,
                    entry.correlation_id,
                    entry.source_file,
                    entry.component,
                    json.dumps(entry.metadata)
                ))
        except Exception as e:
            self.logger.error(f"Error persisting entry to database: {e}")
    
    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000,
        offset: int = 0,
        search_database: bool = True
    ) -> SearchResult:
        """
        Search log entries with advanced filtering and full-text search
        
        Args:
            query: Full-text search query
            filters: Dictionary of filters (level, component, start_time, end_time, etc.)
            limit: Maximum number of results
            offset: Result offset for pagination
            search_database: Whether to search database or just memory
            
        Returns:
            SearchResult with entries and metadata
        """
        start_time = time.time()
        filters = filters or {}
        
        entries = []
        total_count = 0
        
        if search_database:
            entries, total_count = self._search_database(query, filters, limit, offset)
        else:
            entries, total_count = self._search_memory(query, filters, limit, offset)
        
        # Calculate correlations
        correlations = defaultdict(int)
        for entry in entries:
            if entry.correlation_id:
                correlations[entry.correlation_id] += 1
        
        search_time_ms = int((time.time() - start_time) * 1000)
        
        # Update metrics
        self.metrics["search_queries"] += 1
        self.metrics["average_search_time"] = (
            (self.metrics["average_search_time"] * (self.metrics["search_queries"] - 1) + search_time_ms) /
            self.metrics["search_queries"]
        )
        
        return SearchResult(
            entries=entries,
            total_count=total_count,
            search_time_ms=search_time_ms,
            filters_applied=filters,
            correlations=dict(correlations)
        )
    
    def _search_database(
        self,
        query: Optional[str],
        filters: Dict[str, Any],
        limit: int,
        offset: int
    ) -> Tuple[List[LogEntry], int]:
        """Search database with SQL"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build WHERE clause
                where_conditions = []
                params = []
                
                if filters.get('level'):
                    where_conditions.append("level = ?")
                    params.append(filters['level'])
                
                if filters.get('component'):
                    where_conditions.append("component LIKE ?")
                    params.append(f"%{filters['component']}%")
                
                if filters.get('correlation_id'):
                    where_conditions.append("correlation_id = ?")
                    params.append(filters['correlation_id'])
                
                if filters.get('start_time'):
                    where_conditions.append("timestamp >= ?")
                    params.append(filters['start_time'])
                
                if filters.get('end_time'):
                    where_conditions.append("timestamp <= ?")
                    params.append(filters['end_time'])
                
                # Full-text search
                if query and self.config.get("enable_full_text_search", True):
                    sql = '''
                        SELECT * FROM log_entries 
                        WHERE id IN (
                            SELECT id FROM log_entries_fts WHERE log_entries_fts MATCH ?
                        )
                    '''
                    params.insert(0, query)
                    
                    if where_conditions:
                        sql += " AND " + " AND ".join(where_conditions)
                else:
                    sql = "SELECT * FROM log_entries"
                    if where_conditions:
                        sql += " WHERE " + " AND ".join(where_conditions)
                    elif query:
                        # Fallback to LIKE search if FTS not available
                        sql += " WHERE message LIKE ?"
                        params.insert(0, f"%{query}%")
                
                # Count total results
                count_sql = sql.replace("SELECT *", "SELECT COUNT(*)")
                total_count = conn.execute(count_sql, params).fetchone()[0]
                
                # Add ordering and pagination
                sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                # Execute query
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                
                # Convert to LogEntry objects
                entries = []
                for row in rows:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    entries.append(LogEntry(
                        id=row['id'],
                        timestamp=row['timestamp'],
                        level=row['level'],
                        logger=row['logger'],
                        message=row['message'],
                        correlation_id=row['correlation_id'],
                        source_file=row['source_file'],
                        component=row['component'],
                        metadata=metadata
                    ))
                
                return entries, total_count
                
        except Exception as e:
            self.logger.error(f"Error searching database: {e}")
            return [], 0
    
    def _search_memory(
        self,
        query: Optional[str],
        filters: Dict[str, Any],
        limit: int,
        offset: int
    ) -> Tuple[List[LogEntry], int]:
        """Search in-memory entries"""
        with self._lock:
            entries = list(self.entries)
        
        # Apply filters
        filtered_entries = []
        for entry in entries:
            if entry.matches_filter(filters):
                # Apply text search if query provided
                if query:
                    if query.lower() in entry.message.lower():
                        filtered_entries.append(entry)
                else:
                    filtered_entries.append(entry)
        
        # Sort by timestamp (newest first)
        filtered_entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        total_count = len(filtered_entries)
        
        # Apply pagination
        paginated_entries = filtered_entries[offset:offset + limit]
        
        return paginated_entries, total_count
    
    def get_correlation_trace(self, correlation_id: str) -> List[LogEntry]:
        """Get all log entries for a correlation ID"""
        with self._lock:
            memory_entries = self.index_by_correlation.get(correlation_id, [])
        
        # Also search database for complete trace
        db_entries, _ = self._search_database(
            query=None,
            filters={"correlation_id": correlation_id},
            limit=10000,
            offset=0
        )
        
        # Combine and deduplicate
        all_entries = memory_entries + db_entries
        seen_ids = set()
        unique_entries = []
        
        for entry in all_entries:
            if entry.id not in seen_ids:
                unique_entries.append(entry)
                seen_ids.add(entry.id)
        
        # Sort by timestamp
        unique_entries.sort(key=lambda x: x.timestamp)
        
        return unique_entries
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregator performance metrics"""
        with self._lock:
            memory_stats = {
                "entries_in_memory": len(self.entries),
                "correlations_tracked": len(self.index_by_correlation),
                "components_tracked": len(self.index_by_component),
                "levels_tracked": len(self.index_by_level)
            }
        
        return {**self.metrics, **memory_stats}
    
    def cleanup_old_entries(self, retention_days: Optional[int] = None):
        """Remove old entries from database"""
        retention_days = retention_days or self.config.get("retention_days", 30)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        cutoff_iso = cutoff_date.isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM log_entries WHERE timestamp < ?", (cutoff_iso,))
                deleted_count = cursor.rowcount
                self.logger.info(f"Cleaned up {deleted_count} old log entries")
        except Exception as e:
            self.logger.error(f"Error cleaning up old entries: {e}")
    
    def export_logs(
        self,
        output_file: Path,
        filters: Optional[Dict[str, Any]] = None,
        format: str = "json"
    ):
        """Export logs to file"""
        result = self.search(filters=filters, limit=100000, search_database=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            if format == "json":
                json.dump([entry.to_dict() for entry in result.entries], f, indent=2, default=str)
            elif format == "csv":
                import csv
                if result.entries:
                    writer = csv.DictWriter(f, fieldnames=result.entries[0].to_dict().keys())
                    writer.writeheader()
                    for entry in result.entries:
                        writer.writerow(entry.to_dict())
        
        self.logger.info(f"Exported {len(result.entries)} log entries to {output_file}")


# Global aggregator instance
_log_aggregator: Optional[LogAggregator] = None
_aggregator_lock = Lock()


def get_log_aggregator(config: Optional[Dict[str, Any]] = None) -> LogAggregator:
    """
    Get or create global log aggregator instance
    
    Args:
        config: Optional configuration override
        
    Returns:
        LogAggregator instance
    """
    global _log_aggregator
    with _aggregator_lock:
        if _log_aggregator is None:
            _log_aggregator = LogAggregator(config)
        return _log_aggregator


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    aggregator = get_log_aggregator()
    
    # Add log directories
    aggregator.add_log_directory("logs")
    aggregator.add_log_directory("audit_logs")
    
    # Manual entry addition
    entry = LogEntry(
        id="test-1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        level="INFO",
        logger="test_logger",
        message="Test log message",
        correlation_id="test-correlation",
        source_file="test.log",
        component="test_component",
        metadata={"key": "value"}
    )
    aggregator.add_entry(entry)
    
    # Search examples
    result = aggregator.search(query="test", filters={"level": "INFO"}, limit=10)
    print(f"Search results: {len(result.entries)} entries found in {result.search_time_ms}ms")
    
    # Correlation trace
    trace = aggregator.get_correlation_trace("test-correlation")
    print(f"Correlation trace: {len(trace)} entries")
    
    # Metrics
    metrics = aggregator.get_metrics()
    print(f"Aggregator metrics: {metrics}")
    
    # Export
    aggregator.export_logs(Path("exported_logs.json"), format="json")
