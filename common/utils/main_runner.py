"""
Generic main function runner to reduce code duplication.
Provides a standard way to run scripts with common setup and error handling.
"""

import sys
import argparse
import logging
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path

from .shared_utilities import setup_logging, cleanup_resources


class MainRunner:
    """Generic main function runner with standard setup and error handling."""
    
    def __init__(self, 
                 script_name: str,
                 description: str,
                 version: str = "1.0.0"):
        """
        Initialize the main runner.
        
        Args:
            script_name: Name of the script
            description: Description for help text
            version: Version string
        """
        self.script_name = script_name
        self.description = description
        self.version = version
        self.logger = None
        self.args = None
        
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """
        Add custom arguments to the parser.
        Override this method to add script-specific arguments.
        
        Args:
            parser: ArgumentParser instance
        """
        pass
        
    def setup_parser(self) -> argparse.ArgumentParser:
        """
        Set up the argument parser with common arguments.
        
        Returns:
            Configured ArgumentParser
        """
        parser = argparse.ArgumentParser(
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Common arguments
        parser.add_argument(
            '--version', 
            action='version', 
            version=f'{self.script_name} {self.version}'
        )
        parser.add_argument(
            '--log-level',
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Set the logging level'
        )
        parser.add_argument(
            '--config',
            type=str,
            help='Path to configuration file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode (no actual changes)'
        )
        
        # Allow subclasses to add custom arguments
        self.add_arguments(parser)
        
        return parser
        
    def setup(self) -> None:
        """
        Perform common setup tasks.
        Override to add custom setup.
        """
        pass
        
    def cleanup(self) -> None:
        """
        Perform cleanup tasks.
        Override to add custom cleanup.
        """
        pass
        
    def validate_args(self) -> bool:
        """
        Validate parsed arguments.
        Override to add custom validation.
        
        Returns:
            True if arguments are valid
        """
        return True
        
    def run(self, main_func: Callable[[argparse.Namespace], int]) -> int:
        """
        Run the main function with standard setup and error handling.
        
        Args:
            main_func: The actual main function to run
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Parse arguments
            parser = self.setup_parser()
            self.args = parser.parse_args()
            
            # Set up logging
            self.logger = setup_logging(self.script_name, self.args.log_level)
            self.logger.info(f"Starting {self.script_name} v{self.version}")
            
            # Validate arguments
            if not self.validate_args():
                self.logger.error("Invalid arguments provided")
                return 1
                
            # Run setup
            self.setup()
            
            # Run the main function
            result = main_func(self.args)
            
            # Ensure we return an int
            if result is None:
                result = 0
            elif not isinstance(result, int):
                result = 0 if result else 1
                
            self.logger.info(f"{self.script_name} completed successfully")
            return result
            
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            return 130
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unhandled exception: {e}", exc_info=True)
            else:
                print(f"Error: {e}", file=sys.stderr)
            return 1
            
        finally:
            try:
                self.cleanup()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error during cleanup: {e}")
                    

def create_simple_main(script_name: str, 
                      description: str,
                      func: Callable[[], Any]) -> Callable[[], int]:
    """
    Create a simple main function wrapper for scripts without arguments.
    
    Args:
        script_name: Name of the script
        description: Description of what the script does
        func: Function to run
        
    Returns:
        Main function that can be called directly
    """
    def main() -> int:
        runner = MainRunner(script_name, description)
        return runner.run(lambda args: func())
    
    return main


def run_with_args(script_name: str,
                  description: str,
                  func: Callable[[argparse.Namespace], Any],
                  custom_args: Optional[List[Dict[str, Any]]] = None) -> int:
    """
    Run a function with argument parsing.
    
    Args:
        script_name: Name of the script
        description: Description of what the script does
        func: Function to run (receives parsed args)
        custom_args: List of custom arguments to add
        
    Returns:
        Exit code
    """
    class CustomRunner(MainRunner):
        def add_arguments(self, parser):
            if custom_args:
                for arg in custom_args:
                    parser.add_argument(**arg)
    
    runner = CustomRunner(script_name, description)
    return runner.run(func)


# Example usage:
if __name__ == "__main__":
    # Example 1: Simple script without arguments
    def hello_world():
        print("Hello, World!")
        
    main = create_simple_main("hello", "A simple hello world script", hello_world)
    sys.exit(main())
    
    # Example 2: Script with custom arguments
    def process_file(args):
        print(f"Processing {args.input_file}")
        
    # run_with_args(
    #     "processor",
    #     "File processor script",
    #     process_file,
    #     [{"name": "input_file", "help": "Input file to process"}]
    # )