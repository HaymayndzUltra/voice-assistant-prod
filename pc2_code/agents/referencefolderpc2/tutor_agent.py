import os
import json
import time
import logging
import threading
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import zmq
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import uuid
from config.system_config import get_service_host, get_service_port

# Load configuration
with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "tutor_config.json"), "r") as f:
    CONFIG = json.load(f)["tutor"]

# Setup logging
LOG_PATH = "tutor_agent.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

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
    mastery_levels: Dict[str, float] = None
    weak_areas: List[str] = None
    strong_areas: List[str] = None

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
        features = np.array([
            current_performance.accuracy,
            current_performance.speed,
            current_performance.confidence,
            student_profile.mastery_levels.get(student_profile.current_lesson, 0.5),
            len(student_profile.performance_history) / 100  # Normalized experience
        ]).reshape(1, -1)
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features)
        
        # Predict difficulty adjustment
        with torch.no_grad():
            adjustment = self.difficulty_model(torch.FloatTensor(features_scaled))
            
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
    """Generates personalized feedback and motivation"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.feedback_templates = self._load_feedback_templates()
        
    def _load_feedback_templates(self) -> Dict[str, List[str]]:
        """Load feedback templates from configuration"""
        return {
            "encouragement": [
                "Great job! You're making excellent progress!",
                "Keep up the good work! You're getting better every day!",
                "Your dedication is paying off!",
                "You're showing great improvement!"
            ],
            "improvement": [
                "Let's work on this together. You're getting closer!",
                "Don't worry, learning takes time. You're doing well!",
                "Keep practicing, you're making progress!",
                "You're on the right track, keep going!"
            ],
            "mastery": [
                "Outstanding! You've mastered this concept!",
                "Perfect! You're ready for the next challenge!",
                "Excellent work! You've shown great understanding!",
                "You've achieved mastery! Well done!"
            ]
        }
        
    def generate_feedback(self, performance: PerformanceMetrics, 
                         previous_performance: Optional[PerformanceMetrics] = None) -> str:
        """Generate personalized feedback based on performance"""
        # Determine feedback type
        if performance.accuracy > 0.9:
            feedback_type = "mastery"
        elif performance.accuracy > 0.7:
            feedback_type = "encouragement"
        else:
            feedback_type = "improvement"
            
        # Get random template
        template = np.random.choice(self.feedback_templates[feedback_type])
        
        # Add specific feedback
        if previous_performance:
            improvement = performance.accuracy - previous_performance.accuracy
            if improvement > 0:
                template += f" You've improved by {improvement:.1%}!"
                
        # Add specific areas for improvement
        if performance.areas_for_improvement:
            template += f" Let's focus on {', '.join(performance.areas_for_improvement)}."
            
        return template

class ParentDashboard:
    """Manages parent dashboard and reporting"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.dashboard_data = {}
        
    def update_dashboard(self, student_id: str, 
                        progress_data: Dict[str, Any]):
        """Update dashboard with new progress data"""
        if student_id not in self.dashboard_data:
            self.dashboard_data[student_id] = {
                "last_updated": time.time(),
                "progress": [],
                "goals": {},
                "notifications": []
            }
            
        self.dashboard_data[student_id]["progress"].append(progress_data)
        self.dashboard_data[student_id]["last_updated"] = time.time()
        
    def get_dashboard_data(self, student_id: str) -> Dict[str, Any]:
        """Get dashboard data for a student"""
        if student_id not in self.dashboard_data:
            return {"error": "No dashboard data found"}
            
        return self.dashboard_data[student_id]
        
    def set_goals(self, student_id: str, goals: Dict[str, Any]):
        """Set learning goals for a student"""
        if student_id not in self.dashboard_data:
            self.dashboard_data[student_id] = {
                "last_updated": time.time(),
                "progress": [],
                "goals": {},
                "notifications": []
            }
            
        self.dashboard_data[student_id]["goals"] = goals
        
    def add_notification(self, student_id: str, notification: str):
        """Add notification to dashboard"""
        if student_id not in self.dashboard_data:
            return
            
        self.dashboard_data[student_id]["notifications"].append({
            "message": notification,
            "timestamp": time.time()
        })

class TutorAgent:
    """Main tutor agent that coordinates with PC2's TutoringServiceAgent"""
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        
        # Get host and port from environment or config
        self.host = get_service_host('tutor', '0.0.0.0')
        self.port = get_service_port('tutor', 5603)
        
        # Bind to all interfaces
        self.socket.bind(f"tcp://{self.host}:{self.port}")
        logging.info(f"Tutor Agent listening on {self.host}:{self.port}")
        
        # Initialize tutor state
        self.tutor_state = {}
        
    def start(self):
        try:
            while True:
                # Receive message
                identity, _, message = self.socket.recv_multipart()
                message = json.loads(message.decode())
                
                # Process message
                response = self.process_message(message)
                
                # Send response
                self.socket.send_multipart([
                    identity,
                    b'',
                    json.dumps(response).encode()
                ])
                
        except KeyboardInterrupt:
            logging.info("Shutting down Tutor Agent...")
        finally:
            self.socket.close()
            self.context.term()
            
    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Process message and return response
        return {"status": "success", "message": "Tutor session updated"}
        
if __name__ == "__main__":
    agent = TutorAgent()
    agent.start() 