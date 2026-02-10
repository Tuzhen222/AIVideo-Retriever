"""Schemas for the augmented search endpoint."""

from pydantic import BaseModel
from typing import Any, Dict


class AugmentedSearchResponse(BaseModel):
    """Response with query augmentation support"""
    query_0: Dict[str, Any]
    query_1: Dict[str, Any]
    query_2: Dict[str, Any]
    query_3: Dict[str, Any]
    total: int
    original_query: str
    method: str
