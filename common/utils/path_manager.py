import os

class PathManager:
    @staticmethod
    def get_project_root():
        """Return the absolute path to the project root directory."""
        # Adjust this as needed for your project structure
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
