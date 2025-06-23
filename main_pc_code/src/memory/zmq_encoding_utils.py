#!/usr/bin/env python3
"""
ZMQ Encoding Utilities
----------------------

This module provides utilities for safely encoding and decoding data for ZMQ communication.
It addresses potential null byte issues by ensuring proper UTF-8 encoding/decoding.
"""

import json
import logging
from typing import Any, Dict, Union, Optional

logger = logging.getLogger(__name__)

def safe_encode_json(data: Any) -> bytes:
    """
    Safely encode data to JSON and then to UTF-8 bytes.
    
    Args:
        data: The data to encode
        
    Returns:
        Encoded bytes
    """
    try:
        # First convert to JSON
        json_str = json.dumps(data, ensure_ascii=False)
        # Then encode to UTF-8 bytes
        return json_str.encode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding data to JSON: {e}")
        # Return a safe error message
        error_msg = json.dumps({"error": "Encoding error"})
        return error_msg.encode('utf-8')

def safe_decode_json(data: Union[bytes, str]) -> Dict[str, Any]:
    """
    Safely decode UTF-8 bytes to JSON.
    
    Args:
        data: The data to decode (bytes or string)
        
    Returns:
        Decoded JSON data
    """
    try:
        # If input is bytes, decode to string first
        if isinstance(data, bytes):
            data_str = data.decode('utf-8', errors='replace')
        else:
            data_str = data
            
        # Then parse JSON
        return json.loads(data_str)
    except Exception as e:
        logger.error(f"Error decoding JSON data: {e}")
        # Return a safe empty dict
        return {"error": f"Decoding error: {str(e)}"}

def send_json_safe(socket: Any, data: Any, flags: int = 0) -> None:
    """
    Safely send JSON data through a ZMQ socket.
    
    Args:
        socket: ZMQ socket
        data: Data to send
        flags: ZMQ flags
    """
    encoded_data = safe_encode_json(data)
    socket.send(encoded_data, flags=flags)

def recv_json_safe(socket: Any, flags: int = 0) -> Dict[str, Any]:
    """
    Safely receive JSON data from a ZMQ socket.
    
    Args:
        socket: ZMQ socket
        flags: ZMQ flags
        
    Returns:
        Decoded JSON data
    """
    message = socket.recv(flags=flags)
    return safe_decode_json(message)

def send_multipart_safe(socket: Any, frames: list, flags: int = 0) -> None:
    """
    Safely send multipart ZMQ message with JSON data.
    
    Args:
        socket: ZMQ socket
        frames: List of frames to send
        flags: ZMQ flags
    """
    encoded_frames = []
    
    for frame in frames:
        if isinstance(frame, bytes):
            encoded_frames.append(frame)
        elif frame == b'':  # Empty frame
            encoded_frames.append(b'')
        else:
            encoded_frames.append(safe_encode_json(frame))
            
    socket.send_multipart(encoded_frames, flags=flags)

def recv_multipart_safe(socket: Any, flags: int = 0) -> list:
    """
    Safely receive multipart ZMQ message with JSON data.
    
    Args:
        socket: ZMQ socket
        flags: ZMQ flags
        
    Returns:
        List of decoded frames
    """
    frames = socket.recv_multipart(flags=flags)
    decoded_frames = []
    
    for i, frame in enumerate(frames):
        if i == 0:  # Identity frame in ROUTER pattern - keep as bytes
            decoded_frames.append(frame)
        elif frame == b'':  # Empty delimiter frame
            decoded_frames.append(b'')
        else:
            try:
                decoded_frames.append(safe_decode_json(frame))
            except:
                # If not JSON, keep the original bytes
                decoded_frames.append(frame)
                
    return decoded_frames

# Test the module
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test data with potential null byte issues
    test_data = {
        "text": "Hello\u0000World",  # Contains a null byte
        "nested": {
            "array": [1, 2, 3, None, "Test\u0000String"]
        }
    }
    
    # Test encoding and decoding
    encoded = safe_encode_json(test_data)
    print(f"Encoded: {encoded}")
    
    decoded = safe_decode_json(encoded)
    print(f"Decoded: {decoded}")
    
    # Verify the null bytes are handled correctly
    assert "\u0000" not in json.dumps(decoded) 