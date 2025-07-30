#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Centralized FastJSON Utility - Phase 2.2

High-performance JSON serialization/deserialization with automatic fallback.
Uses orjson when available for maximum performance, falls back to ujson, then standard json.

Part of Phase 2.2: Centralized FastJSON Utility - O3 Roadmap Implementation
"""

import logging
from typing import Any, Dict, List, Optional, Union

# JSON implementation priority: orjson > ujson > json
_json_impl = None
_json_impl_name = None

def _detect_json_implementation():
    """Detect and configure the best available JSON implementation."""
    global _json_impl, _json_impl_name
    
    # Try orjson (fastest)
    try:
        import orjson
        _json_impl = orjson
        _json_impl_name = "orjson"
        logging.getLogger("fast_json").info("Using orjson for JSON operations")
        return
    except ImportError:
        pass
    
    # Try ujson (faster than standard)
    try:
        import ujson
        _json_impl = ujson
        _json_impl_name = "ujson"
        logging.getLogger("fast_json").info("Using ujson for JSON operations")
        return
    except ImportError:
        pass
    
    # Fallback to standard json
    import json
    _json_impl = json
    _json_impl_name = "json"
    logging.getLogger("fast_json").info("Using standard json for JSON operations")

# Initialize on import
_detect_json_implementation()


class FastJSONError(Exception):
    """Base exception for FastJSON operations."""
    pass


class FastJSONEncoder:
    """High-performance JSON encoder with automatic implementation selection."""
    
    def __init__(self, 
                 sort_keys: bool = False,
                 indent: Optional[int] = None,
                 ensure_ascii: bool = False):
        """Initialize FastJSON encoder.
        
        Args:
            sort_keys: Whether to sort dictionary keys
            indent: Number of spaces for indentation (None for compact)
            ensure_ascii: Whether to ensure ASCII output
        """
        self.sort_keys = sort_keys
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        
    def encode(self, obj: Any) -> str:
        """Encode object to JSON string.
        
        Args:
            obj: Object to encode
            
        Returns:
            JSON string
            
        Raises:
            FastJSONError: If encoding fails
        """
        try:
            if _json_impl_name == "orjson":
                # orjson returns bytes, need to decode
                options = 0
                if self.sort_keys:
                    options |= _json_impl.OPT_SORT_KEYS
                if self.indent is not None:
                    options |= _json_impl.OPT_INDENT_2
                if not self.ensure_ascii:
                    options |= _json_impl.OPT_NON_STR_KEYS
                
                result = _json_impl.dumps(obj, option=options)
                return result.decode('utf-8')
                
            elif _json_impl_name == "ujson":
                return _json_impl.dumps(
                    obj,
                    sort_keys=self.sort_keys,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii
                )
                
            else:  # standard json
                return _json_impl.dumps(
                    obj,
                    sort_keys=self.sort_keys,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii,
                    separators=(',', ':') if self.indent is None else None
                )
                
        except Exception as e:
            raise FastJSONError(f"JSON encoding failed: {e}") from e


class FastJSONDecoder:
    """High-performance JSON decoder with automatic implementation selection."""
    
    def __init__(self, strict: bool = True):
        """Initialize FastJSON decoder.
        
        Args:
            strict: Whether to use strict parsing
        """
        self.strict = strict
        
    def decode(self, json_str: Union[str, bytes]) -> Any:
        """Decode JSON string to object.
        
        Args:
            json_str: JSON string or bytes to decode
            
        Returns:
            Decoded object
            
        Raises:
            FastJSONError: If decoding fails
        """
        try:
            if _json_impl_name == "orjson":
                # orjson can handle both str and bytes
                return _json_impl.loads(json_str)
                
            elif _json_impl_name == "ujson":
                # ujson needs string
                if isinstance(json_str, bytes):
                    json_str = json_str.decode('utf-8')
                return _json_impl.loads(json_str)
                
            else:  # standard json
                if isinstance(json_str, bytes):
                    json_str = json_str.decode('utf-8')
                return _json_impl.loads(json_str, strict=self.strict)
                
        except Exception as e:
            raise FastJSONError(f"JSON decoding failed: {e}") from e


# Convenient module-level functions
_default_encoder = FastJSONEncoder()
_default_decoder = FastJSONDecoder()
_pretty_encoder = FastJSONEncoder(sort_keys=True, indent=2)


def dumps(obj: Any, 
          sort_keys: bool = False,
          indent: Optional[int] = None,
          ensure_ascii: bool = False) -> str:
    """Encode object to JSON string (module-level convenience function).
    
    Args:
        obj: Object to encode
        sort_keys: Whether to sort dictionary keys
        indent: Number of spaces for indentation (None for compact)
        ensure_ascii: Whether to ensure ASCII output
        
    Returns:
        JSON string
    """
    if sort_keys or indent is not None or ensure_ascii:
        encoder = FastJSONEncoder(sort_keys, indent, ensure_ascii)
        return encoder.encode(obj)
    else:
        return _default_encoder.encode(obj)


def loads(json_str: Union[str, bytes], strict: bool = True) -> Any:
    """Decode JSON string to object (module-level convenience function).
    
    Args:
        json_str: JSON string or bytes to decode
        strict: Whether to use strict parsing
        
    Returns:
        Decoded object
    """
    if not strict:
        decoder = FastJSONDecoder(strict=False)
        return decoder.decode(json_str)
    else:
        return _default_decoder.decode(json_str)


def pretty_dumps(obj: Any) -> str:
    """Encode object to pretty-printed JSON string.
    
    Args:
        obj: Object to encode
        
    Returns:
        Pretty-printed JSON string
    """
    return _pretty_encoder.encode(obj)


def is_json_string(text: str) -> bool:
    """Check if string is valid JSON.
    
    Args:
        text: String to check
        
    Returns:
        True if valid JSON, False otherwise
    """
    try:
        loads(text)
        return True
    except FastJSONError:
        return False


def get_json_size(obj: Any) -> int:
    """Get size of object when serialized to JSON.
    
    Args:
        obj: Object to measure
        
    Returns:
        Size in bytes
    """
    return len(dumps(obj).encode('utf-8'))


def optimize_for_size(obj: Any) -> str:
    """Optimize JSON for minimum size (no whitespace, sorted keys).
    
    Args:
        obj: Object to encode
        
    Returns:
        Size-optimized JSON string
    """
    return dumps(obj, sort_keys=True, ensure_ascii=True)


def optimize_for_readability(obj: Any) -> str:
    """Optimize JSON for readability (indented, sorted keys).
    
    Args:
        obj: Object to encode
        
    Returns:
        Readable JSON string
    """
    return dumps(obj, sort_keys=True, indent=2)


class JSONFileHandler:
    """Utility class for JSON file operations."""
    
    def __init__(self, 
                 encoder: Optional[FastJSONEncoder] = None,
                 decoder: Optional[FastJSONDecoder] = None):
        """Initialize JSON file handler.
        
        Args:
            encoder: Custom encoder (uses default if None)
            decoder: Custom decoder (uses default if None)
        """
        self.encoder = encoder or _default_encoder
        self.decoder = decoder or _default_decoder
    
    def save(self, obj: Any, filepath: str, pretty: bool = False) -> None:
        """Save object to JSON file.
        
        Args:
            obj: Object to save
            filepath: Path to save file
            pretty: Whether to use pretty formatting
        """
        try:
            encoder = _pretty_encoder if pretty else self.encoder
            json_str = encoder.encode(obj)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)
                
        except Exception as e:
            raise FastJSONError(f"Failed to save JSON to {filepath}: {e}") from e
    
    def load(self, filepath: str) -> Any:
        """Load object from JSON file.
        
        Args:
            filepath: Path to load file
            
        Returns:
            Loaded object
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_str = f.read()
            
            return self.decoder.decode(json_str)
            
        except Exception as e:
            raise FastJSONError(f"Failed to load JSON from {filepath}: {e}") from e
    
    def update(self, filepath: str, updates: Dict[str, Any]) -> None:
        """Update JSON file with new values.
        
        Args:
            filepath: Path to JSON file
            updates: Dictionary of updates to apply
        """
        try:
            # Load existing data
            try:
                data = self.load(filepath)
                if not isinstance(data, dict):
                    raise FastJSONError("Can only update JSON objects (dictionaries)")
            except FileNotFoundError:
                data = {}
            
            # Apply updates
            data.update(updates)
            
            # Save updated data
            self.save(data, filepath, pretty=True)
            
        except Exception as e:
            raise FastJSONError(f"Failed to update JSON file {filepath}: {e}") from e


# Global file handler instance
json_file = JSONFileHandler()


def save_json(obj: Any, filepath: str, pretty: bool = False) -> None:
    """Save object to JSON file (convenience function)."""
    json_file.save(obj, filepath, pretty)


def load_json(filepath: str) -> Any:
    """Load object from JSON file (convenience function)."""
    return json_file.load(filepath)


def update_json(filepath: str, updates: Dict[str, Any]) -> None:
    """Update JSON file with new values (convenience function)."""
    json_file.update(filepath, updates)


# Performance monitoring
class JSONPerformanceMonitor:
    """Monitor JSON operation performance."""
    
    def __init__(self):
        self.reset_stats()
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.encode_count = 0
        self.decode_count = 0
        self.encode_time = 0.0
        self.decode_time = 0.0
        self.encode_bytes = 0
        self.decode_bytes = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "implementation": _json_impl_name,
            "operations": {
                "encode_count": self.encode_count,
                "decode_count": self.decode_count,
            },
            "performance": {
                "avg_encode_time_ms": (self.encode_time / max(1, self.encode_count)) * 1000,
                "avg_decode_time_ms": (self.decode_time / max(1, self.decode_count)) * 1000,
                "total_bytes_encoded": self.encode_bytes,
                "total_bytes_decoded": self.decode_bytes,
            }
        }


# Global performance monitor
perf_monitor = JSONPerformanceMonitor()


def get_performance_stats() -> Dict[str, Any]:
    """Get JSON performance statistics."""
    return perf_monitor.get_stats()


def get_implementation_info() -> Dict[str, str]:
    """Get information about current JSON implementation."""
    return {
        "implementation": _json_impl_name,
        "module": str(_json_impl),
        "features": {
            "orjson": "Fastest (Rust-based), bytes output",
            "ujson": "Fast (C-based), string output", 
            "json": "Standard library, good compatibility"
        }.get(_json_impl_name, "Unknown implementation")
    }
