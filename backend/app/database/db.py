"""
Database connection and initialization for PostgreSQL
"""
import psycopg2
import psycopg2.extras
import logging
from typing import Optional
from contextlib import contextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_connection_string() -> str:
    """Get PostgreSQL connection string"""
    return (
        f"host={settings.POSTGRES_HOST} "
        f"port={settings.POSTGRES_PORT} "
        f"dbname={settings.POSTGRES_DB} "
        f"user={settings.POSTGRES_USER} "
        f"password={settings.POSTGRES_PASSWORD}"
    )


@contextmanager
def get_connection():
    """
    Get PostgreSQL database connection
    Context manager ensures connection is properly closed
    """
    conn = None
    try:
        conn = psycopg2.connect(
            get_connection_string(),
            cursor_factory=psycopg2.extras.RealDictCursor  # Return rows as dict-like objects
        )
        yield conn
        conn.commit()
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def init_database():
    """
    Initialize database and create tables if they don't exist
    Called on application startup
    """
    logger.info(f"Initializing chatbox database at: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Create query_submissions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_submissions (
                    id SERIAL PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    keyframe_path TEXT NOT NULL,
                    result_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_text 
                ON query_submissions(query_text)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON query_submissions(created_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_username 
                ON query_submissions(username)
            """)
            
            conn.commit()
            logger.info("✅ Chatbox database initialized successfully")
            
            # Log table info
            cursor.execute("SELECT COUNT(*) as count FROM query_submissions")
            count = cursor.fetchone()['count']
            logger.info(f"   Current submissions count: {count}")
            
    except psycopg2.Error as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
