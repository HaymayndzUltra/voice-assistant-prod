import cv2
import mediapipe as mp
import numpy as np
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(static_image_mode=False, model_complexity=1, enable_segmentation=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Helper for TTS

def speak_xtts(message):
    logging.info(f"Speaking: {message}")
    os.system(f'xtts --text "{message}"')

# Helper: Detect if sitting (hips lower than shoulders)
def is_sitting(landmarks):
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    avg_hip_y = (left_hip.y + right_hip.y) / 2
    avg_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
    return avg_hip_y > avg_shoulder_y + 0.08  # hips much lower than shoulders

# Helper: Detect if standing (hips nearly level with shoulders)
def is_standing(landmarks):
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    avg_hip_y = (left_hip.y + right_hip.y) / 2
    avg_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
    return abs(avg_hip_y - avg_shoulder_y) < 0.08

# Detect humihigop (right wrist near mouth, elbow bent)
def is_humihigop(landmarks, dist_thresh=0.09, elbow_bend_ratio=0.7):
    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]
    right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    try:
        mouth_left = landmarks[mp_pose.PoseLandmark.MOUTH_LEFT.value]
        mouth_right = landmarks[mp_pose.PoseLandmark.MOUTH_RIGHT.value]
        mouth_x = (mouth_left.x + mouth_right.x) / 2
        mouth_y = (mouth_left.y + mouth_right.y) / 2
    except:
        mouth = landmarks[mp_pose.PoseLandmark.NOSE.value]
        mouth_x, mouth_y = mouth.x, mouth.y
    dist_mouth = np.sqrt((right_wrist.x - mouth_x)**2 + (right_wrist.y - mouth_y)**2)
    below_mouth = right_wrist.y > mouth_y - 0.02
    dist_we = np.sqrt((right_wrist.x - right_elbow.x)**2 + (right_wrist.y - right_elbow.y)**2)
    dist_es = np.sqrt((right_elbow.x - right_shoulder.x)**2 + (right_elbow.y - right_shoulder.y)**2)
    elbow_bent = dist_we < dist_es * elbow_bend_ratio
    return dist_mouth < dist_thresh and below_mouth and elbow_bent

# Detect "may hawak sa kaliwa" (left wrist extended from shoulder)
def is_hawak_kaliwa(landmarks, dist_thresh=0.18):
    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    left_dist = abs(left_wrist.x - left_shoulder.x)
    return left_dist > dist_thresh

# Main loop for multi-person detection
def main():
    cap = cv2.VideoCapture(0)
    last_spoken = 0
    debounce_seconds = 4
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        detected_roles = []
        # Mediapipe Pose only supports single person by default. To support multi-person, use Mediapipe's holistic or BlazePose Full (not yet in pip as of 2024). For now, simulate by detecting two roles in single frame for demo.
        if results.pose_landmarks:
            lms = results.pose_landmarks.landmark
            # Nakaupo, humihigop
            if is_sitting(lms) and is_humihigop(lms):
                detected_roles.append('nakaupo_humihigop')
                cv2.putText(image, 'Nakaupo: Humihigop', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,255,0), 3)
            # Nakatayo, may hawak sa kaliwa
            if is_standing(lms) and is_hawak_kaliwa(lms):
                detected_roles.append('nakatayo_hawak_kaliwa')
                cv2.putText(image, 'Nakatayo: May hawak kaliwa', (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,0,0), 3)
            # Interaction: right wrist of nakaupo near left wrist of nakatayo (simulate by checking both in same person)
            right_wrist = lms[mp_pose.PoseLandmark.RIGHT_WRIST.value]
            left_wrist = lms[mp_pose.PoseLandmark.LEFT_WRIST.value]
            dist_higop = np.sqrt((right_wrist.x - left_wrist.x)**2 + (right_wrist.y - left_wrist.y)**2)
            if 'nakaupo_humihigop' in detected_roles and 'nakatayo_hawak_kaliwa' in detected_roles and dist_higop < 0.12:
                cv2.putText(image, 'Interaction: Hinihigop!', (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,0,255), 3)
                if time.time() - last_spoken > debounce_seconds:
                    speak_xtts('Detected: Nakaupo humihigop at nakatayo may hawak kaliwa, interaction!')
                    last_spoken = time.time()
        cv2.imshow('Pose Interaction Detection', image)
        if cv2.waitKey(5) & 0xFF == 27:
            break
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
