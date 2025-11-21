"""
Database connection and initialization for SQLite
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """Get database file path"""
    db_path = Path(settings.BASE_DIR) / settings.CHATBOX_DB_PATH
    # Create parent directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


@contextmanager
def get_connection():
    """
    Get SQLite database connection with WAL mode enabled
    Context manager ensures connection is properly closed
    """
    db_path = get_db_path()
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        # Enable foreign keys (if needed in future)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        yield conn
        conn.commit()
    except sqlite3.Error as e:
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
    db_path = get_db_path()
    logger.info(f"Initializing chatbox database at: {db_path}")
    
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Create query_submissions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            cursor.execute("SELECT COUNT(*) FROM query_submissions")
            count = cursor.fetchone()[0]
            logger.info(f"   Current submissions count: {count}")
            
    except sqlite3.Error as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

