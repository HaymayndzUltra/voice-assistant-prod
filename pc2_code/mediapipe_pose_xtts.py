import cv2
import mediapipe as mp
import numpy as np
import os
import time
import logging
from common.utils.log_setup import configure_logging

# Logging setup
logger = configure_logging(__name__)s] %(message)s')

# Mediapipe pose setup
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# XTTS command (palitan ang command na ito kung may mas direct na XTTS API)
def speak_xtts(message):
    logging.info(f"Speaking: {message}")
    os.system(f'xtts --text "{message}"')  # Palitan ayon sa iyong XTTS setup

# Pose 1: "Humihigop" (right wrist near mouth/lower face, elbow bent)
def is_humihigop(landmarks, dist_thresh=0.09, elbow_bend_ratio=0.7):
    if not landmarks:
        return False
    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]
    right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    # Use NOSE as proxy for bibig, or average MOUTH_LEFT/MOUTH_RIGHT if available
    try:
        mouth_left = landmarks[mp_pose.PoseLandmark.MOUTH_LEFT.value]
        mouth_right = landmarks[mp_pose.PoseLandmark.MOUTH_RIGHT.value]
        mouth_x = (mouth_left.x + mouth_right.x) / 2
        mouth_y = (mouth_left.y + mouth_right.y) / 2
    except:
        mouth = landmarks[mp_pose.PoseLandmark.NOSE.value]
        mouth_x, mouth_y = mouth.x, mouth.y
    # Distance wrist to mouth
    dist_mouth = np.sqrt((right_wrist.x - mouth_x)**2 + (right_wrist.y - mouth_y)**2)
    # Wrist must be below or level with mouth (not above)
    below_mouth = right_wrist.y > mouth_y - 0.02  # allow small tolerance
    # Elbow bend: wrist-elbow distance < elbow-shoulder distance * ratio
    dist_we = np.sqrt((right_wrist.x - right_elbow.x)**2 + (right_wrist.y - right_elbow.y)**2)
    dist_es = np.sqrt((right_elbow.x - right_shoulder.x)**2 + (right_elbow.y - right_shoulder.y)**2)
    elbow_bent = dist_we < dist_es * elbow_bend_ratio
    return dist_mouth < dist_thresh and below_mouth and elbow_bent

# Pose 2: "Parehong may hawak" (both wrists extended, arms straight, wrists at similar height)
def is_hawak_both(landmarks, dist_thresh=0.18, height_thresh=0.05, straight_ratio=0.8):
    if not landmarks:
        return False
    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]
    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]
    left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value]
    right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    # Horizontal distance wrists to shoulders
    left_dist = abs(left_wrist.x - left_shoulder.x)
    right_dist = abs(right_wrist.x - right_shoulder.x)
    # Arms straight: wrist-elbow distance ~= elbow-shoulder distance
    left_dist_we = np.sqrt((left_wrist.x - left_elbow.x)**2 + (left_wrist.y - left_elbow.y)**2)
    left_dist_es = np.sqrt((left_elbow.x - left_shoulder.x)**2 + (left_elbow.y - left_shoulder.y)**2)
    right_dist_we = np.sqrt((right_wrist.x - right_elbow.x)**2 + (right_wrist.y - right_elbow.y)**2)
    right_dist_es = np.sqrt((right_elbow.x - right_shoulder.x)**2 + (right_elbow.y - right_shoulder.y)**2)
    left_straight = left_dist_we > left_dist_es * straight_ratio
    right_straight = right_dist_we > right_dist_es * straight_ratio
    # Wrists at similar height
    wrists_level = abs(left_wrist.y - right_wrist.y) < height_thresh
    return left_dist > dist_thresh and right_dist > dist_thresh and left_straight and right_straight and wrists_level

# Modular pose detection
def detect_pose(landmarks):
    if is_humihigop(landmarks):
        return "humihigop"
    elif is_hawak_both(landmarks):
        return "hawak_both"
    return None

def main():
    cap = cv2.VideoCapture(0)
    last_pose = None
    last_spoken = 0
    debounce_seconds = 4
    pose_colors = {
        "humihigop": (0, 255, 0),
        "hawak_both": (255, 0, 0)
    }
    pose_messages = {
        "humihigop": "May na-detect akong humihigop na pose!",
        "hawak_both": "May taong may hawak sa kaliwa at kanan!"
    }
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        detected_pose = None
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            detected_pose = detect_pose(results.pose_landmarks.landmark)
            if detected_pose:
                # Draw indicator
                h, w, _ = image.shape
                cv2.putText(image, f"Detected: {detected_pose}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, pose_colors[detected_pose], 3)
                # Speak only if pose changed or debounce
                if (last_pose != detected_pose) or (time.time() - last_spoken > debounce_seconds):
                    speak_xtts(pose_messages[detected_pose])
                    last_spoken = time.time()
            last_pose = detected_pose
        else:
            last_pose = None
        cv2.imshow('Pose Detection', image)
        if cv2.waitKey(5) & 0xFF == 27:
            break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
