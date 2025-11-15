"""
New search endpoint with query augmentation.
This will replace the old search.py after testing.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging
import time
from collections import defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.logger.logger import log_search_query
from app.services.method.multimodel_search import get_multimodel_search
from app.services.method.asr_ocr import get_asr_ocr_search
from app.services.method.ic_search import get_ic_search
from app.services.method.object_filter import ObjectFilterSearch
from app.utils.scale import ScoreScaler
from app.utils.translator import get_translator
from app.services.gemini.query_augmentation import get_query_augmentor

logger = logging.getLogger(__name__)
router = APIRouter()

# Thread pool for parallel search execution
_search_executor = ThreadPoolExecutor(max_workers=5)


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


class AugmentedSearchResponse(BaseModel):
    """Response with query augmentation support"""
    query_0: Dict[str, Any]
    query_1: Dict[str, Any]
    query_2: Dict[str, Any]
    query_3: Dict[str, Any]
    total: int
    original_query: str
    method: str


def _search_single_query(query_text: str, enabled_methods: set, top_k: int, ocr_text: str = None, object_filter_enabled: bool = False, selected_objects: List[str] = None):
    """
    Search with a single query across all enabled methods.
    Returns: dict with keys: ocr, multimodal, ic, asr (if enabled)
    Applies object filter to all methods if enabled.
    """
    results = {}
    
    # Initialize object filter if needed
    obj_filter = None
    if object_filter_enabled and selected_objects:
        obj_filter = ObjectFilterSearch()
        logger.info(f"[OBJECT FILTER] Enabled with objects: {selected_objects}")
    
    # Multimodal search
    if "multimodal" in enabled_methods:
        multimodel_search = get_multimodel_search()
        clip_res = multimodel_search.search_single_model(query_text, "clip", top_k * 2)
        beit3_res = multimodel_search.search_single_model(query_text, "beit3", top_k * 2)
        bigg_res = multimodel_search.search_single_model(query_text, "bigg", top_k * 2)
        
        # Apply object filter to multimodal results
        if obj_filter:
            clip_res = _apply_object_filter(clip_res, obj_filter, selected_objects)
            beit3_res = _apply_object_filter(beit3_res, obj_filter, selected_objects)
            bigg_res = _apply_object_filter(bigg_res, obj_filter, selected_objects)
        
        # Ensemble multimodal
        multimodal_results = _ensemble_multimodal(clip_res, beit3_res, bigg_res, top_k)
        results["multimodal"] = multimodal_results
        
        # Also store individual model results
        results["clip"] = clip_res[:top_k]
        results["beit3"] = beit3_res[:top_k]
        results["bigg"] = bigg_res[:top_k]
    
    # IC search
    if "ic" in enabled_methods:
        ic_results = get_ic_search().search(query_text, top_k)
        
        # Apply object filter
        if obj_filter:
            ic_results = _apply_object_filter(ic_results, obj_filter, selected_objects)
        
        # Scale IC scores
        if ic_results:
            raw_scores = [r["score"] for r in ic_results]
            scaled_scores = ScoreScaler.min_max_scale(raw_scores)
            for r, scaled in zip(ic_results, scaled_scores):
                r["score"] = scaled
        results["ic"] = ic_results
    
    # ASR search (uses original Vietnamese if applicable)
    if "asr" in enabled_methods:
        asr_results = get_asr_ocr_search().search_asr(query_text, top_k)
        
        # Apply object filter
        if obj_filter:
            asr_results = _apply_object_filter(asr_results, obj_filter, selected_objects)
        
        if asr_results:
            raw_scores = [r["score"] for r in asr_results]
            scaled_scores = ScoreScaler.bm25_scale(raw_scores)
            for r, scaled in zip(asr_results, scaled_scores):
                r["score"] = scaled
        results["asr"] = asr_results
    
    # OCR search
    if "ocr" in enabled_methods:
        ocr_query = ocr_text if ocr_text else query_text
        ocr_results = get_asr_ocr_search().search_ocr(ocr_query, top_k)
        
        # Apply object filter
        if obj_filter:
            ocr_results = _apply_object_filter(ocr_results, obj_filter, selected_objects)
        
        if ocr_results:
            raw_scores = [r["score"] for r in ocr_results]
            scaled_scores = ScoreScaler.bm25_scale(raw_scores)
            for r, scaled in zip(ocr_results, scaled_scores):
                r["score"] = scaled
        results["ocr"] = ocr_results
    
    # Ensemble all methods for this query
    method_results = {k: v for k, v in results.items() if k in enabled_methods}
    ensemble_result = _ensemble_methods(method_results, top_k)
    results["ensemble"] = ensemble_result
    
    return results


async def _search_single_query_async(query_text: str, enabled_methods: set, top_k: int, ocr_text: str = None, object_filter_enabled: bool = False, selected_objects: List[str] = None):
    """Async wrapper for _search_single_query to enable parallel execution"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _search_executor,
        _search_single_query,
        query_text,
        enabled_methods,
        top_k,
        ocr_text,
        object_filter_enabled,
        selected_objects
    )


def _apply_object_filter(results: List, obj_filter: ObjectFilterSearch, selected_objects: List[str]) -> List:
    """Apply object filter to search results"""
    if not results or not obj_filter or not selected_objects:
        return results
    
    # Extract IDs
    ids = [str(r["id"]) for r in results]
    
    # Filter IDs
    filtered_ids = obj_filter.filter(ids, selected_objects)
    filtered_id_set = set(filtered_ids)
    
    # Keep only filtered results
    filtered_results = [r for r in results if str(r["id"]) in filtered_id_set]
    
    logger.info(f"[OBJECT FILTER] Before: {len(results)}, After: {len(filtered_results)}")
    
    return filtered_results


def _ensemble_multimodal(clip_res, beit3_res, bigg_res, top_k):
    """Ensemble CLIP + BEiT3 + BIGG"""
    clip_z = ScoreScaler.z_score_normalize([r["score"] for r in clip_res])
    beit3_z = ScoreScaler.z_score_normalize([r["score"] for r in beit3_res])
    bigg_z = ScoreScaler.z_score_normalize([r["score"] for r in bigg_res])
    
    ensemble = defaultdict(float)
    meta = {}
    
    for r, z in zip(clip_res, clip_z):
        ensemble[r["id"]] += z * 0.25
        if r["id"] not in meta:
            meta[r["id"]] = r
    
    for r, z in zip(beit3_res, beit3_z):
        ensemble[r["id"]] += z * 0.50
        if r["id"] not in meta:
            meta[r["id"]] = r
    
    for r, z in zip(bigg_res, bigg_z):
        ensemble[r["id"]] += z * 0.25
        if r["id"] not in meta:
            meta[r["id"]] = r
    
    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)[:top_k]
    final_scores = ScoreScaler.min_max_scale([s for _, s in ranked])
    
    results = []
    for (rid, _), s in zip(ranked, final_scores):
        item = meta.get(rid, {}).copy()
        item["score"] = s
        item["id"] = rid
        results.append(item)
    
    return results


def _ensemble_methods(method_results: Dict[str, List], top_k: int):
    """Ensemble results from multiple methods (all scores already in [0,1])"""
    ensemble = defaultdict(float)
    meta = {}
    
    num_methods = len(method_results)
    if num_methods == 0:
        return []
    
    weight = 1.0 / num_methods
    
    for method_name, results in method_results.items():
        if not results:
            continue
        for r in results:
            rid = r["id"]
            ensemble[rid] += r["score"] * weight
            if rid not in meta:
                meta[rid] = r
    
    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    final_results = []
    for rid, score in ranked:
        item = meta.get(rid, {}).copy()
        item["score"] = score
        item["id"] = rid
        final_results.append(item)
    
    return final_results


def _ensemble_cross_queries(q0_results, q1_results, q2_results, top_k):
    """Ensemble results from Q0, Q1, Q2 for a specific method"""
    ensemble = defaultdict(float)
    meta = {}
    
    for r in q0_results:
        ensemble[r["id"]] += r["score"] / 3.0
        if r["id"] not in meta:
            meta[r["id"]] = r
    
    for r in q1_results:
        ensemble[r["id"]] += r["score"] / 3.0
        if r["id"] not in meta:
            meta[r["id"]] = r
    
    for r in q2_results:
        ensemble[r["id"]] += r["score"] / 3.0
        if r["id"] not in meta:
            meta[r["id"]] = r
    
    ranked = sorted(ensemble.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    results = []
    for rid, score in ranked:
        item = meta.get(rid, {}).copy()
        item["score"] = score
        item["id"] = rid
        results.append(item)
    
    return results


@router.post("/search", response_model=AugmentedSearchResponse)
async def search_with_augmentation(request: SearchRequest):
    """
    Search endpoint with automatic query augmentation.
    Always generates Q0 (original), Q1, Q2 (augmented), Q3 (ensemble).
    """
    start_time = time.time()
    top_k = request.top_k or settings.DEFAULT_TOP_K
    
    try:
        # Determine enabled methods from queries
        queries = request.queries or []
        enabled_methods = set()
        
        if queries:
            for q_section in queries:
                toggles = q_section.toggles or {}
                if toggles.get("multimodal"):
                    enabled_methods.add("multimodal")
                if toggles.get("ic"):
                    enabled_methods.add("ic")
                if toggles.get("asr"):
                    enabled_methods.add("asr")
                if toggles.get("ocr"):
                    enabled_methods.add("ocr")
        
        if not enabled_methods:
            enabled_methods = {"multimodal", "ic"}  # Default
        
        logger.info(f"[AUGMENTED SEARCH] Enabled methods: {enabled_methods}")
        
        # Get original query
        query_text = request.query
        
        # Translate Vietnamese to English if NOT using ASR
        if "asr" not in enabled_methods:
            translator = get_translator()
            if translator.is_vietnamese(query_text):
                query_text = translator.translate(query_text)
                logger.info(f"[TRANSLATE] '{request.query}' → '{query_text}'")
        
        # Generate Q1, Q2 using Gemini
        augmentor = get_query_augmentor()
        q1_text, q2_text = augmentor.augment_query(query_text)
        
        # Get OCR text if provided
        ocr_text = None
        if queries and "ocr" in enabled_methods:
            for q_section in queries:
                if q_section.toggles.get("ocr") and q_section.ocrText:
                    ocr_text = q_section.ocrText
                    break
        
        # Get object filter settings
        object_filter_enabled = False
        selected_objects = []
        if request.filters:
            object_filter_enabled = request.filters.get("objectFilter", False)
            selected_objects = request.filters.get("selectedObjects", [])
        
        if object_filter_enabled and selected_objects:
            logger.info(f"[AUGMENTED SEARCH] Object filter enabled: {selected_objects}")
        
        # Search Q0, Q1, Q2 in PARALLEL (3x faster!)
        logger.info(f"[AUGMENTED SEARCH] Parallel search: Q0='{query_text}', Q1='{q1_text}', Q2='{q2_text}'")
        
        q0_methods, q1_methods, q2_methods = await asyncio.gather(
            _search_single_query_async(query_text, enabled_methods, top_k, ocr_text, object_filter_enabled, selected_objects),
            _search_single_query_async(q1_text, enabled_methods, top_k, ocr_text, object_filter_enabled, selected_objects),
            _search_single_query_async(q2_text, enabled_methods, top_k, ocr_text, object_filter_enabled, selected_objects)
        )
        
        logger.info(f"[AUGMENTED SEARCH] Parallel search completed")
        
        # Build Q3: ensemble across queries for each method
        q3_methods = {}
        
        for method in enabled_methods:
            if method in q0_methods and method in q1_methods and method in q2_methods:
                q3_methods[f"{method}_ensemble"] = _ensemble_cross_queries(
                    q0_methods[method],
                    q1_methods[method],
                    q2_methods[method],
                    top_k
                )
        
        # Final ensemble of ensemble
        ensemble_of_ensemble = _ensemble_methods(
            {k: v for k, v in q3_methods.items()},
            top_k
        )
        q3_methods["ensemble_of_ensemble"] = ensemble_of_ensemble
        
        # Build response
        response = AugmentedSearchResponse(
            query_0={
                "text": query_text,
                "methods": q0_methods
            },
            query_1={
                "text": q1_text,
                "methods": q1_methods
            },
            query_2={
                "text": q2_text,
                "methods": q2_methods
            },
            query_3={
                "methods": q3_methods
            },
            total=len(ensemble_of_ensemble),
            original_query=request.query,
            method=request.method
        )
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[AUGMENTED SEARCH] Completed in {duration_ms:.2f}ms")
        
        return response
        
    except Exception as exc:
        logger.error(f"[AUGMENTED SEARCH] Error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search error: {exc}")
