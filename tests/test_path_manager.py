import os
import sys
import unittest
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils.path_env import (
    path_manager, get_path, join_path, get_file_path,
    get_project_root, get_main_pc_code, get_pc2_code
)


class TestPathManager(unittest.TestCase):
    """Test the PathManager functionality."""
    
    def test_project_root(self):
        """Test that the project root is correctly identified."""
        expected_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.assertEqual(get_project_root(), expected_root)
    
    def test_main_directories(self):
        """Test that main directories are correctly identified."""
        self.assertEqual(get_main_pc_code(), os.path.join(get_project_root(), "main_pc_code"))
        self.assertEqual(get_pc2_code(), os.path.join(get_project_root(), "pc2_code"))
    
    def test_get_path(self):
        """Test getting paths for different directory types."""
        self.assertEqual(get_path("config"), os.path.join(get_project_root(), "config"))
        self.assertEqual(get_path("logs"), os.path.join(get_project_root(), "logs"))
        self.assertEqual(get_path("data"), os.path.join(get_project_root(), "data"))
        self.assertEqual(get_path("main_pc_config"), os.path.join(get_main_pc_code(), "config"))
        self.assertEqual(get_path("pc2_logs"), os.path.join(get_pc2_code(), "logs"))
        
        # Test that invalid path types raise ValueError
        with self.assertRaises(ValueError):
            get_path("nonexistent_path_type")
    
    def test_join_path(self):
        """Test joining paths with additional components."""
        self.assertEqual(
            join_path("config", "system_config.json"),
            os.path.join(get_project_root(), "config", "system_config.json")
        )
        self.assertEqual(
            join_path("logs", "agent_logs", "model_manager.log"),
            os.path.join(get_project_root(), "logs", "agent_logs", "model_manager.log")
        )
    
    def test_get_file_path(self):
        """Test getting file paths."""
        self.assertEqual(
            get_file_path("config", "startup_config.yaml"),
            os.path.join(get_project_root(), "config", "startup_config.yaml")
        )
        self.assertEqual(
            get_file_path("main_pc_logs", "system.log"),
            os.path.join(get_main_pc_code(), "logs", "system.log")
        )
    
    def test_directory_creation(self):
        """Test that directories are created if they don't exist."""
        for path_type in ["config", "logs", "data", "models", "cache", 
                          "main_pc_logs", "main_pc_data", "pc2_logs"]:
            dir_path = get_path(path_type)
            self.assertTrue(os.path.exists(dir_path), f"Directory {dir_path} does not exist")
    
    def test_custom_path(self):
        """Test adding and retrieving custom paths."""
        test_path = os.path.join(get_project_root(), "test_custom_dir")
        
        # Add a custom path
        path_manager.add_custom_path("test_custom", test_path)
        
        # Verify it was added correctly
        self.assertEqual(get_path("test_custom"), test_path)
        self.assertTrue(os.path.exists(test_path))
        
        # Clean up
        try:
            os.rmdir(test_path)
        except:
            pass
        
        # Test adding a path that already exists
        with self.assertRaises(ValueError):
            path_manager.add_custom_path("config", "some/path")
    
    def test_relative_path(self):
        """Test converting absolute paths to relative paths."""
        abs_path = os.path.join(get_project_root(), "config", "system_config.json")
        rel_path = path_manager.get_relative_path(abs_path)
        self.assertEqual(rel_path, os.path.join("config", "system_config.json"))


if __name__ == "__main__":
    unittest.main() 