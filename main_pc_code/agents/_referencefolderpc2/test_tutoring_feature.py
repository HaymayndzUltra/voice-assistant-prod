import zmq
import json
import time
import uuid

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# --- Configuration ---
COORDINATOR_PORT = 5558
COORDINATOR_HOST = "192.168.1.128"
# ---------------------

def send_tutor_request(action, subject=None, question=None, session_id=None, user_profile=None):
    """Sends a structured request to the CoordinatorAgent."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.connect(f"tcp://{COORDINATOR_HOST}:{COORDINATOR_PORT}")

    request = {
        "type": "tutor",
        "action": action,
        "subject": subject,
        "question": question,
        "session_id": session_id,
        "user_id": "test_user_001",
        "request_id": str(uuid.uuid4()),
        "timestamp": time.time()
    }
    
    # Add user_profile if provided
    if user_profile:
        request["user_profile"] = user_profile

    print(f"\n>>> Sending Request (Action: {action})...")
    print(json.dumps(request, indent=2))
    
    try:
        socket.send_json(request)

        # Wait for a response with a timeout
        if socket.poll(10000): # 10 second timeout
            response = socket.recv_json()
            print(f"\n<<< Received Response:")
            print(json.dumps(response, indent=2))
            return response
        else:
            print("\n<<< ERROR: No response from CoordinatorAgent within 10 seconds.")
            return None
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    print("--- Tutoring Feature End-to-End Test ---")
    
    # Test 1: Start a new session
    # We expect the PC2 TutoringServiceAgent to create a new session.
    # Include a user_profile as required by the TutoringServiceAgent
    user_profile = {
        "age": 12,
        "language": "en",
        "level": "beginner"
    }
    
    session_response = send_tutor_request(
        action="start_session", 
        subject="Mathematics", 
        user_profile=user_profile
    )
    
    if session_response and session_response.get("status") == "success":
        current_session_id = session_response.get("session_id")
        print(f"\n--- Test 1 PASSED: Session started with ID: {current_session_id} ---")

        # Test 2: Get a lesson using the new session ID
        # We expect to get a lesson from the PC2 agent.
        lesson_response = send_tutor_request(action="get_lesson", subject="Mathematics", session_id=current_session_id)
        if lesson_response and lesson_response.get("status") == "success":
            print("\n--- Test 2 PASSED: Successfully retrieved a lesson. ---")
        else:
            print("\n--- Test 2 FAILED: Could not retrieve a lesson. ---")

    else:
        print("\n--- Test 1 FAILED: Could not start a session. Aborting further tests. ---")
        print("Please ensure mainPC and PC2 systems (especially TutoringServiceAgent) are running.")

    print("\n--- Test Complete ---") 