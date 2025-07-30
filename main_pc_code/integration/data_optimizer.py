import msgpack
import json
from typing import Dict, Any
import zlib
import base64
import hashlib

class DataOptimizer:
    def __init__(self):
        self.compression_level = 9
        self.serialization_methods = {
            'json': self._serialize_json,
            'msgpack': self._serialize_msgpack,
            'compressed_json': self._serialize_compressed_json,
            'compressed_msgpack': self._serialize_compressed_msgpack
        }
        
    def optimize_payload(self, data: Any, method: str = 'compressed_msgpack') -> Dict[str, Any]:
        """Optimize data payload for ZMQ transmission"""
        if method not in self.serialization_methods:
            raise ValueError(f"Unknown serialization method: {method}")
            
        serialized_data = self.serialization_methods[method](data)
        return {
            'method': method,
            'data': serialized_data,
            'timestamp': time.time()
        }

    def _serialize_json(self, data: Any) -> str:
        """Serialize data using JSON"""
        return json.dumps(data, separators=(',', ':'))

    def _serialize_msgpack(self, data: Any) -> bytes:
        """Serialize data using MessagePack"""
        return msgpack.packb(data, use_bin_type=True)

    def _serialize_compressed_json(self, data: Any) -> str:
        """Serialize and compress data using JSON"""
        json_str = json.dumps(data, separators=(',', ':'))
        compressed = zlib.compress(json_str.encode(), level=self.compression_level)
        return base64.b64encode(compressed).decode()

    def _serialize_compressed_msgpack(self, data: Any) -> str:
        """Serialize and compress data using MessagePack"""
        msgpack_bytes = msgpack.packb(data, use_bin_type=True)
        compressed = zlib.compress(msgpack_bytes, level=self.compression_level)
        return base64.b64encode(compressed).decode()

    def optimize_references(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize data by replacing large objects with references"""
        optimized = {}
        for key, value in data.items():
            if self._is_large_object(value):
                optimized[key] = self._create_reference(value)
            else:
                optimized[key] = value
        return optimized

    def _is_large_object(self, value: Any) -> bool:
        """Check if object is large enough to optimize"""
        if isinstance(value, str):
            return len(value) > 1000
        if isinstance(value, (list, dict)):
            return len(str(value)) > 1000
        return False

    def _create_reference(self, value: Any) -> Dict[str, str]:
        """Create a reference for a large object"""
        reference_id = hashlib.md5(str(value).encode()).hexdigest()
        return {
            'type': 'reference',
            'id': reference_id,
            'size': len(str(value))
        }

    def restore_references(self, data: Dict[str, Any], reference_store: Dict[str, Any]) -> Dict[str, Any]:
        """Restore references to actual objects"""
        restored = {}
        for key, value in data.items():
            if isinstance(value, dict) and value.get('type') == 'reference':
                ref_id = value['id']
                restored[key] = reference_store.get(ref_id, value)
            else:
                restored[key] = value
        return restored

    def get_optimized_payload_size(self, data: Any, method: str = 'compressed_msgpack') -> int:
        """Get size of optimized payload"""
        optimized = self.optimize_payload(data, method)
        return len(str(optimized))

    def get_reference_optimized_size(self, data: Dict[str, Any]) -> int:
        """Get size of reference-optimized payload"""
        optimized = self.optimize_references(data)
        return len(str(optimized))

def optimize_zmq_message(message: Dict[str, Any], optimize_references: bool = True) -> Dict[str, Any]:
    """Optimize a ZMQ message"""
    optimizer = DataOptimizer()
    
    # First optimize references if needed
    if optimize_references:
        message = optimizer.optimize_references(message)
    
    # Then optimize serialization
    optimized = optimizer.optimize_payload(message)
    
    # Add size information for debugging
    optimized['original_size'] = len(str(message))
    optimized['optimized_size'] = len(str(optimized))
    optimized['compression_ratio'] = optimized['original_size'] / optimized['optimized_size'] if optimized['optimized_size'] > 0 else 1
    
    return optimized

def main():
    # Example usage
    DataOptimizer()
    
    # Example large message
    large_message = {
        'session_id': '1234567890',
        'conversation_history': [
            {'user': 'Hello', 'assistant': 'Hi there!'} for _ in range(1000)
        ],
        'user_profile': {'name': 'John Doe', 'preferences': {'theme': 'dark', 'language': 'en'}}
    }
    
    # Optimize the message
    optimized = optimize_zmq_message(large_message)
    print(f"Original size: {optimized['original_size']} bytes")
    print(f"Optimized size: {optimized['optimized_size']} bytes")
    print(f"Compression ratio: {optimized['compression_ratio']:.2f}")

if __name__ == "__main__":
    main()
