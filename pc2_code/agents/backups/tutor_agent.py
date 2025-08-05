import os
import json
import time
import logging
import threading
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import zmq
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import uuid
import sys
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", ".."))
from common.utils.path_manager import PathManager
# Add project root to Python path for common_utils import
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root)

# Import BaseAgent
from main_pc_code.src.core.base_agent import BaseAgent

# Import config loader
from pc2_code.agents.utils.config_loader import Config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error


# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS = True
except ImportError as e:
    print(f"Import error: {e}")
    USE_COMMON_UTILS = False

# Load configuration at the module level
try:
    config = Config().get_config()
    TUTOR_CONFIG = config.get('tutor', {})
except Exception as e:
    print(f"Failed to load config: {e}")
    # Fallback to local config file
    try:
        with open(PathManager.join_path("config", "tutor_config.json"), "r") as f:
            TUTOR_CONFIG = json.load(f).get("tutor", {})
    except Exception as e:
        print(f"Failed to load local config: {e}")
        TUTOR_CONFIG = {}

# Setup logging
LOG_PATH = str(PathManager.get_logs_dir() / "tutor_agent.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TutorAgent")

@dataclass
class StudentProfile:
    """Represents a student's profile and learning history"""
    student_id: str
    name: str
    age: int
    grade_level: int
    learning_style: str
    interests: List[str]
    created_at: float
    last_active: float
    performance_history: List[Dict[str, Any]]
    current_lesson: Optional[str] = None
    mastery_levels: Dict[str, float] = field(default_factory=dict)
    weak_areas: List[str] = field(default_factory=list)
    strong_areas: List[str] = field(default_factory=list)

@dataclass
class Lesson:
    """Represents a lesson module"""
    lesson_id: str
    title: str
    subject: str
    difficulty: float
    age_range: Tuple[int, int]
    prerequisites: List[str]
    content: Dict[str, Any]
    assessment_criteria: Dict[str, Any]
    estimated_duration: int  # in minutes

@dataclass
class PerformanceMetrics:
    """Represents performance metrics for a lesson attempt"""
    accuracy: float
    speed: float
    confidence: float
    completion_time: float
    mistakes: List[Dict[str, Any]]
    strengths: List[str]
    areas_for_improvement: List[str]

class AdaptiveLearningEngine:
    """Core engine for adaptive learning and difficulty adjustment"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.scaler = StandardScaler()
        self.difficulty_model = self._init_difficulty_model()
        self.learning_style_model = self._init_learning_style_model()
        
    def _init_difficulty_model(self) -> nn.Module:
        """Initialize neural network for difficulty prediction"""
        model = nn.Sequential(
            nn.Linear(5, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
        return model
        
    def _init_learning_style_model(self) -> KMeans:
        """Initialize clustering model for learning style analysis"""
        return KMeans(n_clusters=4, random_state=42)
        
    def adjust_difficulty(self, student_profile: StudentProfile, 
                         current_performance: PerformanceMetrics) -> float:
        """Adjust lesson difficulty based on performance"""
        # Prepare features
        mastery = 0.5
        if student_profile.mastery_levels and student_profile.current_lesson:
            mastery = student_profile.mastery_levels.get(student_profile.current_lesson, 0.5)
        features = np.array([
            current_performance.accuracy,
            current_performance.speed,
            current_performance.confidence,
            mastery,
            len(student_profile.performance_history) / 100  # Normalized experience
        ]).reshape(1, -1)
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features)
        
        # Predict difficulty adjustment
        with torch.no_grad():
            adjustment = self.difficulty_model(torch.FloatTensor(features_scaled)
            
        return float(adjustment[0])
        
    def analyze_learning_style(self, student_profile: StudentProfile) -> str:
        """Analyze student's learning style based on performance history"""
        if not student_profile.performance_history:
            return "balanced"
            
        # Extract features for clustering
        features = []
        for performance in student_profile.performance_history[-10:]:  # Last 10 lessons
            features.append([
                performance["accuracy"],
                performance["speed"],
                performance["confidence"],
                performance["completion_time"],
                len(performance["mistakes"])
            ])
            
        features = np.array(features)
        features_scaled = self.scaler.fit_transform(features)
        
        # Predict learning style cluster
        cluster = self.learning_style_model.fit_predict(features_scaled)
        
        # Map cluster to learning style
        styles = ["visual", "auditory", "kinesthetic", "balanced"]
        return styles[cluster[-1]]

class ProgressTracker:
    """Tracks and analyzes student progress"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.progress_db = {}  # In-memory database for progress tracking
        
    def update_progress(self, student_id: str, 
                       lesson_id: str, 
                       performance: PerformanceMetrics):
        """Update student's progress with new performance data"""
        if student_id not in self.progress_db:
            self.progress_db[student_id] = []
            
        self.progress_db[student_id].append({
            "timestamp": time.time(),
            "lesson_id": lesson_id,
            "performance": performance
        })
        
    def analyze_progress(self, student_id: str) -> Dict[str, Any]:
        """Analyze student's overall progress"""
        if student_id not in self.progress_db:
            return {"error": "No progress data found"}
            
        progress = self.progress_db[student_id]
        
        # Calculate overall metrics
        accuracy_trend = [p["performance"].accuracy for p in progress]
        speed_trend = [p["performance"].speed for p in progress]
        confidence_trend = [p["performance"].confidence for p in progress]
        
        # Identify weak and strong areas
        weak_areas = self._identify_weak_areas(progress)
        strong_areas = self._identify_strong_areas(progress)
        
        return {
            "overall_progress": {
                "accuracy": np.mean(accuracy_trend),
                "speed": np.mean(speed_trend),
                "confidence": np.mean(confidence_trend)
            },
            "trends": {
                "accuracy": accuracy_trend,
                "speed": speed_trend,
                "confidence": confidence_trend
            },
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "recommendations": self._generate_recommendations(progress)
        }
        
    def _identify_weak_areas(self, progress: List[Dict[str, Any]]) -> List[str]:
        """Identify areas where student struggles"""
        weak_areas = set()
        for p in progress[-5:]:  # Last 5 lessons
            for mistake in p["performance"].mistakes:
                weak_areas.add(mistake["area"])
        return list(weak_areas)
        
    def _identify_strong_areas(self, progress: List[Dict[str, Any]]) -> List[str]:
        """Identify areas where student excels"""
        strong_areas = set()
        for p in progress[-5:]:  # Last 5 lessons
            for strength in p["performance"].strengths:
                strong_areas.add(strength)
        return list(strong_areas)
        
    def _generate_recommendations(self, progress: List[Dict[str, Any]]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Analyze recent performance
        recent_performance = progress[-5:]
        avg_accuracy = np.mean([p["performance"].accuracy for p in recent_performance])
        
        if avg_accuracy < 0.7:
            recommendations.append("Consider reviewing previous lessons")
        elif avg_accuracy > 0.9:
            recommendations.append("Ready for more challenging content")
            
        # Add specific recommendations based on weak areas
        weak_areas = self._identify_weak_areas(recent_performance)
        for area in weak_areas:
            recommendations.append(f"Focus on improving {area}")
            
        return recommendations

class FeedbackGenerator:
    """Generates personalized feedback for students"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates = self._load_feedback_templates()
        
    def _load_feedback_templates(self) -> Dict[str, List[str]]:
        """Load feedback templates from configuration"""
        default_templates = {
            "high_performance": [
                "Excellent work! You've mastered this concept.",
                "Outstanding! Your understanding is exceptional.",
                "Fantastic job! You're making great progress."
            ],
            "medium_performance": [
                "Good work! You're on the right track.",
                "Nice job! With a bit more practice, you'll master this.",
                "You're making good progress. Keep it up!"
            ],
            "low_performance": [
                "You're making progress, but this area needs more attention.",
                "Let's focus on strengthening your understanding here.",
                "With more practice, you'll improve in this area."
            ],
            "improvement": [
                "You've shown improvement since last time!",
                "Your hard work is paying off! You're doing better than before.",
                "Great progress! You've improved significantly."
            ]
        }
        
        # Try to load templates from config
        templates = self.config.get("feedback_templates", default_templates)
        
        return templates
        
    def generate_feedback(self, performance: PerformanceMetrics, 
                         previous_performance: Optional[PerformanceMetrics] = None) -> str:
        """Generate personalized feedback based on performance"""
        import random
        
        # Determine performance level
        if performance.accuracy > 0.85:
            template_key = "high_performance"
        elif performance.accuracy > 0.6:
            template_key = "medium_performance"
        else:
            template_key = "low_performance"
            
        # Check for improvement
        if previous_performance and performance.accuracy > previous_performance.accuracy + 0.1:
            template_key = "improvement"
            
        # Select random template from appropriate category
        templates = self.templates.get(template_key, ["Good work!"])
        feedback = random.choice(templates)
        
        # Add specific feedback on areas for improvement
        if performance.areas_for_improvement:
            area = performance.areas_for_improvement[0]
            feedback += f" Focus on improving your {area}."
            
        return feedback

class ParentDashboard:
    """Dashboard for parents to track student progress"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dashboard_data = {}
        
    def update_dashboard(self, student_id: str, 
                        progress_data: Dict[str, Any]):
        """Update dashboard with new progress data"""
        if student_id not in self.dashboard_data:
            self.dashboard_data[student_id] = {
                "progress_history": [],
                "goals": [],
                "notifications": []
            }
            
        # Add new progress data
        self.dashboard_data[student_id]["progress_history"].append({
            "timestamp": datetime.now().isoformat(),
            "data": progress_data
        })
        
    def get_dashboard_data(self, student_id: str) -> Dict[str, Any]:
        """Get dashboard data for a student"""
        if student_id not in self.dashboard_data:
            return {"error": "No dashboard data found"}
            
        return self.dashboard_data[student_id]
        
    def set_goals(self, student_id: str, goals: Dict[str, Any]):
        """Set goals for a student"""
        if student_id not in self.dashboard_data:
            self.dashboard_data[student_id] = {
                "progress_history": [],
                "goals": [],
                "notifications": []
            }
            
        # Add new goal
        self.dashboard_data[student_id]["goals"].append({
            "timestamp": datetime.now().isoformat(),
            "goal": goals
        })
        
        return {"status": "success", "message": "Goal set successfully"}
        
    def add_notification(self, student_id: str, notification: str):
        """Add notification for parent"""
        if student_id not in self.dashboard_data:
            self.dashboard_data[student_id] = {
                "progress_history": [],
                "goals": [],
                "notifications": []
            }
            
        # Add notification
        self.dashboard_data[student_id]["notifications"].append({
            "timestamp": datetime.now().isoformat(),
            "message": notification,
            "read": False
        })

class TutorAgent(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()"""Main tutor agent that coordinates all tutoring functionality"""
    def __init__(self):
        # Get port from config
        port = TUTOR_CONFIG.get('port', 5605)
        
        # Initialize BaseAgent
        super().__init__(name="TutorAgent", port=port)
        
        # Initialize components
        self.learning_engine = AdaptiveLearningEngine(TUTOR_CONFIG)
        self.progress_tracker = ProgressTracker(TUTOR_CONFIG)
        self.feedback_generator = FeedbackGenerator(TUTOR_CONFIG)
        self.parent_dashboard = ParentDashboard(TUTOR_CONFIG)
        
        # Initialize student data
        self.students = {}
        self.lessons = {}
        
        # Load lessons if available
        self._load_lessons()
        
        logger.info("TutorAgent initialized successfully")
        
    def _load_lessons(self):
        """Load lesson data from storage"""
        try:
            lessons_path = TUTOR_CONFIG.get("lessons_path", PathManager.join_path("data", "lessons.json")
            if os.path.exists(lessons_path):
                with open(lessons_path, "r") as f:
                    lessons_data = json.load(f)
                    
                for lesson_id, lesson_data in lessons_data.items():
                    self.lessons[lesson_id] = Lesson(**lesson_data)
                    
                logger.info(f"Loaded {len(self.lessons)} lessons")
            else:
                logger.warning(f"Lessons file not found at {lessons_path}")
        except Exception as e:
            logger.error(f"Error loading lessons: {e}")
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        # Call parent implementation
        status = super()._get_health_status()
        
        # Add agent-specific health information
        status.update({
            "agent_type": "tutor",
            "students_count": len(self.students),
            "lessons_count": len(self.lessons),
            "components": {
                "learning_engine": hasattr(self, "learning_engine"),
                "progress_tracker": hasattr(self, "progress_tracker"),
                "feedback_generator": hasattr(self, "feedback_generator"),
                "parent_dashboard": hasattr(self, "parent_dashboard")
            }
        })
        
        return status
    
    def handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = message.get("action", "")
        
        if action in ["health_check", "health", "ping"]:
            return self._get_health_status()
        elif action == "get_student":
            return self._handle_get_student(message)
        elif action == "update_student":
            return self._handle_update_student(message)
        elif action == "get_lesson":
            return self._handle_get_lesson(message)
        elif action == "submit_performance":
            return self._handle_submit_performance(message)
        elif action == "get_progress":
            return self._handle_get_progress(message)
        elif action == "set_goal":
            return self._handle_set_goal(message)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def _handle_get_student(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_student request"""
        student_id = message.get("student_id")
        if not student_id:
            return {"status": "error", "message": "Missing student_id"}
            
        if student_id not in self.students:
            return {"status": "error", "message": "Student not found"}
            
        return {
            "status": "success",
            "student": self.students[student_id].__dict__
        }
    
    def _handle_update_student(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update_student request"""
        student_data = message.get("student_data")
        if not student_data:
            return {"status": "error", "message": "Missing student_data"}
            
        student_id = student_data.get("student_id")
        if not student_id:
            return {"status": "error", "message": "Missing student_id in student_data"}
            
        # Create or update student
        if student_id not in self.students:
            self.students[student_id] = StudentProfile(**student_data)
        else:
            # Update existing student
            for key, value in student_data.items():
                if hasattr(self.students[student_id], key):
                    setattr(self.students[student_id], key, value)
                    
        return {
            "status": "success",
            "message": "Student updated successfully"
        }
    
    def _handle_get_lesson(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_lesson request"""
        lesson_id = message.get("lesson_id")
        if not lesson_id:
            return {"status": "error", "message": "Missing lesson_id"}
            
        if lesson_id not in self.lessons:
            return {"status": "error", "message": "Lesson not found"}
            
        return {
            "status": "success",
            "lesson": self.lessons[lesson_id].__dict__
        }
    
    def _handle_submit_performance(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle submit_performance request"""
        student_id = message.get("student_id")
        lesson_id = message.get("lesson_id")
        performance_data = message.get("performance")
        
        if not student_id or not lesson_id or not performance_data:
            return {"status": "error", "message": "Missing required data"}
            
        if student_id not in self.students:
            return {"status": "error", "message": "Student not found"}
            
        if lesson_id not in self.lessons:
            return {"status": "error", "message": "Lesson not found"}
            
        # Create performance metrics
        performance = PerformanceMetrics(**performance_data)
        
        # Update progress tracker
        self.progress_tracker.update_progress(student_id, lesson_id, performance)
        
        # Generate feedback
        previous_performance = None
        if self.students[student_id].performance_history:
            prev_perf_data = self.students[student_id].performance_history[-1]
            if prev_perf_data.get("lesson_id") == lesson_id:
                previous_performance = PerformanceMetrics(**prev_perf_data.get("performance", {})
                
        feedback = self.feedback_generator.generate_feedback(performance, previous_performance)
        
        # Update student profile
        self.students[student_id].performance_history.append({
            "timestamp": time.time(),
            "lesson_id": lesson_id,
            "performance": performance_data
        })
        
        # Update parent dashboard
        progress_data = self.progress_tracker.analyze_progress(student_id)
        self.parent_dashboard.update_dashboard(student_id, progress_data)
        
        return {
            "status": "success",
            "message": "Performance submitted successfully",
            "feedback": feedback
        }
    
    def _handle_get_progress(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_progress request"""
        student_id = message.get("student_id")
        if not student_id:
            return {"status": "error", "message": "Missing student_id"}
            
        if student_id not in self.students:
            return {"status": "error", "message": "Student not found"}
            
        progress_data = self.progress_tracker.analyze_progress(student_id)
        
        return {
            "status": "success",
            "progress": progress_data
        }
    
    def _handle_set_goal(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set_goal request"""
        student_id = message.get("student_id")
        goal = message.get("goal")
        
        if not student_id or not goal:
            return {"status": "error", "message": "Missing required data"}
            
        if student_id not in self.students:
            return {"status": "error", "message": "Student not found"}
            
        result = self.parent_dashboard.set_goals(student_id, goal)
        
        return result
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up TutorAgent resources")
        
        # Call parent cleanup
        super().cleanup()
        
        logger.info("TutorAgent cleanup complete")

if __name__ == "__main__":
    agent = TutorAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.cleanup() 