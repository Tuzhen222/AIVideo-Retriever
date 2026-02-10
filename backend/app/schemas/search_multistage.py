"""Schemas for the multi-stage search endpoint."""

from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class StageQuerySection(BaseModel):
    """Single stage query with its own settings"""
    stage_id: int
    stage_name: Optional[str] = ""
    query: str
    ocr_text: Optional[str] = ""
    toggles: Dict[str, bool]
    selected_objects: Optional[List[str]] = None


class MultiStageSearchRequest(BaseModel):
    """Request with multiple query stages"""
    stages: List[StageQuerySection]
    top_k: Optional[int] = None
    mode: Optional[str] = "E"  # E = ensemble only, A = all methods
    temporal_mode: Optional[str] = None  # "tuple" or "id" for temporal aggregation


class StageSearchResult(BaseModel):
    """Search result for a single stage"""
    stage_id: int
    stage_name: Optional[str] = ""
    query_original: str
    query_0: str  # Q0 = original (or translated)
    query_1: str  # Q1 = augmented 1
    query_2: str  # Q2 = augmented 2
    results: List[Dict[str, Any]]  # Ensemble of Q0+Q1+Q2 (for mode E)
    total: int
    enabled_methods: List[str]
    per_method_results: Optional[Dict[str, List[Dict[str, Any]]]] = None  # For mode M
    # For mode A: separate results per query
    q0_results: Optional[List[Dict[str, Any]]] = None
    q1_results: Optional[List[Dict[str, Any]]] = None
    q2_results: Optional[List[Dict[str, Any]]] = None


class MultiStageSearchResponse(BaseModel):
    """Response with results from all stages"""
    stages: List[StageSearchResult]
    total_stages: int
    temporal_aggregation: Optional[Dict[str, Any]] = None  # Temporal aggregated results
