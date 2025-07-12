#!/usr/bin/env python3
"""
Example file demonstrating how to refactor imports after installing the package with pip install -e .
This is part of the packaging modernization effort.

NOTE: This is a demonstration file only. The imports shown here are examples
and may not resolve in your environment.
"""

# ===== BEFORE REFACTORING =====
"""
import os
import sys
import json
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

# Add main_pc_code to path
main_pc_code_dir = os.path.join(project_root, "main_pc_code")
sys.path.insert(0, main_pc_code_dir)

from main_pc_code.config.config_manager import ConfigManager
from main_pc_code.agents.some_agent import SomeAgent
from common.utils.data_models import DataModel
"""

# ===== AFTER REFACTORING =====
import os
import json
from pathlib import Path

# Direct imports without sys.path manipulation
# NOTE: These are example imports for demonstration purposes
# In a real file, you would import actual modules that exist in your project
# after installing with pip install -e .
from main_pc_code.config.config_manager import ConfigManager  # Example import
from main_pc_code.agents.some_agent import SomeAgent  # Example import
from common.utils.data_models import DataModel  # Example import

# The code below is just for demonstration and won't actually run
if False:  # This condition ensures the code is never executed
    class ExampleClass:
        """Example class demonstrating proper imports."""
        
        def __init__(self, config_path: str):
            self.config_manager = ConfigManager(config_path)
            self.agent = SomeAgent()
            self.data_model = DataModel()
        
        def run(self):
            """Run the example."""
            print("Running with proper imports!")
            
    if __name__ == "__main__":
        example = ExampleClass("config.json")
        example.run() 