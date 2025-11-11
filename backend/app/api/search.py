from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
import logging

from app.logger.logger import log_search_query
from app.services.multimodel_search import get_multimodel_search

router = APIRouter()
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    """Search request model"""
    query: str
    method: Optional[str] = "ensemble"  # ensemble, clip, beit3, blip2, etc.
    top_k: Optional[int] = 10
    filters: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Search response model"""
    results: List[Dict[str, Any]]
    total: int
    query: str
    method: str


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search endpoint for video retrieval
    
    Args:
        request: Search request with query and parameters
        
    Returns:
        Search results with video segments/keyframes
    """
    start_time = time.time()
    
    try:
        logger.info(f"Search request received - Query: '{request.query}', Method: {request.method}, TopK: {request.top_k}")
        
        # Get multi-model search instance
        search_engine = get_multimodel_search()
        
        # Perform search based on method
        if request.method.lower() == "ensemble":
            results = search_engine.search(
                query=request.query,
                top_k=request.top_k,
                filters=request.filters
            )
        elif request.method.lower() in ["clip", "beit3", "blip2"]:
            results = search_engine.search_single_model(
                query=request.query,
                model=request.method.lower(),
                top_k=request.top_k,
                filters=request.filters
            )
        else:
            logger.warning(f"Unknown search method: {request.method}, using ensemble")
            results = search_engine.search(
                query=request.query,
                top_k=request.top_k,
                filters=request.filters
            )
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log search query
        log_search_query(
            query=request.query,
            method=request.method,
            top_k=request.top_k,
            filters=request.filters,
            results_count=len(results),
            duration_ms=duration_ms
        )
        
        logger.info(f"Search completed - Results: {len(results)}, Duration: {duration_ms:.2f}ms")
        
        return SearchResponse(
            results=results,
            total=len(results),
            query=request.query,
            method=request.method
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"Search error - Query: '{request.query}', Error: {str(e)}, Duration: {duration_ms:.2f}ms")
        
        # Log failed search
        log_search_query(
            query=request.query,
            method=request.method,
            top_k=request.top_k,
            filters=request.filters,
            results_count=0,
            duration_ms=duration_ms
        )
        
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")


@router.get("/search/methods")
async def get_search_methods():
    """Get available search methods"""
    return {
        "methods": [
            "ensemble",
            "clip",
            "beit3",
            "blip2",
            "caption",
            "object",
            "text"
        ]
    }

