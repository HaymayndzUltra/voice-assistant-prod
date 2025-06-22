"""
PostgreSQL Database Schema Creation Script
-----------------------------------------
Creates the database schema for the Memory Orchestrator service.
Based on the schema defined in docs/design/memory_db_schema.md.
"""

import psycopg2
import logging
import os
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, 'logs', 'db_setup.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DatabaseSetup")

# Database connection parameters
DB_PARAMS = {
    'dbname': 'memory_db',
    'user': 'voiceassistant',
    'password': 'voiceassistant123',
    'host': 'localhost',
    'port': '5432'
}

# Maximum number of connection attempts
MAX_RETRIES = 10
RETRY_DELAY = 5  # seconds

def wait_for_postgres():
    """Wait for PostgreSQL to be available."""
    logger.info("Waiting for PostgreSQL to be available...")
    
    for attempt in range(MAX_RETRIES):
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            conn.close()
            logger.info("PostgreSQL is available!")
            return True
        except psycopg2.OperationalError:
            logger.info(f"PostgreSQL not available yet. Retry {attempt+1}/{MAX_RETRIES}")
            time.sleep(RETRY_DELAY)
    
    logger.error("Failed to connect to PostgreSQL after multiple attempts")
    return False

def create_schema():
    """Create the database schema."""
    logger.info("Creating database schema...")
    
    # SQL statements for creating tables and indexes
    sql_statements = [
        # Enable pgvector extension
        """
        CREATE EXTENSION IF NOT EXISTS vector;
        """,
        
        # 1. Sessions Table
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR(64) PRIMARY KEY,
            user_id VARCHAR(64),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            metadata JSONB,
            summary TEXT,
            is_archived BOOLEAN NOT NULL DEFAULT FALSE,
            session_type VARCHAR(32) NOT NULL
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_sessions_session_type ON sessions(session_type);
        """,
        
        # 2. Memory Entries Table
        """
        CREATE TABLE IF NOT EXISTS memory_entries (
            memory_id VARCHAR(64) PRIMARY KEY,
            session_id VARCHAR(64) REFERENCES sessions(session_id) ON DELETE CASCADE,
            memory_type VARCHAR(32) NOT NULL,
            content JSONB NOT NULL,
            text_content TEXT,
            source_agent VARCHAR(64),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            priority INTEGER NOT NULL DEFAULT 5,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            
            CONSTRAINT valid_priority CHECK (priority BETWEEN 1 AND 10)
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_session_id ON memory_entries(session_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type ON memory_entries(memory_type);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_created_at ON memory_entries(created_at);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_expires_at ON memory_entries(expires_at);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_source_agent ON memory_entries(source_agent);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_text_content ON memory_entries USING GIN (to_tsvector('english', text_content));
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_priority ON memory_entries(priority);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_content ON memory_entries USING GIN (content);
        """,
        
        # 3. Memory Tags Table
        """
        CREATE TABLE IF NOT EXISTS memory_tags (
            tag_id SERIAL PRIMARY KEY,
            memory_id VARCHAR(64) NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
            tag VARCHAR(64) NOT NULL,
            
            CONSTRAINT unique_memory_tag UNIQUE (memory_id, tag)
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_tags_memory_id ON memory_tags(memory_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_tags_tag ON memory_tags(tag);
        """,
        
        # 4. Vector Embeddings Table
        """
        CREATE TABLE IF NOT EXISTS vector_embeddings (
            embedding_id SERIAL PRIMARY KEY,
            memory_id VARCHAR(64) NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
            embedding VECTOR(1536) NOT NULL,
            embedding_model VARCHAR(64) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            CONSTRAINT unique_memory_embedding UNIQUE (memory_id, embedding_model)
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_vector_embeddings_memory_id ON vector_embeddings(memory_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_vector_embeddings_embedding_model ON vector_embeddings(embedding_model);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_vector_embeddings_embedding ON vector_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """,
        
        # 5. User Profiles Table
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id VARCHAR(64) PRIMARY KEY,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            profile_data JSONB,
            preferences JSONB,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_user_profiles_is_active ON user_profiles(is_active);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_user_profiles_preferences ON user_profiles USING GIN (preferences);
        """,
        
        # 6. Agent States Table
        """
        CREATE TABLE IF NOT EXISTS agent_states (
            state_id SERIAL PRIMARY KEY,
            agent_id VARCHAR(64) NOT NULL,
            session_id VARCHAR(64) REFERENCES sessions(session_id) ON DELETE SET NULL,
            state_data JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            
            CONSTRAINT unique_agent_session UNIQUE (agent_id, session_id)
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_agent_states_agent_id ON agent_states(agent_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_agent_states_session_id ON agent_states(session_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_agent_states_expires_at ON agent_states(expires_at);
        """,
        
        # 7. Memory Relationships Table
        """
        CREATE TABLE IF NOT EXISTS memory_relationships (
            relationship_id SERIAL PRIMARY KEY,
            source_memory_id VARCHAR(64) NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
            target_memory_id VARCHAR(64) NOT NULL REFERENCES memory_entries(memory_id) ON DELETE CASCADE,
            relationship_type VARCHAR(32) NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            CONSTRAINT unique_memory_relationship UNIQUE (source_memory_id, target_memory_id, relationship_type)
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_relationships_source ON memory_relationships(source_memory_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_relationships_target ON memory_relationships(target_memory_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_relationships_type ON memory_relationships(relationship_type);
        """,
        
        # 8. Memory Access Log Table
        """
        CREATE TABLE IF NOT EXISTS memory_access_log (
            log_id SERIAL PRIMARY KEY,
            memory_id VARCHAR(64) REFERENCES memory_entries(memory_id) ON DELETE SET NULL,
            session_id VARCHAR(64) REFERENCES sessions(session_id) ON DELETE SET NULL,
            agent_id VARCHAR(64),
            access_type VARCHAR(32) NOT NULL,
            access_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            details JSONB
        );
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_access_log_memory_id ON memory_access_log(memory_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_access_log_session_id ON memory_access_log(session_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_access_log_agent_id ON memory_access_log(agent_id);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_access_log_access_type ON memory_access_log(access_type);
        """,
        
        """
        CREATE INDEX IF NOT EXISTS idx_memory_access_log_access_time ON memory_access_log(access_time);
        """
    ]
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_PARAMS)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Execute each SQL statement
        for statement in sql_statements:
            cursor.execute(statement)
            
        logger.info("Database schema created successfully")
        
        # Close the connection
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating database schema: {e}")
        return False

def main():
    """Main function to set up the database schema."""
    # Wait for PostgreSQL to be available
    if not wait_for_postgres():
        sys.exit(1)
    
    # Create the schema
    if not create_schema():
        sys.exit(1)
    
    logger.info("Database setup completed successfully")

if __name__ == "__main__":
    main() 