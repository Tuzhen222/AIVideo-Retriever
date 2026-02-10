"""
Database connection and initialization for PostgreSQL
Supports both local PostgreSQL and AWS RDS PostgreSQL
"""
import psycopg2
import psycopg2.extras
import logging
import time
from typing import Optional
from contextlib import contextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_connection_params() -> dict:
    """
    Get PostgreSQL connection parameters as dict
    Supports SSL for AWS RDS connections
    """
    params = {
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
        "dbname": settings.POSTGRES_DB,
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
        "cursor_factory": psycopg2.extras.RealDictCursor
    }
    
    # Enable SSL for AWS RDS connections (if host contains .rds.amazonaws.com)
    if ".rds.amazonaws.com" in settings.POSTGRES_HOST.lower():
        params["sslmode"] = "require"
        logger.debug("SSL enabled for RDS connection")
    
    return params


def get_connection_string() -> str:
    """Get PostgreSQL connection string (for backward compatibility)"""
    params = get_connection_params()
    # Remove cursor_factory from connection string (it's a Python object)
    conn_str = (
        f"host={params['host']} "
        f"port={params['port']} "
        f"dbname={params['dbname']} "
        f"user={params['user']} "
        f"password={params['password']}"
    )
    if 'sslmode' in params:
        conn_str += f" sslmode={params['sslmode']}"
    return conn_str


@contextmanager
def get_connection(retry_attempts: int = 3, retry_delay: int = 2):
    """
    Get PostgreSQL database connection with retry logic
    Context manager ensures connection is properly closed
    
    Args:
        retry_attempts: Number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts
    """
    conn = None
    last_error = None
    
    for attempt in range(1, retry_attempts + 1):
        try:
            params = get_connection_params()
            conn = psycopg2.connect(**params)
            logger.debug(f"Database connection established to {params['host']}:{params['port']}")
            yield conn
            conn.commit()
            return
        except psycopg2.OperationalError as e:
            last_error = e
            if conn:
                try:
                    conn.close()
                except:
                    pass
                conn = None
            
            if attempt < retry_attempts:
                logger.warning(f"Database connection attempt {attempt} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Database connection failed after {retry_attempts} attempts: {e}")
                raise
        except psycopg2.Error as e:
            last_error = e
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass


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
