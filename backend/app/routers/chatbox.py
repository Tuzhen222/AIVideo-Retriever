"""
Chatbox API endpoints for storing and retrieving query answers
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging

from app.core.config import settings
from app.database import chatbox_db
from app.logger.logger import app_logger as logger

router = APIRouter()


# Request/Response Models
class SubmitAnswerRequest(BaseModel):
    """Request model for submitting an answer"""
    query_text: str = Field(..., min_length=1, description="Query text")
    keyframe_path: str = Field(..., min_length=1, description="Path to keyframe image")
    result_id: str = Field(..., min_length=1, description="Result ID from search")
    username: str = Field(..., min_length=1, description="Username of submitter")
    notes: Optional[str] = Field(None, description="Optional notes")


class SubmissionResponse(BaseModel):
    """Response model for a single submission"""
    id: int
    query_text: str
    keyframe_path: str
    result_id: str
    username: str
    notes: Optional[str]
    created_at: str


class SubmitAnswerResponse(BaseModel):
    """Response model for submit endpoint"""
    success: bool
    submission: SubmissionResponse


class FetchSubmissionsResponse(BaseModel):
    """Response model for fetch endpoint"""
    submissions: List[SubmissionResponse]
    total: int
    limit: int
    offset: int


class UniqueQueriesResponse(BaseModel):
    """Response model for unique queries endpoint"""
    queries: List[str]


class DeleteSubmissionResponse(BaseModel):
    """Response model for delete endpoint"""
    success: bool
    message: str


@router.post("/submit", response_model=SubmitAnswerResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """
    Submit a new answer for a query
    
    Args:
        request: SubmitAnswerRequest with query_text, keyframe_path, result_id, username, notes
        
    Returns:
        SubmitAnswerResponse with created submission
        
    Note: Future enhancements could include:
    - User authentication/authorization
    - Rate limiting per user
    - Validation of keyframe_path existence
    - Duplicate detection
    """
    try:
        logger.info(f"📥 Received submit request: query_text='{request.query_text[:50]}...', keyframe_path='{request.keyframe_path}', result_id='{request.result_id}', username='{request.username}'")
        # Validate keyframe_path format (basic check)
        if not request.keyframe_path.startswith("/keyframe/"):
            logger.warning(f"Invalid keyframe_path format: {request.keyframe_path}")
            # Still allow it, but log warning
        
        # Create submission
        submission = chatbox_db.create_submission(
            query_text=request.query_text,
            keyframe_path=request.keyframe_path,
            result_id=request.result_id,
            username=request.username,
            notes=request.notes
        )
        
        logger.info(f"✅ Submission created: id={submission['id']}, query='{request.query_text[:50]}...', user={request.username}")
        
        return SubmitAnswerResponse(
            success=True,
            submission=SubmissionResponse(
                id=submission['id'],
                query_text=submission['query_text'],
                keyframe_path=submission['keyframe_path'],
                result_id=submission['result_id'],
                username=submission['username'],
                notes=submission['notes'],
                created_at=submission['created_at']
            )
        )
        
    except Exception as e:
        logger.error(f"❌ Error submitting answer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit answer: {str(e)}")


@router.get("/fetch", response_model=FetchSubmissionsResponse)
async def fetch_submissions(
    query_text: Optional[str] = Query(None, description="Filter by query text (partial match)"),
    username: Optional[str] = Query(None, description="Filter by username"),
    limit: int = Query(50, ge=1, le=settings.CHATBOX_MAX_LIMIT, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Fetch submissions with optional filters
    
    Args:
        query_text: Optional filter by query text (partial match)
        username: Optional filter by username
        limit: Maximum number of results (default 50, max 200)
        offset: Offset for pagination (default 0)
        
    Returns:
        FetchSubmissionsResponse with list of submissions
        
    Note: Future enhancements could include:
    - Full-text search
    - Sorting options
    - Date range filtering
    """
    try:
        submissions, total = chatbox_db.get_submissions(
            query_text=query_text,
            username=username,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        submission_responses = [
            SubmissionResponse(
                id=sub['id'],
                query_text=sub['query_text'],
                keyframe_path=sub['keyframe_path'],
                result_id=sub['result_id'],
                username=sub['username'],
                notes=sub['notes'],
                created_at=sub['created_at']
            )
            for sub in submissions
        ]
        
        return FetchSubmissionsResponse(
            submissions=submission_responses,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"❌ Error fetching submissions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch submissions: {str(e)}")


@router.get("/queries", response_model=UniqueQueriesResponse)
async def get_unique_queries():
    """
    Get list of unique query texts (for filter dropdown)
    
    Returns:
        UniqueQueriesResponse with list of unique queries
        
    Note: Future enhancements could include:
    - Query frequency/count
    - Most recent query first
    - Search/filter within unique queries
    """
    try:
        queries = chatbox_db.get_unique_queries()
        return UniqueQueriesResponse(queries=queries)
        
    except Exception as e:
        logger.error(f"❌ Error getting unique queries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get unique queries: {str(e)}")


@router.delete("/submissions/{submission_id}", response_model=DeleteSubmissionResponse)
async def delete_submission(submission_id: int):
    """
    Delete a submission by ID
    
    WARNING: Currently allows anyone to delete any submission.
    Future enhancements should include:
    - User authentication
    - Permission checks (only submitter or admin can delete)
    - Soft delete instead of hard delete
    - Audit log for deletions
    
    Args:
        submission_id: ID of submission to delete
        
    Returns:
        DeleteSubmissionResponse with success status
    """
    try:
        # Check if submission exists
        submission = chatbox_db.get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail=f"Submission {submission_id} not found")
        
        # Delete submission
        deleted = chatbox_db.delete_submission(submission_id)
        
        if deleted:
            logger.warning(f"⚠️  Submission {submission_id} deleted (query: '{submission['query_text'][:50]}...', user: {submission['username']})")
            return DeleteSubmissionResponse(
                success=True,
                message=f"Submission {submission_id} deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail=f"Submission {submission_id} not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting submission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete submission: {str(e)}")

