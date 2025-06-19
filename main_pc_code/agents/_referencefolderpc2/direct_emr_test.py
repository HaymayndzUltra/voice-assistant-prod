import zmq
import json
import time

EMR_PORT = 5598
EMR_HOST = 'localhost'

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect(f"tcp://{EMR_HOST}:{EMR_PORT}")

prompt = {
    "action": "route",
    "prompt": """
    Create an educational lesson about Mathematics at a medium level.
    Structure your response as a valid JSON object with the following format:
    {
        \"title\": \"A clear, engaging title for the lesson\",
        \"content\": \"A concise explanation of the topic (3-4 paragraphs)\",
        \"exercises\": [
            {\"question\": \"First question about the topic\", \"answer\": \"Answer to first question\"},
            {\"question\": \"Second question about the topic\", \"answer\": \"Answer to second question\"},
            {\"question\": \"Third question about the topic\", \"answer\": \"Answer to third question\"}
        ]
    }
    Ensure your content is educational, accurate, and appropriate for the medium difficulty level.
    Return ONLY the JSON object, nothing else.
    """,
    "model": "ollama/llama3",
    "task_type": "creative",
    "temperature": 0.7
}

print("Sending direct LLM lesson request to EMR...")
socket.send_json(prompt)
if socket.poll(15000):
    response = socket.recv_json()
    print("Received response from EMR:")
    print(json.dumps(response, indent=2))
else:
    print("No response from EMR within 15 seconds.")
socket.close()
context.term() 