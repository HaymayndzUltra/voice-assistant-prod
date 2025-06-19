import zmq
import json
import time
import uuid

def send_tutor_request(action, subject=None, difficulty=None, session_id=None, user_profile=None):
    """Sends a structured request to the TutorAgent."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5558")

    request = {
        "type": "tutor",
        "action": action,
        "subject": subject,
        "difficulty": difficulty,
        "session_id": session_id,
        "user_id": "test_user_001",
        "request_id": str(uuid.uuid4()),
        "timestamp": time.time()
    }
    
    if user_profile:
        request["user_profile"] = user_profile

    print(f"\n>>> Sending Request (Action: {action})...")
    print(json.dumps(request, indent=2))
    
    try:
        socket.send_json(request)
        if socket.poll(10000):  # 10 second timeout
            response = socket.recv_json()
            print(f"\n<<< Received Response:")
            print(json.dumps(response, indent=2))
            return response
        else:
            print("\n<<< ERROR: No response within 10 seconds.")
            return None
    finally:
        socket.close()
        context.term()

def test_different_subjects():
    print("\n=== Testing Different Subjects ===")
    
    # Test user profile with advanced level
    user_profile = {
        "age": 15,
        "language": "en",
        "level": "advanced"
    }
    
    # Start session
    session_response = send_tutor_request(
        action="start_session",
        subject="Science",
        user_profile=user_profile
    )
    
    if session_response and session_response.get("status") == "success":
        session_id = session_response.get("session_id")
        print(f"\nSession started with ID: {session_id}")
        
        # Test Science lesson
        print("\n--- Testing Science Lesson ---")
        science_lesson = send_tutor_request(
            action="get_lesson",
            subject="Science",
            difficulty="advanced",
            session_id=session_id
        )
        
        # Test English lesson
        print("\n--- Testing English Lesson ---")
        english_lesson = send_tutor_request(
            action="get_lesson",
            subject="English",
            difficulty="advanced",
            session_id=session_id
        )
        
        # Test History lesson
        print("\n--- Testing History Lesson ---")
        history_lesson = send_tutor_request(
            action="get_lesson",
            subject="History",
            difficulty="advanced",
            session_id=session_id
        )
        
        # Submit feedback to test difficulty adjustment
        print("\n--- Testing Feedback System ---")
        feedback_response = send_tutor_request(
            action="submit_feedback",
            session_id=session_id,
            user_profile={"engagement_score": 0.8}  # High engagement
        )
        
        # Get another lesson to see if difficulty adjusted
        print("\n--- Testing Difficulty Adjustment ---")
        adjusted_lesson = send_tutor_request(
            action="get_lesson",
            subject="Science",
            difficulty="hard",  # Should be adjusted based on feedback
            session_id=session_id
        )
    else:
        print("Failed to start session")

if __name__ == "__main__":
    print("=== Custom Tutoring System Test ===")
    test_different_subjects()
    print("\n=== Test Complete ===") 