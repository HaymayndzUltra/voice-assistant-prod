"""
PostgreSQL Connection Pool
-------------------------
Provides a connection pool for PostgreSQL database connections.
"""

import psycopg2
import psycopg2.pool
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logger = logging.getLogger("DBPool")

class DatabasePool:
    """
    Singleton class for managing a pool of PostgreSQL database connections.
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure only one instance of the pool exists."""
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, min_conn=2, max_conn=10, **db_params):
        """Initialize the connection pool if not already initialized."""
        if self._initialized:
            return
            
        # Default database parameters
        self.db_params = {
            'dbname': 'memory_db',
            'user': 'voiceassistant',
            'password': 'voiceassistant123',
            'host': 'localhost',
            'port': '5432'
        }
        
        # Update with any provided parameters
        self.db_params.update(db_params)
        
        # Create the connection pool
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                min_conn,
                max_conn,
                **self.db_params
            )
            logger.info(f"Database connection pool initialized with {min_conn}-{max_conn} connections")
            self._initialized = True
        except Exception as e:
            logger.error(f"Error initializing database connection pool: {e}")
            raise
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns:
            A database connection from the pool
        """
        try:
            conn = self.pool.getconn()
            logger.debug("Got connection from pool")
            return conn
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise
    
    def release_connection(self, conn):
        """
        Release a connection back to the pool.
        
        Args:
            conn: The connection to release
        """
        try:
            self.pool.putconn(conn)
            logger.debug("Released connection back to pool")
        except Exception as e:
            logger.error(f"Error releasing connection to pool: {e}")
            raise
    
    def close_all(self):
        """Close all connections in the pool."""
        try:
            self.pool.closeall()
            logger.info("Closed all connections in the pool")
        except Exception as e:
            logger.error(f"Error closing all connections: {e}")
            raise

# Global instance of the database pool
db_pool = DatabasePool()

def get_connection():
    """Get a connection from the global pool."""
    return db_pool.get_connection()

def release_connection(conn):
    """Release a connection back to the global pool."""
    db_pool.release_connection(conn)

def close_all_connections():
    """Close all connections in the global pool."""
    db_pool.close_all() 