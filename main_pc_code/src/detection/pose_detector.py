"""
Pose Detector Component for detecting human poses
"""

import time
import logging
from typing import Dict, Any
from dataclasses import dataclass
import numpy as np
import cv2
from PIL import ImageGrab
import mediapipe as mp

logger = logging.getLogger(__name__)

@dataclass
class PoseData:
    """Class for storing pose detection results."""
    landmarks: Dict[str, Dict[str, float]]
    pose_type: str
    confidence: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "landmarks": self.landmarks,
            "pose_type": self.pose_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp
        }

class PoseDetector:
    """Detector for human poses using MediaPipe."""
    
    def __init__(self):
        """Initialize the pose detector."""
        logger.info("Initializing Pose Detector")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5
        )
    
    def detect_pose(self) -> PoseData:
        """Detect pose in the current screen.
        
        Returns:
            PoseData object with detection results
        """
        try:
            # Capture screen
            screen = np.array(ImageGrab.grab())
            screen_rgb = cv2.cvtColor(screen, cv2.COLOR_BGR2RGB)
            
            # Detect pose
            results = self.pose.process(screen_rgb)
            
            if results.pose_landmarks:
                landmarks = {}
                for idx, landmark in enumerate(results.pose_landmarks.landmark):
                    landmarks[f"landmark_{idx}"] = {
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": landmark.z,
                        "visibility": landmark.visibility
                    }
                
                # Simple pose classification (replace with proper classifier)
                pose_type = "standing" if landmarks["landmark_24"]["y"] < landmarks["landmark_23"]["y"] else "sitting"
                
                return PoseData(
                    landmarks=landmarks,
                    pose_type=pose_type,
                    confidence=float(results.pose_landmarks.landmark[0].visibility),
                    timestamp=time.time()
                )
            else:
                return PoseData(
                    landmarks={},
                    pose_type="unknown",
                    confidence=0.0,
                    timestamp=time.time()
                )
        except Exception as e:
            logger.error(f"Error in pose detection: {e}")
            return PoseData(
                landmarks={},
                pose_type="error",
                confidence=0.0,
                timestamp=time.time()
            ) 