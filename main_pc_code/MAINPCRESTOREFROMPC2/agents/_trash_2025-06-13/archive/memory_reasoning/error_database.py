from main_pc_code.src.core.base_agent import BaseAgent
"""
Error Database for AutoFix System
- Stores common errors and their solutions
- Provides quick fixes for known issues
- Learns from successful fixes over time
- Improves efficiency of the auto-fix process
"""
import sqlite3
import json
import time
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/error_database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ErrorDatabase")

class ErrorDatabase(BaseAgent):
    """Database for tracking common errors and their solutions"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ErrorDatabase")
        """Initialize the error database"""
        self.db_path = db_path
        Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
        logger.info(f"Error database initialized at {db_path}")
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Error patterns table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS error_patterns (
            id INTEGER PRIMARY KEY,
            error_type TEXT NOT NULL,
            language TEXT NOT NULL,
            pattern TEXT NOT NULL,
            severity TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            frequency INTEGER DEFAULT 1,
            UNIQUE(error_type, language, pattern)
        )
        ''')
        
        # Solutions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS solutions (
            id INTEGER PRIMARY KEY,
            error_pattern_id INTEGER NOT NULL,
            solution_code TEXT NOT NULL,
            success_rate REAL DEFAULT 0.0,
            usage_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            FOREIGN KEY (error_pattern_id) REFERENCES error_patterns (id)
        )
        ''')
        
        # Fix history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fix_history (
            id INTEGER PRIMARY KEY,
            error_pattern_id INTEGER NOT NULL,
            solution_id INTEGER NOT NULL,
            original_code TEXT NOT NULL,
            error_message TEXT NOT NULL,
            fixed_code TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            execution_time REAL,
            created_at REAL NOT NULL,
            FOREIGN KEY (error_pattern_id) REFERENCES error_patterns (id),
            FOREIGN KEY (solution_id) REFERENCES solutions (id)
        )
        ''')
        
        self.conn.commit()
    
    def add_error_pattern(self, error_type: str, language: str, pattern: str, severity: str = "medium") -> int:
        """Add a new error pattern to the database"""
        cursor = self.conn.cursor()
        now = time.time()
        
        try:
            cursor.execute('''
            INSERT INTO error_patterns (error_type, language, pattern, severity, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (error_type, language, pattern, severity, now, now))
            
            self.conn.commit()
            pattern_id = cursor.lastrowid
            logger.info(f"Added new error pattern: {error_type} in {language}")
            return pattern_id
        
        except sqlite3.IntegrityError:
            # Pattern already exists, update frequency
            cursor.execute('''
            UPDATE error_patterns
            SET frequency = frequency + 1, updated_at = ?
            WHERE error_type = ? AND language = ? AND pattern = ?
            ''', (now, error_type, language, pattern))
            
            cursor.execute('''
            SELECT id FROM error_patterns
            WHERE error_type = ? AND language = ? AND pattern = ?
            ''', (error_type, language, pattern))
            
            pattern_id = cursor.fetchone()[0]
            self.conn.commit()
            logger.info(f"Updated existing error pattern: {error_type} in {language}")
            return pattern_id
    
    def add_solution(self, error_pattern_id: int, solution_code: str) -> int:
        """Add a new solution for an error pattern"""
        cursor = self.conn.cursor()
        now = time.time()
        
        cursor.execute('''
        INSERT INTO solutions (error_pattern_id, solution_code, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ''', (error_pattern_id, solution_code, now, now))
        
        self.conn.commit()
        solution_id = cursor.lastrowid
        logger.info(f"Added new solution for error pattern {error_pattern_id}")
        return solution_id
    
    def record_fix_attempt(self, error_pattern_id: int, solution_id: int, 
                          original_code: str, error_message: str, fixed_code: str, 
                          success: bool, execution_time: float = None) -> int:
        """Record a fix attempt in the history"""
        cursor = self.conn.cursor()
        now = time.time()
        
        cursor.execute('''
        INSERT INTO fix_history (
            error_pattern_id, solution_id, original_code, error_message, 
            fixed_code, success, execution_time, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            error_pattern_id, solution_id, original_code, error_message,
            fixed_code, success, execution_time, now
        ))
        
        # Update solution success rate
        if success:
            cursor.execute('''
            UPDATE solutions
            SET usage_count = usage_count + 1, 
                success_count = success_count + 1,
                success_rate = CAST(success_count + 1 AS REAL) / (usage_count + 1),
                updated_at = ?
            WHERE id = ?
            ''', (now, solution_id))
        else:
            cursor.execute('''
            UPDATE solutions
            SET usage_count = usage_count + 1,
                success_rate = CAST(success_count AS REAL) / (usage_count + 1),
                updated_at = ?
            WHERE id = ?
            ''', (now, solution_id))
        
        self.conn.commit()
        history_id = cursor.lastrowid
        logger.info(f"Recorded fix attempt for error pattern {error_pattern_id}, success: {success}")
        return history_id
    
    def find_matching_error(self, error_message: str, language: str) -> Optional[Tuple[int, str, List[Dict[str, Any]]]]:
        """Find a matching error pattern for the given error message"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
        SELECT id, error_type, pattern FROM error_patterns
        WHERE language = ?
        ORDER BY frequency DESC
        ''', (language,))
        
        patterns = cursor.fetchall()
        
        for pattern_id, error_type, pattern in patterns:
            try:
                if re.search(pattern, error_message, re.IGNORECASE):
                    # Found a matching pattern, get solutions
                    cursor.execute('''
                    SELECT id, solution_code, success_rate
                    FROM solutions
                    WHERE error_pattern_id = ?
                    ORDER BY success_rate DESC
                    ''', (pattern_id,))
                    
                    solutions = [{
                        "id": row[0],
                        "solution_code": row[1],
                        "success_rate": row[2]
                    } for row in cursor.fetchall()]
                    
                    return pattern_id, error_type, solutions
            except re.error:
                # Invalid regex pattern, skip it
                logger.warning(f"Invalid regex pattern: {pattern}")
                continue
        
        return None
    
    def get_best_solution(self, error_pattern_id: int) -> Optional[Dict[str, Any]]:
        """Get the best solution for an error pattern"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
        SELECT id, solution_code, success_rate
        FROM solutions
        WHERE error_pattern_id = ?
        ORDER BY success_rate DESC
        LIMIT 1
        ''', (error_pattern_id,))
        
        row = cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "solution_code": row[1],
                "success_rate": row[2]
            }
        
        return None
    
    def analyze_error_message(self, error_message: str, language: str) -> Dict[str, Any]:
        """Analyze an error message to extract useful information"""
        error_info = {
            "language": language,
            "error_type": "unknown",
            "line_number": None,
            "error_details": error_message,
            "severity": "medium"
        }
        
        # Python error patterns
        if language.lower() == "python":
            # Syntax error
            syntax_match = re.search(r'SyntaxError: (.*?)(?:\n|$)', error_message)
            if syntax_match:
                error_info["error_type"] = "syntax"
                error_info["severity"] = "high"
            
            # Name error
            name_match = re.search(r'NameError: name \'(.*?)\' is not defined', error_message)
            if name_match:
                error_info["error_type"] = "name"
                error_info["variable"] = name_match.group(1)
            
            # Type error
            type_match = re.search(r'TypeError: (.*?)(?:\n|$)', error_message)
            if type_match:
                error_info["error_type"] = "type"
            
            # Import error
            import_match = re.search(r'ImportError: (.*?)(?:\n|$)', error_message)
            if import_match:
                error_info["error_type"] = "import"
                error_info["module"] = import_match.group(1).split()[-1]
            
            # Line number
            line_match = re.search(r'line (\d+)', error_message)
            if line_match:
                error_info["line_number"] = int(line_match.group(1))
        
        # JavaScript error patterns
        elif language.lower() in ["javascript", "js"]:
            # Syntax error
            syntax_match = re.search(r'SyntaxError: (.*?)(?:\n|$)', error_message)
            if syntax_match:
                error_info["error_type"] = "syntax"
                error_info["severity"] = "high"
            
            # Reference error
            ref_match = re.search(r'ReferenceError: (.*?) is not defined', error_message)
            if ref_match:
                error_info["error_type"] = "reference"
                error_info["variable"] = ref_match.group(1)
            
            # Type error
            type_match = re.search(r'TypeError: (.*?)(?:\n|$)', error_message)
            if type_match:
                error_info["error_type"] = "type"
        
        return error_info
    
    def extract_error_pattern(self, error_message: str, language: str) -> str:
        """Extract a regex pattern from an error message"""
        # This is a simplified version - in a real system, this would be more sophisticated
        error_info = self.analyze_error_message(error_message, language)
        
        if error_info["error_type"] == "syntax":
            # For syntax errors, use a more specific pattern
            syntax_match = re.search(r'SyntaxError: (.*?)(?:\n|$)', error_message)
            if syntax_match:
                error_detail = syntax_match.group(1)
                # Escape special regex characters and make a pattern
                pattern = re.escape(f"SyntaxError: {error_detail}")
                return pattern
        
        elif error_info["error_type"] == "name" and language.lower() == "python":
            # For name errors in Python
            name_match = re.search(r'NameError: name \'(.*?)\' is not defined', error_message)
            if name_match:
                variable = name_match.group(1)
                pattern = f"NameError: name '.*?' is not defined"
                return pattern
        
        # Default: use a simplified version of the error message as pattern
        # Remove specific line numbers, file paths, etc.
        simplified = re.sub(r'line \d+', 'line \\d+', error_message)
        simplified = re.sub(r'File ".*?"', 'File ".*?"', simplified)
        
        return simplified
    
    def learn_from_fix(self, error_message: str, language: str, original_code: str, 
                      fixed_code: str, success: bool) -> None:
        """Learn from a successful fix"""
        # Extract error pattern
        pattern = self.extract_error_pattern(error_message, language)
        error_info = self.analyze_error_message(error_message, language)
        
        # Add or update error pattern
        pattern_id = self.add_error_pattern(
            error_info["error_type"], 
            language, 
            pattern, 
            error_info["severity"]
        )
        
        # Add solution if it doesn't exist
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT id FROM solutions
        WHERE error_pattern_id = ? AND solution_code = ?
        ''', (pattern_id, fixed_code))
        
        row = cursor.fetchone()
        if row:
            solution_id = row[0]
        else:
            solution_id = self.add_solution(pattern_id, fixed_code)
        
        # Record the fix attempt
        self.record_fix_attempt(
            pattern_id, 
            solution_id, 
            original_code, 
            error_message, 
            fixed_code, 
            success
        )
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Error database connection closed")


# Example usage
if __name__ == "__main__":
    db = ErrorDatabase()
    
    # Example: Adding error patterns and solutions
    pattern_id = db.add_error_pattern(
        "syntax", 
        "python", 
        "SyntaxError: invalid syntax", 
        "high"
    )
    
    solution_id = db.add_solution(
        pattern_id,
        "# Check for missing parentheses or brackets\n# Make sure all opening brackets have matching closing brackets"
    )
    
    # Example: Recording a fix attempt
    db.record_fix_attempt(
        pattern_id,
        solution_id,
        "print('Hello world'",  # Original code with error
        "SyntaxError: invalid syntax",  # Error message
        "print('Hello world')",  # Fixed code
        True,  # Success
        0.5  # Execution time
    )
    
    # Example: Finding a matching error
    result = db.find_matching_error("SyntaxError: invalid syntax", "python")
    if result:
        pattern_id, error_type, solutions = result
        print(f"Found matching error pattern: {error_type}")
        print(f"Available solutions: {len(solutions)}")
    
    db.close()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
