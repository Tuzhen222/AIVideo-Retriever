"""Schemas for the chatbox endpoint."""

from pydantic import BaseModel, Field
from typing import List, Optional


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
