#!/usr/bin/env python3
"""
Unit tests for PathManager script resolution functionality.

Tests the fix for start_system_v2.py script path validation bug.
"""

import unittest
import sys
from pathlib import Path
import tempfile
import os

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager


class TestPathManagerScriptResolution(unittest.TestCase):
    """Test PathManager script resolution methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path(PathManager.get_project_root())
        
    def test_resolve_script_mainpc(self):
        """Test resolving MainPC agent script paths."""
        # Test with a known MainPC agent script
        script_path = "main_pc_code/agents/service_registry_agent.py"
        resolved_path = PathManager.resolve_script(script_path)
        
        self.assertIsNotNone(resolved_path, "resolve_script should return a Path object")
        self.assertIsInstance(resolved_path, Path, "Should return a Path object")
        self.assertTrue(resolved_path.is_absolute(), "Should return absolute path")
        self.assertEqual(resolved_path.name, "service_registry_agent.py", "Should preserve filename")
        
        # Check that path is within project root
        try:
            resolved_path.relative_to(self.project_root)
        except ValueError:
            self.fail("Resolved path should be within project root")
    
    def test_resolve_script_pc2(self):
        """Test resolving PC2 agent script paths."""
        # Test with a known PC2 agent script  
        script_path = "pc2_code/agents/memory_orchestrator_service.py"
        resolved_path = PathManager.resolve_script(script_path)
        
        self.assertIsNotNone(resolved_path, "resolve_script should return a Path object")
        self.assertIsInstance(resolved_path, Path, "Should return a Path object")
        self.assertTrue(resolved_path.is_absolute(), "Should return absolute path")
        self.assertEqual(resolved_path.name, "memory_orchestrator_service.py", "Should preserve filename")
    
    def test_resolve_script_phase1(self):
        """Test resolving phase1_implementation script paths."""
        # Test with phase1 implementation path structure
        script_path = "phase1_implementation/consolidated_agents/observability_hub/observability_hub.py"
        resolved_path = PathManager.resolve_script(script_path)
        
        self.assertIsNotNone(resolved_path, "resolve_script should return a Path object")
        self.assertIsInstance(resolved_path, Path, "Should return a Path object")
        self.assertTrue(resolved_path.is_absolute(), "Should return absolute path")
        
        # Check path structure
        expected_path = self.project_root / script_path
        self.assertEqual(resolved_path, expected_path.resolve())
    
    def test_resolve_script_missing(self):
        """Test handling of missing script paths."""
        # Test with non-existent script
        script_path = "non_existent/script.py"
        resolved_path = PathManager.resolve_script(script_path)
        
        # Should return a path object even if file doesn't exist
        # (existence check is done by caller)
        self.assertIsNotNone(resolved_path, "Should return path even if file doesn't exist")
        self.assertIsInstance(resolved_path, Path, "Should return a Path object")
    
    def test_resolve_script_empty_path(self):
        """Test handling of empty or None paths."""
        # Test with empty string
        resolved_path = PathManager.resolve_script("")
        self.assertIsNone(resolved_path, "Empty path should return None")
        
        # Test with None
        resolved_path = PathManager.resolve_script(None)
        self.assertIsNone(resolved_path, "None path should return None")
    
    def test_resolve_script_security(self):
        """Test security - prevent path traversal outside project root."""
        # Test with path traversal attempt
        malicious_path = "../../../etc/passwd"
        resolved_path = PathManager.resolve_script(malicious_path)
        
        # Should return None for paths outside project root
        self.assertIsNone(resolved_path, "Path traversal should be blocked")
        
        # Test with subtle path traversal
        malicious_path2 = "main_pc_code/../../../etc/passwd"
        resolved_path2 = PathManager.resolve_script(malicious_path2)
        self.assertIsNone(resolved_path2, "Subtle path traversal should be blocked")
    
    def test_resolve_script_different_formats(self):
        """Test different script path formats."""
        test_cases = [
            "main_pc_code/agents/test_agent.py",
            "pc2_code/agents/test_agent.py",
            "phase1_implementation/test/test_agent.py",
            "common/utils/test_utility.py"
        ]
        
        for script_path in test_cases:
            with self.subTest(script_path=script_path):
                resolved_path = PathManager.resolve_script(script_path)
                self.assertIsNotNone(resolved_path, f"Should resolve {script_path}")
                self.assertTrue(resolved_path.is_absolute(), f"Should be absolute: {script_path}")
                
                # Check that resolved path contains original filename
                self.assertEqual(resolved_path.name, Path(script_path).name)
    
    def test_integration_with_actual_files(self):
        """Integration test with actual files in the project."""
        # Test with files that should actually exist
        actual_files = [
            "main_pc_code/config/startup_config.yaml",  # Config file, not .py but should work
            "common/utils/path_manager.py",             # The file we're testing
            "scripts/validate_config.py"               # The validator we created
        ]
        
        for file_path in actual_files:
            with self.subTest(file_path=file_path):
                resolved_path = PathManager.resolve_script(file_path)
                self.assertIsNotNone(resolved_path, f"Should resolve {file_path}")
                
                # For these known files, check they actually exist
                if resolved_path:
                    self.assertTrue(resolved_path.exists(), 
                                  f"File should exist: {resolved_path}")


class TestPathManagerGeneralMethods(unittest.TestCase):
    """Test other PathManager methods for completeness."""
    
    def test_get_project_root(self):
        """Test project root detection."""
        root = PathManager.get_project_root()
        self.assertIsInstance(root, str, "Should return string")
        self.assertTrue(os.path.isabs(root), "Should be absolute path")
        self.assertTrue(os.path.exists(root), "Project root should exist")
    
    def test_directory_methods(self):
        """Test directory path methods."""
        directories = [
            PathManager.get_logs_dir(),
            PathManager.get_data_dir(),
            PathManager.get_config_dir(),
            PathManager.get_models_dir(),
            PathManager.get_cache_dir()
        ]
        
        for dir_path in directories:
            with self.subTest(dir_path=dir_path):
                self.assertIsInstance(dir_path, Path, "Should return Path object")
                self.assertTrue(dir_path.is_absolute(), "Should be absolute path")
    
    def test_resolve_path(self):
        """Test general path resolution."""
        test_path = "test/example/file.txt"
        resolved = PathManager.resolve_path(test_path)
        
        self.assertIsInstance(resolved, Path, "Should return Path object")
        self.assertTrue(resolved.is_absolute(), "Should be absolute path")
    
    def test_ensure_directory(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test" / "nested" / "directory"
            
            # Directory shouldn't exist initially
            self.assertFalse(test_dir.exists())
            
            # Create it
            result = PathManager.ensure_directory(test_dir)
            
            # Should exist now
            self.assertTrue(test_dir.exists())
            self.assertTrue(test_dir.is_dir())
            self.assertEqual(result, test_dir)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2) 