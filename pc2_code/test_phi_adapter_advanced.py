import zmq
import time
import os
import random
from common.env_helpers import get_env

def send_request(socket, payload):
    socket.send_json(payload)
    try:
        return socket.recv_json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5581")

    token = os.environ.get("PHI_TRANSLATOR_TOKEN", "supersecret")
    wrong_token = "wrongtoken" + str(random.randint(1, 10000)

    print("\n=== HEALTH CHECK (valid token) ->")
    resp = send_request(socket, {"action": "health", "token": token})
    print(resp)
    time.sleep(0.5)

    print("\n=== HEALTH CHECK (invalid token) ===")
    resp = send_request(socket, {"action": "health", "token": wrong_token})
    print(resp)
    time.sleep(0.5)

    print("\n=== TAGALOG->ENGLISH (dictionary match) ===")
    resp = send_request(socket, {
        "action": "translate",
        "text": "Kumusta ka?",
        "source_lang": "tl",
        "target_lang": "en",
        "token": token
    })
    print(resp)
    time.sleep(0.5)

    print("\n=== TAGALOG->ENGLISH (model translation) ===")
    resp = send_request(socket, {
        "action": "translate",
        "text": "Mahalaga ang pamilya sa ating kultura.",
        "source_lang": "tl",
        "target_lang": "en",
        "token": token
    })
    print(resp)
    time.sleep(0.5)

    print("\n=== ENGLISH->TAGALOG (should fail, direction blocked) ===")
    resp = send_request(socket, {
        "action": "translate",
        "text": "How are you?",
        "source_lang": "en",
        "target_lang": "tl",
        "token": token
    })
    print(resp)
    time.sleep(0.5)

    print("\n=== INVALID ACTION ===")
    resp = send_request(socket, {
        "action": "foobar",
        "token": token
    })
    print(resp)
    time.sleep(0.5)

    print("\n=== TRANSLATE with INVALID ${SECRET_PLACEHOLDER}")
    resp = send_request(socket, {
        "action": "translate",
        "text": "Salamat",
        "source_lang": "tl",
        "target_lang": "en",
        "token": wrong_token
    })
    print(resp)

if __name__ == "__main__":
    main()
