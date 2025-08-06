"""
Local Fine Tuner Agent
Purpose: Manages model fine-tuning and artifact management
Features: Model tuning, artifact management, job queuing
"""
from common.utils.path_manager import PathManager

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
from common.utils.log_setup import configure_logging
MAIN_PC_CODE_DIR = PathManager.get_main_pc_code()
if str(MAIN_PC_CODE_DIR) not in sys.path:
    
import zmq
import json
import logging
import sqlite3
import threading
import time
import os
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from transformers import Trainer, TrainingArguments
from peft import get_peft_model, LoraConfig, TaskType, prepare_model_for_kbit_training
from datasets import Dataset
from typing import Dict, Any
from common.core.base_agent import BaseAgent
# Import the model_client for centralized model loading
from main_pc_code.utils import model_client


# Import path manager for containerization-friendly paths
import sys
import os
from pathlib import Path
from common.utils.path_manager import PathManager

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    
# Import common utilities if available
import psutil
from datetime import datetime
from main_pc_code.utils.config_loader import load_config

config = load_config()

try:
    USE_COMMON_UTILS = True
except ImportError as e:
    print(f"Import error: {e}")
    USE_COMMON_UTILS = False

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logger = configure_logging(__name__)
    filename=str(PathManager.get_logs_dir() / str(PathManager.get_logs_dir() / "local_fine_tuner.log"))
)
logger = logging.getLogger(__name__)

class TuningStatus(Enum):
    """
    TuningStatus:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ArtifactType(Enum):
    MODEL = "model"
    CHECKPOINT = "checkpoint"
    CONFIG = "config"
    LOGS = "logs"
    METRICS = "metrics"

@dataclass
class TuningJob:
    id: str
    model_id: str
    config: Dict
    status: TuningStatus
    artifacts: Dict[ArtifactType, str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None

class LocalFineTunerAgent(BaseAgent):
    def __init__(self, port: int = None, name: str = None, **kwargs):
        agent_port = config.get('port', 5000) if port is None else port
        agent_name = config.get('name', 'LocalFineTunerAgent') if name is None else name
        super().__init__(port=agent_port, name=agent_name)
        # ZMQ setup
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        # Health status
        self.health_status = {
            "status": "ok",
            "service": "local_fine_tuner_agent",
            "port": self.port,
            "active_jobs": 0,
            "database_status": "ok"
        }
        # Database setup
        self.db_path = str(PathManager.get_data_dir() / str(PathManager.get_data_dir() / "local_fine_tuner.db"))
        self._init_db()
        # Job management
        self.active_jobs = {}
        self.job_queue = Queue()
        self.artifact_dir = "artifacts"
        self._init_artifact_dir()
        # Thread management
        self.job_thread = None
        self.is_running = True
        # Create output directory for models
        self.output_dir = "fine_tuned_models"
        os.makedirs(self.output_dir, exist_ok=True)
        # Initialize Phi-3-mini model for few-shot learning
        self.few_shot_model = None
        self.few_shot_tokenizer = None
        logger.info(f"Local Fine Tuner Agent initialized on port {self.port}")
    
    


        
    def _init_db(self):
        """Initialize the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create tables
            c.execute('''
                CREATE TABLE IF NOT EXISTS tuning_jobs (
                    id TEXT PRIMARY KEY,
                    model_id TEXT NOT NULL,
                    config TEXT NOT NULL,
                    status TEXT NOT NULL,
                    artifacts TEXT NOT NULL,
                    start_time DATETIME,
                    end_time DATETIME,
                    error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES tuning_jobs (id)
                )
            ''')
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS tuning_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    step INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES tuning_jobs (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            self.health_status["database_status"] = "ok"
            logger.info("Database initialized successfully")
        except Exception as e:
            self.health_status["database_status"] = "error"
            logger.error(f"Database initialization error: {e}")

    def _init_artifact_dir(self):
        """Initialize artifact directory structure."""
        os.makedirs(self.artifact_dir, exist_ok=True)
        for artifact_type in ArtifactType:
            os.makedirs(os.path.join(self.artifact_dir, artifact_type.value), exist_ok=True)

    def create_tuning_job(self, model_id: str, config: Dict) -> Dict:
        """Create a new tuning job."""
        try:
            job_id = f"job_{int(time.time())}_{model_id}"
            
            # Create job
            job = TuningJob(
                id=job_id,
                model_id=model_id,
                config=config,
                status=TuningStatus.PENDING,
                artifacts={}
            )
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO tuning_jobs 
                (id, model_id, config, status, artifacts)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                job.id,
                job.model_id,
                json.dumps(job.config),
                job.status.value,
                json.dumps({k.value: v for k, v in job.artifacts.items()})
            ))
            
            conn.commit()
            conn.close()
            
            # Add to queue
            self.job_queue.put(job)
            
            logger.info(f"Created tuning job: {job_id}")
            return {
                "status": "success",
                "job_id": job_id
            }
            
        except Exception as e:
            logger.error(f"Error creating tuning job: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def start_tuning_job(self, job_id: str) -> Dict:
        """Start a tuning job."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get job
            c.execute('SELECT * FROM tuning_jobs WHERE id = ?', (job_id,))
            job_data = c.fetchone()
            
            if not job_data:
                return {
                    "status": "error",
                    "message": "Job not found"
                }
            
            # Update status
            c.execute('''
                UPDATE tuning_jobs 
                SET status = ?, start_time = ? 
                WHERE id = ?
            ''', (TuningStatus.RUNNING.value, datetime.now(), job_id))
            
            conn.commit()
            conn.close()
            
            # Start job thread
            job = self._create_job_from_db(job_data)
            self.active_jobs[job_id] = job
            
            if not self.job_thread or not self.job_thread.is_alive():
                self.job_thread = threading.Thread(target=self._run_job_manager)
                self.job_thread.start()
            
            logger.info(f"Started tuning job: {job_id}")
            return {
                "status": "success",
                "message": "Job started"
            }
            
        except Exception as e:
            logger.error(f"Error starting tuning job: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def _create_job_from_db(self, job_data) -> TuningJob:
        """Create a TuningJob object from database row."""
        return TuningJob(
            id=job_data[0],
            model_id=job_data[1],
            config=json.loads(job_data[2]),
            status=TuningStatus(job_data[3]),
            artifacts={ArtifactType(k): v for k, v in json.loads(job_data[4]).items()},
            start_time=datetime.fromisoformat(job_data[5]) if job_data[5] else None,
            end_time=datetime.fromisoformat(job_data[6]) if job_data[6] else None,
            error=job_data[7]
        )

    def _run_job_manager(self):
        """Run the job management thread."""
        self.is_running = True
        
        while self.is_running:
            try:
                # Process active jobs
                for job_id, job in list(self.active_jobs.items()):
                    if job.status == TuningStatus.RUNNING:
                        # Execute tuning step
                        success = self._execute_tuning_step(job)
                        
                        if not success:
                            self._fail_job(job_id, "Tuning step failed")
                    
                    elif job.status in [TuningStatus.COMPLETED, TuningStatus.FAILED, TuningStatus.CANCELLED]:
                        self._cleanup_job(job_id)
                
                # Start new jobs if available
                while not self.job_queue.empty():
                    job = self.job_queue.get()
                    self.start_tuning_job(job.id)
                
                time.sleep(1)  # Prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error in job manager: {e}")

    def _execute_tuning_step(self, job: TuningJob) -> bool:
        """Execute a single tuning step."""
        try:
            # Implement actual tuning logic here
            # This is a placeholder for the actual implementation
            
            # Record metrics
            self._record_metrics(job.id, {
                "loss": 0.1,  # Placeholder
                "accuracy": 0.9  # Placeholder
            })
            
            # Save artifacts
            self._save_artifacts(job)
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing tuning step: {e}")
            return False

    def _record_metrics(self, job_id: str, metrics: Dict):
        """Record tuning metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            for metric_name, value in metrics.items():
                c.execute('''
                    INSERT INTO tuning_metrics 
                    (job_id, metric_name, value, step)
                    VALUES (?, ?, ?, ?)
                ''', (job_id, metric_name, value, 1))  # Step is placeholder
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error recording metrics: {e}")

    def _save_artifacts(self, job: TuningJob):
        """Save job artifacts."""
        try:
            # Create job-specific directory
            job_dir = os.path.join(self.artifact_dir, job.id)
            os.makedirs(job_dir, exist_ok=True)
            
            # Save artifacts
            for artifact_type in ArtifactType:
                artifact_path = os.path.join(job_dir, f"{artifact_type.value}.json")
                
                # Save placeholder data
                with open(artifact_path, 'w') as f:
                    json.dump({
                        "type": artifact_type.value,
                        "job_id": job.id,
                        "timestamp": datetime.now().isoformat()
                    }, f)
                
                # Update job artifacts
                job.artifacts[artifact_type] = artifact_path
                
                # Update database
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                c.execute('''
                    INSERT INTO artifacts 
                    (job_id, type, path, metadata)
                    VALUES (?, ?, ?, ?)
                ''', (
                    job.id,
                    artifact_type.value,
                    artifact_path,
                    json.dumps({"timestamp": datetime.now().isoformat()})
                ))
                
                conn.commit()
                conn.close()
            
        except Exception as e:
            logger.error(f"Error saving artifacts: {e}")

    def _fail_job(self, job_id: str, error: str):
        """Mark a job as failed."""
        try:
            job = self.active_jobs[job_id]
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                UPDATE tuning_jobs 
                SET status = ?, end_time = ?, error = ? 
                WHERE id = ?
            ''', (TuningStatus.FAILED.value, datetime.now(), error, job_id))
            
            conn.commit()
            conn.close()
            
            # Update job object
            job.status = TuningStatus.FAILED
            job.end_time = datetime.now()
            job.error = error
            
            logger.info(f"Failed tuning job: {job_id}")
            
        except Exception as e:
            logger.error(f"Error failing job: {e}")

    def _cleanup_job(self, job_id: str):
        """Clean up a completed job."""
        try:
            self.active_jobs[job_id]
            
            # Remove from active jobs
            del self.active_jobs[job_id]
            
            logger.info(f"Cleaned up job: {job_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up job: {e}")

    def get_job_status(self, job_id: str) -> Dict:
        """Get status of a tuning job."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get job
            c.execute('SELECT * FROM tuning_jobs WHERE id = ?', (job_id,))
            job_data = c.fetchone()
            
            if not job_data:
                return {
                    "status": "error",
                    "message": "Job not found"
                }
            
            job = self._create_job_from_db(job_data)
            
            # Get latest metrics
            c.execute('''
                SELECT metric_name, value 
                FROM tuning_metrics 
                WHERE job_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''', (job_id,))
            
            metrics = {row[0]: row[1] for row in c.fetchall()}
            
            # Get artifacts
            c.execute('''
                SELECT type, path 
                FROM artifacts 
                WHERE job_id = ?
            ''', (job_id,))
            
            artifacts = {row[0]: row[1] for row in c.fetchall()}
            
            conn.close()
            
            return {
                "status": "success",
                "job": {
                    "id": job.id,
                    "model_id": job.model_id,
                    "status": job.status.value,
                    "start_time": job.start_time.isoformat() if job.start_time else None,
                    "end_time": job.end_time.isoformat() if job.end_time else None,
                    "error": job.error,
                    "metrics": metrics,
                    "artifacts": artifacts
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        try:
            action = request.get("action")
            
            # Update health status
            self._update_health_status()
            
            if action == "health_check":
                return {
                    "status": "ok",
                    "service": "local_fine_tuner_agent",
                    "ready": True,
                    "initialized": True,
                    "message": "LocalFineTunerAgent is healthy",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": self.health_status["uptime"],
                    "active_jobs": self.health_status["active_jobs"],
                    "database_status": self.health_status["database_status"]
                }
            
            elif action == "create_job":
                return self.create_tuning_job(
                    request["model_id"],
                    request["config"]
                )
                
            elif action == "start_job":
                return self.start_tuning_job(request["job_id"])
                
            elif action == "get_status":
                return self.get_job_status(request["job_id"])
                
            else:
                return {
                    "status": "error",
                    "message": "Unknown action"
                }
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def run(self):
        """Run the agent's main loop (poller-based)"""
        logger.info(f"Starting Local Fine Tuner Agent on port {self.port}")
        
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        
        while self.is_running:
            try:
                socks = dict(poller.poll(1000))  # 1-s tick
                if self.socket in socks:
                    # Receive request
                    request = json.loads(self.socket.recv_string())
                    
                    # Process request
                    response = self.handle_request(request)
                    
                    # Send response
                    self.socket.send_string(json.dumps(response))
            except zmq.Again:
                # No message received; continue
                continue
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                try:
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": str(e)
                    }))
                except zmq.ZMQError:
                    # Socket may be in bad state; skip sending
                    pass

    def stop(self):
        """Stop the agent."""
        logger.info("Stopping Local Fine Tuner Agent")
        self.is_running = False
        if self.job_thread:
            self.job_thread.join()
        self.socket.close()
        self.context.term()

        # Set running flag to false to stop all threads
        self.running = False
        
        # Wait for threads to finish
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
            logging.info("Health thread joined")
        
        # Close health socket if it exists
        if hasattr(self, "health_socket"):
            self.health_socket.close()
            logging.info("Health socket closed")

    def _load_model(self, model_name):
        """Load a pre-trained model using the centralized ModelManagerAgent"""
        try:
            # Instead of direct loading, use the model_client to request the model
            # Generate a simple prompt to get the tokenizer and model from the ModelManagerAgent
            response = model_client.generate(
                prompt=f"Initialize tokenizer and model for {model_name}",
                quality="quality",  # Use high quality for fine-tuning
                model_name=model_name
            )
            
            if response.get("status") != "success":
                error_msg = response.get("message", "Unknown error")
                logger.error(f"Error loading model {model_name} via model_client: {error_msg}")
                raise RuntimeError(f"Failed to load model via ModelManagerAgent: {error_msg}")
            
            # For compatibility with the existing code, we need to return a model and tokenizer
            # However, since we're now using the ModelManagerAgent, we'll need to adapt our fine-tuning
            # approach to work with the centralized model loading
            
            # For now, we'll log a warning and fall back to direct loading if absolutely necessary
            logger.warning(f"Model {model_name} loaded via ModelManagerAgent. Fine-tuning will need to be adapted.")
            
            # For compatibility with existing code, we'll return placeholder objects
            # that will trigger appropriate errors if misused
            class ModelClientModel:
                def __init__(self, model_name):
                    self.model_name = model_name
                def __getattr__(self, name):
                    raise NotImplementedError(f"Direct model access via {name} is not supported when using ModelManagerAgent. Use model_client.generate() instead.")
            
            class ModelClientTokenizer:
                def __init__(self, model_name):
                    self.model_name = model_name
                def __getattr__(self, name):
                    raise NotImplementedError(f"Direct tokenizer access via {name} is not supported when using ModelManagerAgent. Use model_client.generate() instead.")
            
            return ModelClientModel(model_name), ModelClientTokenizer(model_name)
            
        except Exception as e:
            logger.error(f"Error loading model {model_name} via model_client: {str(e)}")
            # Log the error to the error bus
            try:
                self.error_bus_pub.send_string(f"ERROR:LocalFineTunerAgent:model_loading:{str(e)}")
            except:
                pass
            raise
    
    def _prepare_lora_config(self, model_name):
        """Prepare LoRA configuration"""
        return LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=8,
            lora_alpha=32,
            lora_dropout=0.1
        )
    
    def _initialize_few_shot_model(self):
        """Initialize the Phi-3-mini model for few-shot learning"""
        if self.few_shot_model is None:
            try:
                model_name = "microsoft/phi-3-mini"
                self.few_shot_model, self.few_shot_tokenizer = self._load_model(model_name)
                self.few_shot_model = prepare_model_for_kbit_training(self.few_shot_model)
                logger.info("Phi-3-mini model initialized for few-shot learning")
            except Exception as e:
                logger.error(f"Error initializing few-shot model: {str(e)}")
                raise
    
    def trigger_few_shot_learning(self, examples):
        """Perform few-shot learning using Phi-3-mini model
        
        Args:
            examples (list): List of dictionaries containing input-output pairs
                Each dict should have 'input' and 'output' keys
        
        Returns:
            dict: Status of the few-shot learning process
        """
        try:
            # Initialize model if not already done
            self._initialize_few_shot_model()
            
            # Prepare dataset
            dataset_dict = {
                'input': [ex['input'] for ex in examples],
                'output': [ex['output'] for ex in examples]
            }
            dataset = Dataset.from_dict(dataset_dict)
            
            # Prepare LoRA config for efficient fine-tuning
            peft_config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,
                inference_mode=False,
                r=4,  # Smaller rank for faster training
                lora_alpha=16,
                lora_dropout=0.1,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
            )
            
            # Prepare model for LoRA fine-tuning
            model = get_peft_model(self.few_shot_model, peft_config)
            
            # Prepare training arguments for quick fine-tuning
            training_args = TrainingArguments(
                output_dir=os.path.join(self.output_dir, "few_shot"),
                num_train_epochs=3,
                per_device_train_batch_size=2,
                gradient_accumulation_steps=4,
                learning_rate=1e-4,
                max_steps=50,  # Limit training steps for quick adaptation
                save_strategy="no",
                logging_steps=5,
                fp16=True  # Use mixed precision for faster training
            )
            
            # Initialize trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=dataset,
                tokenizer=self.few_shot_tokenizer
            )
            
            # Start training
            trainer.train()
            
            # Save the fine-tuned model
            output_path = os.path.join(self.output_dir, "few_shot", "final_model")
            model.save_pretrained(output_path)
            
            return {
                'status': 'success',
                'message': 'Few-shot learning completed successfully',
                'model_path': output_path
            }
            
        except Exception as e:
            logger.error(f"Error in few-shot learning: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _get_health_status(self) -> Dict[str, Any]:
        base_status = super()._get_health_status()
        self._update_health_status()
        base_status.update({
            "service": "local_fine_tuner_agent",
            "active_jobs": self.health_status["active_jobs"],
            "database_status": self.health_status["database_status"]
        })
        return base_status

    def cleanup(self):
        logger.info("Stopping Local Fine Tuner Agent")
        super().cleanup()
        logger.info("Local Fine Tuner Agent stopped")


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = LocalFineTunerAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup() 