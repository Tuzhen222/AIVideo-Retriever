"""
Chatbox database operations
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.database.db import get_connection

logger = logging.getLogger(__name__)


def _convert_datetime_to_str(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert datetime objects to ISO format strings in dict
    Helper function to ensure created_at is always a string for Pydantic models
    """
    if 'created_at' in data and isinstance(data['created_at'], datetime):
        data['created_at'] = data['created_at'].isoformat()
    return data


def create_submission(
    query_text: str,
    keyframe_path: str,
    result_id: str,
    username: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new submission
    
    Args:
        query_text: Query text
        keyframe_path: Path to keyframe image
        result_id: Result ID from search
        username: Username of submitter
        notes: Optional notes
        
    Returns:
        Created submission dict with id and timestamps
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO query_submissions 
                (query_text, keyframe_path, result_id, username, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, query_text, keyframe_path, result_id, username, notes, created_at
            """, (query_text, keyframe_path, result_id, username, notes))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                return _convert_datetime_to_str(result)
            else:
                raise ValueError("Failed to retrieve created submission")
                
    except Exception as e:
        logger.error(f"Error creating submission: {e}")
        raise


def get_submissions(
    query_text: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> tuple[List[Dict[str, Any]], int]:
    """
    Get submissions with optional filters
    
    Args:
        query_text: Filter by query text (partial match)
        username: Filter by username
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        Tuple of (submissions list, total count)
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Build WHERE clause
            conditions = []
            params = []
            
            if query_text:
                conditions.append("query_text LIKE %s")
                params.append(f"%{query_text}%")
            
            if username:
                conditions.append("username = %s")
                params.append(username)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) as count FROM query_submissions WHERE {where_clause}", params)
            total = cursor.fetchone()['count']
            
            # Get submissions
            cursor.execute(f"""
                SELECT id, query_text, keyframe_path, result_id, username, notes, created_at
                FROM query_submissions
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, params + [limit, offset])
            
            rows = cursor.fetchall()
            submissions = [_convert_datetime_to_str(dict(row)) for row in rows]
            
            return submissions, total
            
    except Exception as e:
        logger.error(f"Error getting submissions: {e}")
        raise


def get_unique_queries() -> List[str]:
    """
    Get list of unique query texts (for filter dropdown)
    
    Returns:
        List of unique query texts, sorted alphabetically
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT query_text
                FROM query_submissions
                ORDER BY query_text ASC
            """)
            
            rows = cursor.fetchall()
            return [row['query_text'] for row in rows]
            
    except Exception as e:
        logger.error(f"Error getting unique queries: {e}")
        raise


def delete_submission(submission_id: int) -> bool:
    """
    Delete a submission by ID
    
    Args:
        submission_id: ID of submission to delete
        
    Returns:
        True if deleted, False if not found
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM query_submissions WHERE id = %s", (submission_id,))
            
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted submission {submission_id}")
            else:
                logger.warning(f"Submission {submission_id} not found for deletion")
            
            return deleted
            
    except Exception as e:
        logger.error(f"Error deleting submission: {e}")
        raise


def get_submission_by_id(submission_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a single submission by ID
    
    Args:
        submission_id: ID of submission
        
    Returns:
        Submission dict or None if not found
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, query_text, keyframe_path, result_id, username, notes, created_at
                FROM query_submissions
                WHERE id = %s
            """, (submission_id,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                return _convert_datetime_to_str(result)
            return None
            
    except Exception as e:
        logger.error(f"Error getting submission by id: {e}")
        raise
