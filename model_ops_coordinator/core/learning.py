"""Learning and fine-tuning job management for ModelOps Coordinator."""

import sqlite3
import uuid
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pathlib import Path

from .errors import LearningJobError, ConfigurationError
from .lifecycle import LifecycleModule
from .telemetry import Telemetry
from .schemas import Config, JobStatus


class LearningJobType(Enum):
    """Types of learning jobs."""
    FINE_TUNE = "fine_tune"
    RLHF = "rlhf"
    LORA = "lora"
    DISTILLATION = "distillation"


class LearningJob:
    """Learning job representation."""
    
    def __init__(self, job_id: str, job_type: str, model_name: str, 
                 dataset_path: str, parameters: Dict[str, Any]):
        self.job_id = job_id
        self.job_type = job_type
        self.model_name = model_name
        self.dataset_path = dataset_path
        self.parameters = parameters
        self.status = JobStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress = 0.0
        self.error_message: Optional[str] = None
        self.result_path: Optional[str] = None


class LearningModule:
    """Learning and fine-tuning job manager with SQLite job store."""
    
    def __init__(self, config: Config, lifecycle: LifecycleModule, telemetry: Telemetry):
        """Initialize learning module."""
        self.config = config
        self.lifecycle = lifecycle
        self.telemetry = telemetry
        self._lock = threading.RLock()
        
        # SQLite database for job storage
        self.db_path = Path(config.learning.job_store)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Job tracking
        self._active_jobs: Dict[str, LearningJob] = {}
        self._job_threads: Dict[str, threading.Thread] = {}
        
        # Initialize database
        self._init_database()
        
        # Load existing jobs
        self._load_jobs_from_db()
    
    def _init_database(self):
        """Initialize SQLite database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS learning_jobs (
                        job_id TEXT PRIMARY KEY,
                        job_type TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        dataset_path TEXT NOT NULL,
                        parameters TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        progress REAL DEFAULT 0.0,
                        error_message TEXT,
                        result_path TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            raise ConfigurationError("learning_db", f"Failed to initialize database: {e}")
    
    def _load_jobs_from_db(self):
        """Load existing jobs from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT job_id, job_type, model_name, dataset_path, parameters,
                           status, created_at, started_at, completed_at, progress,
                           error_message, result_path
                    FROM learning_jobs
                    WHERE status IN ('pending', 'running')
                """)
                
                for row in cursor.fetchall():
                    job = self._row_to_job(row)
                    self._active_jobs[job.job_id] = job
                    
                    # Restart running jobs as pending
                    if job.status == JobStatus.RUNNING:
                        job.status = JobStatus.PENDING
                        self._update_job_in_db(job)
                        
        except Exception as e:
            self.telemetry.record_error("job_load_error", "learning")
    
    def _row_to_job(self, row) -> LearningJob:
        """Convert database row to LearningJob object."""
        import json
        
        job = LearningJob(
            job_id=row[0],
            job_type=row[1],
            model_name=row[2],
            dataset_path=row[3],
            parameters=json.loads(row[4])
        )
        
        job.status = JobStatus(row[5])
        job.created_at = datetime.fromisoformat(row[6])
        job.started_at = datetime.fromisoformat(row[7]) if row[7] else None
        job.completed_at = datetime.fromisoformat(row[8]) if row[8] else None
        job.progress = row[9]
        job.error_message = row[10]
        job.result_path = row[11]
        
        return job
    
    def submit_job(self, job_type: str, model_name: str, dataset_path: str,
                   parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Submit a new learning job.
        
        Args:
            job_type: Type of learning job
            model_name: Target model name
            dataset_path: Path to training dataset
            parameters: Job parameters
            
        Returns:
            Job ID
            
        Raises:
            LearningJobError: If job submission fails
        """
        try:
            # Validate inputs
            if job_type not in [jt.value for jt in LearningJobType]:
                raise LearningJobError("invalid_job_type", f"Unknown job type: {job_type}")
            
            if not Path(dataset_path).exists():
                raise LearningJobError("dataset_not_found", f"Dataset not found: {dataset_path}")
            
            # Check if we can run more parallel jobs
            running_count = sum(1 for job in self._active_jobs.values() 
                              if job.status == JobStatus.RUNNING)
            
            if running_count >= self.config.learning.max_parallel_jobs:
                # Job will be queued
                pass
            
            # Create job
            job_id = str(uuid.uuid4())
            job = LearningJob(
                job_id=job_id,
                job_type=job_type,
                model_name=model_name,
                dataset_path=dataset_path,
                parameters=parameters or {}
            )
            
            # Store in database and memory
            with self._lock:
                self._active_jobs[job_id] = job
                self._store_job_in_db(job)
            
            # Try to start job immediately
            self._try_start_next_job()
            
            return job_id
            
        except Exception as e:
            if isinstance(e, LearningJobError):
                raise
            else:
                raise LearningJobError("job_submission_failed", str(e))
    
    def _store_job_in_db(self, job: LearningJob):
        """Store job in SQLite database."""
        import json
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO learning_jobs 
                    (job_id, job_type, model_name, dataset_path, parameters,
                     status, created_at, started_at, completed_at, progress,
                     error_message, result_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.job_id, job.job_type, job.model_name, job.dataset_path,
                    json.dumps(job.parameters), job.status.value,
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.progress, job.error_message, job.result_path
                ))
                conn.commit()
        except Exception as e:
            self.telemetry.record_error("job_store_error", "learning")
    
    def _update_job_in_db(self, job: LearningJob):
        """Update job in SQLite database."""
        import json
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE learning_jobs SET
                        status = ?, started_at = ?, completed_at = ?,
                        progress = ?, error_message = ?, result_path = ?
                    WHERE job_id = ?
                """, (
                    job.status.value,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.progress, job.error_message, job.result_path,
                    job.job_id
                ))
                conn.commit()
        except Exception as e:
            self.telemetry.record_error("job_update_error", "learning")
    
    def _try_start_next_job(self):
        """Try to start the next pending job if capacity allows."""
        with self._lock:
            running_count = sum(1 for job in self._active_jobs.values() 
                              if job.status == JobStatus.RUNNING)
            
            if running_count >= self.config.learning.max_parallel_jobs:
                return
            
            # Find next pending job
            pending_jobs = [job for job in self._active_jobs.values() 
                          if job.status == JobStatus.PENDING]
            
            if not pending_jobs:
                return
            
            # Start oldest pending job
            next_job = min(pending_jobs, key=lambda j: j.created_at)
            self._start_job(next_job)
    
    def _start_job(self, job: LearningJob):
        """Start executing a learning job."""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        # Update database
        self._update_job_in_db(job)
        
        # Start job thread
        job_thread = threading.Thread(
            target=self._execute_job,
            args=(job,),
            name=f"LearningJob-{job.job_id[:8]}",
            daemon=True
        )
        
        self._job_threads[job.job_id] = job_thread
        job_thread.start()
        
        # Update metrics
        self._update_job_metrics()
    
    def _execute_job(self, job: LearningJob):
        """Execute a learning job (simulation)."""
        start_time = time.time()
        
        try:
            # Simulate job execution
            self._simulate_learning_job(job)
            
            # Job completed successfully
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 1.0
            job.result_path = f"/models/{job.model_name}_trained_{job.job_id[:8]}.pt"
            
            # Record metrics
            duration = time.time() - start_time
            self.telemetry.record_learning_job_completion(job.job_type, duration)
            
        except Exception as e:
            # Job failed
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = str(e)
            
            self.telemetry.record_error("learning_job_failed", "learning")
        
        finally:
            # Update database
            self._update_job_in_db(job)
            
            # Cleanup
            with self._lock:
                if job.job_id in self._job_threads:
                    del self._job_threads[job.job_id]
                
                # Remove from active jobs if completed/failed
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    if job.job_id in self._active_jobs:
                        del self._active_jobs[job.job_id]
            
            # Update metrics and try to start next job
            self._update_job_metrics()
            self._try_start_next_job()
    
    def _simulate_learning_job(self, job: LearningJob):
        """
        Simulate learning job execution.
        
        In production, this would:
        1. Load the base model
        2. Load and preprocess the dataset
        3. Set up training configuration
        4. Run training loop with periodic checkpoints
        5. Evaluate and save final model
        """
        # Simulate different job durations based on type
        duration_map = {
            "fine_tune": 120,    # 2 minutes
            "rlhf": 180,         # 3 minutes
            "lora": 60,          # 1 minute
            "distillation": 90   # 1.5 minutes
        }
        
        total_duration = duration_map.get(job.job_type, 120)
        steps = 20  # 20 progress steps
        step_duration = total_duration / steps
        
        for step in range(steps):
            # Check for cancellation
            if job.status == JobStatus.CANCELLED:
                raise Exception("Job cancelled")
            
            # Simulate training step
            time.sleep(step_duration * 0.01)  # Scaled down for demo
            
            # Update progress
            job.progress = (step + 1) / steps
            self._update_job_in_db(job)
            
            # Simulate occasional failures (1% chance)
            import random
            if random.random() < 0.01:
                raise Exception("Simulated training failure")
    
    def get_job_status(self, job_id: str) -> Optional[LearningJob]:
        """Get status of a specific job."""
        with self._lock:
            if job_id in self._active_jobs:
                return self._active_jobs[job_id]
        
        # Check database for completed jobs
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM learning_jobs WHERE job_id = ?", (job_id,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_job(row)
        except Exception:
            pass
        
        return None
    
    def list_jobs(self, status_filter: Optional[str] = None) -> List[LearningJob]:
        """List all jobs, optionally filtered by status."""
        jobs = []
        
        # Add active jobs
        with self._lock:
            jobs.extend(self._active_jobs.values())
        
        # Add completed jobs from database
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM learning_jobs"
                params = ()
                
                if status_filter:
                    query += " WHERE status = ?"
                    params = (status_filter,)
                
                query += " ORDER BY created_at DESC"
                
                cursor = conn.execute(query, params)
                for row in cursor.fetchall():
                    job = self._row_to_job(row)
                    if job.job_id not in self._active_jobs:
                        jobs.append(job)
        except Exception:
            pass
        
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job."""
        with self._lock:
            if job_id not in self._active_jobs:
                return False
            
            job = self._active_jobs[job_id]
            
            if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
                return False
            
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            job.error_message = "Job cancelled by user"
            
            self._update_job_in_db(job)
            return True
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """Get learning job statistics."""
        with self._lock:
            status_counts = {}
            for status in JobStatus:
                status_counts[status.value] = 0
            
            # Count active jobs
            for job in self._active_jobs.values():
                status_counts[job.status.value] += 1
            
            # Update telemetry
            self.telemetry.update_learning_jobs(status_counts)
            
            return {
                'status_counts': status_counts,
                'active_jobs': len(self._active_jobs),
                'running_jobs': status_counts[JobStatus.RUNNING.value],
                'max_parallel': self.config.learning.max_parallel_jobs
            }
    
    def _update_job_metrics(self):
        """Update job metrics in telemetry."""
        self.get_job_statistics()  # This updates telemetry
    
    def shutdown(self):
        """Shutdown learning module."""
        # Cancel all running jobs
        with self._lock:
            for job in self._active_jobs.values():
                if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
                    job.status = JobStatus.CANCELLED
                    job.error_message = "System shutdown"
                    self._update_job_in_db(job)
        
        # Wait for job threads to complete
        max_wait = 30.0  # 30 seconds
        start_time = time.time()
        
        while self._job_threads and (time.time() - start_time) < max_wait:
            time.sleep(0.1)