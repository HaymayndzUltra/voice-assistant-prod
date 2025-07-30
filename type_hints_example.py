"""
Example module with complete type hints.
"""

from typing import List, Dict, Optional, Union, Any, Callable, Tuple
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


class ExampleClass:
    """Example class with type hints."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the example class.
        
        Args:
            name: Name of the instance
            config: Optional configuration dictionary
        """
        self.name: str = name
        self.config: Dict[str, Any] = config or {}
        self._cache: Dict[str, Any] = {}
        
    def process_data(self, data: List[Dict[str, Any]]) -> List[str]:
        """Process a list of data items.
        
        Args:
            data: List of data dictionaries
            
        Returns:
            List of processed strings
        """
        results: List[str] = []
        for item in data:
            result = self._process_item(item)
            if result:
                results.append(result)
        return results
        
    def _process_item(self, item: Dict[str, Any]) -> Optional[str]:
        """Process a single item.
        
        Args:
            item: Data item to process
            
        Returns:
            Processed string or None if invalid
        """
        if 'value' in item:
            return str(item['value'])
        return None
        
    async def async_operation(self, timeout: float = 30.0) -> bool:
        """Perform an async operation.
        
        Args:
            timeout: Operation timeout in seconds
            
        Returns:
            True if successful
        """
        # Implementation here
        return True
        
    @staticmethod
    def utility_function(path: Union[str, Path]) -> Path:
        """Convert string or Path to Path object.
        
        Args:
            path: File path as string or Path
            
        Returns:
            Path object
        """
        return Path(path) if isinstance(path, str) else path


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    logger.info("Starting application")
    
    # Example usage
    instance = ExampleClass("example", {"debug": True})
    data = [{"value": "test1"}, {"value": "test2"}]
    results = instance.process_data(data)
    
    logger.info(f"Processed {len(results)} items")
    return 0


# Type alias examples
ConfigDict = Dict[str, Any]
ProcessFunc = Callable[[str], Optional[str]]
ResultTuple = Tuple[bool, str, Optional[Dict[str, Any]]]


if __name__ == "__main__":
    import sys
    sys.exit(main())
