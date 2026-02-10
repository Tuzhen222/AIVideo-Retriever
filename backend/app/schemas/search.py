"""Schemas for the basic search endpoint."""

from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class QuerySection(BaseModel):
    query: str
    ocrText: Optional[str] = ""
    toggles: Dict[str, bool]
    selectedObjects: Optional[List[str]] = None


class SearchRequest(BaseModel):
    query: str
    method: str
    top_k: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None
    queries: Optional[List[QuerySection]] = None
    mode: Optional[str] = "E"


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str
    method: str
    per_method_results: Optional[Dict[str, List[Dict[str, Any]]]] = None
