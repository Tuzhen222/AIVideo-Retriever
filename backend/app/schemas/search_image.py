"""Schemas for the image search endpoint."""

from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class ImageSearchRequest(BaseModel):
    """Request for image search using keyframe path"""
    keyframe_path: str
    top_k: Optional[int] = 200


class ImageSearchResponse(BaseModel):
    """Response for image search"""
    results: List[Dict[str, Any]]
    total: int
    query_image: str
    method: str = "clip-image"
    search_time_ms: float
