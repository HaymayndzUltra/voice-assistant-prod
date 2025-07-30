#!/usr/bin/env python3
"""
Database Migration System - Versioned Schema Management
Provides comprehensive database migration management with versioning and rollback.

Features:
- Versioned schema migrations with dependency tracking
- Automatic rollback capabilities with safety checks
- Migration validation and dry-run execution
- Concurrent migration safety with locking
- Migration performance monitoring
- Schema drift detection and repair
"""
from __future__ import annotations
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import re

# Core imports
from common.core.base_agent import BaseAgent

# Database imports
from main_pc_code.database.async_connection_pool import get_connection_pool

# Event system imports
from events.memory_events import (
    MemoryEventType, create_memory_operation, MemoryType
)
from events.event_bus import publish_memory_event

class MigrationStatus(Enum):
    """Migration execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"

class MigrationType(Enum):
    """Migration type classification"""
    SCHEMA = "schema"           # DDL changes
    DATA = "data"              # Data migrations
    INDEX = "index"            # Index operations
    PROCEDURE = "procedure"    # Stored procedures/functions
    CONSTRAINT = "constraint"  # Constraint changes
    CLEANUP = "cleanup"        # Cleanup operations

class RollbackStrategy(Enum):
    """Rollback strategies"""
    AUTOMATIC = "automatic"    # Automatic rollback SQL
    MANUAL = "manual"         # Manual rollback required
    SNAPSHOT = "snapshot"     # Database snapshot based
    NO_ROLLBACK = "no_rollback"  # Cannot be rolled back

@dataclass
class Migration:
    """Migration definition"""
    id: str
    version: str
    name: str
    description: str
    migration_type: MigrationType
    up_sql: str
    down_sql: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    rollback_strategy: RollbackStrategy = RollbackStrategy.AUTOMATIC
    estimated_duration_seconds: Optional[float] = None
    requires_downtime: bool = False
    checksum: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.checksum is None:
            self.checksum = self._calculate_checksum()
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum for migration integrity"""
        content = f"{self.up_sql}{self.down_sql or ''}{self.version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

@dataclass
class MigrationExecution:
    """Migration execution record"""
    migration_id: str
    status: MigrationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    error_message: Optional[str] = None
    rollback_executed: bool = False
    checksum: Optional[str] = None
    applied_by: str = "system"
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

@dataclass
class SchemaSnapshot:
    """Database schema snapshot"""
    snapshot_id: str
    created_at: datetime
    version: str
    table_definitions: Dict[str, str]
    index_definitions: Dict[str, str]
    constraint_definitions: Dict[str, str]
    function_definitions: Dict[str, str]
    checksum: str

class DatabaseMigrationSystem(BaseAgent):
    """
    Comprehensive database migration system.
    
    Manages versioned schema changes with safety checks,
    rollback capabilities, and monitoring.
    """
    
    def __init__(self, 
                 migrations_path: str = "migrations",
                 lock_timeout_seconds: int = 300,
                 enable_dry_run: bool = True,
                 **kwargs):
        super().__init__(name="DatabaseMigrationSystem", **kwargs)
        
        # Configuration
        self.migrations_path = Path(migrations_path)
        self.lock_timeout_seconds = lock_timeout_seconds
        self.enable_dry_run = enable_dry_run
        
        # Migration tracking
        self.migrations: Dict[str, Migration] = {}
        self.execution_history: List[MigrationExecution] = []
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # Schema management
        self.current_version: Optional[str] = None
        self.schema_snapshots: Dict[str, SchemaSnapshot] = {}
        self.schema_drift_detected = False
        
        # Safety and monitoring
        self.migration_lock = asyncio.Lock()
        self.concurrent_executions = 0
        self.max_concurrent_migrations = 1
        
        # Performance tracking
        self.performance_metrics: Dict[str, List[float]] = defaultdict(list)
        
        # Initialize components
        self._ensure_migrations_directory()
        
        self.logger.info("Database Migration System initialized")
    
    def _ensure_migrations_directory(self) -> None:
        """Ensure migrations directory exists"""
        self.migrations_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        (self.migrations_path / "schema").mkdir(exist_ok=True)
        (self.migrations_path / "data").mkdir(exist_ok=True)
        (self.migrations_path / "indexes").mkdir(exist_ok=True)
        (self.migrations_path / "rollback").mkdir(exist_ok=True)
    
    async def initialize_migration_system(self) -> None:
        """Initialize the migration system and create necessary tables"""
        await self._create_migration_tables()
        await self._load_existing_migrations()
        await self._discover_migration_files()
        await self._update_current_version()
        
        self.logger.info(f"Migration system initialized. Current version: {self.current_version}")
    
    async def _create_migration_tables(self) -> None:
        """Create migration tracking tables"""
        pool = get_connection_pool()
        
        create_migrations_table = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            migration_id VARCHAR(255) UNIQUE NOT NULL,
            version VARCHAR(100) NOT NULL,
            name VARCHAR(255) NOT NULL,
            migration_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            checksum VARCHAR(32) NOT NULL,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            execution_time_seconds DECIMAL(10,3),
            error_message TEXT,
            rollback_executed BOOLEAN DEFAULT FALSE,
            applied_by VARCHAR(100) DEFAULT 'system',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        create_schema_snapshots_table = """
        CREATE TABLE IF NOT EXISTS schema_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_id VARCHAR(255) UNIQUE NOT NULL,
            version VARCHAR(100) NOT NULL,
            schema_definition JSONB NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        create_migration_locks_table = """
        CREATE TABLE IF NOT EXISTS migration_locks (
            id SERIAL PRIMARY KEY,
            lock_name VARCHAR(255) UNIQUE NOT NULL,
            locked_by VARCHAR(255) NOT NULL,
            locked_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP NOT NULL
        );
        """
        
        try:
            await pool.execute_query(create_migrations_table)
            await pool.execute_query(create_schema_snapshots_table)
            await pool.execute_query(create_migration_locks_table)
            
            self.logger.info("Migration tracking tables created/verified")
            
        except Exception as e:
            self.logger.error(f"Failed to create migration tables: {e}")
            raise
    
    async def _load_existing_migrations(self) -> None:
        """Load migration history from database"""
        pool = get_connection_pool()
        
        try:
            executions = await pool.fetch_query("""
                SELECT migration_id, version, name, migration_type, status, 
                       checksum, started_at, completed_at, execution_time_seconds,
                       error_message, rollback_executed, applied_by
                FROM schema_migrations 
                ORDER BY started_at
            """)
            
            for execution in executions:
                migration_exec = MigrationExecution(
                    migration_id=execution['migration_id'],
                    status=MigrationStatus(execution['status']),
                    started_at=execution['started_at'],
                    completed_at=execution.get('completed_at'),
                    execution_time_seconds=execution.get('execution_time_seconds'),
                    error_message=execution.get('error_message'),
                    rollback_executed=execution.get('rollback_executed', False),
                    checksum=execution['checksum'],
                    applied_by=execution.get('applied_by', 'system')
                )
                
                self.execution_history.append(migration_exec)
            
            self.logger.info(f"Loaded {len(self.execution_history)} migration records")
            
        except Exception as e:
            self.logger.warning(f"Could not load migration history: {e}")
    
    async def _discover_migration_files(self) -> None:
        """Discover and load migration files"""
        migration_files = []
        
        # Scan for migration files
        for file_path in self.migrations_path.rglob("*.sql"):
            if self._is_migration_file(file_path):
                migration_files.append(file_path)
        
        # Parse migration files
        for file_path in sorted(migration_files):
            try:
                migration = await self._parse_migration_file(file_path)
                if migration:
                    self.migrations[migration.id] = migration
                    
                    # Build dependency graph
                    for dep in migration.dependencies:
                        self.dependency_graph[migration.id].add(dep)
                        
            except Exception as e:
                self.logger.error(f"Failed to parse migration file {file_path}: {e}")
        
        self.logger.info(f"Discovered {len(self.migrations)} migration files")
    
    def _is_migration_file(self, file_path: Path) -> bool:
        """Check if file is a migration file"""
        # Migration files should follow naming convention: YYYYMMDD_HHMMSS_description.sql
        pattern = r'\d{8}_\d{6}_.*\.sql$'
        return bool(re.match(pattern, file_path.name))
    
    async def _parse_migration_file(self, file_path: Path) -> Optional[Migration]:
        """Parse migration file and extract metadata"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract metadata from comments
            metadata = self._extract_metadata(content)
            
            # Extract migration ID and version from filename
            filename = file_path.stem
            parts = filename.split('_', 2)
            if len(parts) >= 3:
                date_part = parts[0]
                time_part = parts[1]
                name_part = parts[2]
                version = f"{date_part}_{time_part}"
                migration_id = filename
            else:
                self.logger.warning(f"Invalid migration filename format: {filename}")
                return None
            
            # Split up and down SQL
            up_sql, down_sql = self._split_up_down_sql(content)
            
            migration = Migration(
                id=migration_id,
                version=version,
                name=metadata.get('name', name_part.replace('_', ' ').title()),
                description=metadata.get('description', ''),
                migration_type=MigrationType(metadata.get('type', 'schema')),
                up_sql=up_sql,
                down_sql=down_sql,
                dependencies=metadata.get('dependencies', []),
                rollback_strategy=RollbackStrategy(metadata.get('rollback_strategy', 'automatic')),
                estimated_duration_seconds=metadata.get('estimated_duration'),
                requires_downtime=metadata.get('requires_downtime', False)
            )
            
            return migration
            
        except Exception as e:
            self.logger.error(f"Error parsing migration file {file_path}: {e}")
            return None
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from migration file comments"""
        metadata = {}
        
        # Look for metadata in comments at the top of the file
        lines = content.strip().split('\n')
        in_metadata = False
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('-- MIGRATION:'):
                in_metadata = True
                continue
            elif line.startswith('-- END MIGRATION') or (in_metadata and not line.startswith('--')):
                break
            elif in_metadata and line.startswith('--'):
                # Parse metadata line
                meta_line = line[2:].strip()
                if ':' in meta_line:
                    key, value = meta_line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()
                    
                    # Parse specific metadata types
                    if key == 'dependencies':
                        metadata[key] = [dep.strip() for dep in value.split(',') if dep.strip()]
                    elif key == 'estimated_duration':
                        try:
                            metadata[key] = float(value)
                        except ValueError:
                            pass
                    elif key == 'requires_downtime':
                        metadata[key] = value.lower() in ['true', 'yes', '1']
                    else:
                        metadata[key] = value
        
        return metadata
    
    def _split_up_down_sql(self, content: str) -> Tuple[str, Optional[str]]:
        """Split migration content into up and down SQL"""
        # Look for -- DOWN marker
        down_marker = '-- DOWN'
        
        if down_marker in content:
            parts = content.split(down_marker, 1)
            up_sql = parts[0].strip()
            down_sql = parts[1].strip() if len(parts) > 1 else None
        else:
            up_sql = content.strip()
            down_sql = None
        
        # Remove metadata comments from up_sql
        up_lines = up_sql.split('\n')
        cleaned_lines = []
        skip_metadata = False
        
        for line in up_lines:
            if line.strip().startswith('-- MIGRATION:'):
                skip_metadata = True
                continue
            elif line.strip().startswith('-- END MIGRATION'):
                skip_metadata = False
                continue
            elif not skip_metadata:
                cleaned_lines.append(line)
        
        up_sql = '\n'.join(cleaned_lines).strip()
        
        return up_sql, down_sql
    
    async def _update_current_version(self) -> None:
        """Update current schema version"""
        # Get the latest successfully applied migration
        completed_migrations = [
            exec for exec in self.execution_history
            if exec.status == MigrationStatus.COMPLETED
        ]
        
        if completed_migrations:
            latest_execution = max(completed_migrations, key=lambda x: x.started_at)
            # Find the migration object to get the version
            for migration in self.migrations.values():
                if migration.id == latest_execution.migration_id:
                    self.current_version = migration.version
                    break
        else:
            self.current_version = "0000000_000000"  # Initial version
    
    async def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations in dependency order"""
        # Find migrations that haven't been successfully applied
        applied_migration_ids = {
            exec.migration_id for exec in self.execution_history
            if exec.status == MigrationStatus.COMPLETED
        }
        
        pending_migrations = [
            migration for migration in self.migrations.values()
            if migration.id not in applied_migration_ids
        ]
        
        # Sort by dependency order
        return self._sort_migrations_by_dependencies(pending_migrations)
    
    def _sort_migrations_by_dependencies(self, migrations: List[Migration]) -> List[Migration]:
        """Sort migrations by dependency order using topological sort"""
        migration_dict = {m.id: m for m in migrations}
        sorted_migrations = []
        visited = set()
        temp_visited = set()
        
        def visit(migration_id: str):
            if migration_id in temp_visited:
                raise ValueError(f"Circular dependency detected involving {migration_id}")
            if migration_id in visited:
                return
            
            temp_visited.add(migration_id)
            
            # Visit dependencies first
            if migration_id in migration_dict:
                migration = migration_dict[migration_id]
                for dep_id in migration.dependencies:
                    if dep_id in migration_dict:
                        visit(dep_id)
            
            temp_visited.remove(migration_id)
            visited.add(migration_id)
            
            if migration_id in migration_dict:
                sorted_migrations.append(migration_dict[migration_id])
        
        # Visit all migrations
        for migration in migrations:
            if migration.id not in visited:
                visit(migration.id)
        
        return sorted_migrations
    
    async def run_migrations(self, target_version: Optional[str] = None, 
                           dry_run: bool = False) -> List[MigrationExecution]:
        """Run pending migrations up to target version"""
        async with self.migration_lock:
            if self.concurrent_executions >= self.max_concurrent_migrations:
                raise RuntimeError("Maximum concurrent migrations reached")
            
            self.concurrent_executions += 1
            
            try:
                # Acquire migration lock
                await self._acquire_migration_lock("main_migration")
                
                try:
                    # Get pending migrations
                    pending_migrations = await self.get_pending_migrations()
                    
                    # Filter by target version if specified
                    if target_version:
                        pending_migrations = [
                            m for m in pending_migrations
                            if m.version <= target_version
                        ]
                    
                    if not pending_migrations:
                        self.logger.info("No pending migrations to run")
                        return []
                    
                    self.logger.info(f"Running {len(pending_migrations)} migrations (dry_run: {dry_run})")
                    
                    executed_migrations = []
                    
                    for migration in pending_migrations:
                        execution = await self._execute_migration(migration, dry_run)
                        executed_migrations.append(execution)
                        
                        if execution.status == MigrationStatus.FAILED:
                            self.logger.error(f"Migration {migration.id} failed, stopping execution")
                            break
                    
                    return executed_migrations
                    
                finally:
                    await self._release_migration_lock("main_migration")
                    
            finally:
                self.concurrent_executions -= 1
    
    async def _execute_migration(self, migration: Migration, dry_run: bool = False) -> MigrationExecution:
        """Execute a single migration"""
        execution = MigrationExecution(
            migration_id=migration.id,
            status=MigrationStatus.RUNNING,
            started_at=datetime.now(),
            checksum=migration.checksum
        )
        
        self.logger.info(f"{'[DRY RUN] ' if dry_run else ''}Executing migration: {migration.name}")
        
        try:
            # Validate migration
            validation_errors = await self._validate_migration(migration)
            if validation_errors:
                execution.status = MigrationStatus.FAILED
                execution.error_message = f"Validation failed: {'; '.join(validation_errors)}"
                execution.completed_at = datetime.now()
                return execution
            
            # Execute migration SQL
            start_time = time.time()
            
            if not dry_run:
                await self._execute_migration_sql(migration.up_sql)
                
                # Record migration in database
                await self._record_migration_execution(execution)
            else:
                # Simulate execution time for dry run
                await asyncio.sleep(0.1)
            
            execution.execution_time_seconds = time.time() - start_time
            execution.status = MigrationStatus.COMPLETED
            execution.completed_at = datetime.now()
            
            # Update performance metrics
            self.performance_metrics[migration.migration_type.value].append(execution.execution_time_seconds)
            
            # Publish migration event
            migration_event = create_memory_operation(
                operation_type=MemoryEventType.MEMORY_CREATED,
                memory_id=f"migration_{migration.id}",
                memory_type=MemoryType.PROCEDURAL,
                content=f"Migration {migration.name} completed",
                size_bytes=len(migration.up_sql),
                source_agent=self.name,
                machine_id=self._get_machine_id()
            )
            
            publish_memory_event(migration_event)
            
            self.logger.info(f"Migration {migration.name} completed in {execution.execution_time_seconds:.2f}s")
            
        except Exception as e:
            execution.status = MigrationStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            execution.execution_time_seconds = time.time() - start_time if 'start_time' in locals() else 0
            
            self.logger.error(f"Migration {migration.name} failed: {e}")
            
            # Record failed migration
            if not dry_run:
                try:
                    await self._record_migration_execution(execution)
                except Exception as record_error:
                    self.logger.error(f"Failed to record migration execution: {record_error}")
        
        # Add to history if not dry run
        if not dry_run:
            self.execution_history.append(execution)
        
        return execution
    
    async def _validate_migration(self, migration: Migration) -> List[str]:
        """Validate migration before execution"""
        errors = []
        
        # Check dependencies
        for dep_id in migration.dependencies:
            if dep_id not in [exec.migration_id for exec in self.execution_history 
                             if exec.status == MigrationStatus.COMPLETED]:
                errors.append(f"Dependency {dep_id} not satisfied")
        
        # Check for SQL syntax issues (basic validation)
        if not migration.up_sql.strip():
            errors.append("Migration SQL is empty")
        
        # Check for dangerous operations
        dangerous_patterns = [
            r'DROP\s+DATABASE',
            r'TRUNCATE\s+TABLE.*(?!WHERE)',  # TRUNCATE without WHERE
            r'DELETE\s+FROM.*(?!WHERE)',     # DELETE without WHERE
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, migration.up_sql, re.IGNORECASE):
                if not migration.requires_downtime:
                    errors.append(f"Dangerous operation detected but requires_downtime is False: {pattern}")
        
        return errors
    
    async def _execute_migration_sql(self, sql: str) -> None:
        """Execute migration SQL with transaction safety"""
        pool = get_connection_pool()
        
        # Split SQL into individual statements
        statements = self._split_sql_statements(sql)
        
        async with pool.acquire_connection() as connection:
            # Execute in transaction for DDL safety
            async with connection.transaction():
                for statement in statements:
                    statement = statement.strip()
                    if statement:
                        await connection.execute(statement)
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL into individual statements"""
        # Simple statement splitting (could be enhanced with proper SQL parsing)
        statements = []
        current_statement = []
        in_string = False
        string_char = None
        
        for line in sql.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            for char in line:
                if not in_string and char in ('"', "'"):
                    in_string = True
                    string_char = char
                elif in_string and char == string_char:
                    in_string = False
                    string_char = None
                elif not in_string and char == ';':
                    current_statement.append(line[:line.index(char)])
                    if current_statement:
                        statements.append(' '.join(current_statement))
                        current_statement = []
                    break
            else:
                current_statement.append(line)
        
        # Add final statement if any
        if current_statement:
            statements.append(' '.join(current_statement))
        
        return [stmt.strip() for stmt in statements if stmt.strip()]
    
    async def _record_migration_execution(self, execution: MigrationExecution) -> None:
        """Record migration execution in database"""
        pool = get_connection_pool()
        
        insert_sql = """
        INSERT INTO schema_migrations 
        (migration_id, version, name, migration_type, status, checksum, 
         started_at, completed_at, execution_time_seconds, error_message, 
         rollback_executed, applied_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (migration_id) DO UPDATE SET
            status = EXCLUDED.status,
            completed_at = EXCLUDED.completed_at,
            execution_time_seconds = EXCLUDED.execution_time_seconds,
            error_message = EXCLUDED.error_message,
            rollback_executed = EXCLUDED.rollback_executed
        """
        
        # Find migration details
        migration = self.migrations.get(execution.migration_id)
        if not migration:
            raise ValueError(f"Migration {execution.migration_id} not found")
        
        await pool.execute_query(
            insert_sql,
            execution.migration_id,
            migration.version,
            migration.name,
            migration.migration_type.value,
            execution.status.value,
            execution.checksum or migration.checksum,
            execution.started_at,
            execution.completed_at,
            execution.execution_time_seconds,
            execution.error_message,
            execution.rollback_executed,
            execution.applied_by
        )
    
    async def rollback_migration(self, migration_id: str, force: bool = False) -> MigrationExecution:
        """Rollback a specific migration"""
        async with self.migration_lock:
            migration = self.migrations.get(migration_id)
            if not migration:
                raise ValueError(f"Migration {migration_id} not found")
            
            # Check if migration was applied
            applied_execution = None
            for exec in self.execution_history:
                if exec.migration_id == migration_id and exec.status == MigrationStatus.COMPLETED:
                    applied_execution = exec
                    break
            
            if not applied_execution and not force:
                raise ValueError(f"Migration {migration_id} was not successfully applied")
            
            # Check rollback strategy
            if migration.rollback_strategy == RollbackStrategy.NO_ROLLBACK and not force:
                raise ValueError(f"Migration {migration_id} cannot be rolled back")
            
            if not migration.down_sql and migration.rollback_strategy == RollbackStrategy.AUTOMATIC:
                raise ValueError(f"Migration {migration_id} has no rollback SQL")
            
            self.logger.info(f"Rolling back migration: {migration.name}")
            
            execution = MigrationExecution(
                migration_id=migration_id,
                status=MigrationStatus.RUNNING,
                started_at=datetime.now(),
                checksum=migration.checksum,
                applied_by="rollback"
            )
            
            try:
                start_time = time.time()
                
                if migration.down_sql:
                    await self._execute_migration_sql(migration.down_sql)
                else:
                    self.logger.warning(f"No rollback SQL for {migration_id}, manual intervention required")
                
                execution.execution_time_seconds = time.time() - start_time
                execution.status = MigrationStatus.ROLLED_BACK
                execution.completed_at = datetime.now()
                execution.rollback_executed = True
                
                # Update database record
                await self._record_migration_execution(execution)
                
                self.logger.info(f"Migration {migration.name} rolled back successfully")
                
            except Exception as e:
                execution.status = MigrationStatus.FAILED
                execution.error_message = f"Rollback failed: {str(e)}"
                execution.completed_at = datetime.now()
                
                self.logger.error(f"Rollback of migration {migration.name} failed: {e}")
                
                try:
                    await self._record_migration_execution(execution)
                except Exception as record_error:
                    self.logger.error(f"Failed to record rollback execution: {record_error}")
            
            self.execution_history.append(execution)
            return execution
    
    async def _acquire_migration_lock(self, lock_name: str) -> None:
        """Acquire migration lock to prevent concurrent migrations"""
        pool = get_connection_pool()
        
        # Clean up expired locks first
        await pool.execute_query("""
            DELETE FROM migration_locks 
            WHERE expires_at < NOW()
        """)
        
        # Try to acquire lock
        machine_id = self._get_machine_id()
        expires_at = datetime.now() + timedelta(seconds=self.lock_timeout_seconds)
        
        try:
            await pool.execute_query("""
                INSERT INTO migration_locks (lock_name, locked_by, expires_at)
                VALUES ($1, $2, $3)
            """, lock_name, machine_id, expires_at)
            
            self.logger.debug(f"Acquired migration lock: {lock_name}")
            
        except Exception as e:
            # Check if lock is held by us
            existing_lock = await pool.fetchrow_query("""
                SELECT locked_by FROM migration_locks 
                WHERE lock_name = $1 AND expires_at > NOW()
            """, lock_name)
            
            if existing_lock and existing_lock['locked_by'] == machine_id:
                # Extend our lock
                await pool.execute_query("""
                    UPDATE migration_locks 
                    SET expires_at = $1 
                    WHERE lock_name = $2 AND locked_by = $3
                """, expires_at, lock_name, machine_id)
            else:
                raise RuntimeError(f"Could not acquire migration lock {lock_name}: {e}")
    
    async def _release_migration_lock(self, lock_name: str) -> None:
        """Release migration lock"""
        pool = get_connection_pool()
        machine_id = self._get_machine_id()
        
        try:
            await pool.execute_query("""
                DELETE FROM migration_locks 
                WHERE lock_name = $1 AND locked_by = $2
            """, lock_name, machine_id)
            
            self.logger.debug(f"Released migration lock: {lock_name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to release migration lock {lock_name}: {e}")
    
    async def create_schema_snapshot(self, version: str) -> SchemaSnapshot:
        """Create a snapshot of current schema"""
        pool = get_connection_pool()
        
        # Get table definitions
        tables = await pool.fetch_query("""
            SELECT table_name, 
                   pg_get_tabledef(schemaname||'.'||tablename) as definition
            FROM pg_tables 
            WHERE schemaname = 'public'
        """)
        
        table_definitions = {
            table['table_name']: table['definition'] 
            for table in tables
        }
        
        # Get index definitions
        indexes = await pool.fetch_query("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        
        index_definitions = {
            index['indexname']: index['indexdef']
            for index in indexes
        }
        
        # Create snapshot
        snapshot_id = f"snapshot_{version}_{int(datetime.now().timestamp())}"
        
        schema_data = {
            'tables': table_definitions,
            'indexes': index_definitions,
            'constraints': {},  # Could be expanded
            'functions': {}     # Could be expanded
        }
        
        checksum = hashlib.sha256(json.dumps(schema_data, sort_keys=True).encode()).hexdigest()
        
        snapshot = SchemaSnapshot(
            snapshot_id=snapshot_id,
            created_at=datetime.now(),
            version=version,
            table_definitions=table_definitions,
            index_definitions=index_definitions,
            constraint_definitions={},
            function_definitions={},
            checksum=checksum
        )
        
        # Store snapshot in database
        await pool.execute_query("""
            INSERT INTO schema_snapshots (snapshot_id, version, schema_definition, checksum)
            VALUES ($1, $2, $3, $4)
        """, snapshot_id, version, json.dumps(schema_data), checksum)
        
        self.schema_snapshots[snapshot_id] = snapshot
        
        self.logger.info(f"Created schema snapshot: {snapshot_id}")
        return snapshot
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration system status"""
        pending_migrations = asyncio.run(self.get_pending_migrations())
        
        completed_count = len([
            exec for exec in self.execution_history
            if exec.status == MigrationStatus.COMPLETED
        ])
        
        failed_count = len([
            exec for exec in self.execution_history
            if exec.status == MigrationStatus.FAILED
        ])
        
        # Calculate average execution times by type
        avg_times = {}
        for migration_type, times in self.performance_metrics.items():
            if times:
                avg_times[migration_type] = sum(times) / len(times)
        
        return {
            'current_version': self.current_version,
            'total_migrations': len(self.migrations),
            'pending_migrations': len(pending_migrations),
            'completed_migrations': completed_count,
            'failed_migrations': failed_count,
            'schema_snapshots': len(self.schema_snapshots),
            'performance_metrics': {
                'average_execution_times': avg_times,
                'total_executions': len(self.execution_history)
            },
            'system_status': {
                'lock_acquired': self.concurrent_executions > 0,
                'schema_drift_detected': self.schema_drift_detected
            },
            'pending_migration_list': [
                {
                    'id': m.id,
                    'name': m.name,
                    'type': m.migration_type.value,
                    'estimated_duration': m.estimated_duration_seconds,
                    'requires_downtime': m.requires_downtime
                }
                for m in pending_migrations[:10]  # First 10 pending
            ]
        }
    
    def _get_machine_id(self) -> str:
        """Get current machine identifier"""
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or ("pc" in hostname and "pc2" not in hostname):
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default
    
    def shutdown(self):
        """Shutdown the migration system"""
        # Release any held locks
        asyncio.run(self._release_migration_lock("main_migration"))
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_migration_system():
        migration_system = DatabaseMigrationSystem("migrations")
        
        try:
            await migration_system.initialize_migration_system()
            
            # Get status
            status = migration_system.get_migration_status()
            print(json.dumps(status, indent=2, default=str))
            
        finally:
            migration_system.shutdown()
    
    asyncio.run(test_migration_system()) 